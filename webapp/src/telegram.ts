// Обёртка над Telegram Mini Apps SDK (telegram-web-app.js подключён в index.html).
// Описаны только те части SDK, которыми пользуемся.

import { onBeforeUnmount, watch, type Ref } from 'vue'

import { askInApp } from './stores/confirm'

interface TelegramWebApp {
  initData: string
  initDataUnsafe: { user?: { id: number; first_name: string; username?: string } }
  colorScheme: 'light' | 'dark'
  ready(): void
  expand(): void
  isVersionAtLeast(version: string): boolean
  setHeaderColor(color: string): void
  setBackgroundColor(color: string): void
  setBottomBarColor(color: string): void
  disableVerticalSwipes(): void
  enableVerticalSwipes(): void
  openTelegramLink(url: string): void
  openLink(url: string): void
  showConfirm(message: string, callback: (confirmed: boolean) => void): void
  openInvoice(url: string, callback: (status: 'paid' | 'cancelled' | 'failed' | 'pending') => void): void
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
}

/** Шапка, фон и нижняя полоса Telegram — в цвет фона приложения (меняется вместе с темой) */
export function paintTelegram(color: string): void {
  if (supports('6.1')) webApp!.setBackgroundColor(color)
  if (supports('6.9')) webApp!.setHeaderColor(color)
  else if (supports('6.1')) webApp!.setHeaderColor('bg_color')
  if (supports('7.10')) webApp!.setBottomBarColor(color)
}

/**
 * Системный жест «свайп вниз — свернуть приложение». Выключаем, пока свой вертикальный свайп
 * что-то делает (раскрытое фото профиля), иначе Telegram перехватит его и закроет приложение.
 */
export function setVerticalSwipes(enabled: boolean): void {
  if (!supports('7.7')) return
  if (enabled) webApp!.enableVerticalSwipes()
  else webApp!.disableVerticalSwipes()
}

export const haptic = {
  tap: () => supports('6.1') && webApp!.HapticFeedback.impactOccurred('light'),
  select: () => supports('6.1') && webApp!.HapticFeedback.selectionChanged(),
  success: () => supports('6.1') && webApp!.HapticFeedback.notificationOccurred('success'),
  error: () => supports('6.1') && webApp!.HapticFeedback.notificationOccurred('error'),
}

/** Подтверждение опасного действия: системное окно Telegram, в браузере — своё окно (ConfirmDialog.vue) */
export function confirmAction(message: string): Promise<boolean> {
  if (supports('6.2')) return new Promise((resolve) => webApp!.showConfirm(message, resolve))
  return askInApp(message)
}

/** Ссылки t.me открываем внутри Telegram, остальные (Discord) — во внешнем браузере */
export function openExternal(url: string): void {
  if (!insideTelegram) {
    window.open(url, '_blank', 'noopener')
  } else if (/^https:\/\/(t\.me|telegram\.me)\//.test(url)) {
    webApp!.openTelegramLink(url)
  } else {
    webApp!.openLink(url)
  }
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

/** Окно оплаты звёздами Telegram по ссылке на счёт. Вне Telegram оплатить нельзя — сразу 'unsupported' */
export function openInvoice(url: string): Promise<'paid' | 'cancelled' | 'failed' | 'pending' | 'unsupported'> {
  if (!supports('6.1')) return Promise.resolve('unsupported')
  return new Promise((resolve) => webApp!.openInvoice(url, resolve))
}
