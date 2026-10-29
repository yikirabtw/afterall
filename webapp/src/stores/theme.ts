// Тема приложения: тёмная по умолчанию, светлая — по выбору в профиле.
// Хранится на телефоне (localStorage): это настройка вида, на сервер её не шлём.

import { ref } from 'vue'

import { paintTelegram } from '../telegram'

export type Theme = 'dark' | 'light' | 'blue' | 'sepia' // blue и sepia — из магазина

const STORAGE_KEY = 'theme'
// Фон страницы в каждой теме — как --page в styles.css; им красим шапку Telegram
const PAGE_COLORS: Record<Theme, string> = { dark: '#000000', light: '#f5f5f5', blue: '#04060d', sepia: '#0b0805' }
const THEMES: Theme[] = ['dark', 'light', 'blue', 'sepia']

function readTheme(): Theme {
  try {
    const saved = localStorage.getItem(STORAGE_KEY) as Theme | null
    return saved && THEMES.includes(saved) ? saved : 'dark'
  } catch {
    return 'dark' // хранилище недоступно — просто тёмная
  }
}

export const theme = ref<Theme>(readTheme())

/** Применить тему к странице и шапке Telegram — при запуске и при каждой смене */
export function applyTheme(): void {
  document.documentElement.dataset.theme = theme.value
  paintTelegram(PAGE_COLORS[theme.value])
}

export function setTheme(value: Theme): void {
  theme.value = value
  try {
    localStorage.setItem(STORAGE_KEY, value)
  } catch {
    // не запомнится до следующего запуска — не страшно
  }
  applyTheme()
}
