// Отражающая карточка по мотивам ReflectiveCard из React Bits, скрещённая с нашим стилем.
// Вместо вебкамеры отражается «полоса света» из референсов (assets/reflection.jpg, уже размыта):
// при прокрутке отражение скользит по карточке, как свет по металлу; курсор или палец наклоняют
// карточку (tiltStrength°) и зажигают блик (glare). Слои — в разметке карточки:
// [data-reflect="reflection"] и [data-reflect="sheen"] директива двигает напрямую через transform
// (только эти два слоя — без пересчёта стилей всей карточки при прокрутке, важно для слабых телефонов);
// наклон карточки и блик — CSS-переменные --rx/--ry и --gx/--gy/--glare.

import type { Directive } from 'vue'

export interface ReflectOptions {
  tiltStrength: number // наклон, градусы
  glare: number // яркость блика, 0–1
  travel: number // насколько отражение уезжает при прокрутке, px
}

const DEFAULTS: ReflectOptions = { tiltStrength: 3, glare: 0.5, travel: 90 }
const PARALLAX = 24 // px: отражение уходит в сторону, противоположную наклону

const still = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

// --- Прокрутка: один слушатель на все карточки, считаем только видимые ---

interface State {
  options: ReflectOptions
  scroll: number // -0.5 — карточка внизу экрана, 0.5 — вверху
  tiltX: number // сдвиг отражения против наклона, px
  tiltY: number
  reflection: HTMLElement | null
  sheen: HTMLElement | null
}

const visible = new Set<HTMLElement>()
const states = new WeakMap<HTMLElement, State>()
let frame = 0

/** Сдвинуть слои отражения: при прокрутке — вдоль карточки, при наклоне — против него */
function paint(el: HTMLElement) {
  const state = states.get(el)
  if (!state) return
  const y = state.scroll * state.options.travel + state.tiltY
  if (state.reflection) state.reflection.style.transform = `translate3d(${state.tiltX.toFixed(1)}px, ${y.toFixed(1)}px, 0) rotate(-8deg)`
  if (state.sheen) state.sheen.style.transform = `translate3d(${(state.scroll * 160).toFixed(1)}%, 0, 0)`
}

function updateScroll() {
  frame = 0
  for (const el of visible) {
    const state = states.get(el)
    if (!state) continue
    const box = el.getBoundingClientRect()
    // 0 — карточка вверху экрана, 1 — внизу
    state.scroll = 0.5 - (box.top + box.height / 2) / window.innerHeight
    paint(el)
  }
}

function onScroll() {
  if (!frame) frame = requestAnimationFrame(updateScroll)
}

const watcher =
  typeof IntersectionObserver === 'undefined'
    ? null
    : new IntersectionObserver((entries) => {
        for (const entry of entries) {
          const el = entry.target as HTMLElement
          if (entry.isIntersecting) visible.add(el)
          else visible.delete(el)
        }
        onScroll()
      })

let listening = 0
function listen(on: boolean) {
  listening += on ? 1 : -1
  if (on && listening === 1) {
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll, { passive: true })
  } else if (!on && listening === 0) {
    window.removeEventListener('scroll', onScroll)
    window.removeEventListener('resize', onScroll)
  }
}

// --- Наклон и блик ---

function tilt(event: PointerEvent) {
  const el = event.currentTarget as HTMLElement
  const state = states.get(el)
  if (!state) return
  const opts = state.options
  const box = el.getBoundingClientRect()
  const x = Math.min(Math.max((event.clientX - box.left) / box.width, 0), 1)
  const y = Math.min(Math.max((event.clientY - box.top) / box.height, 0), 1)
  el.classList.add('is-tilting')
  el.style.setProperty('--rx', `${((0.5 - y) * 2 * opts.tiltStrength).toFixed(2)}deg`)
  el.style.setProperty('--ry', `${((x - 0.5) * 2 * opts.tiltStrength).toFixed(2)}deg`)
  state.tiltX = (0.5 - x) * PARALLAX
  state.tiltY = (0.5 - y) * PARALLAX
  paint(el)
  el.style.setProperty('--gx', `${(x * 100).toFixed(1)}%`)
  el.style.setProperty('--gy', `${(y * 100).toFixed(1)}%`)
  el.style.setProperty('--glare', String(opts.glare))
}

function rest(event: PointerEvent) {
  const el = event.currentTarget as HTMLElement
  el.classList.remove('is-tilting')
  for (const name of ['--rx', '--ry', '--glare']) el.style.removeProperty(name)
  const state = states.get(el)
  if (state) {
    state.tiltX = 0
    state.tiltY = 0
    paint(el)
  }
}

function onPointerMove(event: PointerEvent) {
  // Мышь — всегда; палец — только пока прижат (иначе это прокрутка)
  if (event.pointerType === 'mouse' || event.buttons) tilt(event)
}

export const vReflect: Directive<HTMLElement, Partial<ReflectOptions> | undefined> = {
  mounted(el, binding) {
    states.set(el, {
      options: { ...DEFAULTS, ...binding.value },
      scroll: 0,
      tiltX: 0,
      tiltY: 0,
      reflection: el.querySelector<HTMLElement>('[data-reflect="reflection"]'),
      sheen: el.querySelector<HTMLElement>('[data-reflect="sheen"]'),
    })
    paint(el)
    if (still()) return
    el.addEventListener('pointerdown', tilt)
    el.addEventListener('pointermove', onPointerMove)
    el.addEventListener('pointerup', rest)
    el.addEventListener('pointercancel', rest)
    el.addEventListener('pointerleave', rest)
    if (watcher) watcher.observe(el)
    else visible.add(el)
    listen(true)
    onScroll()
  },
  unmounted(el) {
    if (!states.has(el)) return
    states.delete(el)
    watcher?.unobserve(el)
    visible.delete(el)
    el.removeEventListener('pointerdown', tilt)
    el.removeEventListener('pointermove', onPointerMove)
    el.removeEventListener('pointerup', rest)
    el.removeEventListener('pointercancel', rest)
    el.removeEventListener('pointerleave', rest)
    if (!still()) listen(false)
  },
}

declare module 'vue' {
  interface GlobalDirectives {
    vReflect: typeof vReflect
  }
}
