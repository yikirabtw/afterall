<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { AgeLimits } from '../api/types'
import { SEARCH_AGE_TOP } from '../profile'
import { haptic } from '../telegram'

/*
  Ползунок «от и до» для возраста поиска: два обычных range друг на друге, у каждого нажимается только свой кружок.
  Рамки приходят с сервера (Me.search_age_limits) — дальше них не сдвинуть.
  null с любой стороны — «до самой рамки»; у взрослых верх — «45+», без верхней границы.
*/
const props = defineProps<{ limits: AgeLimits }>()
const model = defineModel<{ min: number | null; max: number | null }>({ required: true })

// Своя копия: родитель обновит v-model только к следующей отрисовке, а два кружка (двумя пальцами)
// могут сдвинуться в одном кадре — иначе второй затёр бы первый
const range = ref({ ...model.value })
watch(model, (next) => (range.value = { ...next }))

function commit(change: Partial<{ min: number | null; max: number | null }>) {
  range.value = { ...range.value, ...change }
  model.value = { ...range.value }
}

const top = computed(() => props.limits.max ?? SEARCH_AGE_TOP)
const openTop = computed(() => props.limits.max === null)
const low = computed(() => Math.max(range.value.min ?? props.limits.min, props.limits.min))
const high = computed(() => Math.min(range.value.max ?? top.value, top.value))

const span = computed(() => Math.max(1, top.value - props.limits.min))
const percent = (value: number) => ((value - props.limits.min) / span.value) * 100

// Кружки сошлись: наверху сверху лежит «от» (его можно увести вниз), иначе — «до»
const lowOnTop = computed(() => low.value >= top.value)

function setLow(event: Event) {
  const input = event.target as HTMLInputElement
  const value = Math.min(Number(input.value), high.value)
  input.value = String(value) // кружки не перескакивают друг через друга
  if (value === low.value) return
  haptic.select()
  commit({ min: value === props.limits.min ? null : value })
}

function setHigh(event: Event) {
  const input = event.target as HTMLInputElement
  const value = Math.max(Number(input.value), low.value)
  input.value = String(value)
  if (value === high.value) return
  haptic.select()
  commit({ max: value === top.value ? null : value })
}
</script>

<template>
  <div class="age-range" :style="{ '--lo': percent(low), '--hi': percent(high) }">
    <div class="age-range__head">
      <span class="field__label">Возраст</span>
      <b class="age-range__value">{{ low }} — {{ high }}<template v-if="openTop && high === top">+</template></b>
    </div>

    <div class="age-range__track">
      <span class="age-range__rail" aria-hidden="true" />
      <span class="age-range__fill" aria-hidden="true" />
      <input
        class="age-range__input"
        :class="{ 'age-range__input--top': lowOnTop }"
        type="range"
        :min="limits.min"
        :max="top"
        step="1"
        :value="low"
        aria-label="Возраст от"
        @input="setLow"
      />
      <input
        class="age-range__input"
        type="range"
        :min="limits.min"
        :max="top"
        step="1"
        :value="high"
        aria-label="Возраст до"
        @input="setHigh"
      />
    </div>

    <p class="hint age-range__hint">
      Взаимно: человек появится, только если и ты подходишь под его возраст. С теми, кому меньше 18, разница — не
      больше 4 лет.
    </p>
  </div>
</template>

<style scoped>
.age-range__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.age-range__value {
  font-family: var(--font-pixel);
  font-size: 20px;
  font-weight: 400;
  text-shadow: 0 0 10px rgb(var(--glow-rgb) / 0.45);
}

.age-range__track {
  position: relative;
  height: 32px;
  margin-top: 6px;
}

/* Полоса — от центра крайнего кружка до центра другого (кружок 24px) */
.age-range__rail,
.age-range__fill {
  position: absolute;
  left: 12px;
  right: 12px;
  top: 50%;
  height: 4px;
  margin-top: -2px;
  border-radius: 2px;
}

.age-range__rail {
  background: var(--line-strong);
}

/* Выбранный отрезок — светится; двигается только transform */
.age-range__fill {
  background: var(--lamp);
  box-shadow: 0 0 8px rgb(var(--glow-rgb) / 0.55);
  transform-origin: left center;
  transform: translateX(calc(var(--lo) * 1%)) scaleX(calc((var(--hi) - var(--lo)) / 100));
}

.age-range__input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  background: none;
  pointer-events: none; /* нажимается только кружок — второй ползунок под ним остаётся доступным */
  -webkit-appearance: none;
  appearance: none;
}

.age-range__input--top {
  z-index: 1;
}

.age-range__input::-webkit-slider-runnable-track {
  height: 32px;
  background: none;
}

.age-range__input::-moz-range-track {
  background: none;
}

.age-range__input::-webkit-slider-thumb {
  width: 24px;
  height: 24px;
  margin-top: 4px;
  border: 2px solid var(--lamp);
  border-radius: 50%;
  background: var(--page);
  box-shadow: 0 0 10px rgb(var(--glow-rgb) / 0.45);
  cursor: grab;
  pointer-events: auto;
  -webkit-appearance: none;
  appearance: none;
  transition: transform 0.15s ease;
}

.age-range__input::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border: 2px solid var(--lamp);
  border-radius: 50%;
  background: var(--page);
  box-shadow: 0 0 10px rgb(var(--glow-rgb) / 0.45);
  cursor: grab;
  pointer-events: auto;
  transition: transform 0.15s ease;
}

.age-range__input:active::-webkit-slider-thumb {
  transform: scale(1.15);
  cursor: grabbing;
}

.age-range__input:active::-moz-range-thumb {
  transform: scale(1.15);
  cursor: grabbing;
}

.age-range__input:focus-visible::-webkit-slider-thumb {
  outline: 2px solid var(--lamp);
  outline-offset: 3px;
}

.age-range__hint {
  margin: 8px 0 0;
}
</style>
