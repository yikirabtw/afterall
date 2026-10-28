<script setup lang="ts">
import '@fontsource/metal-mania/400.css'
import { onBeforeUnmount, onMounted, ref } from 'vue'

// Логотип заставки по референсу ascii-art: хромовая надпись с шипами рисуется скрыто,
// а на экран выводится горизонтальными штрихами разной яркости — с мерцанием, сбоями строк и зерном.
const WORD = 'AFTERALL'
const FONT = '"Metal Mania"'
const CELL_W = 3
const CELL_H = 3
const REVEAL_MS = 1100
const FRAME_MS = 33 // ~30 кадров в секунду — телефону хватит

interface Cell {
  x: number
  y: number
  light: number // яркость 0..1
  seed: number // момент появления при сборке
}

const canvas = ref<HTMLCanvasElement>()
let raf = 0

/** Шипастая хромовая надпись — источник, из которого берутся штрихи */
function drawSource(width: number, height: number): CanvasRenderingContext2D {
  const source = document.createElement('canvas')
  source.width = width
  source.height = height
  const ctx = source.getContext('2d', { willReadFrequently: true })!

  let size = height * 0.42
  ctx.font = `${size}px ${FONT}`
  size *= (width * 0.74) / ctx.measureText(WORD).width
  ctx.font = `${size}px ${FONT}`
  const textWidth = ctx.measureText(WORD).width
  const cx = width / 2
  const cy = height * 0.56
  const left = cx - textWidth / 2
  const right = cx + textWidth / 2

  const chrome = ctx.createLinearGradient(0, cy - size * 0.9, 0, cy + size * 0.8)
  chrome.addColorStop(0, '#ffffff')
  chrome.addColorStop(0.32, '#8c8c8c')
  chrome.addColorStop(0.5, '#ffffff')
  chrome.addColorStop(0.64, '#6e6e6e')
  chrome.addColorStop(1, '#e6e6e6')
  ctx.fillStyle = chrome

  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(WORD, cx, cy)

  // Рога-полумесяцы по краям, загнутые вверх и наружу
  for (const side of [-1, 1]) {
    const baseX = side < 0 ? left + size * 0.2 : right - size * 0.2
    const tipX = baseX + side * size * 0.75
    const tipY = cy - size * 1.05
    ctx.beginPath()
    ctx.moveTo(baseX - side * size * 0.12, cy - size * 0.18)
    ctx.quadraticCurveTo(baseX + side * size * 0.55, cy - size * 0.35, tipX, tipY)
    ctx.quadraticCurveTo(baseX + side * size * 0.2, cy - size * 0.55, baseX + side * size * 0.05, cy - size * 0.3)
    ctx.closePath()
    ctx.fill()

    // Боковой шип наружу
    ctx.beginPath()
    ctx.moveTo(baseX - side * size * 0.05, cy + size * 0.02)
    ctx.lineTo(baseX + side * size * 0.95, cy + size * 0.12)
    ctx.lineTo(baseX - side * size * 0.05, cy + size * 0.2)
    ctx.closePath()
    ctx.fill()
  }

  // Капли-шипы вниз из-под букв
  for (const at of [0.18, 0.41, 0.59, 0.82]) {
    const x = left + textWidth * at
    const long = at === 0.41 || at === 0.59 ? 0.75 : 0.55
    ctx.beginPath()
    ctx.moveTo(x - size * 0.05, cy + size * 0.22)
    ctx.lineTo(x, cy + size * long)
    ctx.lineTo(x + size * 0.05, cy + size * 0.22)
    ctx.closePath()
    ctx.fill()
  }

  // Четырёхлучевая звезда над центром
  const starY = cy - size * 0.82
  const r = size * 0.2
  ctx.beginPath()
  ctx.moveTo(cx, starY - r)
  ctx.quadraticCurveTo(cx, starY, cx + r * 0.6, starY)
  ctx.quadraticCurveTo(cx, starY, cx, starY + r)
  ctx.quadraticCurveTo(cx, starY, cx - r * 0.6, starY)
  ctx.quadraticCurveTo(cx, starY, cx, starY - r)
  ctx.fill()

  return ctx
}

function sampleCells(source: CanvasRenderingContext2D, width: number, height: number): Cell[] {
  const { data } = source.getImageData(0, 0, width, height)
  const cells: Cell[] = []
  for (let y = 0; y < height; y += CELL_H) {
    for (let x = 0; x < width; x += CELL_W) {
      const i = (Math.min(y + (CELL_H >> 1), height - 1) * width + Math.min(x + (CELL_W >> 1), width - 1)) * 4
      const light = ((data[i] + data[i + 1] + data[i + 2]) / 765) * (data[i + 3] / 255)
      if (light > 0.06) cells.push({ x, y, light, seed: Math.random() * 0.75 + (y / height) * 0.25 })
    }
  }
  return cells
}

onMounted(async () => {
  const el = canvas.value
  if (!el) return
  // Шрифт грузится отдельно; если сеть медленная — не ждём дольше секунды
  await Promise.race([document.fonts.load(`64px ${FONT}`), new Promise((resolve) => setTimeout(resolve, 1000))])
  if (!canvas.value) return

  const width = Math.round(el.clientWidth)
  const height = Math.round(el.clientHeight)
  const dpr = Math.min(window.devicePixelRatio || 1, 3)
  el.width = width * dpr
  el.height = height * dpr
  const ctx = el.getContext('2d')!
  ctx.scale(dpr, dpr)

  const cells = sampleCells(drawSource(width, height), width, height)
  const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const startedAt = performance.now()
  let last = 0
  let glitchUntil = 0
  let glitchRow = 0
  let glitchShift = 0

  const render = (now: number) => {
    raf = still ? 0 : requestAnimationFrame(render)
    if (!still && now - last < FRAME_MS) return
    last = now
    const progress = still ? 2 : (now - startedAt) / REVEAL_MS

    // Изредка «сбой»: полоса строк сдвигается вбок, как на плёнке
    if (!still && now > glitchUntil + 900 && Math.random() < 0.04) {
      glitchUntil = now + 90
      glitchRow = Math.random() * height
      glitchShift = (Math.random() < 0.5 ? -1 : 1) * (4 + Math.random() * 8)
    }

    ctx.clearRect(0, 0, width, height)
    ctx.fillStyle = '#fff'
    for (const cell of cells) {
      if (cell.seed > progress) continue
      const flicker = still ? 1 : 0.72 + Math.random() * 0.28
      const shift = now < glitchUntil && Math.abs(cell.y - glitchRow) < 14 ? glitchShift : 0
      ctx.globalAlpha = Math.min(1, cell.light * 1.15) * flicker
      ctx.fillRect(cell.x + shift, cell.y + 1, CELL_W * (0.5 + cell.light * 0.7), 1.3)
    }

    // Зерно поверх
    ctx.globalAlpha = 0.18
    for (let n = 0; n < 90; n++) ctx.fillRect(Math.random() * width, Math.random() * height, 1, 1)
    ctx.globalAlpha = 1
  }
  raf = requestAnimationFrame(render)
})

onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<template>
  <canvas ref="canvas" class="ascii-logo" role="img" aria-label="afterall" />
</template>

<style scoped>
.ascii-logo {
  display: block;
  width: min(88vw, 420px);
  aspect-ratio: 2 / 1;
  filter: drop-shadow(0 0 6px rgb(255 255 255 / 0.35)) drop-shadow(0 0 28px rgb(255 255 255 / 0.12));
}
</style>
