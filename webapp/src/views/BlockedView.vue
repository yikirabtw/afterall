<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, assetUrl } from '../api/client'
import { errorMessage } from '../api/errors'
import type { BlockedUser } from '../api/types'
import PageHeader from '../components/PageHeader.vue'
import WireCubes from '../components/WireCubes.vue'
import { confirmAction, haptic } from '../telegram'

// Кого я заблокировал (сам или жалобой) — здесь можно передумать: мэтч и переписка вернутся
const people = ref<BlockedUser[]>([])
const loading = ref(true)
const error = ref('')
const busy = ref<number | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    people.value = await api.blocks()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function unblock(person: BlockedUser) {
  if (!(await confirmAction(`Разблокировать «${person.display_name}»? Если у вас был мэтч — он вернётся.`))) return
  busy.value = person.user_id
  try {
    await api.unblock(person.user_id)
    people.value = people.value.filter((item) => item.user_id !== person.user_id)
    haptic.success()
  } catch (e) {
    error.value = errorMessage(e)
    haptic.error()
  } finally {
    busy.value = null
  }
}

onMounted(load)
</script>

<template>
  <main class="page">
    <PageHeader title="Заблокированные" />

    <div v-if="loading" class="center"><div class="spinner" /></div>
    <template v-else>
      <p v-if="error" class="error-text">{{ error }}</p>
      <div v-if="!people.length && !error" class="empty">
        <WireCubes class="empty__art" />
        <p class="empty__title">Никого нет</p>
        <p class="hint">Заблокировать или пожаловаться можно в мэтчах и в чате — кнопка «⋯».</p>
      </div>
      <ul v-else class="stack list rise-in">
        <li v-for="person in people" :key="person.user_id" class="card row">
          <span class="row__avatar">
            <img v-if="person.photo" :src="assetUrl(person.photo.url)" alt="" />
            <template v-else>{{ person.display_name.charAt(0).toUpperCase() }}</template>
          </span>
          <b class="row__name">{{ person.display_name }}</b>
          <button
            class="btn btn-outline btn-small"
            type="button"
            :disabled="busy === person.user_id"
            @click="unblock(person)"
          >
            Вернуть
          </button>
        </li>
      </ul>
    </template>
  </main>
</template>

<style scoped>
.center {
  display: flex;
  justify-content: center;
  padding: 24px 0;
}

.list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.row__avatar {
  flex: none;
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  overflow: hidden;
  border: 1px solid var(--line-strong);
  border-radius: 50%;
  background: var(--raised);
  font-family: var(--font-pixel);
  font-size: 18px;
  filter: grayscale(1);
}

.row__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.row__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-title);
  font-size: 16px;
  font-weight: 400;
}
</style>
