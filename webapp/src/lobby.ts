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

// Цвет игры — светящаяся полоска на карточках (цвет в визуале только точечный)
const GAME_COLORS: Record<string, string> = {
  dota2: '#ff4b3e',
  cs2: '#ffa62b',
  valorant: '#ff3d8b',
  minecraft: '#3ddc6a',
}
const NO_GAME_COLOR = '#7b5cff' // «Просто посидеть»

export function gameColor(gameId: number | null): string {
  const slug = gameById(gameId)?.slug
  if (!slug) return NO_GAME_COLOR
  return GAME_COLORS[slug] ?? '#d4d4d4'
}

// Верхние границы ELO для уровней FACEIT 1–9; выше 2000 — 10 уровень
const FACEIT_LEVEL_MAX = [500, 750, 900, 1050, 1200, 1350, 1530, 1750, 2000]

export function faceitLevel(elo: number): number {
  const index = FACEIT_LEVEL_MAX.findIndex((max) => elo <= max)
  return index === -1 ? 10 : index + 1
}

/** «FACEIT 2150 · 10 lvl» */
export function faceitLabel(elo: number): string {
  return `FACEIT ${elo} · ${faceitLevel(elo)} lvl`
}
