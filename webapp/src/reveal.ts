// «Расплытие»: новый вид раскрывается из нажатого элемента и проявляется из размытия.
// Работает на View Transitions API: браузер снимает старый кадр, мы меняем страницу, а форму
// рисует CSS (styles.css → «Расплытие»). Где API нет (старые webview) — меняем без анимации.
//   circle — круг из центра элемента (карандаш, смена темы);
//   morph — сам элемент растягивается до экрана (кнопка «Создать»).

import { nextTick } from 'vue'

export type RevealShape = 'circle' | 'morph'

/** Где был нажатый элемент: прямоугольник и скругление */
export interface Origin {
  left: number
  top: number
  width: number
  height: number
  radius: number
}

export function originOf(el: Element): Origin {
  const box = el.getBoundingClientRect()
  const radius = parseFloat(getComputedStyle(el).borderTopLeftRadius) || 0
  return { left: box.left, top: box.top, width: box.width, height: box.height, radius }
}

// Экраны, открытые «расплытием», и откуда: «Назад» сворачивает их туда же
const origins = new Map<string, { origin: Origin; shape: RevealShape }>()

export function rememberOrigin(path: string, origin: Origin, shape: RevealShape): void {
  origins.set(path, { origin, shape })
}

export function takeOrigin(path: string): { origin: Origin; shape: RevealShape } | undefined {
  const saved = origins.get(path)
  origins.delete(path)
  return saved
}

function setShapeVars(root: HTMLElement, from: Origin, shape: RevealShape) {
  const set = (name: string, px: number) => root.style.setProperty(name, `${Math.round(px)}px`)
  if (shape === 'circle') {
    const x = from.left + from.width / 2
    const y = from.top + from.height / 2
    set('--reveal-x', x)
    set('--reveal-y', y)
    // Радиус — до самого дальнего угла экрана, чтобы круг закрыл всё
    set('--reveal-r', Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y)))
  } else {
    // Отступы прямоугольника кнопки от краёв экрана — из них clip-path растёт до полного экрана
    set('--reveal-top', from.top)
    set('--reveal-right', innerWidth - from.left - from.width)
    set('--reveal-bottom', innerHeight - from.top - from.height)
    set('--reveal-left', from.left)
    set('--reveal-radius', from.radius)
  }
}

/**
 * Сменить вид «расплытием»: open — новый вид вырастает из элемента,
 * close — старый сворачивается в него, открывая то, что под ним.
 */
export async function reveal(
  from: Origin,
  change: () => unknown,
  mode: 'open' | 'close' = 'open',
  shape: RevealShape = 'circle',
): Promise<void> {
  const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (!document.startViewTransition || still) {
    await change()
    return
  }
  const root = document.documentElement
  setShapeVars(root, from, shape)
  root.dataset.reveal = `${mode}-${shape}`
  const transition = document.startViewTransition(async () => {
    await change()
    await nextTick() // новый экран должен успеть отрисоваться до снимка
  })
  try {
    await transition.finished
  } finally {
    delete root.dataset.reveal
  }
}
