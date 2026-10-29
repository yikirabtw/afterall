<script setup lang="ts">
import { computed } from 'vue'

import { BADGE_STYLE, badgeCells } from '../cosmetics'

// Пиксельный значок у ника (косметика): по id вещи, например badge-night
const props = defineProps<{ item: string; size?: number }>()

const cells = computed(() => badgeCells(BADGE_STYLE[props.item] ?? ''))
</script>

<template>
  <svg
    v-if="cells.length"
    class="pixel-badge"
    viewBox="0 0 7 7"
    :width="size ?? 16"
    :height="size ?? 16"
    aria-hidden="true"
    shape-rendering="crispEdges"
  >
    <rect v-for="cell in cells" :key="`${cell.x}-${cell.y}`" :x="cell.x" :y="cell.y" width="1" height="1" />
  </svg>
</template>

<style scoped>
.pixel-badge {
  display: inline-block;
  margin-left: 6px;
  vertical-align: -1px;
  fill: currentColor;
  filter: drop-shadow(0 0 4px currentColor);
}
</style>
