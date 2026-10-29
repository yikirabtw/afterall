// Косметика на живых экранах (а не только в превью магазина): пиксельные значки, темы, классы рамок и фонов.
// Что продаётся — src/shop.ts; что надето — profile.equipped (своё) и person.look / match.look (у других).

import type { Theme } from './stores/theme'

// Пиксельные значки 7×7: # — закрашенная клетка
export const BADGE_PIXELS: Record<string, string[]> = {
  night: ['..###..', '.##....', '##.....', '##.....', '##.....', '.##....', '..###..'],
  heart: ['.##.##.', '#######', '#######', '#######', '.#####.', '..###..', '...#...'],
  star: ['...#...', '...#...', '#######', '.#####.', '..###..', '.##.##.', '.#...#.'],
  crown: ['#..#..#', '#.###.#', '#######', '#######', '#######', '.......', '#######'],
}

// id вещи → рисунок значка
export const BADGE_STYLE: Record<string, string> = {
  'badge-night': 'night',
  'badge-heart': 'heart',
  'badge-first': 'star',
  'badge-veteran': 'crown',
}

export function badgeCells(style: string): { x: number; y: number }[] {
  const rows = BADGE_PIXELS[style] ?? []
  return rows.flatMap((row, y) => [...row].map((cell, x) => (cell === '#' ? { x, y } : null)).filter((c) => c !== null))
}

/** Класс рамки для аватара: frame-neon → look-frame--neon */
export function frameClass(itemId: string | undefined): string | undefined {
  return itemId ? `look-frame--${itemId.replace('frame-', '')}` : undefined
}

/** Класс фона карточки: bg-smoke → look-bg--smoke */
export function backgroundClass(itemId: string | undefined): string | undefined {
  return itemId ? `look-bg--${itemId.replace('bg-', '')}` : undefined
}

// Темы из магазина — включаются в профиле, если куплены
export const ITEM_THEMES: { item: string; value: Theme; label: string }[] = [
  { item: 'theme-blue', value: 'blue', label: 'Синий час' },
  { item: 'theme-sepia', value: 'sepia', label: 'Сепия' },
]
