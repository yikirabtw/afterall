<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Match, PeopleParams, Person, ReactionKind } from '../api/types'
import MatchOverlay from '../components/MatchOverlay.vue'
import PeopleFilters from '../components/PeopleFilters.vue'
import PersonCard from '../components/PersonCard.vue'
import { haptic } from '../telegram'

const SWIPE_THRESHOLD = 90 // px — дальше этого отпущенная анкета улетает
const FLY_OUT_MS = 220
const FILTERS_KEY = 'people-filters'

const queue = ref<Person[]>([])
const loading = ref(false)
const exhausted = ref(false) // сервер больше никого не нашёл
const error = ref('')
const busy = ref(false)
const matchesCount = ref(0)
const newMatch = ref<Match | null>(null)

const filtersOpen = ref(false)
const filters = ref<PeopleParams>(loadFilters())
const filtersActive = computed(() => Object.values(filters.value).some((value) => value !== undefined && value !== false))

const current = computed(() => queue.value[0] ?? null)
const next = computed(() => queue.value[1] ?? null)

// Фильтры запоминаем на телефоне; если хранилище недоступно — просто начинаем без них
function loadFilters(): PeopleParams {
  try {
    return JSON.parse(localStorage.getItem(FILTERS_KEY) ?? '{}') as PeopleParams
  } catch {
    return {}
  }
}

function saveFilters(value: PeopleParams) {
  try {
    localStorage.setItem(FILTERS_KEY, JSON.stringify(value))
  } catch {
    // не страшно — фильтры просто не запомнятся
  }
}

