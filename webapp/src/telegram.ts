// Обёртка над Telegram Mini Apps SDK (telegram-web-app.js подключён в index.html).
// Описаны только те части SDK, которыми пользуемся.

import { onBeforeUnmount, watch, type Ref } from 'vue'

interface TelegramWebApp {
  initData: string
  initDataUnsafe: { user?: { id: number; first_name: string; username?: string } }
  colorScheme: 'light' | 'dark'
  ready(): void
  expand(): void
  isVersionAtLeast(version: string): boolean
  setHeaderColor(color: string): void
  setBackgroundColor(color: string): void
  openTelegramLink(url: string): void
  openLink(url: string): void
  BackButton: {
    show(): void
    hide(): void
    onClick(callback: () => void): void
    offClick(callback: () => void): void
  }
  HapticFeedback: {
    impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void
    notificationOccurred(type: 'error' | 'success' | 'warning'): void
    selectionChanged(): void
  }
}

declare global {
  interface Window {
    Telegram?: { WebApp: TelegramWebApp }
  }
}

const webApp = window.Telegram?.WebApp

/** Приложение открыто из Telegram (а не в обычном браузере при разработке) */
export const insideTelegram = Boolean(webApp?.initData)

function supports(version: string): boolean {
  return insideTelegram && webApp!.isVersionAtLeast(version)
}

const LOCAL_HOSTS = new Set(['127.0.0.1', 'localhost'])

/**
 * initData для заголовка Authorization. Вне Telegram в режиме разработки — тестовая подпись из
 * .env.development.local, но только на этом компьютере: если dev-сервер открыт наружу через туннель,
 * посторонний по ссылке не должен войти тестовым пользователем.
 */
export function getInitData(): string {
  if (webApp?.initData) return webApp.initData
  if (import.meta.env.DEV && LOCAL_HOSTS.has(window.location.hostname)) {
    return import.meta.env.VITE_DEV_INIT_DATA ?? ''
  }
  return ''
}

export function setupTelegram(): void {
  if (!insideTelegram) return
  webApp!.ready()
  webApp!.expand()
  if (supports('6.1')) {
    webApp!.setHeaderColor('secondary_bg_color')
    webApp!.setBackgroundColor('secondary_bg_color')
  }
}

export const haptic = {
  tap: () => supports('6.1') && webApp!.HapticFeedback.impactOccurred('light'),
  select: () => supports('6.1') && webApp!.HapticFeedback.selectionChanged(),
  success: () => supports('6.1') && webApp!.HapticFeedback.notificationOccurred('success'),
  error: () => supports('6.1') && webApp!.HapticFeedback.notificationOccurred('error'),
}

/** Системная кнопка «Назад» Telegram: показывается, пока visible = true */
export function useBackButton(onBack: () => void, visible: Ref<boolean>): void {
  if (!supports('6.1')) return
  const button = webApp!.BackButton
  button.onClick(onBack)
  watch(visible, (show) => (show ? button.show() : button.hide()), { immediate: true })
  onBeforeUnmount(() => {
    button.offClick(onBack)
    button.hide()
  })
}
