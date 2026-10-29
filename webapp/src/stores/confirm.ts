import { reactive } from 'vue'

// Подтверждение опасного действия вне Telegram — своё окно (ConfirmDialog.vue), а не window.confirm:
// встроенные браузеры и панели разработки системные окна часто глушат, и confirm сразу отвечает «нет»
export const confirmState = reactive({ open: false, message: '' })

let resolve: ((ok: boolean) => void) | null = null

export function askInApp(message: string): Promise<boolean> {
  resolve?.(false) // прошлый вопрос без ответа — считаем отменой
  confirmState.message = message
  confirmState.open = true
  return new Promise((done) => (resolve = done))
}

export function answer(ok: boolean): void {
  confirmState.open = false
  resolve?.(ok)
  resolve = null
}
