// «Желейные» переключатели — механика JellyRadio из React Bits, переписанная для Vue без библиотек.
// Выбранный элемент раздувается (сначала вширь, потом ввысь), соседи расступаются с задержкой
// по расстоянию, остальные чуть сжимаются. Всё на пружинах с теми же параметрами, что у оригинала.
//
// Вешается на контейнер: <nav v-jelly>, <div class="segmented" v-jelly.soft>, <span v-jelly="{ room: true }">.
// Выбранный ребёнок — тот, у кого aria-pressed/aria-checked="true" или класс router-link-active;
// смену выбора директива замечает сама, по атрибутам.

import type { Directive } from 'vue'

export interface JellyOptions {
  swell: number // насколько раздувается выбранный (0.2 = на 20%)
  barge: number // на сколько px соседей отталкивает сверх места под раздувшегося
  shrink: number // насколько сжимаются невыбранные
  jelly: number // «сначала вширь, потом ввысь»: 0 — равномерно, 1.5 — утрированно
  bounce: number // 1 − коэффициент затухания: 0 — без колебаний, 0.4 — звенит
  stagger: number // мс задержки на каждый шаг от выбранного
  stiffness: number // жёсткость пружины выбранного; соседям мягче с расстоянием
  room: boolean // добавить контейнеру отступы под раздувание, как у оригинала
}

const DEFAULTS: JellyOptions = {
  swell: 0.2,
  barge: 6,
  shrink: 0.05,
  jelly: 1,
  bounce: 0.25,
  stagger: 22,
  stiffness: 580,
  room: false,
}

// Сегменты на всю ширину: раздувать их на 20% — это пол-экрана, поэтому только «вздох»
const SOFT: Partial<JellyOptions> = { swell: 0.03, barge: 1, shrink: 0.03 }

const SUBSTEP = 1 / 240 // шаг интегрирования пружины, с
const MAX_FRAME = 1 / 15 // после паузы вкладки не прыгаем на много шагов разом

/** Пружина: масса на пружине с затуханием, как spring в motion */
class Spring {
  value: number
  target: number
  velocity = 0
  private k = 0
  private c = 0
  private m = 1
  private startAt = 0

  constructor(value: number) {
    this.value = value
    this.target = value
  }

  get moving(): boolean {
    return this.value !== this.target || this.velocity !== 0
  }

  jump(value: number) {
    this.value = value
    this.target = value
    this.velocity = 0
  }

  to(target: number, stiffness: number, mass: number, bounce: number, startAt: number) {
    this.target = target
    this.k = stiffness
    this.m = mass
    this.c = 2 * Math.sqrt(stiffness * mass) * (1 - bounce)
    this.startAt = startAt
  }

  step(dt: number, now: number) {
    if (!this.moving || now < this.startAt) return
    for (let left = dt; left > 0; left -= SUBSTEP) {
      const h = Math.min(SUBSTEP, left)
      const force = -this.k * (this.value - this.target) - this.c * this.velocity
      this.velocity += (force / this.m) * h
      this.value += this.velocity * h
    }
    if (Math.abs(this.value - this.target) < 5e-4 && Math.abs(this.velocity) < 5e-3) this.jump(this.target)
  }
}

interface Chip {
  el: HTMLElement
  x: Spring
  sx: Spring
  sy: Spring
}

function isActive(el: Element): boolean {
  return (
    el.getAttribute('aria-pressed') === 'true' ||
    el.getAttribute('aria-checked') === 'true' ||
    el.classList.contains('router-link-active')
  )
}

class Jelly {
  private chips: Chip[] = []
  private widths: number[] = []
  private selected = -1
  private frame = 0
  private last = 0
  private readonly mutations: MutationObserver
  private readonly resizes: ResizeObserver
  private readonly reduce = window.matchMedia('(prefers-reduced-motion: reduce)')

