// Отражающая карточка по мотивам ReflectiveCard из React Bits, скрещённая с нашим стилем.
// Вместо вебкамеры отражается «полоса света» из референсов (assets/reflection.jpg, уже размыта):
// при прокрутке отражение скользит по карточке, как свет по металлу; курсор или палец наклоняют
// карточку (tiltStrength°) и зажигают блик (glare). Слои — в разметке карточки, директива двигает их
// через CSS-переменные: --rx/--ry — наклон, --ref-x/--ref-y — сдвиг отражения, --gx/--gy/--glare — блик.

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

const visible = new Set<HTMLElement>()
const options = new WeakMap<HTMLElement, ReflectOptions>()
let frame = 0

function updateScroll() {
  frame = 0
  for (const el of visible) {
    const box = el.getBoundingClientRect()
    // 0 — карточка вверху экрана, 1 — внизу
    const progress = (box.top + box.height / 2) / window.innerHeight
    el.style.setProperty('--ref-scroll', (0.5 - progress).toFixed(3))
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
  const opts = options.get(el) ?? DEFAULTS
  const box = el.getBoundingClientRect()
  const x = Math.min(Math.max((event.clientX - box.left) / box.width, 0), 1)
  const y = Math.min(Math.max((event.clientY - box.top) / box.height, 0), 1)
  el.classList.add('is-tilting')
  el.style.setProperty('--rx', `${((0.5 - y) * 2 * opts.tiltStrength).toFixed(2)}deg`)
  el.style.setProperty('--ry', `${((x - 0.5) * 2 * opts.tiltStrength).toFixed(2)}deg`)
  el.style.setProperty('--tilt-x', ((0.5 - x) * PARALLAX).toFixed(1))
  el.style.setProperty('--tilt-y', ((0.5 - y) * PARALLAX).toFixed(1))
  el.style.setProperty('--gx', `${(x * 100).toFixed(1)}%`)
  el.style.setProperty('--gy', `${(y * 100).toFixed(1)}%`)
  el.style.setProperty('--glare', String(opts.glare))
}

function rest(event: PointerEvent) {
  const el = event.currentTarget as HTMLElement
  el.classList.remove('is-tilting')
  for (const name of ['--rx', '--ry', '--tilt-x', '--tilt-y', '--glare']) el.style.removeProperty(name)
}

function onPointerMove(event: PointerEvent) {
  // Мышь — всегда; палец — только пока прижат (иначе это прокрутка)
  if (event.pointerType === 'mouse' || event.buttons) tilt(event)
}

export const vReflect: Directive<HTMLElement, Partial<ReflectOptions> | undefined> = {
  mounted(el, binding) {
    const opts = { ...DEFAULTS, ...binding.value }
    options.set(el, opts)
    el.style.setProperty('--ref-travel', String(opts.travel))
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
    if (!options.has(el)) return
    options.delete(el)
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
