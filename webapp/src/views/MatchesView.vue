<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, ApiError, assetUrl } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Match } from '../api/types'
import FuseButton from '../components/FuseButton.vue'
import MatchContacts from '../components/MatchContacts.vue'
import PageHeader from '../components/PageHeader.vue'
import PersonSheet from '../components/PersonSheet.vue'
import PlanBadge from '../components/PlanBadge.vue'
import WireCubes from '../components/WireCubes.vue'
import { refreshUnread } from '../stores/chats'
import { gameById } from '../stores/session'
import { haptic } from '../telegram'

const matches = ref<Match[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    matches.value = await api.matches()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

// Удаление: карточка сразу гаснет, а по-настоящему мэтч удаляется, когда догорит фитиль на кнопке
const leaving = ref(new Set<number>())
const deleteError = ref('')

function markLeaving(match: Match, on: boolean) {
  const next = new Set(leaving.value)
  if (on) next.add(match.user_id)
  else next.delete(match.user_id)
  leaving.value = next
}

async function purge(match: Match) {
  deleteError.value = ''
  try {
    await api.deleteMatch(match.user_id)
  } catch (e) {
    // «Уже нет» — значит, удалил второй человек: результат тот же
    if (!(e instanceof ApiError && e.code === 'match_not_found')) {
      markLeaving(match, false)
      deleteError.value = errorMessage(e)
      return
    }
  }
  matches.value = matches.value.filter((item) => item.user_id !== match.user_id)
  markLeaving(match, false)
  void refreshUnread() // вместе с мэтчем ушёл и личный чат
}

// «⋯» на карточке: пожаловаться или заблокировать — человек сразу пропадает из списка
const sheetFor = ref<Match | null>(null)
const notice = ref('')

function openSheet(match: Match) {
  haptic.tap()
  notice.value = ''
  sheetFor.value = match
}

function onSafetyDone(kind: 'reported' | 'blocked') {
  const match = sheetFor.value!
  sheetFor.value = null
  matches.value = matches.value.filter((item) => item.user_id !== match.user_id)
  notice.value =
    kind === 'reported'
      ? `Жалоба отправлена — «${match.display_name}» больше тебя не увидит.`
      : `Готово — «${match.display_name}» больше тебя не увидит. Вернуть — в профиле → «Заблокированные».`
  void refreshUnread() // его чат тоже пропал
}

onMounted(load)
</script>

<template>
  <main class="page">
    <PageHeader title="Мэтчи" />

    <div v-if="loading" class="center"><div class="spinner" /></div>
    <p v-else-if="error" class="error-text center">
      {{ error }}
      <button class="btn btn-ghost" type="button" @click="load">Повторить</button>
    </p>
    <div v-else-if="matches.length === 0" class="empty">
      <WireCubes class="empty__art" />
      <p class="empty__title">Пока нет мэтчей</p>
      <p class="hint">Ставь ♥ тем, с кем хочешь играть. Если симпатия взаимная — человек появится здесь с контактами.</p>
    </div>
    <template v-else>
      <p v-if="deleteError" class="error-text">{{ deleteError }}</p>
      <p v-if="notice" class="hint notice" role="status">{{ notice }}</p>
      <TransitionGroup tag="ul" name="match-list" class="stack list">
        <li
          v-for="match in matches"
          :key="match.user_id"
          class="card match"
          :class="{ 'match--leaving': leaving.has(match.user_id) }"
        >
          <button class="match__more" type="button" aria-label="Пожаловаться или заблокировать" @click="openSheet(match)">
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <circle cx="5" cy="12" r="1.8" fill="currentColor" />
              <circle cx="12" cy="12" r="1.8" fill="currentColor" />
              <circle cx="19" cy="12" r="1.8" fill="currentColor" />
            </svg>
          </button>
          <span class="match__avatar">
            <img v-if="match.photos[0]" :src="assetUrl(match.photos[0].url)" alt="" />
            <template v-else>{{ match.display_name.charAt(0).toUpperCase() }}</template>
          </span>
          <div class="match__body">
            <b class="match__name">
              {{ match.display_name }}<span v-if="match.age !== null">, {{ match.age }}</span>
              <PlanBadge :plan="match.plan" />
            </b>
            <p v-if="match.main_game_id" class="hint match__game">{{ gameById(match.main_game_id)?.name }}</p>
            <MatchContacts :match="match" class="match__contacts" />
            <FuseButton
              class="match__delete"
              label="Удалить мэтч"
              done-label="Удалено"
              undo-label="Вернуть"
              @commit="markLeaving(match, true)"
              @undo="markLeaving(match, false)"
              @fuse-end="purge(match)"
            />
          </div>
        </li>
      </TransitionGroup>
    </template>

    <PersonSheet
      :open="sheetFor !== null"
      :user-id="sheetFor?.user_id ?? 0"
      :name="sheetFor?.display_name ?? ''"
      @close="sheetFor = null"
      @done="onSafetyDone"
    />
  </main>
</template>

<style scoped>
.center {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0;
  text-align: center;
}

.list {
  position: relative;
  margin: 0;
  padding: 0;
  list-style: none;
}

/* Удалённая карточка уходит, остальные плавно подтягиваются (только transform/opacity) */
.match-list-move,
.match-list-leave-active {
  transition:
    transform 0.32s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.24s ease;
}

.match-list-leave-active {
  position: absolute;
  left: 0;
  right: 0;
}

.match-list-leave-to {
  opacity: 0;
  transform: translateX(-24px) scale(0.97);
}

.match {
  position: relative;
  display: flex;
  gap: 14px;
}

.match__more {
  position: absolute;
  top: 8px;
  right: 8px;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--text-2);
  cursor: pointer;
}

.match__more:active {
  background: var(--raised);
  color: var(--text);
}

.notice {
  margin: 0 0 12px;
}

.match__avatar {
  flex: none;
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  border: 1px solid var(--line-strong);
  border-radius: 16px;
  overflow: hidden;
  background: var(--g-100);
  color: var(--text);
  font-family: var(--font-pixel);
  font-size: 30px;
  text-shadow: 0 0 10px rgb(var(--glow-rgb) / 0.6);
}

.match__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.match__body {
  min-width: 0;
  padding-right: 24px; /* место под «⋯» */
}

.match__name {
  font-family: var(--font-title);
  font-size: 17px;
  overflow-wrap: anywhere;
}

.match__game {
  margin: 2px 0 0;
}

.match__contacts {
  margin-top: 10px;
}

.match__delete {
  margin-top: 8px;
  min-height: 34px;
  padding: 0 12px;
  font-size: 12px;
}

/* Пока горит фитиль — карточка погашена, контакты не нажимаются; кнопка «Вернуть» остаётся яркой */
.match__avatar,
.match__name,
.match__game,
.match__contacts {
  transition:
    opacity 0.25s ease,
    filter 0.25s ease;
}

.match--leaving .match__avatar,
.match--leaving .match__name,
.match--leaving .match__game,
.match--leaving .match__contacts {
  opacity: 0.3;
  filter: grayscale(1);
}

.match--leaving .match__contacts {
  pointer-events: none;
}
</style>
