<script setup lang="ts">
import { haptic } from '../telegram'

const TABS = [
  { to: '/feed', label: 'Пати', icon: 'M4 6h16M4 12h16M4 18h10' },
  {
    to: '/people',
    label: 'Лента',
    icon: 'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zm-6 9a6 6 0 0 1 12 0M16 4.5a3.5 3.5 0 0 1 0 6.5M18 14.5a6 6 0 0 1 3 5.5',
  },
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
  border: 1px solid var(--line);
  border-radius: 18px;
  background: rgb(10 10 10 / 0.86);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 10px 30px rgb(0 0 0 / 0.6), var(--edge-light);
  z-index: 10;
}

.tabbar__item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  min-width: 78px;
  padding: 7px 12px 6px;
  border-radius: 12px;
  color: var(--g-500);
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  text-decoration: none;
  transition: color 0.15s ease, background 0.15s ease;
}

/* Активная вкладка — «под лампой»: светящаяся полоса над ней и мягкий свет вниз */
.tabbar__item.router-link-active {
  color: var(--text);
  background: linear-gradient(to bottom, rgb(255 255 255 / 0.1), transparent 80%);
}

.tabbar__item.router-link-active::before {
  content: '';
  position: absolute;
  top: -7px;
  left: 22%;
  right: 22%;
  height: 2px;
  border-radius: 1px;
  background: #fff;
  box-shadow: 0 0 8px 1px rgb(255 255 255 / 0.8), 0 4px 18px 2px rgb(255 255 255 / 0.25);
}

.tabbar__item.router-link-active svg {
  filter: drop-shadow(0 0 5px rgb(255 255 255 / 0.6));
}
</style>
