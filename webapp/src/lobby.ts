// Подписи для пати, общие для карточки в ленте и экрана пати

import type { Lobby, LobbyStatus } from './api/types'
import { gameById } from './stores/session'

export const ACTIVE_STATUSES: LobbyStatus[] = ['open', 'full']

export function rankName(gameId: number | null, rankId: number | null): string | null {
  return gameById(gameId)?.ranks.find((rank) => rank.id === rankId)?.name ?? null
}

export function roleNames(gameId: number | null, roleIds: number[]): string[] {
  return gameById(gameId)?.roles.filter((role) => roleIds.includes(role.id)).map((role) => role.name) ?? []
}

/** «Страж – Легенда», «Герой и выше», «Рыцарь и ниже» или null, если ранг неважен */
export function rankRangeLabel(lobby: Pick<Lobby, 'game_id' | 'rank_min_id' | 'rank_max_id'>): string | null {
  const min = rankName(lobby.game_id, lobby.rank_min_id)
  const max = rankName(lobby.game_id, lobby.rank_max_id)
  if (min && max) return min === max ? min : `${min} – ${max}`
  if (min) return `${min} и выше`
  if (max) return `${max} и ниже`
  return null
}

export function gameTitle(lobby: Pick<Lobby, 'game_id'>): string {
  return gameById(lobby.game_id)?.name ?? 'Просто посидеть'
}
