<script setup lang="ts">
import { computed } from 'vue'

import { faceitColor, faceitLevel } from '../lobby'

// Значок уровня FACEIT: дуга с разрывом снизу заполняется по уровню, цвет — как в самом FACEIT
const props = withDefaults(defineProps<{ elo: number; size?: number }>(), { size: 40 })

const R = 15
const CIRCUMFERENCE = 2 * Math.PI * R
const ARC = CIRCUMFERENCE * (300 / 360)

const level = computed(() => faceitLevel(props.elo))
const color = computed(() => faceitColor(level.value))
const filled = computed(() => (ARC * level.value) / 10)
</script>

<template>
  <svg
    class="faceit-level"
    :width="size"
    :height="size"
    viewBox="0 0 40 40"
    role="img"
    :aria-label="`FACEIT, ${level} уровень`"
    :style="{ '--level': color }"
  >
    <!-- Поворот на 120°: дуга начинается слева снизу, разрыв — по центру снизу -->
    <g transform="rotate(120 20 20)" fill="none" stroke-width="3.6" stroke-linecap="round">
      <circle cx="20" cy="20" :r="R" class="faceit-level__track" :stroke-dasharray="`${ARC} ${CIRCUMFERENCE}`" />
      <circle cx="20" cy="20" :r="R" class="faceit-level__arc" :stroke-dasharray="`${filled} ${CIRCUMFERENCE}`" />
    </g>
    <text x="20" y="21.5" text-anchor="middle" dominant-baseline="middle">{{ level }}</text>
  </svg>
</template>

<style scoped>
.faceit-level {
  flex: none;
  display: inline-block;
  vertical-align: middle;
  filter: drop-shadow(0 0 3px color-mix(in srgb, var(--level) 55%, transparent));
}

.faceit-level__track {
  stroke: var(--g-300);
}

.faceit-level__arc {
  stroke: var(--level);
}

text {
  fill: var(--text);
  font-family: var(--font-pixel);
  font-size: 15px;
}
</style>
