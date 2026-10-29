<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import { haptic } from '../telegram'

/*
  Кнопка с «фитилём» (по мотивам FuseButton из React Bits). Нажатие сразу делает действие на экране (commit),
  а по контуру кнопки начинает догорать фитиль. Пока горит — повторное нажатие всё возвращает (undo).
  Догорел — действие окончательное (fuse-end), кнопка возвращается в исходный вид.
  Ушли с экрана или свернули приложение во время отсчёта — тоже окончательно: фитиль «догорает» сразу.
  Мышь над кнопкой ставит фитиль на паузу (на телефоне «наведения» нет — там не ставит).
*/
const props = withDefaults(
  defineProps<{
    label: string
    doneLabel?: string // пусто — после нажатия только «Вернуть», для тесных мест
    undoLabel?: string
    undoWindow?: number // мс на отмену
    disabled?: boolean
  }>(),
  { doneLabel: '', undoLabel: 'Вернуть', undoWindow: 4000, disabled: false },
)

const emit = defineEmits<{ commit: []; undo: []; fuseEnd: [] }>()

const FUSE_WIDTH = 1.5

const button = ref<HTMLButtonElement>()
const fuse = ref<SVGPathElement>()
const spark = ref<HTMLElement>()

const armed = ref(false)
const paused = ref(false)
const box = ref({ width: 0, height: 0, d: '' })

// --- Контур кнопки: скруглённый прямоугольник по линии рамки, от середины верха по часовой ---

function measure() {
  const el = button.value
  if (!el) return
  const width = el.offsetWidth
  const height = el.offsetHeight
  const t = FUSE_WIDTH / 2
  const w = width - FUSE_WIDTH
  const h = height - FUSE_WIDTH
  const r = Math.max(0, Math.min(parseFloat(getComputedStyle(el).borderTopLeftRadius) - t, w / 2, h / 2))
  const [left, top, right, bottom] = [t, t, t + w, t + h]
  const d = [
    `M ${t + w / 2} ${top}`,
    `H ${right - r} A ${r} ${r} 0 0 1 ${right} ${top + r}`,
    `V ${bottom - r} A ${r} ${r} 0 0 1 ${right - r} ${bottom}`,
    `H ${left + r} A ${r} ${r} 0 0 1 ${left} ${bottom - r}`,
    `V ${top + r} A ${r} ${r} 0 0 1 ${left + r} ${top} Z`,
  ].join(' ')
  box.value = { width, height, d }
}

let observer: ResizeObserver | undefined

// --- Горение: свой таймер на кадрах, чтобы пауза и «догореть сразу» были точными ---

let raf = 0
let elapsed = 0
let last = 0
let length = 0

function paint(progress: number) {
  const path = fuse.value
  if (!path) return
  path.style.strokeDashoffset = String(length * progress)
  // Искра — на горящем конце; двигается только transform, без пересчёта раскладки
  const point = path.getPointAtLength(length * (1 - progress))
  if (spark.value) spark.value.style.transform = `translate(${point.x}px, ${point.y}px)`
}

function frame(now: number) {
  if (!paused.value) elapsed += now - last
  last = now
  const progress = Math.min(elapsed / props.undoWindow, 1)
  paint(progress)
  if (progress >= 1) finish()
  else raf = requestAnimationFrame(frame)
}

async function arm() {
  armed.value = true
  paused.value = false
  elapsed = 0
  measure()
  await nextTick()
  length = fuse.value?.getTotalLength() ?? 0
  if (fuse.value) fuse.value.style.strokeDasharray = `${length} ${length}`
  paint(0)
  last = performance.now()
  raf = requestAnimationFrame(frame)
}

function stop() {
  cancelAnimationFrame(raf)
  armed.value = false
}

function finish() {
  if (!armed.value) return
  stop()
  emit('fuseEnd')
}

function onClick() {
  if (props.disabled) return
  if (armed.value) {
    stop()
    haptic.select()
    emit('undo')
  } else {
    haptic.tap()
    emit('commit')
    void arm()
  }
}

// Пауза — только под мышью: на телефоне «наведение» залипает после нажатия и остановило бы фитиль
function onPointerEnter(event: PointerEvent) {
  if (event.pointerType === 'mouse') paused.value = true
}

