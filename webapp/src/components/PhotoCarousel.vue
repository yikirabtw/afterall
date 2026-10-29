<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { assetUrl } from '../api/client'
import placeholderLight from '../assets/splash-light.jpg'
import type { Photo } from '../api/types'
import { haptic } from '../telegram'

// Фото листаются свайпом влево/вправо или нажатием: слева — назад, справа — вперёд. Подписи кладутся в слот.
const props = defineProps<{ photos: Photo[]; name: string }>()

const SWIPE_MIN = 40 // px по горизонтали — это свайп, а не нажатие

const index = ref(0)
watch(
  () => props.photos.map((photo) => photo.id).join(),
  () => (index.value = 0),
)

const initial = computed(() => props.name.trim().charAt(0).toUpperCase() || '?')

function step(forward: boolean) {
  index.value = (index.value + (forward ? 1 : props.photos.length - 1)) % props.photos.length
  haptic.select()
}

let startX = 0
let startY = 0
let swiped = false

function onPointerDown(event: PointerEvent) {
  startX = event.clientX
  startY = event.clientY
  swiped = false
}

function onPointerUp(event: PointerEvent) {
  const dx = event.clientX - startX
  const dy = event.clientY - startY
  if (props.photos.length < 2 || Math.abs(dx) < SWIPE_MIN || Math.abs(dx) < Math.abs(dy)) return
  swiped = true
  step(dx < 0) // палец влево — следующее фото
}

function onTap(event: MouseEvent) {
  // После свайпа браузер присылает ещё и нажатие — второй раз не листаем
  if (swiped) {
    swiped = false
    return
  }
  if (props.photos.length < 2) return
  const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
  step(event.clientX - box.left > box.width / 3)
}
</script>

<template>
  <div class="carousel" @click="onTap" @pointerdown="onPointerDown" @pointerup="onPointerUp">
    <!-- Все фото в разметке сразу — переключение мгновенное, без подгрузки -->
    <img
      v-for="(photo, i) in photos"
      :key="photo.id"
      :src="assetUrl(photo.url)"
      class="carousel__img"
      :class="{ 'carousel__img--on': i === index }"
      alt=""
      draggable="false"
    />
    <div
      v-if="!photos.length"
      class="carousel__placeholder"
      :style="{ backgroundImage: `url(${placeholderLight})` }"
      aria-hidden="true"
    >
      {{ initial }}
    </div>

    <div v-if="photos.length > 1" class="carousel__bars" aria-hidden="true">
      <i v-for="(photo, i) in photos" :key="photo.id" :class="{ on: i === index }" />
    </div>
    <div class="carousel__shade" />
    <div class="carousel__overlay"><slot /></div>
  </div>
</template>

<style scoped>
.carousel {
  position: relative;
  touch-action: pan-y; /* вертикальную прокрутку отдаём странице, горизонтальный свайп — нам */
  overflow: hidden;
  background: var(--card);
  user-select: none;
  -webkit-user-select: none;
}

.carousel__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.carousel__img--on {
  opacity: 1;
}

/* Без фото — полоса света из референсов фона и пиксельная буква со свечением */
.carousel__placeholder {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background-color: #000;
  background-size: cover;
  background-position: 60% 40%;
  color: #fff;
  font-family: var(--font-pixel);
  font-size: 120px;
  line-height: 1;
  text-shadow: 0 0 12px rgb(255 255 255 / 0.8), 0 0 60px rgb(255 255 255 / 0.4);
}

.carousel__bars {
  position: absolute;
  top: 10px;
  left: 12px;
  right: 12px;
  display: flex;
  gap: 4px;
  z-index: 2;
}

.carousel__bars i {
  flex: 1;
  height: 3px;
  border-radius: 2px;
  background: rgb(255 255 255 / 0.3);
}

.carousel__bars i.on {
  background: #fff;
  box-shadow: 0 0 6px rgb(255 255 255 / 0.8);
}

/* Затемнение снизу — чтобы белый текст читался на любом фото */
.carousel__shade {
  position: absolute;
  inset: 45% 0 0;
  background: linear-gradient(to top, rgb(0 0 0 / 0.88), rgb(0 0 0 / 0.4) 55%, transparent);
  pointer-events: none;
}

.carousel__overlay {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 16px;
  color: #fff;
  z-index: 1;
}

@media (prefers-reduced-motion: reduce) {
  .carousel__img {
    transition: none;
  }
}
</style>
