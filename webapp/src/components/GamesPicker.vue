<script setup lang="ts">
import { computed, nextTick, reactive, ref } from 'vue'

import type { UserGameInput } from '../api/types'
import { gameColor } from '../lobby'
import { FACEIT_MAX, FACEIT_MIN } from '../profile'
import { gameById, session } from '../stores/session'
import { haptic } from '../telegram'
import FaceitLevel from './FaceitLevel.vue'
import GameSheet from './GameSheet.vue'

// Выбор игр с рангом, ролями и FACEIT — общий для регистрации и редактирования профиля.
// Основная игра — первая в списке: её можно поменять кнопкой на карточке.
const choices = defineModel<UserGameInput[]>({ required: true })

const MAX_GAMES = 10

const sheetOpen = ref(false)
const available = computed(() =>
  session.games.filter((game) => !choices.value.some((choice) => choice.game_id === game.id)),
)
const canAdd = computed(() => choices.value.length < MAX_GAMES && available.value.length > 0)

async function addGame(gameId: number | null) {
  sheetOpen.value = false
  if (gameId === null) return
  choices.value.push({ game_id: gameId, rank_id: null, role_ids: [], faceit_elo: null, is_main: false })
  // Новая карточка — внизу списка: показываем её, чтобы сразу выбрать ранг
  await nextTick()
  document.querySelector(`[data-game="${gameId}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

// У CS2 два рейтинга — Premier и FACEIT: человек заполняет один из них или оба
type RatingTab = 'premier' | 'faceit'
const ratingTabs = reactive<Record<number, RatingTab>>({})

function ratingTab(choice: UserGameInput): RatingTab {
  return ratingTabs[choice.game_id] ?? (choice.faceit_elo !== null && choice.rank_id === null ? 'faceit' : 'premier')
}

function setRatingTab(choice: UserGameInput, tab: RatingTab) {
  haptic.select()
  ratingTabs[choice.game_id] = tab
}

/** Внутри вкладки Premier слово «Premier» в каждом ранге лишнее */
function premierRankName(name: string): string {
  return name.replace(/^Premier\s+/, '')
}

function makeMain(index: number) {
  haptic.select()
  const [choice] = choices.value.splice(index, 1)
  choices.value.unshift(choice!)
}

function removeGame(index: number) {
  haptic.tap()
  choices.value.splice(index, 1)
}

function setRank(choice: UserGameInput, rankId: number) {
  haptic.select()
  choice.rank_id = choice.rank_id === rankId ? null : rankId
}

function toggleRole(choice: UserGameInput, roleId: number) {
  haptic.select()
  choice.role_ids = choice.role_ids.includes(roleId)
    ? choice.role_ids.filter((id) => id !== roleId)
    : [...choice.role_ids, roleId]
}

// Пустое поле — «не указан», а не 0 и не пустая строка
function setFaceit(choice: UserGameInput, raw: string) {
  const value = raw.trim()
  choice.faceit_elo = value === '' ? null : Number(value)
}

function faceitValid(elo: number | null): elo is number {
  return elo !== null && Number.isFinite(elo) && elo >= FACEIT_MIN && elo <= FACEIT_MAX
}
</script>

<template>
  <TransitionGroup name="choice" tag="div" class="stack">
    <article
      v-for="(choice, index) in choices"
      :key="choice.game_id"
      class="card choice"
      :class="{ 'card--lit': index === 0 }"
      :style="{ '--game': gameColor(choice.game_id) }"
      :data-game="choice.game_id"
    >
      <header class="choice__header">
        <h2 class="choice__title">{{ gameById(choice.game_id)?.name }}</h2>
        <button
          class="choice__remove"
          type="button"
          :aria-label="`Убрать «${gameById(choice.game_id)?.name}»`"
          @click="removeGame(index)"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path
              d="M4 7h16M9 7V4.5h6V7M6.5 7l1 13h9l1-13M10 11v5.5M14 11v5.5"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
      </header>
      <span v-if="index === 0" class="badge badge--accent choice__main">Основная</span>
      <button v-else class="choice__main choice__make-main" type="button" @click="makeMain(index)">
        Сделать основной
      </button>

      <template v-if="gameById(choice.game_id)?.has_faceit">
        <p class="field__label">Рейтинг — укажи один или оба</p>
        <div v-jelly.soft class="segmented rating-tabs">
          <button
            type="button"
            :aria-pressed="ratingTab(choice) === 'premier'"
            @click="setRatingTab(choice, 'premier')"
          >
            Premier
            <i v-if="choice.rank_id !== null" class="rating-tabs__filled" aria-label="указан" />
          </button>
          <button type="button" :aria-pressed="ratingTab(choice) === 'faceit'" @click="setRatingTab(choice, 'faceit')">
            FACEIT
            <i v-if="faceitValid(choice.faceit_elo)" class="rating-tabs__filled" aria-label="указан" />
          </button>
        </div>

        <div v-if="ratingTab(choice) === 'premier'" class="chips rating-body">
          <button
            v-for="rank in gameById(choice.game_id)!.ranks"
            :key="rank.id"
            type="button"
            class="chip chip--small"
            :class="{ 'chip--on': choice.rank_id === rank.id }"
            @click="setRank(choice, rank.id)"
          >
            {{ premierRankName(rank.name) }}
          </button>
        </div>

        <label v-else class="faceit rating-body">
          <span class="faceit__row">
            <input
              class="input"
              type="number"
              inputmode="numeric"
              :min="FACEIT_MIN"
              :max="FACEIT_MAX"
              placeholder="ELO, например 1850"
              aria-label="FACEIT ELO"
              :value="choice.faceit_elo ?? ''"
              @input="setFaceit(choice, ($event.target as HTMLInputElement).value)"
            />
            <FaceitLevel v-if="faceitValid(choice.faceit_elo)" :elo="choice.faceit_elo" :size="46" />
          </span>
          <span class="hint faceit__hint">Уровень 1–10 посчитаем по ELO сами.</span>
        </label>
      </template>

      <template v-else-if="gameById(choice.game_id)?.ranks.length">
        <p class="field__label">Ранг</p>
        <div class="chips">
          <button
            v-for="rank in gameById(choice.game_id)!.ranks"
            :key="rank.id"
            type="button"
            class="chip chip--small"
            :class="{ 'chip--on': choice.rank_id === rank.id }"
            @click="setRank(choice, rank.id)"
          >
            {{ rank.name }}
          </button>
        </div>
      </template>

      <template v-if="gameById(choice.game_id)?.roles.length">
        <p class="field__label">Роли</p>
        <div class="chips">
          <button
            v-for="role in gameById(choice.game_id)!.roles"
            :key="role.id"
            type="button"
            class="chip chip--small"
            :class="{ 'chip--on': choice.role_ids.includes(role.id) }"
            @click="toggleRole(choice, role.id)"
          >
            {{ role.name }}
          </button>
        </div>
      </template>

      <p v-if="!gameById(choice.game_id)?.ranks.length && !gameById(choice.game_id)?.roles.length" class="hint">
        Здесь рангов нет — просто играем вместе.
      </p>
    </article>
  </TransitionGroup>

  <button v-if="canAdd" class="add-game" :class="{ 'add-game--first': !choices.length }" type="button" @click="sheetOpen = true">
    <span class="add-game__plus" aria-hidden="true">+</span>
    {{ choices.length ? 'Добавить игру' : 'Выбрать игру' }}
  </button>

  <GameSheet :open="sheetOpen" :games="available" @pick="addGame" @close="sheetOpen = false" />
</template>

<style scoped>
.choice__header {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Название с огоньком цвета игры */
.choice__title {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-family: var(--font-title);
  font-size: 18px;
  font-weight: 400;
}

.choice__title::before {
  content: '';
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: var(--game);
  box-shadow: 0 0 8px 1px var(--game);
}

.choice__main {
  margin-top: 8px;
}

.choice__make-main {
  display: inline-flex;
  padding: 5px 9px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  background: transparent;
  color: var(--text-2);
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
}

.choice__make-main:active {
  border-color: var(--accent);
  color: var(--text);
}

.choice__remove {
  flex: none;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--line-strong);
  border-radius: 9px;
  background: var(--card);
  color: var(--text-2);
  cursor: pointer;
}

.choice__remove:active {
  border-color: var(--danger);
  color: var(--danger);
  box-shadow: 0 0 12px color-mix(in srgb, var(--danger) 45%, transparent);
}

/* Поменяли основную — карточки плавно меняются местами */
.choice-move,
.choice-enter-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.choice-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.add-game {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  min-height: 52px;
  margin-top: var(--gap);
  border: 1px dashed var(--g-400);
  border-radius: var(--radius);
  background: transparent;
  color: var(--text);
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
}

.add-game:active {
  border-color: var(--accent);
  box-shadow: var(--glow-1);
}

/* Пока игр нет — кнопка крупнее: это главное действие экрана */
.add-game--first {
  min-height: 72px;
  margin-top: 0;
}

.add-game__plus {
  font-family: var(--font-pixel);
  font-size: 22px;
  line-height: 1;
  text-shadow: 0 0 8px rgb(var(--glow-rgb) / 0.7);
}

@media (prefers-reduced-motion: reduce) {
  .choice-move,
  .choice-enter-active {
    transition: none;
  }
}

.card .field__label {
  margin: 14px 0 8px;
}

.chip--small {
  padding: 6px 12px;
  font-size: 14px;
}

.rating-body {
  margin-top: 10px;
}

/* Огонёк на вкладке — в ней уже что-то указано */
.rating-tabs button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
}

.rating-tabs__filled {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 6px currentColor;
}

.faceit {
  display: block;
}

.faceit__hint {
  display: block;
  margin-top: 6px;
}

.faceit__row {
  display: flex;
  align-items: center;
  gap: 10px;
}

</style>
