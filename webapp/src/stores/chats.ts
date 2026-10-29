// Непрочитанные сообщения — для значка на вкладке «Чат». Опрашиваем сервер, пока открыты основные разделы.

import { ref } from 'vue'

import { api } from '../api/client'

const POLL_MS = 15_000

export const chatUnread = ref(0)

let timer = 0

export async function refreshUnread(): Promise<void> {
  try {
    const chats = await api.chats()
    chatUnread.value = chats.reduce((total, chat) => total + chat.unread, 0)
  } catch {
    // значок — не главное: при ошибке сети просто оставляем прежнее число
  }
}

export function startUnreadPolling(): void {
  void refreshUnread()
  window.clearInterval(timer)
  timer = window.setInterval(refreshUnread, POLL_MS)
}

export function stopUnreadPolling(): void {
  window.clearInterval(timer)
}
