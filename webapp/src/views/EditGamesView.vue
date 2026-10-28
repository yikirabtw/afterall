<script setup lang="ts">
import { ref } from 'vue'

import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { UserGameInput } from '../api/types'
import GamesPicker from '../components/GamesPicker.vue'
import PageHeader from '../components/PageHeader.vue'
import { gameChoicesFrom, gamesError } from '../profile'
import { goBack } from '../router'
import { session, setMe } from '../stores/session'
import { haptic } from '../telegram'

const choices = ref<UserGameInput[]>(gameChoicesFrom(session.me!, new Set(session.games.map((game) => game.id))))
const saving = ref(false)
const error = ref('')

async function save() {
  const problem = gamesError(choices.value)
  if (problem) {
    error.value = problem
    haptic.error()
    return
  }
  saving.value = true
  error.value = ''
  try {
    setMe(await api.saveGames(choices.value.map((choice, index) => ({ ...choice, is_main: index === 0 }))))
    haptic.success()
    goBack()
  } catch (e) {
    error.value = errorMessage(e)
    haptic.error()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <main class="page">
    <PageHeader title="Игры" />
    <p class="lead">Первая выбранная игра — основная. Чтобы сделать основной другую, сними выбор и выбери заново.</p>

    <GamesPicker v-model="choices" />

    <p v-if="error" class="error-text">{{ error }}</p>
    <div class="actions">
      <button class="btn btn-primary" type="button" :disabled="saving" @click="save">Сохранить</button>
    </div>
  </main>
</template>

<style scoped>
.lead {
  margin: -8px 0 20px;
  color: var(--hint);
}
</style>
