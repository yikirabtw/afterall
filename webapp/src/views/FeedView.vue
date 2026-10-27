<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Lobby } from '../api/types'
import LobbyCard from '../components/LobbyCard.vue'
import { session } from '../stores/session'
import { haptic } from '../telegram'

const items = ref<Lobby[]>([])
const nextCursor = ref<number | null>(null)
const loading = ref(false)
const error = ref('')

const gameFilter = ref<number | null>(null)
const fitsMe = ref(false)

// Сначала свои игры, потом остальные
const filterGames = computed(() => {
  const mine = new Set(session.me!.games.map((game) => game.game_id))
  return [...session.games].sort((a, b) => Number(mine.has(b.id)) - Number(mine.has(a.id)))
})

async function load(more = false) {
  loading.value = true
  error.value = ''
  try {
    const page = await api.feed({
      game_id: gameFilter.value ?? undefined,
      fits_me: fitsMe.value,
      cursor: more ? (nextCursor.value ?? undefined) : undefined,
    })
    items.value = more ? [...items.value, ...page.items] : page.items
    nextCursor.value = page.next_cursor
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function selectGame(gameId: number | null) {
  haptic.select()
  gameFilter.value = gameId
}

watch([gameFilter, fitsMe], () => load())
onMounted(() => load())
</script>

<template>
  <main class="page">
    <header class="page-top">
      <h1 class="page-title">Пати</h1>
      <RouterLink to="/create" class="btn btn-primary btn-small" @click="haptic.tap()">+ Создать</RouterLink>
    </header>

    <div class="chips chips--scroll">
      <button type="button" class="chip" :class="{ 'chip--on': gameFilter === null }" @click="selectGame(null)">
        Все
      </button>
      <button
        v-for="game in filterGames"
        :key="game.id"
        type="button"
        class="chip"
        :class="{ 'chip--on': gameFilter === game.id }"
        @click="selectGame(game.id)"
      >
        {{ game.name }}
      </button>
    </div>

    <label class="card toggle-row fits">
      <span>
        <b>Только куда подхожу</b>
        <span class="hint block">По рангу и микрофону</span>
      </span>
      <input v-model="fitsMe" class="switch" type="checkbox" @change="haptic.select()" />
    </label>

    <div class="stack">
      <LobbyCard v-for="lobby in items" :key="lobby.id" :lobby="lobby" />
    </div>

    <div v-if="loading" class="center"><div class="spinner" /></div>
    <p v-else-if="error" class="error-text center">
      {{ error }}
      <button class="btn btn-ghost" type="button" @click="load()">Повторить</button>
    </p>
    <div v-else-if="items.length === 0" class="empty">
      <p class="empty__title">Открытых пати пока нет</p>
      <p class="hint">
        {{ gameFilter || fitsMe ? 'Попробуй убрать фильтры.' : 'Собери свою — остальные увидят её здесь.' }}
      </p>
      <RouterLink v-if="!gameFilter && !fitsMe" to="/create" class="btn btn-primary btn-small empty__cta">
        Создать пати
      </RouterLink>
    </div>
    <div v-else-if="nextCursor" class="center">
      <button class="btn btn-ghost" type="button" @click="load(true)">Показать ещё</button>
    </div>
  </main>
</template>

<style scoped>
.fits {
  margin: 12px 0 16px;
}

.block {
  display: block;
  margin-top: 2px;
}

.center {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0;
  text-align: center;
}
</style>
