<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { ApiError, api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { LobbyDetail, LobbyMember, MemberDecision } from '../api/types'
import PageHeader from '../components/PageHeader.vue'
import { formatStart } from '../format'
import { LOBBY_STATUS_LABELS, PLAY_STYLE_LABELS } from '../labels'
import { ACTIVE_STATUSES, faceitLabel, gameTitle, rankName, rankRangeLabel, roleNames } from '../lobby'
import { confirmAction, haptic, openExternal } from '../telegram'

const props = defineProps<{ id: number }>()

const lobby = ref<LobbyDetail | null>(null)
const loading = ref(true)
const loadError = ref('')
const busy = ref(false)
const actionError = ref('')
const note = ref('')
const copied = ref<string | null>(null)

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    lobby.value = await api.lobby(props.id)
  } catch (e) {
    loadError.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)

const isActive = computed(() => (lobby.value ? ACTIVE_STATUSES.includes(lobby.value.status) : false))
const pending = computed(() => lobby.value?.members.filter((member) => member.status === 'pending') ?? [])
const accepted = computed(() => lobby.value?.members.filter((member) => member.status === 'accepted') ?? [])
// Создатель тоже «принят» — ему видны контакты своих участников
const inParty = computed(() => lobby.value?.my_status === 'accepted')
const canApply = computed(() => {
  const current = lobby.value
  return Boolean(
    current && !current.is_owner && current.status === 'open' && (current.my_status === null || current.my_status === 'left'),
  )
})

const banner = computed<{ text: string; tone: 'accent' | 'warm' | 'muted' } | null>(() => {
  const current = lobby.value
  if (!current) return null
  if (current.status === 'cancelled') return { text: 'Пати отменена.', tone: 'muted' }
  if (current.status === 'expired') return { text: 'Пати закончилась.', tone: 'muted' }
  if (current.is_owner) {
    if (pending.value.length) return { text: `Новых откликов: ${pending.value.length}. Реши, кого берёшь.`, tone: 'warm' }
    return current.status === 'full' ? { text: 'Пати собрана — все места заняты.', tone: 'accent' } : null
  }
  switch (current.my_status) {
    case 'pending':
      return { text: 'Отклик отправлен — ждём ответа создателя.', tone: 'warm' }
    case 'accepted':
      return { text: 'Тебя приняли! Ниже контакты — договаривайтесь и играйте.', tone: 'accent' }
    case 'declined':
      return { text: 'Создатель отклонил отклик.', tone: 'muted' }
    case 'kicked':
      return { text: 'Создатель убрал тебя из этой пати.', tone: 'muted' }
  }
  return current.status === 'full' ? { text: 'Все места уже заняты.', tone: 'muted' } : null
})

const contactLabel = computed(() => {
  const link = lobby.value?.contact_link ?? ''
  return /discord/.test(link) ? 'Перейти в Discord' : 'Перейти в чат'
})

function memberMeta(member: LobbyMember): string[] {
  const gameId = lobby.value?.game_id ?? null
  const parts: string[] = []
  const rank = rankName(gameId, member.rank_id)
  if (rank) parts.push(rank)
  if (member.faceit_elo !== null) parts.push(faceitLabel(member.faceit_elo))
  parts.push(...roleNames(gameId, member.role_ids))
  if (!member.has_mic) parts.push('без микрофона')
  if (member.reputation) parts.push(`репутация ${member.reputation > 0 ? '+' : ''}${member.reputation}`)
  return parts
}

/** Каждое действие возвращает свежую карточку пати — просто подменяем её */
async function run(action: () => Promise<LobbyDetail>): Promise<boolean> {
  busy.value = true
  actionError.value = ''
  try {
    lobby.value = await action()
    haptic.success()
    return true
  } catch (e) {
    actionError.value = errorMessage(e)
    haptic.error()
    // Пати могли отменить, пока экран был открыт — показываем, что с ней сейчас
    if (e instanceof ApiError && e.status === 409) await load()
    return false
  } finally {
    busy.value = false
  }
}

async function apply() {
  if (await run(() => api.apply(props.id, note.value.trim() || null))) note.value = ''
}

async function leave() {
  const question =
    lobby.value?.my_status === 'pending'
      ? 'Отозвать отклик?'
      : 'Выйти из пати? Вернуться можно будет, только откликнувшись заново.'
  if (await confirmAction(question)) await run(() => api.leave(props.id))
}

