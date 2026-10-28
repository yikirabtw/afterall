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
  faceit_elo: number | null
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
  photos: Photo[] // первое — главное
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
  has_faceit: boolean // можно указать FACEIT ELO (пока только CS2)
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
  faceit_elo: number | null
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

export interface LobbyMember {
  user_id: number
  display_name: string
  avatar_url: string | null
  reputation: number
  has_mic: boolean
  rank_id: number | null // ранг в игре этой пати
  role_ids: number[]
  faceit_elo: number | null
  status: MemberStatus
  is_owner: boolean
  note: string | null
  // Контакты — только когда смотрящий и сам участник приняты в пати
  username: string | null
  discord_tag: string | null
}

export interface LobbyDetail extends Lobby {
  // Создатель видит откликнувшихся и принятых, принятый — принятых, остальные — никого
  members: LobbyMember[]
}

export interface LobbyInput {
  kind: LobbyKind
  game_id: number | null
  title: string
  description: string | null
  slots_total: number
  rank_min_id: number | null
  rank_max_id: number | null
  need_mic: boolean
  play_style: PlayStyle | null
  language: string
  starts_at: string | null // ISO с часовым поясом; null — «прямо сейчас»
  contact_link: string | null
}

export type MemberDecision = 'accept' | 'decline' | 'kick'

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

export interface Photo {
  id: number
  url: string // подписанная ссылка, живёт несколько часов
}

export type ReactionKind = 'like' | 'skip'

export interface PersonGame {
  game_id: number
  rank_id: number | null
  role_ids: number[]
  faceit_elo: number | null
  is_main: boolean
}

/** Анкета в ленте людей. Контактов нет — они открываются после взаимного лайка */
export interface Person {
  user_id: number
  display_name: string
  age: number | null
  city: string | null
  bio: string | null
  has_mic: boolean
  play_style: PlayStyle
  looking_for: LookingFor
  languages: string[]
  reputation: number
  photos: Photo[]
  games: PersonGame[]
  compatibility: number // 0–100
  common_game_ids: number[]
  reasons: string[]
}

export interface Match {
  user_id: number
  display_name: string
  age: number | null
  photos: Photo[]
  main_game_id: number | null
  username: string | null
  discord_tag: string | null
  matched_at: string
}

export interface PeopleParams {
  game_id?: number
  need_mic?: boolean
  play_style?: PlayStyle
  language?: string
  limit?: number
}
