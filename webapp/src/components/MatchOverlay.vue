<script setup lang="ts">
import { computed } from 'vue'

import { assetUrl } from '../api/client'
import type { Match } from '../api/types'
import { session } from '../stores/session'
import MatchContacts from './MatchContacts.vue'

// «Это мэтч!» — показывается сразу после взаимного лайка
defineProps<{ match: Match }>()
const emit = defineEmits<{ close: [] }>()

const myPhoto = computed(() => session.me?.photos[0] ?? null)
// Своя сцена мэтча из косметики: красная лампа или неоновая вывеска вместо лампы
const scene = computed(() => session.me?.profile?.equipped.match ?? null)
const myInitial = computed(() => session.me?.profile?.display_name.charAt(0).toUpperCase() ?? '?')
</script>

<template>
  <Teleport to="body">
    <div
      class="overlay theme-dark"
      :class="{ 'overlay--red': scene === 'match-red', 'overlay--sign': scene === 'match-neon' }"
      role="dialog"
      aria-label="Взаимный лайк"
    >
      <span v-if="scene === 'match-neon'" class="sign" aria-hidden="true">MATCH</span>
      <!-- Лампа над экраном: свет падает на надпись, как в референсе со светом -->
      <div v-else class="lamp" aria-hidden="true">
        <span class="lamp__cord" />
        <span class="lamp__shade" />
        <span class="lamp__glow" />
        <span class="lamp__beam" />
      </div>

      <h2 class="overlay__title">Это мэтч</h2>
      <div class="overlay__avatars">
        <span class="avatar">
          <img v-if="myPhoto" :src="assetUrl(myPhoto.url)" alt="" />
          <template v-else>{{ myInitial }}</template>
        </span>
        <span class="avatar avatar--them">
          <img v-if="match.photos[0]" :src="assetUrl(match.photos[0].url)" alt="" />
          <template v-else>{{ match.display_name.charAt(0).toUpperCase() }}</template>
        </span>
      </div>
      <!-- «Ты и Лера», а не «Вы с Лера»: имена не склоняются -->
      <p class="overlay__text">Ты и {{ match.display_name }} понравились друг другу. Напишите первым?</p>
      <MatchContacts :match="match" class="overlay__contacts" />
      <button class="btn btn-ghost" type="button" @click="emit('close')">Смотреть дальше</button>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 24px;
  overflow: hidden;
  background: var(--g-0);
  text-align: center;
  animation: fade-in 0.25s ease;
}

.overlay > :not(.lamp) {
  position: relative;
}

.lamp {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.lamp__cord {
  position: absolute;
  top: 0;
  left: 50%;
  width: 2px;
  height: 9vh;
  margin-left: -1px;
  background: var(--g-300);
}

.lamp__shade {
  position: absolute;
  top: 9vh;
  left: 50%;
  width: 92px;
  height: 46px;
  margin-left: -46px;
  border-radius: 46px 46px 6px 6px;
  background: linear-gradient(to bottom, var(--g-300), var(--g-100));
  box-shadow: 0 6px 0 -2px rgb(var(--light)), 0 8px 24px 4px rgb(var(--light) / 0.55);
}

/*
  Конус света: верх трапеции — ровно ширина отверстия абажура (84px) и прямо под ним,
  поэтому луч выходит из лампы при любой ширине экрана; книзу расходится и гаснет, края мягкие.
*/
/* Цвет света сцены: белый, у «Красной лампы» — красный (косметика) */
.overlay {
  --light: 255 255 255;
}

.overlay--red {
  --light: 255 75 62;
}

/* «Неоновая вывеска» вместо лампы */
.sign {
  position: absolute;
  top: 10vh;
  left: 50%;
  transform: translateX(-50%);
  color: #fff;
  font-family: var(--font-pixel);
  font-size: 44px;
  letter-spacing: 0.1em;
  text-shadow:
    0 0 6px #fff,
    0 0 18px rgb(255 255 255 / 0.75),
    0 0 42px rgb(255 255 255 / 0.4);
  animation: flicker 3.2s infinite;
}

.overlay--sign .overlay__title {
  margin-top: 22vh;
}

.lamp__beam {
  position: absolute;
  top: calc(9vh + 44px);
  left: 50%;
  width: min(130vw, 760px);
  height: 74vh;
  transform: translateX(-50%);
  clip-path: polygon(calc(50% - 42px) 0, calc(50% + 42px) 0, 100% 100%, 0 100%);
  background: linear-gradient(to bottom, rgb(var(--light) / 0.34), rgb(var(--light) / 0.12) 40%, transparent 92%);
  -webkit-mask-image: linear-gradient(to right, transparent, #000 30%, #000 70%, transparent);
  mask-image: linear-gradient(to right, transparent, #000 30%, #000 70%, transparent);
  animation: flicker 3.2s infinite;
}

/* Рассеянный свет вокруг луча — из той же точки под лампой; выше отверстия плавно гаснет, без резкой границы */
.lamp__glow {
  position: absolute;
  top: 9vh;
  left: 50%;
  width: 380px;
  height: 58vh;
  transform: translateX(-50%);
  background: radial-gradient(ellipse 50% 70% at 50% 46px, rgb(var(--light) / 0.16), transparent 70%);
  -webkit-mask-image: linear-gradient(to bottom, transparent 30px, #000 70px);
  mask-image: linear-gradient(to bottom, transparent 30px, #000 70px);
  animation: flicker 3.2s infinite;
}

.overlay__title {
  margin: 12vh 0 0;
  font-family: var(--font-pixel);
  font-size: 54px;
  font-weight: 400;
  line-height: 1;
  text-transform: uppercase;
  text-shadow: 0 0 14px rgb(255 255 255 / 0.85), 0 0 60px rgb(255 255 255 / 0.4);
}

.overlay__avatars {
  display: flex;
  margin: 6px 0 4px;
}

.avatar {
  display: grid;
  place-items: center;
  width: 104px;
  height: 104px;
  border: 1px solid rgb(255 255 255 / 0.7);
  border-radius: 24px;
  overflow: hidden;
  background: var(--g-100);
  color: var(--text);
  font-family: var(--font-pixel);
  font-size: 48px;
  box-shadow: 0 0 18px rgb(255 255 255 / 0.3);
}

.avatar--them {
  margin-left: -18px;
  transform: rotate(6deg);
}

.avatar:first-child {
  transform: rotate(-6deg);
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.overlay__text {
  margin: 0;
  max-width: 320px;
  color: var(--text-2);
}

.overlay__contacts {
  justify-content: center;
  margin: 8px 0;
}

@keyframes fade-in {
  from {
    opacity: 0;
  }
}

/* Лампа чуть «моргает», как настоящая */
@keyframes flicker {
  0%,
  100% {
    opacity: 1;
  }

  4% {
    opacity: 0.6;
  }

  6% {
    opacity: 1;
  }

  48% {
    opacity: 0.92;
  }
}

@media (prefers-reduced-motion: reduce) {
  .overlay,
  .lamp__beam,
  .lamp__glow {
    animation: none;
  }
}
</style>