async function decide(member: LobbyMember, decision: MemberDecision) {
  // Имя в кавычках: имена не склоняются, а «Убрать Миша» звучит коряво
  if (decision === 'kick' && !(await confirmAction(`Убрать «${member.display_name}» из пати? Вернуться в неё уже не получится.`))) {
    return
  }
  await run(() => api.decide(props.id, member.user_id, decision))
}

async function cancel() {
  if (await confirmAction('Отменить пати? Она пропадёт из ленты, а участники увидят, что её отменили.')) {
    await run(() => api.cancelLobby(props.id))
  }
}

function openChat() {
  haptic.tap()
  if (lobby.value?.contact_link) openExternal(lobby.value.contact_link)
}

async function copyDiscord(tag: string) {
  try {
    await navigator.clipboard.writeText(tag)
    copied.value = tag
    haptic.success()
  } catch {
    copied.value = null
  }
}
</script>

<template>
  <main class="page">
    <PageHeader title="Пати" />

    <div v-if="loading && !lobby" class="center"><div class="spinner" /></div>
    <div v-else-if="loadError && !lobby" class="empty">
      <p class="empty__title">Не получилось открыть пати</p>
      <p class="hint">{{ loadError }}</p>
      <button class="btn btn-ghost" type="button" @click="load">Повторить</button>
    </div>

    <template v-else-if="lobby">
      <section class="card hero">
        <header class="hero__top">
          <span class="hero__game">{{ gameTitle(lobby) }}</span>
          <span class="hero__when">{{ formatStart(lobby.starts_at) }}</span>
        </header>
        <h2 class="hero__title">{{ lobby.title }}</h2>
        <p v-if="lobby.description" class="hero__description">{{ lobby.description }}</p>

        <div class="chips hero__tags">
          <span v-if="LOBBY_STATUS_LABELS[lobby.status]" class="badge">{{ LOBBY_STATUS_LABELS[lobby.status] }}</span>
          <span v-if="rankRangeLabel(lobby)" class="badge">{{ rankRangeLabel(lobby) }}</span>
          <span v-if="lobby.need_mic" class="badge">С микрофоном</span>
          <span v-if="lobby.play_style" class="badge">{{ PLAY_STYLE_LABELS[lobby.play_style] }}</span>
          <span v-if="lobby.language !== 'ru'" class="badge">{{ lobby.language.toUpperCase() }}</span>
        </div>

        <footer class="hero__bottom">
          <span class="hint">Собирает {{ lobby.is_owner ? 'ты' : lobby.owner.display_name }}</span>
          <span class="slots">
            <span class="slots__dots" aria-hidden="true">
              <i v-for="n in lobby.slots_total" :key="n" :class="{ taken: n <= lobby.slots_taken }" />
            </span>
            {{ lobby.slots_taken }}/{{ lobby.slots_total }}
          </span>
        </footer>
      </section>

      <p v-if="banner" class="banner" :class="`banner--${banner.tone}`">{{ banner.text }}</p>

      <section v-if="inParty && lobby.contact_link && isActive" class="card contact">
        <div>
          <b>Где собираемся</b>
          <p class="hint">{{ lobby.contact_link.replace(/^https:\/\//, '') }}</p>
        </div>
        <button class="btn btn-primary btn-small" type="button" @click="openChat">{{ contactLabel }}</button>
      </section>

      <template v-if="lobby.is_owner && pending.length">
        <h3 class="section-title">Отклики</h3>
        <ul class="card members">
          <li v-for="member in pending" :key="member.user_id" class="member">
            <div class="member__avatar" aria-hidden="true">{{ member.display_name.charAt(0).toUpperCase() }}</div>
            <div class="member__body">
              <b class="member__name">{{ member.display_name }}</b>
              <p v-if="memberMeta(member).length" class="hint member__meta">{{ memberMeta(member).join(' · ') }}</p>
              <p v-if="member.note" class="member__note">«{{ member.note }}»</p>
              <div class="member__decision">
                <button class="btn btn-primary btn-small" type="button" :disabled="busy" @click="decide(member, 'accept')">
                  Принять
                </button>
                <button class="btn btn-ghost btn-small" type="button" :disabled="busy" @click="decide(member, 'decline')">
                  Отклонить
                </button>
              </div>
            </div>
          </li>
        </ul>
      </template>

      <template v-if="accepted.length">
        <h3 class="section-title">В пати</h3>
        <ul class="card members">
          <li v-for="member in accepted" :key="member.user_id" class="member">
            <div class="member__avatar" aria-hidden="true">{{ member.display_name.charAt(0).toUpperCase() }}</div>
            <div class="member__body">
              <b class="member__name">
                {{ member.display_name }}
                <span v-if="member.is_owner" class="badge badge--accent">Создатель</span>
              </b>
              <p v-if="memberMeta(member).length" class="hint member__meta">{{ memberMeta(member).join(' · ') }}</p>
              <div v-if="member.username || member.discord_tag" class="chips member__contacts">
                <button
                  v-if="member.username"
                  type="button"
                  class="chip chip--small"
                  @click="openExternal(`https://t.me/${member.username}`)"
                >
                  @{{ member.username }}
                </button>
                <button
                  v-if="member.discord_tag"
                  type="button"
                  class="chip chip--small"
                  @click="copyDiscord(member.discord_tag)"
                >
                  {{ copied === member.discord_tag ? 'Скопировано' : `Discord: ${member.discord_tag}` }}
                </button>
              </div>
            </div>
            <button
              v-if="lobby.is_owner && !member.is_owner && isActive"
              class="btn btn-ghost btn-small member__kick"
              type="button"
              :disabled="busy"
              @click="decide(member, 'kick')"
            >
              Убрать
            </button>
          </li>
        </ul>
      </template>

      <template v-if="canApply">
        <label class="field apply">
          <span class="field__label">Сообщение создателю — по желанию</span>
          <textarea
            v-model="note"
            class="input"
            maxlength="200"
            placeholder="Например: играю на саппорте, есть микрофон, свободен после 20:00"
          />
        </label>
      </template>

      <p v-if="actionError" class="error-text">{{ actionError }}</p>

      <div v-if="isActive" class="actions">
        <button v-if="canApply" class="btn btn-primary" type="button" :disabled="busy" @click="apply">Откликнуться</button>
        <button v-else-if="lobby.my_status === 'pending'" class="btn btn-ghost" type="button" :disabled="busy" @click="leave">
          Отозвать отклик
        </button>
        <button
          v-else-if="lobby.my_status === 'accepted' && !lobby.is_owner"
          class="btn btn-ghost"
          type="button"
          :disabled="busy"
          @click="leave"
        >
          Выйти из пати
        </button>
        <button v-else-if="lobby.is_owner" class="btn btn-ghost btn-danger" type="button" :disabled="busy" @click="cancel">
          Отменить пати
        </button>
      </div>
    </template>
  </main>
</template>

<style scoped>
.center {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

.hero__top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
}

.hero__game {
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.hero__when {
  color: var(--warm);
}

.hero__title {
  margin: 8px 0 0;
  font-size: 22px;
  font-weight: 800;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.hero__description {
  margin: 8px 0 0;
  color: var(--hint);
  white-space: pre-line;
  overflow-wrap: anywhere;
}

.hero__tags {
  margin-top: 12px;
  gap: 6px;
}

.hero__tags:empty {
  display: none;
}

.hero__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}

.hero__bottom .hint {
  margin: 0;
}

.slots {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.slots__dots {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 3px;
  max-width: 120px;
}

.slots__dots i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1.5px solid var(--hint);
}

.slots__dots i.taken {
  border-color: var(--accent);
  background: var(--accent);
}

.banner {
  margin: 12px 0 0;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  font-weight: 600;
}

.banner--accent {
  background: var(--accent-soft);
}

.banner--warm {
  background: var(--warm-soft);
}

.banner--muted {
  background: var(--line);
}

.contact {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
}

.contact .hint {
  margin: 2px 0 0;
  overflow-wrap: anywhere;
}

.contact .btn {
  flex: none;
}

.members {
  margin: 0;
  padding: 4px 16px;
  list-style: none;
}

.member {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
}

.member + .member {
  border-top: 1px solid var(--line);
}

.member__avatar {
  flex: none;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--accent), var(--warm));
  color: var(--accent-ink);
  font-weight: 900;
}

.member__body {
  flex: 1;
  min-width: 0;
}

.member__name {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-wrap: anywhere;
}

.member__meta {
  margin: 2px 0 0;
}

.member__note {
  margin: 6px 0 0;
  font-size: 15px;
  overflow-wrap: anywhere;
}

.member__decision {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.member__contacts {
  margin-top: 8px;
  gap: 6px;
}

.member__kick {
  flex: none;
  color: var(--danger);
}

.chip--small {
  padding: 5px 11px;
  font-size: 14px;
}

.apply {
  margin-top: 16px;
}

.btn-danger {
  color: var(--danger);
}
</style>
