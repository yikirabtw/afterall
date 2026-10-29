<script setup lang="ts">
import { ref, watch } from 'vue'

import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { ReportReason } from '../api/types'
import { REPORT_REASONS } from '../labels'
import { SHEET_MS } from '../sheet'
import { confirmAction, haptic } from '../telegram'

/*
  Шторка «Пожаловаться / Заблокировать» — в мэтчах и чатах (решение пользователя).
  Жалоба сразу блокирует человека: он пропадает у тебя отовсюду, а жалоба уходит модераторам в бот.
  В общей пати (lobbyId) модератор увидит сообщения этого человека в её чате.
*/
const props = defineProps<{ open: boolean; userId: number; name: string; lobbyId?: number | null }>()
const emit = defineEmits<{ close: []; done: [kind: 'reported' | 'blocked'] }>()

const COMMENT_MAX = 500

const step = ref<'menu' | 'report'>('menu')
const reason = ref<ReportReason | null>(null)
const comment = ref('')
const sending = ref(false)
const error = ref('')

watch(
  () => props.open,
  (open) => {
    if (!open) return
    step.value = 'menu'
    reason.value = null
    comment.value = ''
    error.value = ''
  },
)

function toReport() {
  haptic.select()
  step.value = 'report'
}

async function block() {
  const sure = await confirmAction(
    `Заблокировать «${props.name}»? Вы перестанете видеть друг друга — мэтч и переписка пропадут. Вернуть можно в профиле.`,
  )
  if (!sure) return
  await run(() => api.block(props.userId), 'blocked')
}

async function report() {
  if (!reason.value) return
  await run(
    () =>
      api.report({
        user_id: props.userId,
        reason: reason.value!,
        comment: comment.value.trim() || null,
        lobby_id: props.lobbyId ?? null,
      }),
    'reported',
  )
}

async function run(action: () => Promise<void>, kind: 'reported' | 'blocked') {
  sending.value = true
  error.value = ''
  try {
    await action()
    haptic.success()
    emit('done', kind)
  } catch (e) {
    error.value = errorMessage(e)
    haptic.error()
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet" :duration="SHEET_MS">
      <div v-if="open" class="sheet-backdrop" @click.self="emit('close')">
        <section class="sheet" role="dialog" :aria-label="name">
          <div class="sheet__handle" aria-hidden="true" />

          <template v-if="step === 'menu'">
            <h2 class="sheet__title">{{ name }}</h2>
            <div class="stack rise-in">
              <button class="card action action--danger" type="button" :disabled="sending" @click="toReport">
                <b>Пожаловаться</b>
                <span class="hint">Человек пропадёт у тебя, жалобу разберёт модератор. Он не узнает, кто пожаловался.</span>
              </button>
              <button class="card action" type="button" :disabled="sending" @click="block">
                <b>Заблокировать</b>
                <span class="hint">Без жалобы: вы просто перестанете видеть друг друга.</span>
              </button>
            </div>
          </template>

          <template v-else>
            <h2 class="sheet__title">Что случилось?</h2>
            <div class="reasons rise-in" role="radiogroup" aria-label="Причина">
              <button
                v-for="option in REPORT_REASONS"
                :key="option.value"
                class="reason"
                type="button"
                role="radio"
                :aria-checked="reason === option.value"
                @click="(reason = option.value), haptic.select()"
              >
                <span class="reason__dot" aria-hidden="true" />
                {{ option.label }}
              </button>
            </div>
            <textarea
              v-model="comment"
              class="input comment"
              rows="2"
              :maxlength="COMMENT_MAX"
              placeholder="Подробности — по желанию"
            />
            <p v-if="reason === 'minor_safety'" class="hint urgent">
              Такие жалобы модератор разбирает первыми. Если есть прямая угроза — расскажи взрослому, которому доверяешь.
            </p>
          </template>

          <p v-if="error" class="error-text">{{ error }}</p>

          <div v-if="step === 'report'" class="sheet__actions">
            <button class="btn btn-primary" type="button" :disabled="!reason || sending" @click="report">
              Отправить жалобу
            </button>
            <button class="btn btn-ghost" type="button" :disabled="sending" @click="step = 'menu'">Назад</button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.action {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  text-align: left;
  color: var(--text);
  font: inherit;
  cursor: pointer;
}

.action b {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.action--danger b {
  color: var(--danger);
  text-shadow: 0 0 10px color-mix(in srgb, var(--danger) 45%, transparent);
}

.action:disabled {
  opacity: 0.5;
}

.reasons {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.reason {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 46px;
  padding: 0 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
  color: var(--text);
  font: inherit;
  font-size: 15px;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.reason__dot {
  flex: none;
  width: 16px;
  height: 16px;
  border: 2px solid var(--line-strong);
  border-radius: 50%;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.reason[aria-checked='true'] {
  border-color: var(--lamp);
  box-shadow: 0 0 12px rgb(var(--glow-rgb) / 0.2);
}

.reason[aria-checked='true'] .reason__dot {
  border: 5px solid var(--lamp);
  box-shadow: 0 0 8px rgb(var(--glow-rgb) / 0.6);
}

.comment {
  width: 100%;
  margin-top: 12px;
  resize: none;
}

.urgent {
  margin: 10px 0 0;
  color: var(--warn);
}

.sheet__actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 16px;
}
</style>
