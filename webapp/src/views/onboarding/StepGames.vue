<script setup lang="ts">
import { ref } from 'vue'

import { api } from '../../api/client'
import { errorMessage } from '../../api/errors'
import type { Me, UserGameInput } from '../../api/types'
import GamesPicker from '../../components/GamesPicker.vue'
import { gameChoicesFrom, gamesError } from '../../profile'
import { session } from '../../stores/session'
import { haptic } from '../../telegram'

defineProps<{ busy?: boolean }>()
const emit = defineEmits<{ done: [me?: Me] }>()

const choices = ref<UserGameInput[]>(gameChoicesFrom(session.me!, new Set(session.games.map((game) => game.id))))
const saving = ref(false)
const error = ref('')

async function submit() {
  const problem = gamesError(choices.value)
  if (problem) {
    error.value = problem
    haptic.error()
    return
  }
  saving.value = true
  error.value = ''
  try {
    emit('done', await api.saveGames(choices.value.map((choice, index) => ({ ...choice, is_main: index === 0 }))))
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
    <p class="lead">Ранг нужен, чтобы звать тебя в пати твоего уровня. Основную игру можно выбрать на карточке.</p>

    <GamesPicker v-model="choices" />

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
</style>
