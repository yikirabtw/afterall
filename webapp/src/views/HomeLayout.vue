<script setup lang="ts">
import { haptic } from '../telegram'

const TABS = [
  { to: '/feed', label: 'Пати', icon: 'M4 6h16M4 12h16M4 18h10' },
  { to: '/mine', label: 'Мои', icon: 'M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z' },
  { to: '/profile', label: 'Профиль', icon: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 9a7 7 0 0 1 14 0' },
]
</script>

<template>
  <RouterView />

  <nav class="tabbar" aria-label="Разделы">
    <RouterLink v-for="tab in TABS" :key="tab.to" :to="tab.to" class="tabbar__item" @click="haptic.select()">
      <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
        <path :d="tab.icon" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <span>{{ tab.label }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.tabbar {
  position: fixed;
  left: 50%;
  bottom: calc(10px + var(--safe-bottom));
  transform: translateX(-50%);
  display: flex;
  gap: 4px;
  padding: 6px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--card) 88%, transparent);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 8px 28px rgb(0 0 0 / 0.28);
  border: 1px solid var(--line);
  z-index: 10;
}

.tabbar__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-width: 76px;
  padding: 6px 12px;
  border-radius: 999px;
  color: var(--hint);
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}

.tabbar__item.router-link-active {
  background: var(--accent);
  color: var(--accent-ink);
}
</style>
