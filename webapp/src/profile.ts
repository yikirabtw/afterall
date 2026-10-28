// Анкета: лимиты и заготовка формы — общие для регистрации и редактирования профиля

import type { Me, ProfileInput, UserGameInput } from './api/types'

export const NAME_MAX = 20
export const BIO_MAX = 150
export const PHOTOS_MAX = 3

export function profileFormFrom(me: Me): ProfileInput {
  const existing = me.profile
  return {
    display_name: existing?.display_name ?? me.first_name.slice(0, NAME_MAX),
    bio: existing?.bio ?? null,
    has_mic: existing?.has_mic ?? true,
    play_style: existing?.play_style ?? 'balanced',
    looking_for: existing?.looking_for ?? 'both',
    languages: existing?.languages ?? ['ru'],
    city: existing?.city ?? null,
    // Часовой пояс берём с телефона — пригодится для уведомлений «в твоё время»
    timezone: existing?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'Europe/Moscow',
    discord_tag: existing?.discord_tag ?? null,
    is_visible: existing?.is_visible ?? true,
  }
}

/** Текст ошибки или null, если анкету можно сохранять */
export function profileError(form: ProfileInput): string | null {
  if (!form.display_name.trim()) return 'Как тебя называть? Ник обязателен.'
  return null
}

export const FACEIT_MIN = 100
export const FACEIT_MAX = 5000

/** Текст ошибки или null, если список игр можно сохранять */
export function gamesError(choices: UserGameInput[]): string | null {
  if (choices.length === 0) return 'Выбери хотя бы одну игру.'
  const badElo = choices.some(
    (choice) => choice.faceit_elo !== null && (choice.faceit_elo < FACEIT_MIN || choice.faceit_elo > FACEIT_MAX),
  )
  if (badElo) return `FACEIT ELO — число от ${FACEIT_MIN} до ${FACEIT_MAX}.`
  return null
}

/** Свои игры для редактирования — без выключенных игр: их больше нельзя выбрать */
export function gameChoicesFrom(me: Me, activeGameIds: Set<number>): UserGameInput[] {
  return me.games
    .filter((game) => activeGameIds.has(game.game_id))
    .map(({ game_id, rank_id, role_ids, faceit_elo, is_main }) => ({ game_id, rank_id, role_ids, faceit_elo, is_main }))
}
