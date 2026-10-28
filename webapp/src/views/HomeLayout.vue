<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { haptic } from '../telegram'

// Желе на вкладках чуть спокойнее, чем у переключателя по умолчанию: вкладки шире
const TAB_JELLY = { swell: 0.14, barge: 4 }

const TABS = [
  { to: '/feed', label: 'Пати', icon: 'M4 6h16M4 12h16M4 18h10' },
  {
    to: '/people',
    label: 'Лента',
    icon: 'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zm-6 9a6 6 0 0 1 12 0M16 4.5a3.5 3.5 0 0 1 0 6.5M18 14.5a6 6 0 0 1 3 5.5',
  },
  { to: '/profile', label: 'Профиль', icon: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 9a7 7 0 0 1 14 0' },
]

// Переход между вкладками: новый экран чуть въезжает с той стороны, куда переключились по панели
const route = useRoute()
const direction = ref<'forward' | 'back'>('forward')
watch(
  () => route.path,
  (to, from) => {
    const index = (path: string) => TABS.findIndex((tab) => path.startsWith(tab.to))
    direction.value = index(to) >= index(from) ? 'forward' : 'back'
  },
)

// Экраны вкладок не хранятся — новый всегда начинается сверху
function scrollToTop() {
  window.scrollTo(0, 0)
}
</script>

<template>
  <RouterView v-slot="{ Component }">
    <Transition :name="`tab-${direction}`" mode="out-in" @after-leave="scrollToTop">
      <component :is="Component" />
    </Transition>
  </RouterView>

  <nav v-jelly="TAB_JELLY" class="tabbar" aria-label="Разделы">
    <RouterLink v-for="tab in TABS" :key="tab.to" :to="tab.to" class="tabbar__item" @click="haptic.select()">
      <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
        <path :d="tab.icon" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <span>{{ tab.label }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
/* Смена вкладки — еле заметно: старый экран за 0.12 с уходит, новый проявляется со сдвигом и лёгким размытием */
.tab-forward-enter-active,
.tab-back-enter-active {
  transition:
    opacity 0.24s ease-out,
    transform 0.28s cubic-bezier(0.22, 1, 0.36, 1),
    filter 0.24s ease-out;
}

.tab-forward-leave-active,
.tab-back-leave-active {
  transition:
    opacity 0.12s ease-in,
    transform 0.12s ease-in;
}

.tab-forward-enter-from {
  opacity: 0;
  transform: translateX(12px);
  filter: blur(2px);
}

.tab-forward-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}

.tab-back-enter-from {
  opacity: 0;
  transform: translateX(-12px);
  filter: blur(2px);
}

.tab-back-leave-to {
  opacity: 0;
  transform: translateX(8px);
}

@media (prefers-reduced-motion: reduce) {
  .tab-forward-enter-from,
  .tab-forward-leave-to,
  .tab-back-enter-from,
  .tab-back-leave-to {
    transform: none;
    filter: none;
  }
}

.tabbar {
  position: fixed;
  left: 50%;
  bottom: calc(10px + var(--safe-bottom));
  transform: translateX(-50%);
  display: flex;
  gap: 4px;
  padding: 6px 14px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: color-mix(in srgb, var(--card) 86%, transparent);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: var(--shadow-float), var(--edge-light);
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
  background: linear-gradient(to bottom, rgb(var(--glow-rgb) / 0.16), rgb(var(--glow-rgb) / 0.04));
}

.tabbar__item.router-link-active::before {
  content: '';
  position: absolute;
  top: -7px;
  left: 22%;
  right: 22%;
  height: 2px;
  border-radius: 1px;
  background: var(--lamp);
  box-shadow: 0 0 8px 1px rgb(var(--glow-rgb) / 0.8), 0 4px 18px 2px rgb(var(--glow-rgb) / 0.25);
}

.tabbar__item.router-link-active svg {
  filter: drop-shadow(0 0 5px rgb(var(--glow-rgb) / 0.6));
}
</style>
