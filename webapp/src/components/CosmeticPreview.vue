<script setup lang="ts">
import { computed } from 'vue'

import { assetUrl } from '../api/client'
import reflection from '../assets/reflection.jpg'
import smoke from '../assets/splash-bg-poster.jpg'
import type { Cosmetic } from '../shop'
import { session } from '../stores/session'

// Как вещь из магазина будет выглядеть — на своей же аватарке и нике. Всё рисуется CSS, без картинок-заглушек
const props = defineProps<{ item: Cosmetic; large?: boolean }>()

const name = computed(() => session.me?.profile?.display_name ?? session.me?.first_name ?? 'Ты')
const photo = computed(() => {
  const first = session.me?.photos[0]
  return first ? assetUrl(first.url) : null
})

// Пиксельные значки 7×7: # — закрашенная клетка
const BADGES: Record<string, string[]> = {
  night: ['..###..', '.##....', '##.....', '##.....', '##.....', '.##....', '..###..'],
  heart: ['.##.##.', '#######', '#######', '#######', '.#####.', '..###..', '...#...'],
  star: ['...#...', '...#...', '#######', '.#####.', '..###..', '.##.##.', '.#...#.'],
  crown: ['#..#..#', '#.###.#', '#######', '#######', '#######', '.......', '#######'],
}

const cells = computed(() => {
  const rows = BADGES[props.item.style] ?? []
  return rows.flatMap((row, y) => [...row].map((cell, x) => (cell === '#' ? { x, y } : null)).filter((c) => c !== null))
})

// Палитры тем: фон, карточка, текст
const THEMES: Record<string, [string, string, string]> = {
  blue: ['#070b1a', '#121a33', '#a9c4ff'],
  sepia: ['#15100a', '#241b12', '#ecd9b6'],
}

const backgroundImage = computed(() => {
  if (props.item.style === 'smoke') return `url(${smoke})`
  if (props.item.style === 'light') return `url(${reflection})`
  return undefined
})
</script>

<template>
  <div class="preview" :class="[`preview--${item.kind}`, { 'preview--large': large }]">
    <!-- Рамка аватара -->
    <template v-if="item.kind === 'frame'">
      <span class="avatar" :class="`frame--${item.style}`">
        <img v-if="photo" :src="photo" alt="" />
        <template v-else>{{ name.charAt(0).toUpperCase() }}</template>
      </span>
    </template>

    <!-- Фон карточки -->
    <div
      v-else-if="item.kind === 'background'"
      class="mini-card theme-dark"
      :class="`bg--${item.style}`"
      :style="{ backgroundImage }"
    >
      <span class="avatar avatar--small">
        <img v-if="photo" :src="photo" alt="" />
        <template v-else>{{ name.charAt(0).toUpperCase() }}</template>
      </span>
      <b class="mini-card__name">{{ name }}</b>
    </div>

    <!-- Значок у ника -->
    <div v-else-if="item.kind === 'badge'" class="nick">
      <b class="nick__name">{{ name }}</b>
      <svg class="pixel-badge" viewBox="0 0 7 7" aria-hidden="true" shape-rendering="crispEdges">
        <rect v-for="cell in cells" :key="`${cell.x}-${cell.y}`" :x="cell.x" :y="cell.y" width="1" height="1" />
      </svg>
    </div>

    <!-- Сцена мэтча -->
    <div v-else-if="item.kind === 'match'" class="scene theme-dark" :class="`scene--${item.style}`">
      <template v-if="item.style === 'sign'">
        <span class="sign">MATCH</span>
      </template>
      <template v-else>
        <span class="scene__cord" />
        <span class="scene__shade" />
        <span class="scene__beam" />
      </template>
    </div>

    <!-- Тема интерфейса -->
    <div
      v-else-if="item.kind === 'theme'"
      class="theme"
      :style="{
        '--t-bg': THEMES[item.style]?.[0],
        '--t-card': THEMES[item.style]?.[1],
        '--t-text': THEMES[item.style]?.[2],
      }"
    >
      <span class="theme__card">
        <b>Аа</b>
        <i />
        <i />
      </span>
    </div>
  </div>
</template>

<style scoped>
.preview {
  position: relative;
  display: grid;
  place-items: center;
  aspect-ratio: 1;
  overflow: hidden;
  border-radius: 12px;
  background: var(--raised);
}

.preview--large {
  aspect-ratio: 16 / 10;
}

/* --- Рамки --- */

.avatar {
  position: relative;
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--g-200);
  color: var(--text);
  font-family: var(--font-pixel);
  font-size: 24px;
}

.preview--large .avatar {
  width: 84px;
  height: 84px;
  font-size: 34px;
}

/* Абсолютно: в ячейке сетки процентная высота считалась бы от фото, и круг вытягивался в овал */
.avatar img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border-radius: inherit;
  object-fit: cover;
}

.frame--neon {
  border: 2px solid var(--lamp);
  box-shadow:
    0 0 8px rgb(var(--glow-rgb) / 0.9),
    0 0 26px 4px rgb(var(--glow-rgb) / 0.35),
    inset 0 0 8px rgb(var(--glow-rgb) / 0.5);
}

