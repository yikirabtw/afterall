<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { loadSession, session } from './stores/session'

const router = useRouter()
// Экраны показываем только после выбора стартового маршрута — иначе на мгновение
// монтируется лента и успевает запросить пати у ещё не прошедшего онбординг пользователя
const routed = ref(false)

async function start() {
  routed.value = false
  await loadSession()
  if (session.me) await router.replace(session.me.is_onboarded ? '/feed' : '/onboarding')
  routed.value = true
}

onMounted(start)
</script>

<template>
  <div v-if="session.status === 'loading' || (session.status === 'ready' && !routed)" class="splash">
    <div class="splash__logo">after<span>all</span></div>
    <div class="spinner" />
  </div>

  <div v-else-if="session.status === 'error'" class="splash">
    <div class="splash__logo">after<span>all</span></div>
    <p class="splash__title">Не получилось войти</p>
    <p class="hint">{{ session.error }}</p>
    <button class="btn btn-primary btn-small" type="button" @click="start">Попробовать ещё раз</button>
  </div>

  <RouterView v-else />
</template>

<style scoped>
.splash {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 24px;
  text-align: center;
}

.splash__logo {
  font-size: 34px;
  font-weight: 900;
  letter-spacing: -0.04em;
}

.splash__logo span {
  color: var(--accent);
}

.splash__title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}

.splash .hint {
  margin: 0;
  max-width: 300px;
}
</style>
