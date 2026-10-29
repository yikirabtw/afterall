<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { assetUrl, api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { ChatSummary } from '../api/types'
import WireCubes from '../components/WireCubes.vue'
import { formatChatTime } from '../format'
import { gameColor } from '../lobby'
import { openFrom } from '../router'
import { chatUnread } from '../stores/chats'
import { haptic } from '../telegram'

// Список переписок: мэтчи и пати, где тебя приняли. Пока экран открыт — обновляем каждые 10 секунд
const POLL_MS = 10_000

const chats = ref<ChatSummary[]>([])
const loading = ref(true)
const error = ref('')
let timer = 0

async function load() {
  try {
    chats.value = await api.chats()
    chatUnread.value = chats.value.reduce((total, chat) => total + chat.unread, 0)
    error.value = ''
  } catch (e) {
    if (!chats.value.length) error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function preview(chat: ChatSummary): string {
  const message = chat.last_message
  if (!message) return chat.kind === 'direct' ? 'Взаимный лайк — напиши первым' : 'Чат пати — договоритесь о катке'
  if (message.mine) return `Ты: ${message.body}`
  return chat.kind === 'lobby' ? `${message.sender_name}: ${message.body}` : message.body
}

// Строка чата растягивается в экран переписки
function open(chat: ChatSummary, event: MouseEvent) {
  haptic.tap()
  openFrom(event.currentTarget as Element, `/chat/${chat.kind}/${chat.ref}`, 'morph')
}

onMounted(() => {
  void load()
  timer = window.setInterval(load, POLL_MS)
})
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <main class="page">
    <header class="page-top">
      <h1 class="page-title">Чат</h1>
    </header>

    <div v-if="loading" class="center"><div class="spinner" /></div>
    <p v-else-if="error" class="error-text center">
      {{ error }}
      <button class="btn btn-ghost" type="button" @click="load">Повторить</button>
    </p>
    <div v-else-if="!chats.length" class="empty">
      <WireCubes class="empty__art" />
      <p class="empty__title">Пока пусто</p>
      <p class="hint">Чаты появятся после взаимного лайка в ленте или когда тебя примут в пати.</p>
    </div>

    <ul v-else class="card chats">
      <li v-for="chat in chats" :key="`${chat.kind}-${chat.ref}`">
        <button class="chat" type="button" @click="open(chat, $event)">
          <span
            class="chat__avatar"
            :class="{ 'chat__avatar--lobby': chat.kind === 'lobby' }"
            :style="chat.kind === 'lobby' ? { '--game': gameColor(chat.game_id) } : undefined"
          >
            <img v-if="chat.photo" :src="assetUrl(chat.photo.url)" alt="" />
            <template v-else>{{ chat.title.charAt(0).toUpperCase() }}</template>
          </span>
          <span class="chat__body">
            <span class="chat__top">
              <b class="chat__title">{{ chat.title }}</b>
              <span class="chat__time">{{ formatChatTime(chat.updated_at) }}</span>
            </span>
            <span class="chat__bottom">
              <span class="chat__preview" :class="{ 'chat__preview--new': chat.unread }">{{ preview(chat) }}</span>
              <b v-if="chat.unread" class="chat__unread">{{ chat.unread > 99 ? '99+' : chat.unread }}</b>
            </span>
          </span>
        </button>
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

.chats {
  margin: 0;
  padding: 0 14px;
  list-style: none;
}

.chats li + li {
  border-top: 1px dashed var(--line-strong);
}

.chat {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.chat:active {
  opacity: 0.7;
}

.chat__avatar {
  flex: none;
  display: grid;
  place-items: center;
  width: 50px;
  height: 50px;
  overflow: hidden;
  border: 1px solid var(--line-strong);
  border-radius: 50%;
  background: var(--raised);
  font-family: var(--font-pixel);
  font-size: 22px;
}

.chat__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Чат пати — квадрат с огоньком цвета игры */
.chat__avatar--lobby {
  border-radius: 14px;
  border-color: var(--game);
  box-shadow: 0 0 12px color-mix(in srgb, var(--game) 45%, transparent);
}

.chat__body {
  flex: 1;
  min-width: 0;
}

.chat__top,
.chat__bottom {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat__title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-title);
  font-size: 16px;
  font-weight: 400;
}

.chat__time {
  flex: none;
  color: var(--hint);
  font-size: 12px;
}

.chat__bottom {
  margin-top: 3px;
}

.chat__preview {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-2);
  font-size: 14px;
}

.chat__preview--new {
  color: var(--text);
}

.chat__unread {
  flex: none;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 6px;
  background: var(--accent);
  color: var(--accent-ink);
  font-family: var(--font-pixel);
  font-size: 14px;
  font-weight: 400;
  line-height: 20px;
  text-align: center;
  box-shadow: var(--glow-1);
}
</style>
