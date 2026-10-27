/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Подписанная initData тестового пользователя — только для разработки в обычном браузере */
  readonly VITE_DEV_INIT_DATA?: string
  /** Адрес API, если он на другом домене. По умолчанию — тот же домен, путь /api */
  readonly VITE_API_URL?: string
}
