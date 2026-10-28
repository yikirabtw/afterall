<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, assetUrl } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Match } from '../api/types'
import MatchContacts from '../components/MatchContacts.vue'
import PageHeader from '../components/PageHeader.vue'
import WireCubes from '../components/WireCubes.vue'
import { gameById } from '../stores/session'

const matches = ref<Match[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    matches.value = await api.matches()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="page">
    <PageHeader title="Мэтчи" />

    <div v-if="loading" class="center"><div class="spinner" /></div>
    <p v-else-if="error" class="error-text center">
      {{ error }}
      <button class="btn btn-ghost" type="button" @click="load">Повторить</button>
    </p>
    <div v-else-if="matches.length === 0" class="empty">
      <WireCubes class="empty__art" />
      <p class="empty__title">Пока нет мэтчей</p>
      <p class="hint">Ставь ♥ тем, с кем хочешь играть. Если симпатия взаимная — человек появится здесь с контактами.</p>
    </div>
    <ul v-else class="stack list">
      <li v-for="match in matches" :key="match.user_id" class="card match">
        <span class="match__avatar">
          <img v-if="match.photos[0]" :src="assetUrl(match.photos[0].url)" alt="" />
          <template v-else>{{ match.display_name.charAt(0).toUpperCase() }}</template>
        </span>
        <div class="match__body">
          <b class="match__name">
            {{ match.display_name }}<span v-if="match.age !== null">, {{ match.age }}</span>
          </b>
          <p v-if="match.main_game_id" class="hint match__game">{{ gameById(match.main_game_id)?.name }}</p>
          <MatchContacts :match="match" class="match__contacts" />
        </div>
      </li>
    </ul>
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

.list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.match {
  display: flex;
  gap: 14px;
}

.match__avatar {
  flex: none;
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  border: 1px solid var(--line-strong);
  border-radius: 16px;
  overflow: hidden;
  background: var(--g-100);
  color: var(--text);
  font-family: var(--font-pixel);
  font-size: 30px;
  text-shadow: 0 0 10px rgb(255 255 255 / 0.6);
}

.match__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.match__body {
  min-width: 0;
}

.match__name {
  font-family: var(--font-title);
  font-size: 17px;
  overflow-wrap: anywhere;
}

.match__game {
  margin: 2px 0 0;
}

.match__contacts {
  margin-top: 10px;
}
</style>
