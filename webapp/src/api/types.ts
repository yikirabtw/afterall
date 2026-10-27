// Типы ответов и запросов API — повторяют схемы бэкенда (backend/app/api/schemas.py)

export type AgeGroup = '13_15' | '16_17' | '18_plus'
export type PlayStyle = 'chill' | 'balanced' | 'tryhard'
export type LookingFor = 'games' | 'hangout' | 'both'
export type LobbyKind = 'game' | 'hangout'
export type LobbyStatus = 'open' | 'full' | 'started' | 'closed' | 'expired' | 'cancelled'
export type MemberStatus = 'pending' | 'accepted' | 'declined' | 'left' | 'kicked'

export interface Profile {
  display_name: string
  bio: string | null
  avatar_url: string | null
  has_mic: boolean
  play_style: PlayStyle
  looking_for: LookingFor
  languages: string[]
  country_code: string | null
  city: string | null
  timezone: string
  discord_tag: string | null
  is_visible: boolean
  reputation: number
}

export interface UserGame {
  game_id: number
  rank_id: number | null
  role_ids: number[]
  in_game_nick: string | null
  is_main: boolean
}

export interface Slot {
  weekday: number // 0 — пн, 6 — вс
  start_minute: number
  end_minute: number
}

export interface Me {
  id: number
  telegram_id: number
  username: string | null
  first_name: string
  language_code: string | null
  role: 'user' | 'moderator' | 'admin'
  birth_date: string | null
  age_group: AgeGroup | null
  is_onboarded: boolean
  profile: Profile | null
  games: UserGame[]
  availability: Slot[]
}

export interface GameRank {
  id: number
  code: string
  name: string
  tier: number
}

export interface GameRole {
  id: number
  code: string
  name: string
}

export interface Game {
  id: number
  slug: string
  name: string
  platforms: string[]
  max_party_size: number | null
  icon_url: string | null
  ranks: GameRank[]
  roles: GameRole[]
}

export interface ProfileInput {
  display_name: string
  bio: string | null
  has_mic: boolean
  play_style: PlayStyle
  looking_for: LookingFor
  languages: string[]
  city: string | null
  timezone: string
  discord_tag: string | null
  is_visible: boolean
}

export interface UserGameInput {
  game_id: number
  rank_id: number | null
  role_ids: number[]
  is_main: boolean
}

export interface LobbyOwner {
  user_id: number
  display_name: string
  avatar_url: string | null
  reputation: number
}

export interface Lobby {
  id: number
  kind: LobbyKind
  game_id: number | null
  title: string
  description: string | null
  slots_total: number
  slots_taken: number
  rank_min_id: number | null
  rank_max_id: number | null
  need_mic: boolean
  play_style: PlayStyle | null
  language: string
  starts_at: string | null
  expires_at: string
  status: LobbyStatus
  owner: LobbyOwner
  is_owner: boolean
  my_status: MemberStatus | null
  contact_link: string | null
}

export interface LobbyFeed {
  items: Lobby[]
  next_cursor: number | null
}

export interface FeedParams {
  game_id?: number
  kind?: LobbyKind
  fits_me?: boolean
  cursor?: number
  limit?: number
}