  constructor(
    private readonly root: HTMLElement,
    private options: JellyOptions,
  ) {
    this.mutations = new MutationObserver(() => this.sync())
    this.mutations.observe(root, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['aria-pressed', 'aria-checked', 'class'],
    })
    this.resizes = new ResizeObserver(() => this.settle())
    this.resizes.observe(root)
    void document.fonts?.ready.then(() => this.settle())
    this.settle()
  }

  update(options: JellyOptions) {
    this.options = options
    this.settle()
  }

  destroy() {
    this.mutations.disconnect()
    this.resizes.disconnect()
    cancelAnimationFrame(this.frame)
  }

  /** Пересобрать список и встать по месту без анимации — при старте, смене размеров и шрифтов */
  private settle() {
    this.collect()
    this.measure()
    this.selected = this.chips.findIndex((chip) => isActive(chip.el))
    this.apply(this.selected, true)
  }

  /** Выбор поменялся — анимируем к новому */
  private sync() {
    if (this.collect()) {
      this.settle()
      return
    }
    const next = this.chips.findIndex((chip) => isActive(chip.el))
    if (next === this.selected) return
    this.selected = next
    this.apply(next, false)
  }

  /** true — если дети поменялись */
  private collect(): boolean {
    const elements = [...this.root.children] as HTMLElement[]
    if (elements.length === this.chips.length && elements.every((el, i) => this.chips[i]?.el === el)) return false
    this.chips = elements.map((el) => {
      el.style.transformOrigin = '50% 50%'
      return { el, x: new Spring(0), sx: new Spring(1), sy: new Spring(1) }
    })
    return true
  }

  private measure() {
    // offsetWidth не зависит от transform — меряем «в покое»
    this.widths = this.chips.map((chip) => chip.el.offsetWidth)
    if (!this.options.room) return
    const { swell, barge } = this.options
    const maxWidth = Math.max(0, ...this.widths)
    const height = this.chips[0]?.el.offsetHeight ?? 0
    this.root.style.padding = `${Math.ceil((height * swell) / 2) + 2}px ${Math.ceil((maxWidth * swell * 1.3) / 2 + barge) + 2}px`
  }

  private apply(selected: number, instant: boolean) {
    const { swell, barge, shrink, jelly: j, bounce, stagger, stiffness } = this.options
    const push = selected < 0 ? 0 : ((this.widths[selected] ?? 0) * swell) / 2 + barge
    const now = performance.now()
    this.chips.forEach((chip, i) => {
      const far = selected < 0 ? 0 : Math.abs(i - selected)
      const x = selected < 0 ? 0 : Math.sign(i - selected) * push
      const scale = selected < 0 ? 1 : i === selected ? 1 + swell : 1 - shrink
      if (instant || this.reduce.matches) {
        chip.x.jump(x)
        chip.sx.jump(scale)
        chip.sy.jump(scale)
        return
      }
      const k = stiffness * (1 - 0.12 * Math.min(far, 3))
      const inFlight = chip.x.moving || chip.sx.moving || chip.sy.moving
      const delay = inFlight ? 0 : far * stagger
      chip.x.to(x, k, 0.9, bounce, now + delay)
      chip.sx.to(scale, k * (1 + 0.24 * j), 0.9 - 0.1 * j, Math.min(0.85, bounce + 0.3 * j), now + delay)
      chip.sy.to(scale, k * (1 - 0.14 * j), 0.9 + 0.05 * j, bounce, now + delay + 50 * j)
    })
    this.render()
    if (!instant && !this.frame) {
      this.last = now
      this.frame = requestAnimationFrame(this.tick)
    }
  }

  private tick = (now: number) => {
    const dt = Math.min((now - this.last) / 1000, MAX_FRAME)
    this.last = now
    let moving = false
    for (const chip of this.chips) {
      chip.x.step(dt, now)
      chip.sx.step(dt, now)
      chip.sy.step(dt, now)
      moving ||= chip.x.moving || chip.sx.moving || chip.sy.moving
    }
    this.render()
    this.frame = moving ? requestAnimationFrame(this.tick) : 0
  }

  private render() {
    for (const chip of this.chips) {
      chip.el.style.transform = `translateX(${chip.x.value}px) scale(${chip.sx.value}, ${chip.sy.value})`
    }
  }
}

const controllers = new WeakMap<HTMLElement, Jelly>()

function optionsOf(value: Partial<JellyOptions> | undefined, soft: boolean): JellyOptions {
  return { ...DEFAULTS, ...(soft ? SOFT : {}), ...value }
}

export const vJelly: Directive<HTMLElement, Partial<JellyOptions> | undefined> = {
  mounted(el, binding) {
    controllers.set(el, new Jelly(el, optionsOf(binding.value, Boolean(binding.modifiers.soft))))
  },
  updated(el, binding) {
    if (JSON.stringify(binding.value) !== JSON.stringify(binding.oldValue)) {
      controllers.get(el)?.update(optionsOf(binding.value, Boolean(binding.modifiers.soft)))
    }
  },
  unmounted(el) {
    controllers.get(el)?.destroy()
    controllers.delete(el)
  },
}

declare module 'vue' {
  interface GlobalDirectives {
    vJelly: typeof vJelly
  }
}
