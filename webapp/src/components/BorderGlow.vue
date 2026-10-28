<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, type Component } from 'vue'

// Светящаяся граница по мотивам BorderGlow из React Bits, переписана для Vue без библиотек.
// Мышью — граница загорается у края, к которому поднёс курсор; пальцем — в сторону касания.
// По умолчанию светится цветом «лампы», как полоса над карточкой: белым в тёмной теме, чёрным в светлой.
// Светящаяся линия на рамке, мягкое свечение вокруг неё и широкий ореол того же направления снаружи.
const props = withDefaults(
  defineProps<{
    as?: string | Component // чем отрисовать: div, p, RouterLink…
    edgeSensitivity?: number // насколько близко к краю (в % от центра) начинает светиться
    glowColor?: string // ореол, HSL без скобок: «40 80 80»; без него — цвет «лампы» темы
    glowRadius?: number // размытие ореола, px
    glowIntensity?: number // яркость ореола, 0–1
    coneSpread?: number // половина ширины светящегося конуса, градусы
    animated?: boolean // один оборот света при появлении
    colors?: string[] // цвета на рамке — по ходу конуса
  }>(),
  {
    as: 'div',
    edgeSensitivity: 30,
    glowColor: undefined,
    glowRadius: 40,
    glowIntensity: 0.45,
    coneSpread: 25,
    animated: false,
    // Два одинаковых цвета — линия ярче в середине конуса и гаснет к краям, как у «лампы»
    colors: () => ['var(--lamp)', 'var(--lamp)'],
  },
)

const TOUCH_MIN = 0.85 // палец не «подкрадывается» к краю — касание светит сразу
const TOUCH_HOLD_MS = 450 // после касания свет гаснет не мгновенно
const SWEEP_MS = 1400

const angle = ref(0) // 0° — вверх, по часовой
const proximity = ref(0) // 0 — не светится, 1 — у самого края
const spread = ref(props.coneSpread)
let fadeTimer = 0
let sweep = 0

// Цвета рамки равномерно по конусу, края конуса — прозрачные
const ring = computed(() => {
  const stops = props.colors.map((color, i) => {
    const at = ((i + 1) / (props.colors.length + 1)) * spread.value * 2
    return `${color} ${at.toFixed(1)}deg`
  })
  return `transparent 0deg, ${stops.join(', ')}, transparent ${(spread.value * 2).toFixed(1)}deg`
})

// «40 80 80» → hsl(40 80% 80%): так понимают и старые webview. Без цвета — «лампа» темы
const halo = computed(() => {
  if (!props.glowColor) return `color-mix(in srgb, var(--lamp) ${Math.round(props.glowIntensity * 100)}%, transparent)`
  const [hue = '0', saturation = '0', lightness = '100'] = props.glowColor.trim().split(/\s+/)
  return `hsl(${hue} ${saturation}% ${lightness}% / ${props.glowIntensity})`
})

const style = computed(() => ({
  '--bg-angle': `${angle.value}deg`,
  '--bg-prox': proximity.value.toFixed(3),
  '--bg-spread': `${spread.value.toFixed(1)}deg`,
  '--bg-ring': ring.value,
  '--bg-halo': halo.value,
  '--bg-blur': `${props.glowRadius / 2}px`,
}))

function track(event: PointerEvent) {
  const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const dx = event.clientX - (box.left + box.width / 2)
  const dy = event.clientY - (box.top + box.height / 2)
  angle.value = (Math.atan2(dy, dx) * 180) / Math.PI + 90
  // Насколько точка у края: 0 в центре, 1 на рамке
  const edge = Math.max(Math.abs(dx) / (box.width / 2), Math.abs(dy) / (box.height / 2))
  const zone = props.edgeSensitivity / 100
  let value = Math.min(Math.max((edge - (1 - zone)) / zone, 0), 1)
  if (event.pointerType !== 'mouse') value = Math.max(value, TOUCH_MIN)
  proximity.value = value
  // У длинной стороны вытянутой карточки угол от центра «короткий» — расширяем конус,
  // чтобы светился заметный кусок края, а не точка
  const nearLongSide = Math.abs(dy) / box.height > Math.abs(dx) / box.width
  const stretch = nearLongSide ? box.width / box.height : box.height / box.width
  spread.value = props.coneSpread * Math.min(Math.max(Math.sqrt(stretch) * 1.4, 1), 3)
  window.clearTimeout(fadeTimer)
}

function fade(delay = 0) {
  window.clearTimeout(fadeTimer)
  fadeTimer = window.setTimeout(() => (proximity.value = 0), delay)
}

function onPointerUp(event: PointerEvent) {
  if (event.pointerType !== 'mouse') fade(TOUCH_HOLD_MS)
}

// animated: свет один раз обегает рамку
onMounted(() => {
  if (!props.animated || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const start = performance.now()
  const step = (now: number) => {
    const t = Math.min((now - start) / SWEEP_MS, 1)
    angle.value = t * 360
    proximity.value = Math.sin(t * Math.PI)
    sweep = t < 1 ? requestAnimationFrame(step) : 0
  }
  sweep = requestAnimationFrame(step)
})

onBeforeUnmount(() => {
  window.clearTimeout(fadeTimer)
  cancelAnimationFrame(sweep)
})
</script>

<template>
  <component
    :is="as"
    class="border-glow"
    :style="style"
    @pointerdown="track"
    @pointermove="track"
    @pointerup="onPointerUp"
    @pointercancel="fade()"
    @pointerleave="fade()"
  >
    <slot />
    <span class="border-glow__halo" aria-hidden="true" />
    <!-- Та же линия, размытая, — свечение вокруг неё (размытие поверх маски даёт только обёртка) -->
    <span class="border-glow__bloom" aria-hidden="true"><span class="border-glow__ring" /></span>
    <span class="border-glow__ring" aria-hidden="true" />
  </component>
</template>

<style scoped>
.border-glow {
  position: relative;
}

/* Конус света на рамке: градиент вырезан маской так, что видна только полоска по краю */
.border-glow__ring {
  position: absolute;
  inset: -1px;
  padding: 1.5px;
  border-radius: inherit;
  background: conic-gradient(from calc(var(--bg-angle) - var(--bg-spread)), var(--bg-ring));
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask:
    linear-gradient(#000 0 0) content-box exclude,
    linear-gradient(#000 0 0);
  opacity: var(--bg-prox);
  pointer-events: none;
  transition: opacity 0.35s ease;
}

/* Свечение вокруг линии: размытая копия рамки */
.border-glow__bloom {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  filter: blur(5px);
  opacity: var(--bg-prox);
  pointer-events: none;
  transition: opacity 0.35s ease;
}

.border-glow__bloom .border-glow__ring {
  padding: 2.5px;
  opacity: 1;
}

/* Ореол: размытый клин того же направления под карточкой — снаружи видна только его кайма */
.border-glow__halo {
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: inherit;
  background: conic-gradient(
    from calc(var(--bg-angle) - var(--bg-spread)),
    transparent 0deg,
    var(--bg-halo) var(--bg-spread),
    transparent calc(var(--bg-spread) * 2)
  );
  filter: blur(var(--bg-blur));
  opacity: calc(var(--bg-prox) * 0.75);
  pointer-events: none;
  transition: opacity 0.35s ease;
}

@media (prefers-reduced-motion: reduce) {
  .border-glow__ring,
  .border-glow__bloom,
  .border-glow__halo {
    transition: none;
  }
}
</style>