function onPointerLeave() {
  paused.value = false
}

// Приложение свернули или закрыли — отсчёт не ждём
function onHidden() {
  if (document.visibilityState === 'hidden') finish()
}

onMounted(() => {
  observer = new ResizeObserver(measure)
  if (button.value) observer.observe(button.value)
  document.addEventListener('visibilitychange', onHidden)
  window.addEventListener('pagehide', finish)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  document.removeEventListener('visibilitychange', onHidden)
  window.removeEventListener('pagehide', finish)
  finish() // ушли с экрана во время отсчёта — действие окончательное
})
</script>

<template>
  <button
    ref="button"
    class="btn btn-small fuse"
    :class="{ 'fuse--armed': armed }"
    type="button"
    :disabled="disabled"
    :aria-label="armed ? `${doneLabel ? `${doneLabel}. ` : ''}${undoLabel}` : label"
    @click="onClick"
    @pointerenter="onPointerEnter"
    @pointerleave="onPointerLeave"
  >
    <!-- Обе подписи лежат в одной клетке сетки: ширина кнопки не прыгает при смене -->
    <span class="fuse__label fuse__label--idle" aria-hidden="true">{{ label }}</span>
    <span class="fuse__label fuse__label--armed" aria-hidden="true">
      <span v-if="doneLabel" class="fuse__done">{{ doneLabel }}</span>
      <span class="fuse__undo">{{ undoLabel }}</span>
    </span>

    <svg
      v-if="armed"
      class="fuse__line"
      :width="box.width"
      :height="box.height"
      :viewBox="`0 0 ${box.width} ${box.height}`"
      aria-hidden="true"
    >
      <path ref="fuse" :d="box.d" :stroke-width="FUSE_WIDTH" />
    </svg>
    <span v-if="armed" ref="spark" class="fuse__spark" aria-hidden="true"><i /></span>
  </button>
</template>

<style scoped>
.fuse {
  position: relative;
  display: inline-grid;
  border-color: var(--line-strong);
  background: transparent;
  color: var(--text-2);
  transition:
    border-color 0.2s ease,
    color 0.2s ease,
    transform 0.08s ease;
}

/* Пока фитиль горит, его линия заменяет рамку */
.fuse--armed {
  border-color: var(--line);
  color: var(--text);
}

.fuse__label {
  grid-area: 1 / 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
  transition:
    opacity 0.2s ease,
    transform 0.2s ease,
    filter 0.2s ease;
}

/* Смена подписи — встречное проявление с лёгким размытием */
.fuse__label--armed,
.fuse--armed .fuse__label--idle {
  opacity: 0;
  transform: translateY(4px);
  filter: blur(3px);
}

.fuse--armed .fuse__label--idle {
  transform: translateY(-4px);
}

.fuse--armed .fuse__label--armed {
  opacity: 1;
  transform: none;
  filter: none;
}

.fuse__done {
  color: var(--text-2);
}

.fuse__done::after {
  content: '·';
  margin-left: 6px;
}

.fuse__line {
  position: absolute;
  top: -1px;
  left: -1px;
  overflow: visible;
  pointer-events: none;
}

.fuse__line path {
  fill: none;
  stroke: var(--warn);
  stroke-linecap: round;
  filter: drop-shadow(0 0 3px var(--warn));
}

/* Искра на горящем конце: точка с ореолом, слегка «трещит» */
.fuse__spark {
  position: absolute;
  top: -1px;
  left: -1px;
  width: 0;
  height: 0;
  pointer-events: none;
  will-change: transform;
}

.fuse__spark i {
  position: absolute;
  left: -3px;
  top: -3px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--warn) 30%, #fff); /* раскалённая середина */
  box-shadow:
    0 0 4px 1px var(--warn),
    0 0 12px 3px color-mix(in srgb, var(--warn) 55%, transparent);
  animation: crackle 0.18s steps(2, jump-none) infinite alternate;
}

@keyframes crackle {
  from {
    transform: scale(0.75);
    opacity: 0.8;
  }

  to {
    transform: scale(1.15);
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .fuse__label {
    transition: none;
  }

  .fuse__spark i {
    animation: none;
  }
}
</style>
