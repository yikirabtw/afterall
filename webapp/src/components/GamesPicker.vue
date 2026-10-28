<script setup lang="ts">
import type { UserGameInput } from '../api/types'
import { faceitLevel } from '../lobby'
import { FACEIT_MAX, FACEIT_MIN } from '../profile'
import { gameById, session } from '../stores/session'
import { haptic } from '../telegram'

// Выбор игр с рангом, ролями и FACEIT — общий для регистрации и редактирования профиля.
// Порядок выбора важен: первая выбранная игра — основная.
const choices = defineModel<UserGameInput[]>({ required: true })

const MAX_GAMES = 10

function isSelected(gameId: number): boolean {
  return choices.value.some((choice) => choice.game_id === gameId)
}

function toggleGame(gameId: number) {
  haptic.select()
  const index = choices.value.findIndex((choice) => choice.game_id === gameId)
  if (index >= 0) choices.value.splice(index, 1)
  else if (choices.value.length < MAX_GAMES) {
    choices.value.push({ game_id: gameId, rank_id: null, role_ids: [], faceit_elo: null, is_main: false })
  }
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
  <div class="chips">
    <button
      v-for="game in session.games"
      :key="game.id"
      type="button"
      class="chip"
      :class="{ 'chip--on': isSelected(game.id) }"
      @click="toggleGame(game.id)"
    >
      {{ game.name }}
    </button>
  </div>

  <div class="stack choices">
    <article v-for="(choice, index) in choices" :key="choice.game_id" class="card">
      <header class="choice__header">
        <h2 class="choice__title">{{ gameById(choice.game_id)?.name }}</h2>
        <span v-if="index === 0" class="badge badge--accent">Основная</span>
      </header>

      <template v-if="gameById(choice.game_id)?.ranks.length">
        <p class="field__label">{{ gameById(choice.game_id)?.has_faceit ? 'Ранг Premier' : 'Ранг' }}</p>
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

      <label v-if="gameById(choice.game_id)?.has_faceit" class="field faceit">
        <span class="field__label">FACEIT ELO — если играешь на FACEIT</span>
        <span class="faceit__row">
          <input
            class="input"
            type="number"
            inputmode="numeric"
            :min="FACEIT_MIN"
            :max="FACEIT_MAX"
            placeholder="Например, 1850"
            :value="choice.faceit_elo ?? ''"
            @input="setFaceit(choice, ($event.target as HTMLInputElement).value)"
          />
          <span v-if="faceitValid(choice.faceit_elo)" class="faceit__level">{{ faceitLevel(choice.faceit_elo) }} lvl</span>
        </span>
      </label>

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
  </div>
</template>

<style scoped>
.choices {
  margin-top: 20px;
}

.choice__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.choice__title {
  margin: 0;
  font-family: var(--font-title);
  font-size: 18px;
  font-weight: 400;
}

.card .field__label {
  margin: 14px 0 8px;
}

.chip--small {
  padding: 6px 12px;
  font-size: 14px;
}

.faceit .field__label {
  margin-bottom: 0;
}

.faceit__row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.faceit__level {
  flex: none;
  padding: 6px 10px 5px;
  border: 1px solid var(--warn);
  border-radius: 6px;
  color: var(--warn);
  font-family: var(--font-pixel);
  font-size: 16px;
  box-shadow: 0 0 12px color-mix(in srgb, var(--warn) 40%, transparent);
}
</style>
