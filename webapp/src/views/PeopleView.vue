<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'

import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { FeedMode, Match, PeopleParams, Person, ReactionKind } from '../api/types'
import MatchOverlay from '../components/MatchOverlay.vue'
import PeopleFilters from '../components/PeopleFilters.vue'
import PersonCard from '../components/PersonCard.vue'
import WireCubes from '../components/WireCubes.vue'
import { formatPeople } from '../format'
import { FEED_MODES } from '../labels'
import { openFrom, router } from '../router'
import { session, setMe } from '../stores/session'
import { shopTab } from '../stores/ui'
import { haptic } from '../telegram'

// «Нравится» и «Дальше» — только кнопками: свайп по анкете листает её фото, и случайно пролайкать нельзя
const STAMP_DISTANCE = 90 // px полёта карточки, за которые штамп проявляется полностью
const FLY_OUT_MS = 220
const FILTERS_KEY = 'people-filters'

const queue = ref<Person[]>([])
const loading = ref(false)
const exhausted = ref(false) // сервер больше никого не нашёл
const error = ref('')
const busy = ref(false)
const matchesCount = ref(0)
const likesCount = ref(0) // кто лайкнул меня, а я ещё не ответил — плашка над анкетами
const newMatch = ref<Match | null>(null)

const filtersOpen = ref(false)
const filters = ref<PeopleParams>(loadFilters())
// Суженный возраст — тоже фильтр: он хранится на сервере, а не в filters
const ageNarrowed = computed(() => {
  const profile = session.me?.profile
  return profile?.search_age_min != null || profile?.search_age_max != null
})
// Режим «Кого ищу» — не фильтр: он выбирается над лентой и точку на ⋮ не зажигает
const filtersActive = computed(
  () =>
    ageNarrowed.value ||
    Object.entries(filters.value).some(([key, value]) => key !== 'mode' && value !== undefined && value !== false),
)

function setMode(mode: FeedMode | undefined) {
  if (filters.value.mode === mode) return
  haptic.select()
  applyFilters({ ...filters.value, mode })
}

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

// «Сбросить фильтры» из пустой ленты — вместе с возрастом
async function resetFilters() {
  if (ageNarrowed.value) {
    try {
      setMe(await api.saveSearchAge(null, null))
    } catch (e) {
      error.value = errorMessage(e)
      return
    }
  }
  applyFilters({})
}

async function refreshLikes() {
  try {
    likesCount.value = (await api.likes()).count
  } catch {
    // счётчик — не главное, лента работает и без него
  }
}

onMounted(async () => {
  await loadMore()
  try {
    matchesCount.value = (await api.matches()).length
  } catch {
    // счётчик мэтчей — не главное, лента работает и без него
  }
  void refreshLikes()
})

// «Тебя лайкнули» вырастает из плашки
function openLikes(event: MouseEvent) {
  haptic.tap()
  openFrom(event.currentTarget as Element, '/likes', 'morph')
}

// --- Кнопка мэтчей: сердце «бьётся», пока мэтчи есть; новый мэтч — сердце подпрыгивает ---

const POP_MS = 700
const heartPop = ref(false)

// Только при новом мэтче из ленты, а не когда счётчик подгрузился при открытии экрана
async function popHeart() {
  heartPop.value = false
  await nextTick() // снять класс и поставить снова — чтобы анимация проигралась заново
  heartPop.value = true
  window.setTimeout(() => (heartPop.value = false), POP_MS)
}

// Экран мэтчей раскрывается кругом из самой кнопки, «Назад» сворачивает его обратно
function openMatches(event: MouseEvent) {
  haptic.tap()
  openFrom(event.currentTarget as Element, '/matches')
}

// --- Улёт карточки после решения: вправо — «Нравится», влево — «Дальше», со штампом ---

const flyX = ref(0)
const entering = ref(false) // вернувшаяся анкета ставится за левый край без анимации, потом въезжает

const cardStyle = computed(() => ({
  transform: `translateX(${flyX.value}px) rotate(${flyX.value / 18}deg)`,
  transition: entering.value ? 'none' : `transform ${FLY_OUT_MS}ms ease`,
}))

