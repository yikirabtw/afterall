<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { assetUrl } from '../api/client'
import type { Photo } from '../api/types'
import { haptic } from '../telegram'

// Фото с переключением как в сторис: нажатие слева — назад, справа — вперёд. Подписи кладутся в слот.
const props = defineProps<{ photos: Photo[]; name: string }>()

const index = ref(0)
watch(
  () => props.photos.map((photo) => photo.id).join(),
  () => (index.value = 0),
)

const initial = computed(() => props.name.trim().charAt(0).toUpperCase() || '?')

function onTap(event: MouseEvent) {
  if (props.photos.length < 2) return
  const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const forward = event.clientX - box.left > box.width / 3
  index.value = (index.value + (forward ? 1 : props.photos.length - 1)) % props.photos.length
  haptic.select()
}
</script>

<template>
  <div class="carousel" @click="onTap">
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
    <div v-if="!photos.length" class="carousel__placeholder" aria-hidden="true">{{ initial }}</div>

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

.carousel__placeholder {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: linear-gradient(140deg, var(--accent), var(--warm));
  color: var(--accent-ink);
  font-size: 96px;
  font-weight: 900;
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
  background: rgb(255 255 255 / 0.35);
}

.carousel__bars i.on {
  background: #fff;
}

/* Затемнение снизу — чтобы белый текст читался на любом фото */
.carousel__shade {
  position: absolute;
  inset: 45% 0 0;
  background: linear-gradient(to top, rgb(0 0 0 / 0.78), transparent);
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
