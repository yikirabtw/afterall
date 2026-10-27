<script setup lang="ts">
import { reactive, ref } from 'vue'

import { api } from '../../api/client'
import { errorMessage } from '../../api/errors'
import type { Me, UserGameInput } from '../../api/types'
import { gameById, session } from '../../stores/session'
import { haptic } from '../../telegram'

defineProps<{ busy?: boolean }>()
const emit = defineEmits<{ done: [me?: Me] }>()

const MAX_GAMES = 10

// Порядок выбора важен: первая выбранная игра — основная
const choices = reactive<UserGameInput[]>(
  session.me!.games.map(({ game_id, rank_id, role_ids, is_main }) => ({ game_id, rank_id, role_ids, is_main })),
)
const saving = ref(false)
const error = ref('')

function isSelected(gameId: number): boolean {
  return choices.some((choice) => choice.game_id === gameId)
}

function toggleGame(gameId: number) {
  haptic.select()
  const index = choices.findIndex((choice) => choice.game_id === gameId)
  if (index >= 0) choices.splice(index, 1)
  else if (choices.length < MAX_GAMES) choices.push({ game_id: gameId, rank_id: null, role_ids: [], is_main: false })
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

async function submit() {
  if (choices.length === 0) {
    error.value = 'Выбери хотя бы одну игру.'
    return
  }
  saving.value = true
  error.value = ''
  try {
    emit('done', await api.saveGames(choices.map((choice, index) => ({ ...choice, is_main: index === 0 }))))
  } catch (e) {
    error.value = errorMessage(e)
    haptic.error()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section>
    <h1 class="page-title">Во что играешь?</h1>
    <p class="lead">Первая выбранная игра станет основной. Ранг нужен, чтобы звать тебя в пати твоего уровня.</p>

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
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>
    <div class="actions">
      <button class="btn btn-primary" type="button" :disabled="saving" @click="submit">
        Далее{{ choices.length ? ` · ${choices.length}` : '' }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.lead {
  margin: -8px 0 20px;
  color: var(--hint);
}

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
  font-size: 18px;
  font-weight: 800;
}

.card .field__label {
  margin: 14px 0 8px;
}

.chip--small {
  padding: 6px 12px;
  font-size: 14px;
}
</style>
