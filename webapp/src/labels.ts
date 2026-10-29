// Подписи для значений из API — в одном месте, чтобы тексты не расползались по экранам

import type { AgeGroup, FeedMode, LobbyStatus, LookingFor, MemberStatus, PlayStyle, ReportReason } from './api/types'

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

// Причины жалобы — в порядке, как их видит человек; «подросток» — разбирается модераторами первой
export const REPORT_REASONS: { value: ReportReason; label: string }[] = [
  { value: 'toxic', label: 'Оскорбления или травля' },
  { value: 'inappropriate', label: 'Неприличные фото или сообщения' },
  { value: 'minor_safety', label: 'Пристаёт к подростку или угрожает' },
  { value: 'scam', label: 'Мошенничество' },
  { value: 'spam', label: 'Спам или реклама' },
  { value: 'fake_profile', label: 'Фейк или чужие фото' },
  { value: 'other', label: 'Другое' },
]

// Лента «Кого ищу»: режим задаёт, кого показывать и что важнее в «Совпадении»
export const FEED_MODES: { value: FeedMode | undefined; label: string }[] = [
  { value: undefined, label: 'Все' },
  { value: 'play', label: 'Побегать' },
  { value: 'chat', label: 'Поболтать' },
  { value: 'friends', label: 'Друзья' }, // «друзья надолго» — не влезает в телефон
]
