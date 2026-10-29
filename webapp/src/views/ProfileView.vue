<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { RouterLink } from 'vue-router'

import PhotoCarousel from '../components/PhotoCarousel.vue'
import { formatAge } from '../format'
import { LANGUAGES, LOOKING_FOR, PLAY_STYLE_LABELS } from '../labels'
import BorderGlow from '../components/BorderGlow.vue'
import FaceitLevel from '../components/FaceitLevel.vue'
import PlanBadge from '../components/PlanBadge.vue'
import { faceitColor, faceitLevel } from '../lobby'
import { gameById, session } from '../stores/session'
import { originOf, reveal } from '../reveal'
import { openFrom } from '../router'
import { setTheme, theme, type Theme } from '../stores/theme'
import { haptic, setVerticalSwipes } from '../telegram'

const me = computed(() => session.me!)
const profile = computed(() => me.value.profile!)

const age = computed(() => {
  if (!me.value.birth_date) return null
  const birth = new Date(me.value.birth_date)
  const today = new Date()
  const hadBirthday =
    today.getMonth() > birth.getMonth() || (today.getMonth() === birth.getMonth() && today.getDate() >= birth.getDate())
  return today.getFullYear() - birth.getFullYear() - (hadBirthday ? 0 : 1)
})

// Выключенные игры (их нет в справочнике) не показываем — выбрать их уже нельзя
const games = computed(() =>
  me.value.games.flatMap((userGame) => {
    const game = gameById(userGame.game_id)
    if (!game) return []
    return [
      {
        id: userGame.game_id,
        name: game.name,
        isMain: userGame.is_main,
        rank: game.ranks.find((rank) => rank.id === userGame.rank_id)?.name ?? null,
        faceit: userGame.faceit_elo,
        roles: game.roles.filter((role) => userGame.role_ids.includes(role.id)).map((role) => role.name),
      },
    ]
  }),
)

// Полоса цифр под шапкой — как блок статистики в референсе
const stats = computed(() => [
  { value: String(games.value.length), label: 'игры' },
  { value: `${profile.value.reputation > 0 ? '+' : ''}${profile.value.reputation}`, label: 'репутация' },
  // Лимит фото — по тарифу; загруженные раньше сверх лимита остаются, поэтому «3/1» не показываем
  { value: `${me.value.photos.length}/${Math.max(me.value.photos.length, me.value.plan.photos_max)}`, label: 'фото' },
])

const lookingFor = computed(() => LOOKING_FOR.find((option) => option.value === profile.value.looking_for)?.label)
const languages = computed(() =>
  profile.value.languages.map((code) => LANGUAGES.find((lang) => lang.value === code)?.label ?? code).join(', '),
)

// --- Шапка раскрывается свайпом вверх: фото видно почти целиком, подпись снизу мельче. Свайп вниз — обратно.

const SWIPE_MIN = 40 // px по вертикали, чтобы считалось свайпом, а не нажатием
const PAGE_MAX_WIDTH = 592 // как у .page (560) плюс поля, на которые шапка выходит за край

const expanded = ref(false)
const canExpand = computed(() => me.value.photos.length > 0)

// Высота по пропорциям главного фото — чтобы оно влезло целиком, но не выше 82% экрана
const heroStyle = computed(() => {
  if (!expanded.value) return undefined
  const photo = me.value.photos[0]
  const ratio = photo?.width ? photo.height / photo.width : 1.25
  return { height: `min(calc(min(100vw, ${PAGE_MAX_WIDTH}px) * ${ratio.toFixed(3)}), 82vh)`, maxHeight: 'none' }
})

function setExpanded(value: boolean) {
  if (expanded.value === value) return
  expanded.value = value
  haptic.select()
  setVerticalSwipes(!value)
}

let startX = 0
let startY = 0
let swiped = false

function onPointerDown(event: PointerEvent) {
  startX = event.clientX
  startY = event.clientY
  swiped = false
}

