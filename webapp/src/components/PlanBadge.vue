<script setup lang="ts">
import type { Plan } from '../api/types'

// Значок у ника: Plus — белый свет, Premium — тёплый. У бесплатного тарифа значка нет
defineProps<{ plan: Plan }>()
</script>

<template>
  <span v-if="plan !== 'free'" class="plan-badge" :class="`plan-badge--${plan}`">{{ plan }}</span>
</template>

<style scoped>
.plan-badge {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 5px 2px;
  border: 1px solid currentColor;
  border-radius: 4px;
  font-family: var(--font-pixel);
  font-size: 11px;
  font-weight: 400;
  line-height: 1.2;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  vertical-align: middle;
  text-shadow: 0 0 6px currentColor;
  white-space: nowrap;
}

.plan-badge--plus {
  box-shadow: 0 0 8px rgb(255 255 255 / 0.25);
}

.plan-badge--premium {
  color: var(--warn);
  box-shadow: 0 0 10px color-mix(in srgb, var(--warn) 45%, transparent);
}
</style>