// --- Вернуть пропущенную анкету: Plus — 3 раза в сутки, Premium — без лимита, бесплатно — подсказка ---

const rewindsLeft = ref<number | null>(null) // что ответил сервер после последнего возврата
const rewindHint = ref('')
let hintTimer = 0

const canRewind = computed(() => session.me!.plan.rewinds_per_day !== 0)

function showHint(text: string) {
  rewindHint.value = text
  window.clearTimeout(hintTimer)
  hintTimer = window.setTimeout(() => (rewindHint.value = ''), 5000)
}

async function rewindLast() {
  if (busy.value) return
  haptic.tap()
  if (!canRewind.value) {
    showHint('Вернуть анкету можно с Plus (3 раза в день) и Premium.')
    return
  }
  busy.value = true
  try {
    const result = await api.rewind()
    rewindsLeft.value = result.left
    queue.value = [result.person, ...queue.value.filter((p) => p.user_id !== result.person.user_id)]
    exhausted.value = false
    // Въезд слева — туда, куда анкета улетела при пропуске
    entering.value = true
    flyX.value = -window.innerWidth
    await nextTick()
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        entering.value = false
        flyX.value = 0
      }),
    )
    haptic.success()
  } catch (e) {
    showHint(errorMessage(e))
    haptic.error()
  } finally {
    busy.value = false
  }
}

function openPlans() {
  haptic.tap()
  shopTab.value = 'plans'
  void router.push('/shop')
}
const likeOpacity = computed(() => Math.min(Math.max(flyX.value / STAMP_DISTANCE, 0), 1))
const skipOpacity = computed(() => Math.min(Math.max(-flyX.value / STAMP_DISTANCE, 0), 1))

async function decide(kind: ReactionKind) {
  const person = current.value
  if (!person || busy.value) return
  busy.value = true
  haptic.tap()
  flyX.value = kind === 'like' ? window.innerWidth : -window.innerWidth
  try {
    const [result] = await Promise.all([
      api.react(person.user_id, kind),
      new Promise((resolve) => setTimeout(resolve, FLY_OUT_MS)),
    ])
    queue.value.shift()
    if (result.match) {
      newMatch.value = result.match
      matchesCount.value += 1
      void popHeart()
      haptic.success()
    }
    if (queue.value.length < 3) void loadMore()
    if (likesCount.value > 0) void refreshLikes() // ответил кому-то из лайкнувших — число уменьшится
  } catch (e) {
    error.value = errorMessage(e)
    haptic.error()
  } finally {
    flyX.value = 0
    busy.value = false
  }
}
</script>