function onPointerUp(event: PointerEvent) {
  const dx = event.clientX - startX
  const dy = event.clientY - startY
  if (!canExpand.value || Math.abs(dy) < SWIPE_MIN || Math.abs(dy) < Math.abs(dx)) return
  swiped = true
  setExpanded(dy < 0)
}

// После свайпа браузер присылает ещё и «нажатие» — фото из-за него не перелистываем
function onClickCapture(event: MouseEvent) {
  if (!swiped) return
  event.stopPropagation()
  swiped = false
}

onBeforeUnmount(() => setVerticalSwipes(true))

const THEMES: { value: Theme; label: string; icon: string }[] = [
  { value: 'dark', label: 'Тёмная', icon: 'M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z' },
  {
    value: 'light',
    label: 'Светлая',
    icon: 'M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4',
  },
]

// Новая тема разливается кругом от нажатой кнопки
function chooseTheme(value: Theme, event: MouseEvent) {
  if (theme.value === value) return
  haptic.select()
  void reveal(originOf(event.currentTarget as Element), () => setTheme(value))
}

// Карандаш: экран редактирования «расплывается» из него, «Назад» сворачивает обратно
function edit(event: Event) {
  event.stopPropagation() // иначе нажатие ещё и перелистнёт фото
  haptic.tap()
  openFrom(event.currentTarget as Element, '/profile/edit')
}
</script>

