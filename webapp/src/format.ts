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
export function formatAge(age: number): string {
  const lastTwo = age % 100
  const last = age % 10
  if (lastTwo >= 11 && lastTwo <= 14) return `${age} лет`
  if (last === 1) return `${age} год`
  if (last >= 2 && last <= 4) return `${age} года`
  return `${age} лет`
}
