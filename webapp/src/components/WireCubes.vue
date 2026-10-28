<script setup lang="ts">
// Каркасные кубы с «пылью» вокруг — иллюстрация из референса полного визуала (EX8).
// Рисуем сами в SVG: изометрический куб — это шесть граней из трёх видимых и трёх скрытых рёбер.

interface Cube {
  x: number
  y: number
  size: number
  solid?: boolean
}

const CUBES: Cube[] = [
  { x: 52, y: 40, size: 22 },
  { x: 92, y: 62, size: 26 },
  { x: 40, y: 88, size: 18 },
  { x: 118, y: 30, size: 14, solid: true },
  { x: 82, y: 106, size: 12, solid: true },
]

const DUST = [
  [14, 30, 3],
  [22, 64, 2],
  [130, 74, 3],
  [142, 50, 2],
  [104, 14, 2],
  [70, 18, 3],
  [124, 104, 2],
  [16, 110, 2],
  [60, 128, 3],
  [140, 120, 2],
] as const

const COS = 0.866

function cubePaths({ x, y, size }: Cube) {
  const dx = size * COS
  const half = size / 2
  // Вершины верхней грани: верх, право, низ (ближняя), лево
  const top = [x, y - size]
  const right = [x + dx, y - half]
  const near = [x, y]
  const left = [x - dx, y - half]
  const down = (point: number[]) => [point[0], point[1] + size]
  const p = (point: number[]) => point.join(',')
  return {
    visible: [
      `M${p(top)}L${p(right)}L${p(near)}L${p(left)}Z`,
      `M${p(left)}L${p(down(left))}L${p(down(near))}L${p(down(right))}L${p(right)}`,
      `M${p(near)}L${p(down(near))}`,
    ].join(''),
    hidden: `M${p(top)}L${p(down(top))}M${p(down(left))}L${p(down(top))}L${p(down(right))}`,
    faces: {
      top: `M${p(top)}L${p(right)}L${p(near)}L${p(left)}Z`,
      leftSide: `M${p(left)}L${p(near)}L${p(down(near))}L${p(down(left))}Z`,
      rightSide: `M${p(near)}L${p(right)}L${p(down(right))}L${p(down(near))}Z`,
    },
  }
}

const cubes = CUBES.map((cube) => ({ ...cube, paths: cubePaths(cube) }))
</script>

<template>
  <svg class="cubes" viewBox="0 0 160 140" aria-hidden="true">
    <g v-for="(cube, index) in cubes" :key="index" class="cubes__cube" :style="{ animationDelay: `${index * -0.7}s` }">
      <template v-if="cube.solid">
        <path :d="cube.paths.faces.top" class="cubes__face--top" />
        <path :d="cube.paths.faces.leftSide" class="cubes__face--left" />
        <path :d="cube.paths.faces.rightSide" class="cubes__face--right" />
      </template>
      <template v-else>
        <path :d="cube.paths.hidden" class="cubes__hidden" />
        <path :d="cube.paths.visible" class="cubes__edge" />
      </template>
    </g>
    <rect
      v-for="([x, y, size], index) in DUST"
      :key="`d${index}`"
      :x="x"
      :y="y"
      :width="size"
      :height="size"
      class="cubes__dust"
      :style="{ animationDelay: `${index * -0.45}s` }"
    />
  </svg>
</template>

<style scoped>
.cubes {
  display: block;
  overflow: visible;
  filter: drop-shadow(0 0 6px rgb(var(--glow-rgb) / 0.25));
}

.cubes__edge,
.cubes__hidden {
  fill: none;
  stroke: var(--g-950);
  stroke-width: 1.4;
  stroke-linejoin: round;
}

.cubes__hidden {
  stroke-opacity: 0.25;
}

.cubes__face--top {
  fill: var(--g-900);
}

.cubes__face--left {
  fill: var(--g-600);
}

.cubes__face--right {
  fill: var(--g-400);
}

.cubes__cube {
  animation: float 4s ease-in-out infinite alternate;
}

.cubes__dust {
  fill: var(--g-700);
  animation: twinkle 2.4s ease-in-out infinite alternate;
}

@keyframes float {
  from {
    transform: translateY(-2px);
  }

  to {
    transform: translateY(3px);
  }
}

@keyframes twinkle {
  from {
    opacity: 0.25;
  }

  to {
    opacity: 0.9;
  }
}

@media (prefers-reduced-motion: reduce) {
  .cubes__cube,
  .cubes__dust {
    animation: none;
  }
}
</style>