<template>
  <main class="page profile">
    <PhotoCarousel
      class="hero"
      :class="{ 'hero--swipe': canExpand, 'hero--expanded': expanded }"
      :style="heroStyle"
      :photos="me.photos"
      :name="profile.display_name"
      @pointerdown="onPointerDown"
      @pointerup="onPointerUp"
      @click.capture="onClickCapture"
    >
      <h1 class="hero__name">{{ profile.display_name }}<PlanBadge :plan="me.plan.plan" /></h1>
      <p class="hero__meta">
        <span v-if="age !== null">{{ formatAge(age) }}</span>
        <span v-if="profile.city">{{ profile.city }}</span>
        <span v-if="me.username">@{{ me.username }}</span>
      </p>
      <!-- Ручка: подсказывает свайп и сама раскрывает/сворачивает по нажатию -->
      <button
        v-if="canExpand"
        class="hero__handle"
        type="button"
        :aria-label="expanded ? 'Свернуть фото' : 'Развернуть фото'"
        @click.stop="setExpanded(!expanded)"
      />
    </PhotoCarousel>
    <button class="edit" type="button" aria-label="Редактировать профиль" @click="edit">
      <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
        <path
          d="M4 20h4L19 9l-4-4L4 16v4zM14 6l4 4"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </button>

    <p v-if="!me.photos.length" class="hint add-photo">
      Добавь фото — с ним тебя заметят в ленте.
      <button class="btn btn-ghost link" type="button" @click="edit">Добавить</button>
    </p>

    <dl class="stats">
      <div v-for="stat in stats" :key="stat.label" class="stats__item">
        <dt>{{ stat.label }}</dt>
        <dd>{{ stat.value }}</dd>
      </div>
    </dl>

    <div class="chips tags">
      <span class="badge badge--accent">Ищу: {{ lookingFor }}</span>
      <span class="badge">{{ PLAY_STYLE_LABELS[profile.play_style] }}</span>
      <span class="badge">{{ profile.has_mic ? 'С микрофоном' : 'Без микрофона' }}</span>
    </div>

    <BorderGlow v-if="profile.bio" as="p" class="card card--lit bio">{{ profile.bio }}</BorderGlow>

    <!-- Разделы нажимаются целиком: «Игры» — редактор игр, «Ещё» — анкета -->
    <h2 class="section-title">Игры</h2>
    <BorderGlow :as="RouterLink" to="/profile/games" class="card list tappable" @click="haptic.tap()">
      <div v-for="game in games" :key="game.id" class="list__row">
        <div>
          <b>{{ game.name }}</b>
          <span v-if="game.isMain" class="badge badge--accent main">Основная</span>
          <p v-if="game.roles.length" class="hint row-hint">{{ game.roles.join(', ') }}</p>
        </div>
        <span class="row-end">
          <span class="hint row-value">
            {{ game.rank ?? (game.faceit !== null ? '' : 'без ранга') }}
            <span v-if="game.faceit !== null" class="faceit" :style="{ color: faceitColor(faceitLevel(game.faceit)) }">
              <FaceitLevel :elo="game.faceit" :size="22" />
              FACEIT {{ game.faceit }}
            </span>
          </span>
          <span class="chevron" aria-hidden="true">›</span>
        </span>
      </div>
      <div v-if="!games.length" class="list__row">
        <span class="hint">Игры не выбраны</span>
        <span class="chevron" aria-hidden="true">›</span>
      </div>
    </BorderGlow>

    <h2 class="section-title">Ещё</h2>
    <BorderGlow class="card list">
      <div class="list__row">
        <span>Тема</span>
        <span v-jelly="{ room: true }" class="theme-switch" role="radiogroup" aria-label="Тема">
          <button
            v-for="option in THEMES"
            :key="option.value"
            type="button"
            role="radio"
            :aria-checked="theme === option.value"
            :aria-label="option.label"
            @click="chooseTheme(option.value, $event)"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path
                :d="option.icon"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            {{ option.label }}
          </button>
        </span>
      </div>
      <RouterLink to="/profile/edit" class="list__row tappable" @click="haptic.tap()">
        <span>Языки</span>
        <span class="row-end"><span class="hint">{{ languages }}</span><span class="chevron" aria-hidden="true">›</span></span>
      </RouterLink>
      <RouterLink to="/profile/edit" class="list__row tappable" @click="haptic.tap()">
        <span>Ник в Telegram</span>
        <span class="row-end">
          <span class="hint">{{ profile.show_telegram ? 'виден мэтчам' : 'скрыт' }}</span>
          <span class="chevron" aria-hidden="true">›</span>
        </span>
      </RouterLink>
      <RouterLink to="/profile/edit" class="list__row tappable" @click="haptic.tap()">
        <span>Discord</span>
        <span class="row-end">
          <span class="hint">{{ profile.discord_tag ?? 'не указан' }}</span>
          <span class="chevron" aria-hidden="true">›</span>
        </span>
      </RouterLink>
      <RouterLink to="/profile/edit" class="list__row tappable" @click="haptic.tap()">
        <span>Кого ищу, стиль, микрофон</span>
        <span class="row-end"><span class="hint">{{ lookingFor }}</span><span class="chevron" aria-hidden="true">›</span></span>
      </RouterLink>
      <RouterLink to="/profile/blocked" class="list__row tappable" @click="haptic.tap()">
        <span>Заблокированные</span>
        <span class="row-end"><span class="chevron" aria-hidden="true">›</span></span>
      </RouterLink>
    </BorderGlow>
    <p class="hint">После взаимного лайка или в общей пати вы пишете друг другу в чате приложения. Discord и ник в Telegram — только если ты их открыл.</p>
  </main>
</template>

<style scoped>
.profile {
  position: relative;
  padding-top: 0;
}

/* Шапка — примерно треть экрана, от края до края */
.hero {
  height: 38vh;
  min-height: 280px;
  max-height: 440px;
  margin: 0 -16px;
  border-bottom: 1px solid var(--line);
  border-radius: 0 0 24px 24px;
  transition: height 0.35s cubic-bezier(0.2, 0.8, 0.2, 1);
}

/* Вертикальный свайп по шапке — наш, страницу с неё не прокручиваем */
.hero.hero--swipe {
  touch-action: none;
}

