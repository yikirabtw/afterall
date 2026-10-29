<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import { ApiError, assetUrl, api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { ChatHead, ChatKind, ChatMessage } from '../api/types'
import FuseButton from '../components/FuseButton.vue'
import PersonSheet from '../components/PersonSheet.vue'
import { formatChatTime, formatMessageTime } from '../format'
import { gameColor, gameTitle } from '../lobby'
import { goBack } from '../router'
import { refreshUnread } from '../stores/chats'
import { haptic, insideTelegram, useBackButton } from '../telegram'

// Переписка: личная после мэтча или общая у пати. Новые сообщения забираем опросом раз в 3 секунды
const props = defineProps<{ kind: ChatKind; target: number }>()

const POLL_MS = 3000
const NEAR_BOTTOM = 120 // px: если пользователь читает внизу — новые сообщения докручиваем сами

const head = ref<ChatHead | null>(null)
const messages = ref<ChatMessage[]>([])
const hasMore = ref(false)
const loading = ref(true)
const loadingOlder = ref(false)
const loadError = ref('')
const sendError = ref('')
const sending = ref(false)
const draft = ref('')
const input = ref<HTMLTextAreaElement>()
let timer = 0

useBackButton(goBack, ref(true))

const subtitle = computed(() => {
  if (!head.value) return ''
  return head.value.kind === 'direct' ? 'взаимный лайк' : `${gameTitle(head.value)} · чат пати`
})

function nearBottom(): boolean {
  return window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - NEAR_BOTTOM
}

async function scrollToBottom(smooth = false) {
  await nextTick()
  window.scrollTo({ top: document.documentElement.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
}

/** Добавить сообщения, которых ещё нет (опрос и отправка могут принести одно и то же) */
function merge(fresh: ChatMessage[]): boolean {
  const known = new Set(messages.value.map((message) => message.id))
  const added = fresh.filter((message) => !known.has(message.id))
  messages.value.push(...added)
  return added.length > 0
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const chat = await api.chat(props.kind, props.target)
    head.value = chat
    messages.value = chat.messages
    hasMore.value = chat.has_more
    void refreshUnread() // открыли — значит, прочитали
    await scrollToBottom()
  } catch (e) {
    loadError.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function poll() {
  if (!head.value || document.hidden) return
  try {
    const after = messages.value.at(-1)?.id ?? 0
    const chat = await api.chat(props.kind, props.target, { after })
    head.value.can_send = chat.can_send
    const stick = nearBottom()
    if (merge(chat.messages)) {
      void refreshUnread()
      if (stick) await scrollToBottom(true)
    }
  } catch {
    // сеть моргнула — попробуем в следующий раз
  }
}

// Старые сообщения подгружаются сверху, не сдвигая то, что человек сейчас читает
async function loadOlder() {
  const first = messages.value[0]
  if (!first || loadingOlder.value) return
  loadingOlder.value = true
  try {
    const chat = await api.chat(props.kind, props.target, { before: first.id })
    const height = document.documentElement.scrollHeight
    messages.value.unshift(...chat.messages)
    hasMore.value = chat.has_more
    await nextTick()
    window.scrollTo({ top: window.scrollY + document.documentElement.scrollHeight - height })
  } catch (e) {
    sendError.value = errorMessage(e)
  } finally {
    loadingOlder.value = false
  }
}

async function send() {
  const body = draft.value.trim()
  if (!body || sending.value || !head.value?.can_send) return
  sending.value = true
  sendError.value = ''
  try {
    merge([await api.sendMessage(props.kind, props.target, body)])
    draft.value = ''
    resize()
    haptic.tap()
    await scrollToBottom(true)
  } catch (e) {
    sendError.value = errorMessage(e)
    haptic.error()
  } finally {
    sending.value = false
    input.value?.focus()
  }
}

// Поле растёт по тексту, но не выше пяти строк
function resize() {
  const el = input.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight + 2, 120)}px` // +2 — рамка поля
  el.style.overflowY = el.scrollHeight + 2 > 120 ? 'auto' : 'hidden'
}

function showSender(index: number): boolean {
  const message = messages.value[index]!
  if (props.kind !== 'lobby' || message.mine) return false
  return messages.value[index - 1]?.sender_id !== message.sender_id
}

function dayOf(message: ChatMessage): string {
  return new Date(message.created_at).toDateString()
}

function showDay(index: number): boolean {
  return index === 0 || dayOf(messages.value[index - 1]!) !== dayOf(messages.value[index]!)
}

function dayLabel(message: ChatMessage): string {
  const label = formatChatTime(message.created_at)
  if (label.includes(':')) return 'Сегодня'
  return label === 'вчера' ? 'Вчера' : label
}

// --- Удаление личного чата: это удаление мэтча у обоих. Пока горит фитиль — переписка погашена ---

const leaving = ref(false)
let leftScreen = false

async function purge() {
  try {
    await api.deleteMatch(props.target)
  } catch (e) {
    // «Уже нет» — мэтч удалил второй человек: результат тот же
    if (!(e instanceof ApiError && e.code === 'match_not_found')) {
      leaving.value = false
      sendError.value = errorMessage(e)
      return
    }
  }
  void refreshUnread()
  if (!leftScreen) goBack() // если ушли сами во время отсчёта — второй раз назад не идём
}

// --- Пожаловаться / заблокировать: в личном чате — собеседника («⋯» в шапке),
// в чате пати — автора сообщения (нажатие на его имя) ---

const sheetFor = ref<{ id: number; name: string } | null>(null)
const notice = ref('')

function openSheet(id: number, name: string) {
  haptic.tap()
  sheetFor.value = { id, name }
}

function onSafetyDone() {
  const person = sheetFor.value!
  sheetFor.value = null
  void refreshUnread()
  if (props.kind === 'direct') {
    goBack() // переписки с ним больше нет
    return
  }
  // В пати остаёмся — его сообщений просто больше не видно
  messages.value = messages.value.filter((message) => message.sender_id !== person.id)
  notice.value = `Сообщений «${person.name}» больше не видно.`
}

onMounted(async () => {
  await load()
  timer = window.setInterval(poll, POLL_MS)
})

onBeforeUnmount(() => {
  leftScreen = true // до кнопки: она при уходе с экрана сразу «догорает» и вызывает purge
  window.clearInterval(timer)
})
</script>

<template>
  <main class="chat-page" :class="{ 'chat-page--leaving': leaving }">
    <header class="chat-head">
      <button v-if="!insideTelegram" class="btn btn-ghost chat-head__back" type="button" aria-label="Назад" @click="goBack">
        ←
      </button>
      <template v-if="head">
        <span
          class="chat-head__avatar"
          :class="{ 'chat-head__avatar--lobby': head.kind === 'lobby' }"
          :style="head.kind === 'lobby' ? { '--game': gameColor(head.game_id) } : undefined"
        >
          <img v-if="head.photo" :src="assetUrl(head.photo.url)" alt="" />
          <template v-else>{{ head.title.charAt(0).toUpperCase() }}</template>
        </span>
        <span class="chat-head__text">
          <b class="chat-head__title">{{ head.title }}</b>
          <span class="chat-head__subtitle">{{ subtitle }}</span>
        </span>
        <FuseButton
          v-if="head.kind === 'direct' && !loadError"
          class="chat-head__delete"
          label="Удалить"
          undo-label="Вернуть"
          @commit="leaving = true"
          @undo="leaving = false"
          @fuse-end="purge"
        />
        <button
          v-if="head.kind === 'direct' && !loadError"
          class="chat-head__more"
          type="button"
          aria-label="Пожаловаться или заблокировать"
          @click="openSheet(target, head.title)"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <circle cx="5" cy="12" r="1.8" fill="currentColor" />
            <circle cx="12" cy="12" r="1.8" fill="currentColor" />
            <circle cx="19" cy="12" r="1.8" fill="currentColor" />
          </svg>
        </button>
      </template>
    </header>

    <div v-if="loading" class="chat-state"><span class="dots-loader"><i /><i /><i /></span></div>
    <div v-else-if="loadError" class="chat-state">
      <p class="empty__title">Чат недоступен</p>
      <p class="hint">{{ loadError }}</p>
      <button class="btn btn-ghost" type="button" @click="goBack">Назад</button>
    </div>

    <template v-else>
      <p v-if="leaving" class="leaving-note" role="status">Мэтч и переписка удалятся у обоих</p>
      <p v-if="notice" class="hint notice" role="status">{{ notice }}</p>
      <section class="messages" aria-live="polite">
        <button v-if="hasMore" class="btn btn-ghost btn-small messages__older" type="button" :disabled="loadingOlder" @click="loadOlder">
          Показать раньше
        </button>
        <p v-if="!messages.length && !leaving" class="hint messages__empty">
          {{ head?.kind === 'direct' ? 'Напиши первым — договоритесь о катке 👋' : 'Здесь пишут все участники пати' }}
        </p>

        <template v-for="(message, index) in messages" :key="message.id">
          <span v-if="showDay(index)" class="messages__day">{{ dayLabel(message) }}</span>
          <div class="bubble" :class="message.mine ? 'bubble--mine' : 'bubble--theirs'">
            <button
              v-if="showSender(index)"
              class="bubble__sender"
              type="button"
              @click="openSheet(message.sender_id, message.sender_name)"
            >
              {{ message.sender_name }}
            </button>
            <span class="bubble__text">{{ message.body }}</span>
            <span class="bubble__time">{{ formatMessageTime(message.created_at) }}</span>
          </div>
        </template>
      </section>

      <footer class="composer">
        <p v-if="sendError" class="error-text composer__error">{{ sendError }}</p>
        <p v-if="head && !head.can_send" class="hint composer__closed">Пати закончилась — в её чате можно только читать.</p>
        <form v-else class="composer__row" @submit.prevent="send">
          <textarea
            ref="input"
            v-model="draft"
            class="input composer__input"
            rows="1"
            maxlength="1000"
            placeholder="Сообщение"
            enterkeyhint="send"
            @input="resize"
            @keydown.enter.exact.prevent="send"
          />
          <button class="composer__send" type="submit" aria-label="Отправить" :disabled="sending || !draft.trim()">
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
              <path d="M5 12h13M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
        </form>
      </footer>
    </template>
    <PersonSheet
      :open="sheetFor !== null"
      :user-id="sheetFor?.id ?? 0"
      :name="sheetFor?.name ?? ''"
      :lobby-id="kind === 'lobby' ? target : null"
      @close="sheetFor = null"
      @done="onSafetyDone"
    />
  </main>
</template>

<style scoped>
.chat-page {
  min-height: 100vh;
  max-width: 560px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  padding-bottom: calc(80px + var(--safe-bottom));
}

/* Шапка прилипает сверху и чуть прозрачная — переписка видна под ней */
.chat-head {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--line);
  background: color-mix(in srgb, var(--page) 86%, transparent);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

.chat-head__back {
  min-height: 36px;
  padding: 0 6px 0 0;
  font-size: 20px;
}

.chat-head__avatar {
  flex: none;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  overflow: hidden;
  border: 1px solid var(--line-strong);
  border-radius: 50%;
  background: var(--raised);
  font-family: var(--font-pixel);
  font-size: 18px;
}

.chat-head__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.chat-head__avatar--lobby {
  border-radius: 12px;
  border-color: var(--game);
  box-shadow: 0 0 10px color-mix(in srgb, var(--game) 45%, transparent);
}

.chat-head__text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-head__more {
  flex: none;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--text-2);
  cursor: pointer;
}

.chat-head__more:active {
  background: var(--raised);
  color: var(--text);
}

.notice {
  margin: 10px 16px 0;
  text-align: center;
}

.chat-head__delete {
  flex: none;
  margin-left: auto;
  min-height: 34px;
  padding: 0 12px;
  font-size: 12px;
}

/* Пока горит фитиль: переписка и поле ввода гаснут, сверху — что произойдёт */
.messages,
.composer {
  transition: opacity 0.25s ease;
}

.chat-page--leaving .messages {
  opacity: 0.2;
  pointer-events: none;
}

.chat-page--leaving .composer {
  opacity: 0;
  pointer-events: none;
}

.leaving-note {
  position: fixed;
  top: 50%;
  left: 50%;
  z-index: 4;
  margin: 0;
  padding: 10px 16px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: var(--raised);
  color: var(--text);
  font-size: 14px;
  white-space: nowrap;
  transform: translate(-50%, -50%);
  animation: note-in 0.25s ease;
}

@keyframes note-in {
  from {
    opacity: 0;
    transform: translate(-50%, calc(-50% + 6px));
  }
}

.chat-head__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-title);
  font-size: 17px;
  font-weight: 400;
}

.chat-head__subtitle {
  color: var(--hint);
  font-size: 12px;
}

.chat-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 40px 24px;
  text-align: center;
}

.messages {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
}

.messages__older {
  align-self: center;
  margin-bottom: 8px;
}

.messages__empty {
  margin: auto;
  padding: 40px 0;
  text-align: center;
}

.messages__day {
  align-self: center;
  margin: 12px 0 6px;
  padding: 3px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--hint);
  font-family: var(--font-display);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

/* Пузыри: свои — справа, цветом акцента; чужие — слева, карточкой */
.bubble {
  max-width: 80%;
  padding: 7px 12px 6px;
  border-radius: 16px;
  font-size: 15px;
  line-height: 1.35;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  animation: bubble-in 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}

.bubble--mine {
  align-self: flex-end;
  border-bottom-right-radius: 5px;
  background: var(--accent);
  color: var(--accent-ink);
  box-shadow: 0 0 14px rgb(var(--glow-rgb) / 0.12);
}

.bubble--theirs {
  align-self: flex-start;
  border: 1px solid var(--line);
  border-bottom-left-radius: 5px;
  background: var(--card);
  box-shadow: var(--edge-light);
}

/* Имя автора в чате пати нажимается — пожаловаться или заблокировать */
.bubble__sender {
  display: block;
  margin-bottom: 2px;
  padding: 0;
  border: 0;
  background: none;
  text-align: left;
  cursor: pointer;
  color: var(--text-2);
  font-family: var(--font-display);
  font-size: 11px;
  letter-spacing: 0.06em;
}

.bubble__time {
  float: right;
  margin: 6px 0 0 10px;
  font-size: 10.5px;
  opacity: 0.55;
}

@keyframes bubble-in {
  from {
    opacity: 0;
    transform: translateY(6px) scale(0.98);
  }
}

/* Поле ввода закреплено внизу */
.composer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 5;
  padding: 10px 12px calc(10px + var(--safe-bottom));
  background: linear-gradient(to top, var(--page) 75%, transparent);
}

.composer__row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  max-width: 536px;
  margin: 0 auto;
}

.composer__input {
  flex: 1;
  min-height: 44px;
  max-height: 120px;
  padding: 11px 16px;
  border-radius: 22px;
  resize: none;
  line-height: 1.35;
  overflow-y: hidden; /* полоса прокрутки — только когда текст выше пяти строк (resize()) */
}

.composer__send {
  flex: none;
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: 50%;
  background: var(--accent);
  color: var(--accent-ink);
  box-shadow: var(--glow-1);
  cursor: pointer;
  transition: transform 0.1s ease, opacity 0.15s ease;
}

.composer__send:active {
  transform: scale(0.92);
}

.composer__send:disabled {
  opacity: 0.4;
  box-shadow: none;
}

.composer__error,
.composer__closed {
  max-width: 536px;
  margin: 0 auto 8px;
  text-align: center;
}

@media (prefers-reduced-motion: reduce) {
  .bubble {
    animation: none;
  }
}
</style>
