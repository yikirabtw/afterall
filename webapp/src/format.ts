import type { Slot } from './api/types'
import { WEEKDAYS_SHORT } from './labels'

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

export function formatMinutes(minutes: number): string {
  const hours = Math.floor(minutes / 60) % 24
  return `${String(hours).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`
}

/** Дни недели подряд склеиваются: [0,1,2,3,4] → «Пн–Пт», [0,2] → «Пн, Ср» */
function formatWeekdays(days: number[]): string {
  const parts: string[] = []
  let start = 0
  for (let i = 1; i <= days.length; i++) {
    if (i < days.length && days[i] === days[i - 1]! + 1) continue
    const first = WEEKDAYS_SHORT[days[start]!]
    const last = WEEKDAYS_SHORT[days[i - 1]!]
    parts.push(i - start >= 3 ? `${first}–${last}` : days.slice(start, i).map((d) => WEEKDAYS_SHORT[d]).join(', '))
    start = i
  }
  return parts.join(', ')
}

/** Расписание по-человечески: одинаковое время в разные дни — одной строкой, «Пн–Пт 18:00–23:00» */
export function formatSchedule(slots: Slot[]): string[] {
  const daysByTime = new Map<string, number[]>()
  for (const slot of slots) {
    const time = `${formatMinutes(slot.start_minute)}–${formatMinutes(slot.end_minute)}`
    daysByTime.set(time, [...(daysByTime.get(time) ?? []), slot.weekday])
  }
  return [...daysByTime].map(([time, days]) => `${formatWeekdays([...days].sort((a, b) => a - b))} ${time}`)
}

/** Сливает пересекающиеся и соседние интервалы одного дня — API не принимает пересечения */
export function mergeSlots(slots: Slot[]): Slot[] {
  const sorted = [...slots].sort((a, b) => a.weekday - b.weekday || a.start_minute - b.start_minute)
  const merged: Slot[] = []
  for (const slot of sorted) {
    const last = merged[merged.length - 1]
    if (last && last.weekday === slot.weekday && slot.start_minute <= last.end_minute) {
      last.end_minute = Math.max(last.end_minute, slot.end_minute)
    } else {
      merged.push({ ...slot })
    }
  }
  return merged
}