.hero__name {
  margin: 0;
  font-family: var(--font-title);
  font-size: 32px;
  font-weight: 400;
  line-height: 1.1;
  overflow-wrap: anywhere;
  transition: font-size 0.35s ease;
}

.hero__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 12px;
  margin: 6px 0 0;
  font-size: 15px;
  opacity: 0.85;
  transition: font-size 0.35s ease;
}

/* Раскрыто: фото главнее, подпись скромнее */
.hero--expanded .hero__name {
  font-size: 22px;
}

.hero--expanded .hero__meta {
  margin-top: 3px;
  font-size: 13px;
}

/* Ручка внизу шапки — светящаяся черта, область нажатия больше её самой */
.hero__handle {
  position: absolute;
  left: 50%;
  bottom: 0;
  width: 64px;
  height: 18px;
  margin-left: -32px;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.hero__handle::after {
  content: '';
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 7px;
  height: 3px;
  border-radius: 2px;
  background: rgb(255 255 255 / 0.7);
  box-shadow: 0 0 8px rgb(255 255 255 / 0.6);
}

@media (prefers-reduced-motion: reduce) {
  .hero,
  .hero__name,
  .hero__meta {
    transition: none;
  }
}

.edit {
  position: absolute;
  top: calc(12px + var(--tg-content-safe-area-inset-top, 0px));
  right: 12px;
  z-index: 3;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 1px solid rgb(255 255 255 / 0.25);
  border-radius: 12px;
  background: rgb(0 0 0 / 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  color: #fff;
  cursor: pointer;
}

.add-photo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.link {
  min-height: 32px;
  padding: 0;
  color: var(--text);
  text-decoration: underline;
  text-underline-offset: 3px;
}

/* Цифры пиксельным шрифтом, между ними пунктирные разделители */
.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin: 18px 0 0;
  padding: 14px 0;
  border-top: 1px dashed var(--line-strong);
  border-bottom: 1px dashed var(--line-strong);
}

.stats__item {
  display: flex;
  flex-direction: column-reverse;
  align-items: center;
  gap: 4px;
}

.stats__item + .stats__item {
  border-left: 1px dashed var(--line-strong);
}

.stats dd {
  margin: 0;
  font-family: var(--font-pixel);
  font-size: 30px;
  line-height: 1;
  text-shadow: 0 0 6px rgb(var(--glow-rgb) / 0.4);
}

.stats dt {
  font-size: 12px;
  color: var(--hint);
}

.tags {
  margin-top: 16px;
}

.bio {
  margin: 20px 0 0;
  white-space: pre-line;
  overflow-wrap: anywhere;
}

.list {
  padding: 4px 16px;
}

.list__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
}

.list__row + .list__row {
  border-top: 1px dashed var(--line-strong);
}

.main {
  margin-left: 8px;
}

.tappable {
  display: block;
  color: inherit;
  text-decoration: none;
  cursor: pointer;
}

a.list__row.tappable {
  display: flex;
}

.tappable:active {
  opacity: 0.7;
}

.row-end {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  text-align: right;
}

.row-value {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

/* Цвет текста задаётся уровнем FACEIT */
.faceit {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
  font-weight: 700;
}

/* Тема: две «пилюли» с луной и солнцем, выбранная раздувается желе (v-jelly) */
.theme-switch {
  display: inline-flex;
  gap: 8px;
  margin-right: -12px; /* отступы под раздувание — не сдвигаем ряд от края */
}

.theme-switch button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  border: 1px solid var(--line-strong);
  border-radius: 16px;
  background: var(--raised);
  color: var(--text-2);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}

.theme-switch button[aria-checked='true'] {
  border-color: var(--accent);
  background: var(--accent);
  color: var(--accent-ink);
  box-shadow: 0 0 12px rgb(var(--glow-rgb) / 0.25);
}

.chevron {
  flex: none;
  color: var(--hint);
  font-size: 22px;
  line-height: 1;
}

.row-hint {
  margin: 2px 0 0;
}
</style>
