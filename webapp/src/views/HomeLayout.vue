<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { chatUnread, startUnreadPolling, stopUnreadPolling } from '../stores/chats'
import { haptic } from '../telegram'

// Желе на вкладках чуть спокойнее, чем у переключателя по умолчанию: вкладки шире
const TAB_JELLY = { swell: 0.14, barge: 4 }

// Основные разделы — в общей панели; профиль — отдельной круглой кнопкой с человечком справа
const TABS = [
  { to: '/feed', label: 'Пати', icon: 'M4 6h16M4 12h16M4 18h10' },
  {
    to: '/people',
    label: 'Лента',
    icon: 'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zm-6 9a6 6 0 0 1 12 0M16 4.5a3.5 3.5 0 0 1 0 6.5M18 14.5a6 6 0 0 1 3 5.5',
  },
  { to: '/shop', label: 'Магазин', icon: 'M3.5 8h17l-1.4 13H4.9L3.5 8zM8 8V6.5a4 4 0 0 1 8 0V8' },
  { to: '/chats', label: 'Чат', icon: 'M2.5 4h19v13H10l-6 4.5V17H2.5V4z' },
]
const ORDER = [...TABS.map((tab) => tab.to), '/profile']

// Переход между вкладками: новый экран чуть въезжает с той стороны, куда переключились по панели
const route = useRoute()
const direction = ref<'forward' | 'back'>('forward')
watch(
  () => route.path,
  (to, from) => {
    const index = (path: string) => ORDER.findIndex((tab) => path.startsWith(tab))
    direction.value = index(to) >= index(from) ? 'forward' : 'back'
  },
)

// Экраны вкладок не хранятся — новый всегда начинается сверху
function scrollToTop() {
  window.scrollTo(0, 0)
}

// Непрочитанные — на значке «Чат», пока открыты основные разделы
onMounted(startUnreadPolling)
onBeforeUnmount(stopUnreadPolling)
</script>

<template>
  <RouterView v-slot="{ Component }">
    <Transition :name="`tab-${direction}`" mode="out-in" @after-leave="scrollToTop">
      <component :is="Component" />
    </Transition>
  </RouterView>

  <div class="dock" :class="`dock--${direction}`">
    <nav v-jelly="TAB_JELLY" class="tabbar" aria-label="Разделы">
      <RouterLink v-for="tab in TABS" :key="tab.to" :to="tab.to" class="tabbar__item" @click="haptic.select()">
        <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
          <path :d="tab.icon" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <span>{{ tab.label }}</span>
        <b v-if="tab.to === '/chats' && chatUnread" class="tabbar__badge">{{ chatUnread > 99 ? '99+' : chatUnread }}</b>
      </RouterLink>
    </nav>

    <RouterLink to="/profile" class="dock__profile" aria-label="Профиль" @click="haptic.select()">
      <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true">
        <path
          d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 9a7 7 0 0 1 14 0"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </RouterLink>
  </div>
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

/* Нижний док: панель разделов и отдельная кнопка профиля справа */
.dock {
  position: fixed;
  left: 50%;
  bottom: calc(10px + var(--safe-bottom));
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 10;
}

.tabbar,
.dock__profile {
  border: 1px solid var(--line);
  background: color-mix(in srgb, var(--card) 86%, transparent);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: var(--shadow-float), var(--edge-light);
}

.tabbar {
  display: flex;
  gap: 2px;
  padding: 6px 12px;
  border-radius: 18px;
}

.tabbar__item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  min-width: 60px;
  padding: 7px 6px 9px;
  border-radius: 12px;
  color: var(--g-500);
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-decoration: none;
  transition: color 0.15s ease, background 0.15s ease;
}

/* Активная вкладка — подсвечена, снизу под подписью светящаяся полоса */
.tabbar__item.router-link-active {
  color: var(--text);
  background: linear-gradient(to bottom, rgb(var(--glow-rgb) / 0.16), rgb(var(--glow-rgb) / 0.04));
}

/*
  Полоса снизу есть у каждой кнопки, но видна только у активной. При переключении свет «перетекает»:
  у старой вкладки полоса сжимается в сторону новой, у новой — вырастает со стороны старой.
  Сторону задаёт направление перехода (dock--forward / dock--back).
*/
.tabbar__item::after,
.dock__profile::after {
  content: '';
  position: absolute;
  bottom: 3px;
  left: 26%;
  right: 26%;
  height: 2px;
  border-radius: 1px;
  background: var(--lamp);
  box-shadow: 0 0 8px 1px rgb(var(--glow-rgb) / 0.8), 0 -4px 14px 1px rgb(var(--glow-rgb) / 0.25);
  opacity: 0;
  transform: scaleX(0);
  transition:
    transform 0.32s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.32s ease;
}

.tabbar__item.router-link-active::after,
.dock__profile.router-link-active::after {
  opacity: 1;
  transform: scaleX(1);
}

/* Вперёд (вправо по панели): старая гаснет к правому краю, новая растёт от левого */
.dock--forward .tabbar__item::after,
.dock--forward .dock__profile::after {
  transform-origin: right center;
}

.dock--forward .tabbar__item.router-link-active::after,
.dock--forward .dock__profile.router-link-active::after {
  transform-origin: left center;
}

/* Назад — зеркально */
.dock--back .tabbar__item::after,
.dock--back .dock__profile::after {
  transform-origin: left center;
}

.dock--back .tabbar__item.router-link-active::after,
.dock--back .dock__profile.router-link-active::after {
  transform-origin: right center;
}

@media (prefers-reduced-motion: reduce) {
  .tabbar__item::after,
  .dock__profile::after {
    transition: none;
  }
}

.tabbar__item.router-link-active svg {
  filter: drop-shadow(0 0 5px rgb(var(--glow-rgb) / 0.6));
}

/* Непрочитанные — красный кружок с кольцом цвета панели и свечением: не сливается с белой иконкой */
.tabbar__badge {
  position: absolute;
  top: 0;
  right: 4px;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  border: 2px solid var(--card);
  border-radius: 10px;
  background: var(--danger);
  color: #fff;
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 800;
  line-height: 16px;
  letter-spacing: 0;
  text-align: center;
  box-shadow: 0 0 10px color-mix(in srgb, var(--danger) 70%, transparent);
}

/* Профиль — круглая кнопка с человечком */
.dock__profile {
  position: relative;
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  padding: 4px;
  border-radius: 50%;
  color: var(--g-500);
  text-decoration: none;
  transition: color 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}

.dock__profile:active {
  transform: scale(0.94);
}

.dock__profile.router-link-active {
  color: var(--text);
  border-color: var(--g-700);
}

.dock__profile.router-link-active svg {
  filter: drop-shadow(0 0 5px rgb(var(--glow-rgb) / 0.6));
}

.dock__profile::after {
  bottom: 8px;
  left: 32%;
  right: 32%;
}
</style>
