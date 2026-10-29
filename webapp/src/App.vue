<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import ConfirmDialog from './components/ConfirmDialog.vue'
import SplashScreen from './components/SplashScreen.vue'
import { openStartLink } from './router'
import { loadSession, session } from './stores/session'

// Заставка видна хотя бы столько, чтобы логотип успел собраться, — но только при первом запуске
const SPLASH_MIN_MS = 1300

const router = useRouter()
// Экраны показываем только после выбора стартового маршрута — иначе на мгновение
// монтируется лента и успевает запросить пати у ещё не прошедшего онбординг пользователя
const routed = ref(false)
let firstStart = true

async function start() {
  routed.value = false
  const minDelay = firstStart ? new Promise((resolve) => setTimeout(resolve, SPLASH_MIN_MS)) : null
  firstStart = false
  await Promise.all([loadSession(), minDelay])
  if (session.me) await router.replace(session.me.is_onboarded ? '/feed' : '/onboarding')
  if (session.me?.is_onboarded) await openStartLink() // открыли из уведомления бота
  routed.value = true
}

onMounted(start)
</script>

<template>
  <Transition name="splash">
    <SplashScreen v-if="session.status === 'loading' || (session.status === 'ready' && !routed)" />
    <SplashScreen v-else-if="session.status === 'error'">
      <p class="splash-error__title">Не получилось войти</p>
      <p class="hint splash-error__text">{{ session.error }}</p>
      <button class="btn btn-outline btn-small" type="button" @click="start">Попробовать ещё раз</button>
    </SplashScreen>
  </Transition>

  <RouterView v-if="session.status === 'ready' && routed" />
  <ConfirmDialog />
</template>

<style scoped>
.splash-error__title {
  margin: 0;
  font-family: var(--font-pixel);
  font-size: 20px;
  text-transform: uppercase;
}

.splash-error__text {
  margin: 0 0 8px;
  max-width: 300px;
}

.splash-leave-active {
  transition: opacity 0.35s ease;
}

.splash-leave-to {
  opacity: 0;
}
</style>
