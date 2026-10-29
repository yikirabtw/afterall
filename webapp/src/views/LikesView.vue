<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api, assetUrl } from '../api/client'
import { errorMessage } from '../api/errors'
import type { LikesInfo, Match, Person, ReactionKind } from '../api/types'
import MatchOverlay from '../components/MatchOverlay.vue'
import PageHeader from '../components/PageHeader.vue'
import PersonCard from '../components/PersonCard.vue'
import PlanBadge from '../components/PlanBadge.vue'
import WireCubes from '../components/WireCubes.vue'
import { formatPeople } from '../format'
import { router } from '../router'
import { shopTab } from '../stores/ui'
import { haptic } from '../telegram'

// «Кто лайкнул»: бесплатно — только число (сервер не присылает ни имён, ни фото),
// с Plus и Premium — сами люди: открыть анкету и ответить ♥ (сразу мэтч) или ✕
const FREE_TEASER_TILES = 6

const likes = ref<LikesInfo | null>(null)
const loading = ref(true)
const error = ref('')
const opened = ref<Person | null>(null)
const busy = ref(false)
const newMatch = ref<Match | null>(null)

const locked = computed(() => likes.value !== null && likes.value.people === null)
const teaser = computed(() => Math.min(likes.value?.count ?? 0, FREE_TEASER_TILES))