async function loadMore() {
  if (loading.value || exhausted.value) return
  loading.value = true
  error.value = ''
  try {
    const people = await api.people({ ...filters.value, limit: 10 })
    const known = new Set(queue.value.map((person) => person.user_id))
    const fresh = people.filter((person) => !known.has(person.user_id))
    queue.value.push(...fresh)
    if (fresh.length === 0) exhausted.value = true
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function reload() {
  queue.value = []
  exhausted.value = false
  await loadMore()
}

function applyFilters(value: PeopleParams) {
  filters.value = value
  saveFilters(value)
  filtersOpen.value = false
  void reload()
}

onMounted(async () => {
  await loadMore()
  try {
    matchesCount.value = (await api.matches()).length
  } catch {
    // счётчик мэтчей — не главное, лента работает и без него
  }
})

// --- Свайп ---

const dragX = ref(0)
const dragging = ref(false)
let startX = 0
let moved = false

const cardStyle = computed(() => ({
  transform: `translateX(${dragX.value}px) rotate(${dragX.value / 18}deg)`,
  transition: dragging.value ? 'none' : `transform ${FLY_OUT_MS}ms ease`,
}))
const likeOpacity = computed(() => Math.min(Math.max(dragX.value / SWIPE_THRESHOLD, 0), 1))
const skipOpacity = computed(() => Math.min(Math.max(-dragX.value / SWIPE_THRESHOLD, 0), 1))

function onPointerDown(event: PointerEvent) {
  if (busy.value || !current.value) return
  dragging.value = true
  moved = false
  startX = event.clientX
  // Слушаем окно, а не карточку: палец может уйти за её край
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', onPointerUp)
}

function onPointerMove(event: PointerEvent) {
  dragX.value = event.clientX - startX
  if (Math.abs(dragX.value) > 8) moved = true
}

function stopListening() {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerUp)
}

function onPointerUp() {
  stopListening()
  dragging.value = false
  if (dragX.value > SWIPE_THRESHOLD) void decide('like')
  else if (dragX.value < -SWIPE_THRESHOLD) void decide('skip')
  else dragX.value = 0
}

// Если анкету тащили — это свайп, а не нажатие: фото не перелистываем
function onClickCapture(event: MouseEvent) {
  if (moved) {
    event.stopPropagation()
    moved = false
  }
}

onBeforeUnmount(stopListening)

async function decide(kind: ReactionKind) {
  const person = current.value
  if (!person || busy.value) return
  busy.value = true
  haptic.tap()
  dragX.value = kind === 'like' ? window.innerWidth : -window.innerWidth
  try {
    const [result] = await Promise.all([
      api.react(person.user_id, kind),
      new Promise((resolve) => setTimeout(resolve, FLY_OUT_MS)),
    ])
    queue.value.shift()
    if (result.match) {
      newMatch.value = result.match
      matchesCount.value += 1
      haptic.success()
    }
    if (queue.value.length < 3) void loadMore()
  } catch (e) {
    error.value = errorMessage(e)
    haptic.error()
  } finally {
    dragX.value = 0
    busy.value = false
  }
}
</script>

<template>
  <main class="people">
    <header class="page-top people__top">
      <h1 class="page-title">Лента</h1>
      <div class="people__tools">
        <RouterLink to="/matches" class="icon-btn" aria-label="Мэтчи" @click="haptic.tap()">
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
            <path
              d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"
              fill="currentColor"
            />
          </svg>
          <span v-if="matchesCount" class="icon-btn__count">{{ matchesCount }}</span>
        </RouterLink>
        <button class="icon-btn" type="button" aria-label="Фильтры" @click="(filtersOpen = true), haptic.tap()">
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
            <circle cx="12" cy="5" r="2" fill="currentColor" />
            <circle cx="12" cy="12" r="2" fill="currentColor" />
            <circle cx="12" cy="19" r="2" fill="currentColor" />
          </svg>
          <span v-if="filtersActive" class="icon-btn__dot" />
        </button>
      </div>
    </header>

    <section class="deck">
      <PersonCard v-if="next" :key="`under-${next.user_id}`" :person="next" class="deck__under" />
      <div
        v-if="current"
        :key="current.user_id"
        class="deck__top"
        :style="cardStyle"
        @pointerdown="onPointerDown"
        @click.capture="onClickCapture"
      >
        <PersonCard :person="current" />
        <span class="stamp stamp--like" :style="{ opacity: likeOpacity }">Нравится</span>
        <span class="stamp stamp--skip" :style="{ opacity: skipOpacity }">Дальше</span>
      </div>

      <div v-if="!current && loading" class="deck__state"><div class="spinner" /></div>
      <div v-else-if="!current && error" class="deck__state">
        <p class="empty__title">Не получилось загрузить</p>
        <p class="hint">{{ error }}</p>
        <button class="btn btn-ghost" type="button" @click="reload">Повторить</button>
      </div>
      <div v-else-if="!current" class="deck__state">
        <p class="empty__title">Анкеты закончились</p>
        <p class="hint">
          {{ filtersActive ? 'Попробуй ослабить фильтры.' : 'Загляни позже — пропущенные анкеты вернутся через пару дней.' }}
        </p>
        <button v-if="filtersActive" class="btn btn-ghost" type="button" @click="applyFilters({})">Сбросить фильтры</button>
      </div>
    </section>

    <div v-if="current" class="people__actions">
      <button class="round round--skip" type="button" aria-label="Дальше" :disabled="busy" @click="decide('skip')">
        <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true">
          <path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
        </svg>
      </button>
      <button class="round round--like" type="button" aria-label="Нравится" :disabled="busy" @click="decide('like')">
        <svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true">
          <path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" fill="currentColor" />
        </svg>
      </button>
    </div>
    <p v-if="current && error" class="error-text people__error">{{ error }}</p>

    <PeopleFilters :open="filtersOpen" :filters="filters" @apply="applyFilters" @close="filtersOpen = false" />
    <MatchOverlay v-if="newMatch" :match="newMatch" @close="newMatch = null" />
  </main>
</template>

<style scoped>
/* Лента занимает весь экран над нижней навигацией */
.people {
  display: flex;
  flex-direction: column;
  height: var(--tg-viewport-stable-height, 100dvh);
  max-width: 560px;
  margin: 0 auto;
  padding: 12px 16px calc(84px + var(--safe-bottom));
}

.people__top {
  margin: 0 0 12px;
}

.people__tools {
  display: flex;
  gap: 8px;
}

.icon-btn {
  position: relative;
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 50%;
  background: var(--card);
  color: var(--text);
  cursor: pointer;
}

a.icon-btn {
  color: var(--accent);
}

.icon-btn__count {
  position: absolute;
  top: -2px;
  right: -2px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: var(--accent);
  color: var(--accent-ink);
  font-size: 11px;
  font-weight: 800;
  line-height: 18px;
  text-align: center;
}

.icon-btn__dot {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--warm);
}

.deck {
  position: relative;
  flex: 1;
  min-height: 0;
}

.deck__under,
.deck__top {
  position: absolute;
  inset: 0;
}

/* Следующая анкета чуть меньше и ниже — видно, что за этой есть ещё */
.deck__under {
  transform: scale(0.95) translateY(10px);
  opacity: 0.6;
}

.deck__top {
  touch-action: pan-y;
  cursor: grab;
}

.stamp {
  position: absolute;
  top: 28px;
  padding: 6px 14px;
  border: 3px solid;
  border-radius: 10px;
  font-size: 22px;
  font-weight: 900;
  text-transform: uppercase;
  pointer-events: none;
}

.stamp--like {
  left: 20px;
  color: var(--accent);
  transform: rotate(-12deg);
}

.stamp--skip {
  right: 20px;
  color: var(--danger);
  transform: rotate(12deg);
}

.deck__state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 24px;
  text-align: center;
}

.people__actions {
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
  border: 0;
  border-radius: 50%;
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
  color: var(--danger);
}

.round--like {
  background: var(--accent);
  color: var(--accent-ink);
}

.people__error {
  text-align: center;
}
</style>