/* Ступенчатая рамка: квадрат и четыре сдвинутые тени дают «пиксельные» углы */
.frame--pixel {
  border-radius: 0;
  box-shadow:
    0 -4px 0 0 var(--lamp),
    0 4px 0 0 var(--lamp),
    -4px 0 0 0 var(--lamp),
    4px 0 0 0 var(--lamp);
}

.frame--pixel img {
  border-radius: 0;
}

/* Шипы — лучи вокруг аватара, как у надписи на заставке */
.frame--spikes::before {
  content: '';
  position: absolute;
  inset: -12px;
  z-index: -1;
  border-radius: 50%;
  background: repeating-conic-gradient(var(--lamp) 0 5deg, transparent 5deg 18deg);
  mask-image: radial-gradient(circle, transparent 54%, #000 56%, #000 64%, transparent 72%);
  filter: drop-shadow(0 0 4px rgb(var(--glow-rgb) / 0.6));
}

.frame--spikes {
  z-index: 0;
  border: 2px solid var(--lamp);
}

/* Лампа — конус света сверху */
.frame--lamp {
  box-shadow: 0 -10px 24px -6px rgb(var(--glow-rgb) / 0.8);
  border-top: 2px solid var(--lamp);
}

.frame--lamp::before {
  content: '';
  position: absolute;
  bottom: 70%;
  left: 50%;
  width: 140%;
  height: 120%;
  transform: translateX(-50%);
  clip-path: polygon(42% 0, 58% 0, 100% 100%, 0 100%);
  background: linear-gradient(to bottom, rgb(var(--glow-rgb) / 0.05), rgb(var(--glow-rgb) / 0.35));
  pointer-events: none;
}

/* --- Фоны --- */

.mini-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  width: 78%;
  height: 82%;
  padding-bottom: 10px;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
  background-color: #050505;
  background-position: center;
  background-size: cover;
  color: #fff;
}

.avatar--small {
  width: 34px;
  height: 34px;
  font-size: 16px;
}

.preview--large .avatar--small {
  width: 52px;
  height: 52px;
  font-size: 22px;
}

.mini-card__name {
  max-width: 90%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-title);
  font-size: 12px;
  font-weight: 400;
}

.preview--large .mini-card__name {
  font-size: 16px;
}

.bg--light {
  filter: saturate(0);
}

.bg--grid {
  background-image:
    linear-gradient(rgb(255 255 255 / 0.09) 1px, transparent 1px),
    linear-gradient(90deg, rgb(255 255 255 / 0.09) 1px, transparent 1px);
  background-size: 8px 8px;
}

/* --- Значки --- */

.nick {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 90%;
}

.nick__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-title);
  font-size: 15px;
  font-weight: 400;
}

.preview--large .nick__name {
  font-size: 22px;
}

.pixel-badge {
  flex: none;
  width: 18px;
  height: 18px;
  fill: var(--lamp);
  filter: drop-shadow(0 0 4px rgb(var(--glow-rgb) / 0.7));
}

.preview--large .pixel-badge {
  width: 26px;
  height: 26px;
}

/* --- Сцена мэтча --- */

.scene {
  position: absolute;
  inset: 0;
  background: #000;
  --light: 255 255 255;
}

.scene--red {
  --light: 255 75 62;
}

.scene__cord {
  position: absolute;
  top: 0;
  left: 50%;
  width: 1px;
  height: 18%;
  background: #444;
}

.scene__shade {
  position: absolute;
  top: 18%;
  left: 50%;
  width: 26%;
  height: 12%;
  transform: translateX(-50%);
  clip-path: polygon(30% 0, 70% 0, 100% 100%, 0 100%);
  background: #2a2a2a;
  box-shadow: 0 6px 18px rgb(var(--light) / 0.6);
}

.scene__beam {
  position: absolute;
  top: 30%;
  left: 50%;
  width: 100%;
  height: 70%;
  transform: translateX(-50%);
  clip-path: polygon(37% 0, 63% 0, 100% 100%, 0 100%);
  background: linear-gradient(to bottom, rgb(var(--light) / 0.45), transparent 90%);
}

.sign {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #fff;
  font-family: var(--font-pixel);
  font-size: 20px;
  letter-spacing: 0.08em;
  text-shadow:
    0 0 6px #fff,
    0 0 16px rgb(255 255 255 / 0.7),
    0 0 34px rgb(255 255 255 / 0.4);
  animation: sign-flicker 3s infinite;
}

.preview--large .sign {
  font-size: 34px;
}

@keyframes sign-flicker {
  0%,
  92%,
  100% {
    opacity: 1;
  }

  94% {
    opacity: 0.4;
  }

  96% {
    opacity: 0.9;
  }
}

/* --- Темы --- */

.theme {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: var(--t-bg);
}

.theme__card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 64%;
  padding: 10px;
  border-radius: 8px;
  background: var(--t-card);
  color: var(--t-text);
}

.theme__card b {
  font-family: var(--font-title);
  font-size: 16px;
  font-weight: 400;
}

.theme__card i {
  height: 4px;
  border-radius: 2px;
  background: var(--t-text);
  opacity: 0.35;
}

.theme__card i:last-child {
  width: 60%;
}

@media (prefers-reduced-motion: reduce) {
  .sign {
    animation: none;
  }
}
</style>
