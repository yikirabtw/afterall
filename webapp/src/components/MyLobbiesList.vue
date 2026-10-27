<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Lobby } from '../api/types'
import LobbyCard from './LobbyCard.vue'

// «Мои пати»: созданные, где меня приняли и куда я откликнулся
const items = ref<Lobby[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    items.value = await api.myLobbies()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="center"><div class="spinner" /></div>
  <p v-else-if="error" class="error-text center">
    {{ error }}
    <button class="btn btn-ghost" type="button" @click="load">Повторить</button>
  </p>
  <div v-else-if="items.length === 0" class="empty">
    <p class="empty__title">Пока пусто</p>
    <p class="hint">Здесь будут пати, которые ты создашь, и те, куда откликнешься.</p>
    <RouterLink to="/create" class="btn btn-primary btn-small empty__cta">Создать пати</RouterLink>
  </div>
  <div v-else class="stack">
    <LobbyCard v-for="lobby in items" :key="lobby.id" :lobby="lobby" show-my-status />
  </div>
</template>

<style scoped>
.center {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0;
  text-align: center;
}
</style>
