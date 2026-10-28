<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError, api } from '../../api/client'
import { errorMessage } from '../../api/errors'
import type { Me } from '../../api/types'
import { session, setMe } from '../../stores/session'
import { haptic, insideTelegram, useBackButton } from '../../telegram'
import StepAge from './StepAge.vue'
import StepGames from './StepGames.vue'
import StepProfile from './StepProfile.vue'

const STEPS = [StepAge, StepProfile, StepGames]
// Что API называет недостающим → какой шаг открыть
const STEP_FOR_MISSING = ['birth_date', 'profile', 'games']

const router = useRouter()
const step = ref(firstUnfinishedStep(session.me!))
const finishing = ref(false)
const error = ref('')

function firstUnfinishedStep(me: Me): number {
  if (!me.birth_date) return 0
  if (!me.profile) return 1
  return 2
}

function back() {
  if (step.value > 0) step.value -= 1
}

const canGoBack = computed(() => step.value > 0 && !finishing.value)
useBackButton(back, canGoBack)

async function next(me?: Me) {
  if (me) setMe(me)
  error.value = ''
  haptic.tap()
  if (step.value < STEPS.length - 1) {
    step.value += 1
    window.scrollTo(0, 0)
  } else {
    await finish()
  }
}

async function finish() {
  finishing.value = true
  try {
    setMe(await api.completeOnboarding())
    haptic.success()
    await router.replace('/feed')
  } catch (e) {
    if (e instanceof ApiError && e.code === 'onboarding_incomplete') {
      const missing = (e.detail as { missing: string[] }).missing
      step.value = STEP_FOR_MISSING.findIndex((name) => missing.includes(name))
    } else {
      error.value = errorMessage(e)
      haptic.error()
    }
  } finally {
    finishing.value = false
  }
}
</script>

<template>
  <main class="page">
    <header class="progress">
      <!-- Вне Telegram системной кнопки «Назад» нет — показываем свою -->
      <button v-if="!insideTelegram && canGoBack" class="btn btn-ghost progress__back" type="button" @click="back">
        ← Назад
      </button>
      <div class="progress__bar" role="progressbar" :aria-valuenow="step + 1" aria-valuemin="1" :aria-valuemax="STEPS.length">
        <span v-for="(_, index) in STEPS" :key="index" :class="{ active: index <= step }" />
      </div>
      <span class="progress__label">Шаг {{ step + 1 }} из {{ STEPS.length }}</span>
    </header>

    <component :is="STEPS[step]" :key="step" :busy="finishing" @done="next" />
    <p v-if="error" class="error-text">{{ error }}</p>
  </main>
</template>

<style scoped>
.progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.progress__back {
  padding: 0;
  margin-right: 4px;
}

.progress__bar {
  flex: 1;
  display: flex;
  gap: 6px;
}

.progress__bar span {
  flex: 1;
  height: 2px;
  border-radius: 1px;
  background: var(--line-strong);
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.progress__bar span.active {
  background: var(--accent);
  box-shadow: 0 0 8px 1px rgb(var(--glow-rgb) / 0.7);
}

.progress__label {
  font-family: var(--font-pixel);
  font-size: 14px;
  color: var(--text-2);
  white-space: nowrap;
}
</style>
