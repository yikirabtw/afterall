// Подписи для значений из API — в одном месте, чтобы тексты не расползались по экранам

import type { AgeGroup, LobbyStatus, LookingFor, MemberStatus, PlayStyle } from './api/types'

export const PLAY_STYLES: { value: PlayStyle; label: string }[] = [
  { value: 'chill', label: 'Чилл' },
  { value: 'balanced', label: 'Баланс' },
  { value: 'tryhard', label: 'Трайхард' },
]

export const LOOKING_FOR: { value: LookingFor; label: string }[] = [
  { value: 'games', label: 'Тиммейтов' },
  { value: 'hangout', label: 'Компанию' },
  { value: 'both', label: 'Всё сразу' },
]

export const LANGUAGES: { value: string; label: string }[] = [
  { value: 'ru', label: 'Русский' },
  { value: 'en', label: 'English' },
  { value: 'uk', label: 'Українська' },
  { value: 'kk', label: 'Қазақша' },
]

export const AGE_GROUP_LABELS: Record<AgeGroup, string> = {
  '13_15': '13–15 лет',
  '16_17': '16–17 лет',
  '18_plus': '18+',
}

export const PLAY_STYLE_LABELS: Record<PlayStyle, string> = Object.fromEntries(
  PLAY_STYLES.map(({ value, label }) => [value, label]),
) as Record<PlayStyle, string>

export const LOBBY_STATUS_LABELS: Partial<Record<LobbyStatus, string>> = {
  full: 'Набрана',
  expired: 'Закончилась',
  cancelled: 'Отменена',
}

export const MEMBER_STATUS_LABELS: Partial<Record<MemberStatus, string>> = {
  pending: 'Ждёт ответа',
  accepted: 'Ты в пати',
}