<template>
  <main class="people">
    <header class="page-top people__top">
      <h1 class="page-title">Лента</h1>
      <div class="people__tools">
        <button
          class="icon-btn heart-btn"
          :class="{ 'heart-btn--beat': matchesCount > 0, 'heart-btn--pop': heartPop }"
          type="button"
          aria-label="Мэтчи"
          @click="openMatches"
        >
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
            <path
              d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"
              fill="currentColor"
            />
          </svg>
          <span v-if="matchesCount" class="icon-btn__count">{{ matchesCount }}</span>
        </button>
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

    <button v-if="likesCount > 0" class="likes-pill" type="button" @click="openLikes">
      <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
        <path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" fill="currentColor" />
      </svg>
      <span>{{ formatPeople(likesCount) }} {{ likesCount === 1 ? 'лайкнул' : 'лайкнули' }} тебя</span>
      <span class="likes-pill__arrow" aria-hidden="true">›</span>
    </button>

    <!-- «Сегодня мне нужно…»: режим ленты -->
    <div class="chips chips--scroll modes" role="tablist" aria-label="Сегодня мне нужно">
      <button
        v-for="option in FEED_MODES"
        :key="option.label"
        type="button"
        role="tab"
        class="chip"
        :class="{ 'chip--on': filters.mode === option.value }"
        :aria-selected="filters.mode === option.value"
        @click="setMode(option.value)"
      >
        {{ option.label }}
      </button>
    </div>

    <section class="deck">
      <PersonCard v-if="next" :key="`under-${next.user_id}`" :person="next" class="deck__under" />
      <div v-if="current" :key="current.user_id" class="deck__top" :style="cardStyle">
        <PersonCard :person="current" />
        <span class="stamp stamp--like" :style="{ opacity: likeOpacity }">Нравится</span>
        <span class="stamp stamp--skip" :style="{ opacity: skipOpacity }">Дальше</span>
      </div>

      <div v-if="!current && loading" class="deck__state"><span class="dots-loader"><i /><i /><i /></span></div>
      <div v-else-if="!current && error" class="deck__state">
        <p class="empty__title">Не получилось загрузить</p>
        <p class="hint">{{ error }}</p>
        <button class="btn btn-ghost" type="button" @click="reload">Повторить</button>
      </div>
      <div v-else-if="!current" class="deck__state">
        <WireCubes class="deck__cubes" />
        <p class="empty__title">Анкеты закончились</p>
        <p class="hint">
          {{
            filtersActive
              ? 'Попробуй ослабить фильтры.'
              : filters.mode
                ? 'В этом режиме анкеты закончились — посмотри всех.'
                : 'Загляни позже — пропущенные анкеты вернутся через пару дней.'
          }}
        </p>
        <button v-if="filtersActive" class="btn btn-ghost" type="button" @click="resetFilters">Сбросить фильтры</button>
        <button v-else-if="filters.mode" class="btn btn-ghost" type="button" @click="setMode(undefined)">Показать всех</button>
      </div>
    </section>

    <p v-if="rewindHint" class="hint people__hint" role="status">
      {{ rewindHint }}
      <button v-if="!canRewind" class="btn btn-ghost btn-small" type="button" @click="openPlans">К подпискам</button>
    </p>

    <div class="people__actions">
      <button
        class="round round--small round--rewind"
        :class="{ 'round--locked': !canRewind }"
        type="button"
        aria-label="Вернуть пропущенную анкету"
        :disabled="busy"
        @click="rewindLast"
      >
        <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
          <path
            d="M9 14L4 9l5-5M4 9h10.5a5.5 5.5 0 0 1 0 11H11"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        <span v-if="rewindsLeft !== null" class="round__count">{{ rewindsLeft }}</span>
      </button>
      <button v-if="current" class="round round--skip" type="button" aria-label="Дальше" :disabled="busy" @click="decide('skip')">
        <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true">
          <path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
        </svg>
      </button>
      <button v-if="current" class="round round--like" type="button" aria-label="Нравится" :disabled="busy" @click="decide('like')">
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

.modes {
  flex: none;
  margin-bottom: 10px;
}

.modes .chip {
  padding: 6px 12px;
  font-size: 14px;
}

/* «N человек лайкнули тебя» — над анкетами, светится, пока есть кому ответить */
.likes-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 40px;
  margin: 0 0 10px;
  padding: 0 14px;
  border: 1px solid var(--line-strong);
  border-radius: 12px;
  background: var(--card);
  box-shadow: 0 0 14px rgb(var(--glow-rgb) / 0.12), var(--edge-light);
  color: var(--text);
  font-family: var(--font-display);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
}

.likes-pill svg {
  flex: none;
  filter: drop-shadow(0 0 5px rgb(var(--glow-rgb) / 0.7));
}

.likes-pill__arrow {
  margin-left: auto;
  font-size: 18px;
  color: var(--text-2);
}

/* Иконки-плитки — как в наборе виджетов */
.icon-btn {
  position: relative;
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
  box-shadow: var(--edge-light);
  color: var(--text);
  cursor: pointer;
}

.icon-btn:active {
  box-shadow: var(--glow-1);
}

.icon-btn__count {
  position: absolute;
  top: -5px;
  right: -5px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: 5px;
  background: var(--accent);
  color: var(--accent-ink);
  font-family: var(--font-pixel);
  font-size: 13px;
  line-height: 18px;
  text-align: center;
  box-shadow: var(--glow-1);
}

