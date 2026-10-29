function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

/** «Сейчас», «Сегодня в 21:00», «Завтра в 19:30» — в часовом поясе телефона */
export function formatStart(startsAt: string | null, now = new Date()): string {
  if (!startsAt) return 'Сейчас'
  const start = new Date(startsAt)
  if (start <= now) return 'Сейчас'
  const time = start.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  if (sameDay(start, now)) return `Сегодня в ${time}`
  const tomorrow = new Date(now)
  tomorrow.setDate(now.getDate() + 1)
  if (sameDay(start, tomorrow)) return `Завтра в ${time}`
  return start.toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

/** «16 лет», «21 год», «13 лет» */
/** «28.11.2026» — до какого числа действует подписка */
export function formatDate(at: string): string {
  return new Date(at).toLocaleDateString('ru-RU')
}

export function formatAge(age: number): string {
  const lastTwo = age % 100
  const last = age % 10
  if (lastTwo >= 11 && lastTwo <= 14) return `${age} лет`
  if (last === 1) return `${age} год`
  if (last >= 2 && last <= 4) return `${age} года`
  return `${age} лет`
}

/** Время в чатах: «14:05» сегодня, «вчера», иначе «12.10» */
export function formatChatTime(at: string, now = new Date()): string {
  const date = new Date(at)
  if (sameDay(date, now)) return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (sameDay(date, yesterday)) return 'вчера'
  return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
}

/** Время под сообщением — всегда часы и минуты */
export function formatMessageTime(at: string): string {
  return new Date(at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}