async function load() {
  loading.value = true
  error.value = ''
  try {
    likes.value = await api.likes()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function open(person: Person) {
  haptic.tap()
  opened.value = person
}

async function answer(kind: ReactionKind) {
  const person = opened.value
  if (!person || busy.value || !likes.value?.people) return
  busy.value = true
  haptic.tap()
  try {
    const result = await api.react(person.user_id, kind)
    likes.value.people = likes.value.people.filter((item) => item.user_id !== person.user_id)
    likes.value.count -= 1
    opened.value = null
    if (result.match) {
      newMatch.value = result.match
      haptic.success()
    }
  } catch (e) {
    error.value = errorMessage(e)
    haptic.error()
  } finally {
    busy.value = false
  }
}

function toPlans() {
  haptic.tap()
  shopTab.value = 'plans'
  void router.push('/shop')
}

onMounted(load)
</script>

<template>
  <main class="page">
    <PageHeader title="Тебя лайкнули" />

    <div v-if="loading" class="center"><span class="dots-loader"><i /><i /><i /></span></div>
    <p v-else-if="error && !likes" class="error-text center">
      {{ error }}
      <button class="btn btn-ghost" type="button" @click="load">Повторить</button>
    </p>

    <template v-else-if="likes">
      <div v-if="likes.count === 0" class="empty">
        <WireCubes class="empty__art" />
        <p class="empty__title">Пока никто</p>
        <p class="hint">Добавь фото и пару слов о себе — так тебя чаще замечают в ленте.</p>
      </div>

      <template v-else>
        <p class="count"><b>{{ formatPeople(likes.count) }}</b> {{ likes.count === 1 ? 'поставил' : 'поставили' }} тебе ♥</p>

        <!-- Бесплатно: размытые плитки — без чужих данных, просто картинка -->
        <template v-if="locked">
          <div class="grid" aria-hidden="true">
            <span v-for="tile in teaser" :key="tile" class="tile tile--locked" :style="{ '--hue': tile * 47 }">
              <span class="tile__photo tile__photo--blur" />
              <svg class="tile__lock" viewBox="0 0 24 24" width="22" height="22">
                <path d="M7 11V8a5 5 0 0 1 10 0v3M6 11h12v9H6z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
              </svg>
            </span>
          </div>
          <section class="card card--lit upsell">
            <b class="upsell__title">Посмотри, кто это</b>
            <p class="hint">Список тех, кто лайкнул, — с Plus и Premium. Ответишь ♥ — сразу мэтч.</p>
            <p class="hint">Бесплатно они тоже есть в ленте — листай, и вы встретитесь.</p>
            <button class="btn btn-primary upsell__btn" type="button" @click="toPlans">К подпискам</button>
          </section>
        </template>

        <div v-else class="grid rise-in">
          <button v-for="person in likes.people" :key="person.user_id" class="tile" type="button" @click="open(person)">
            <img v-if="person.photos[0]" class="tile__photo" :src="assetUrl(person.photos[0].url)" alt="" />
            <span v-else class="tile__photo tile__photo--initial">{{ person.display_name.charAt(0).toUpperCase() }}</span>
            <span class="tile__match">{{ person.compatibility }}%</span>
            <span class="tile__name">
              {{ person.display_name }}<template v-if="person.age !== null">, {{ person.age }}</template>
              <PlanBadge :plan="person.plan" />
            </span>
          </button>
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
      </template>
    </template>

    <!-- Анкета целиком: ответить ♥ или ✕ -->
    <Teleport to="body">
      <Transition name="sheet">
        <div v-if="opened" class="viewer theme-dark" role="dialog" :aria-label="opened.display_name">
          <button class="viewer__close" type="button" aria-label="Закрыть" @click="opened = null">✕</button>
          <div class="viewer__card">
            <PersonCard :person="opened" />
          </div>
          <div class="viewer__actions">
            <button class="round round--skip" type="button" aria-label="Дальше" :disabled="busy" @click="answer('skip')">
              <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true">
                <path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
              </svg>
            </button>
            <button class="round round--like" type="button" aria-label="Нравится" :disabled="busy" @click="answer('like')">
              <svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true">
                <path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" fill="currentColor" />
              </svg>
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>

    <MatchOverlay v-if="newMatch" :match="newMatch" @close="newMatch = null" />
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

.count {
  margin: 0 0 14px;
  font-size: 15px;
}

.count b {
  font-family: var(--font-pixel);
  font-size: 22px;
  font-weight: 400;
  text-shadow: 0 0 10px rgb(var(--glow-rgb) / 0.4);
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

@media (min-width: 520px) {
  .grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.tile {
  position: relative;
  display: block;
  aspect-ratio: 3 / 4;
  overflow: hidden;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--raised);
  color: #fff;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: transform 0.12s ease;
}

.tile:active {
  transform: scale(0.97);
}

.tile__photo {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.tile__photo--initial {
  display: grid;
  place-items: center;
  background: var(--g-200);
  color: var(--text);
  font-family: var(--font-pixel);
  font-size: 44px;
}

/* Затемнение снизу — под имя */
.tile::after {
  content: '';
  position: absolute;
  inset: 45% 0 0;
  background: linear-gradient(to top, rgb(0 0 0 / 0.8), transparent);
  pointer-events: none;
}

.tile__name {
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: 10px;
  z-index: 1;
  overflow: hidden;
  font-family: var(--font-title);
  font-size: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tile__match {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 1;
  padding: 2px 7px;
  border: 1px solid rgb(255 255 255 / 0.35);
  border-radius: 6px;
  background: rgb(0 0 0 / 0.55);
  font-family: var(--font-pixel);
  font-size: 13px;
}

/* Бесплатно: абстрактные размытые пятна — без чужих фото */
.tile--locked {
  cursor: default;
}

.tile__photo--blur {
  background:
    radial-gradient(circle at 35% 30%, hsl(var(--hue) 30% 55% / 0.9), transparent 55%),
    radial-gradient(circle at 70% 75%, hsl(calc(var(--hue) + 90) 25% 40% / 0.9), transparent 60%),
    var(--g-200);
  filter: blur(14px) saturate(0.6);
  transform: scale(1.2);
}

.tile__lock {
  position: absolute;
  top: 50%;
  left: 50%;
  z-index: 1;
  transform: translate(-50%, -50%);
  color: #fff;
  filter: drop-shadow(0 0 6px rgb(255 255 255 / 0.7));
}

.upsell {
  margin-top: 16px;
}

.upsell__title {
  font-family: var(--font-title);
  font-size: 18px;
  font-weight: 400;
}

.upsell__btn {
  width: 100%;
  margin-top: 14px;
}

/* --- Анкета целиком --- */

.viewer {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  flex-direction: column;
  padding: 56px 16px calc(20px + var(--safe-bottom));
  background: rgb(0 0 0 / 0.92);
}

.viewer__close {
  position: absolute;
  top: 12px;
  right: 16px;
  width: 36px;
  height: 36px;
  border: 1px solid rgb(255 255 255 / 0.25);
  border-radius: 10px;
  background: transparent;
  color: #fff;
  font-size: 16px;
  cursor: pointer;
}

.viewer__card {
  position: relative;
  flex: 1;
  min-height: 0;
  width: 100%;
  max-width: 528px;
  margin: 0 auto;
}

.viewer__card > :deep(*) {
  position: absolute;
  inset: 0;
}

.viewer__actions {
  display: flex;
  justify-content: center;
  gap: 28px;
  padding-top: 14px;
}

.round {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  border: 1px solid var(--line-strong);
  border-radius: 20px;
  cursor: pointer;
  transition: transform 0.08s ease;
}

.round:active {
  transform: scale(0.92);
}

.round:disabled {
  opacity: 0.6;
}

.round--skip {
  background: var(--card);
  color: var(--text);
}

.round--like {
  border-color: var(--accent);
  background: var(--accent);
  color: var(--accent-ink);
  box-shadow: var(--glow-1), var(--glow-2);
}
</style>