/* Сердце мэтчей: спокойное «тук-тук» раз в несколько секунд и прыжок со вспышкой при новом мэтче */
.heart-btn svg {
  transform-origin: 50% 55%;
}

.heart-btn--beat svg {
  animation: heartbeat 2.8s ease-in-out infinite;
}

.heart-btn--pop svg {
  animation: heart-pop 0.7s cubic-bezier(0.3, 1.6, 0.5, 1);
}

.heart-btn--pop {
  box-shadow: var(--glow-1), var(--glow-2);
}

.heart-btn--pop .icon-btn__count {
  animation: count-pop 0.7s cubic-bezier(0.3, 1.6, 0.5, 1);
}

@keyframes heartbeat {
  0%,
  30%,
  100% {
    transform: scale(1);
  }

  8% {
    transform: scale(1.16);
  }

  16% {
    transform: scale(1);
  }

  23% {
    transform: scale(1.1);
  }
}

@keyframes heart-pop {
  0% {
    transform: scale(1);
  }

  35% {
    transform: scale(1.45) rotate(-8deg);
  }

  70% {
    transform: scale(0.92);
  }
}

@keyframes count-pop {
  0% {
    transform: scale(0.4);
  }

  50% {
    transform: scale(1.3);
  }
}

@media (prefers-reduced-motion: reduce) {
  .heart-btn--beat svg,
  .heart-btn--pop svg,
  .heart-btn--pop .icon-btn__count {
    animation: none;
  }
}

.icon-btn__dot {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: var(--glow-1);
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


/* Штампы при свайпе — пиксельные, светятся своим цветом */
.stamp {
  position: absolute;
  top: 32px;
  padding: 6px 12px 4px;
  border: 2px solid;
  border-radius: 6px;
  background: rgb(0 0 0 / 0.35);
  font-family: var(--font-pixel);
  font-size: 26px;
  line-height: 1;
  text-transform: uppercase;
  pointer-events: none;
  box-shadow: 0 0 18px currentColor, inset 0 0 12px color-mix(in srgb, currentColor 40%, transparent);
  text-shadow: 0 0 10px currentColor;
}

.stamp--like {
  left: 20px;
  color: var(--ok);
  transform: rotate(-10deg);
}

.stamp--skip {
  right: 20px;
  color: var(--danger);
  transform: rotate(10deg);
}

.deck__cubes {
  width: 150px;
  margin-bottom: 18px;
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

/* Кнопки решения — плитки из набора виджетов */
.round {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  border: 1px solid var(--line-strong);
  border-radius: 20px;
  cursor: pointer;
  transition: transform 0.08s ease, box-shadow 0.15s ease;
}

.round:active {
  transform: scale(0.92);
}

.round:disabled {
  opacity: 0.6;
}

.round--skip {
  background: var(--card);
  box-shadow: var(--edge-light);
  color: var(--text);
}

.round--skip:active {
  color: var(--danger);
  box-shadow: 0 0 18px color-mix(in srgb, var(--danger) 50%, transparent);
}

.round--like {
  border-color: var(--accent);
  background: var(--accent);
  color: var(--accent-ink);
  box-shadow: var(--glow-1), var(--glow-2);
}

.people__error {
  text-align: center;
}

/* «Вернуть» — маленькая плитка слева; без подписки — приглушена, нажатие объясняет, где это есть */
.people__actions {
  align-items: center;
}

.round--small {
  position: relative;
  width: 48px;
  height: 48px;
  border-radius: 15px;
  background: var(--card);
  box-shadow: var(--edge-light);
  color: var(--text);
}

.round--rewind:active {
  color: var(--warn);
  box-shadow: 0 0 16px color-mix(in srgb, var(--warn) 45%, transparent);
}

.round--locked {
  color: var(--text-2);
  opacity: 0.7;
}

.round__count {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: 5px;
  background: var(--raised);
  border: 1px solid var(--line-strong);
  font-family: var(--font-pixel);
  font-size: 12px;
  line-height: 16px;
}

.people__hint {
  margin: 8px 0 0;
  text-align: center;
}
</style>
