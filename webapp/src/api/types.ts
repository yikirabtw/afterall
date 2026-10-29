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
  show_telegram: boolean // ник в Telegram видят мэтчи и участники пати, только если включено
  is_visible: boolean
  // Возраст поиска в ленте людей; null — до рамки (Me.search_age_limits)
  search_age_min: number | null
  search_age_max: number | null
  feed_presets: FeedPreset[] // наборы настроек ленты (Premium)
  equipped: Record<string, string> // надетая косметика: frame / background / badge / match → id
  reputation: number
}

/** Рамки ползунка «Возраст»: дальше них выбрать нельзя. max = null — без верхней границы (у взрослых) */
export interface AgeLimits {
  min: number
  max: number | null
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
  search_age_limits: AgeLimits | null
  plan: PlanInfo
  items: string[] // свои вещи косметики
  gift_available: boolean // Premium: можно забрать вещь в подарок
}

export type Plan = 'free' | 'plus' | 'premium'

/** Свой тариф и что он даёт; until — до какого момента действует (у бесплатного null) */
export interface PlanInfo {
  plan: Plan
  until: string | null
  photos_max: number
  active_lobbies_max: number
  rewinds_per_day: number | null // вернуть пропущенную анкету: 0 — нельзя, null — без лимита
}

/** Вернувшаяся анкета и сколько возвратов ещё осталось за сутки (null — без лимита) */
export interface RewindResult {
  person: Person
  left: number | null
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
  show_telegram: boolean
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
  boosted_until: string | null // поднята бустом до — на карточке пометка «поднята»
  is_private: boolean // закрытая: в ленте её нет, только по ссылке
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
  invite_code: string | null // код приглашения закрытой пати — только создателю
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
  is_private?: boolean // закрытая — только по ссылке-приглашению (Premium)
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
  width: number
  height: number
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
  plan: Plan // значок Plus / Premium у ника
  boosted: boolean // анкета поднята бустом — честная пометка
  look: Record<string, string> // надетая косметика: frame / background / badge
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

/** Кто поставил мне ♥, а я ещё не ответил. people = null — бесплатный тариф: видно только число */
export interface LikesInfo {
  count: number
  people: Person[] | null
}

export interface Match {
  user_id: number
  display_name: string
  plan: Plan
  age: number | null
  photos: Photo[]
  main_game_id: number | null
  username: string | null
  discord_tag: string | null
  matched_at: string
  look: Record<string, string>
}

/** Лента «Кого ищу»: play — побегать, chat — поболтать, friends — друзья надолго; без режима — все */
export type FeedMode = 'play' | 'chat' | 'friends'

export interface PeopleParams {
  mode?: FeedMode
  game_id?: number
  need_mic?: boolean
  play_style?: PlayStyle
  language?: string
  limit?: number
}

// --- Чаты ---

export type ChatKind = 'direct' | 'lobby' // direct — личный после мэтча, lobby — общий у пати

export interface ChatMessage {
  id: number
  sender_id: number
  sender_name: string
  mine: boolean
  body: string
  created_at: string
}

export interface ChatHead {
  kind: ChatKind
  ref: number // direct — id собеседника, lobby — id пати
  title: string
  photo: Photo | null
  game_id: number | null
  can_send: boolean // у закончившейся пати — только чтение
}

export interface ChatSummary extends ChatHead {
  last_message: ChatMessage | null
  unread: number
  updated_at: string
}

export interface Chat extends ChatHead {
  messages: ChatMessage[] // по возрастанию id
  has_more: boolean
}

// --- Жалобы и блокировки ---

export type ReportReason = 'minor_safety' | 'toxic' | 'spam' | 'scam' | 'inappropriate' | 'fake_profile' | 'other'

/** Жалоба на человека из мэтчей или из общей пати (тогда lobby_id). Сразу блокирует его для автора */
export interface ReportInput {
  user_id: number
  reason: ReportReason
  comment?: string | null
  lobby_id?: number | null
}

export interface BlockedUser {
  user_id: number
  display_name: string
  photo: Photo | null
  blocked_at: string
}

// --- Бусты ---

export type BoostKind = 'lobby' | 'profile'

/** Мои бусты: бесплатные по подписке на неделе, купленные, что поднято сейчас */
export interface BoostStatus {
  weekly_total: number
  weekly_left: number
  credits: number
  today_left: number
  profile_until: string | null
  lobbies: Record<string, string> // id моей пати → до какого момента поднята
}

/** О самом сервисе: ник бота — для ссылок-приглашений (локально его нет) */
export interface Meta {
  bot_username: string | null
}

/** Набор настроек ленты (Premium): режим «Кого ищу» и фильтры под именем */
export interface FeedPreset {
  name: string
  mode: FeedMode | null
  game_id: number | null
  need_mic: boolean
  play_style: PlayStyle | null
  language: string | null
}

// --- Магазин и оплата звёздами ---

export interface ShopProduct {
  id: string // как в src/shop.ts
  kind: 'plan' | 'boosts' | 'cosmetic'
  stars: number // обычная цена
  price: number // цена для меня (подписчикам косметика со скидкой)
  owned: boolean
}

export interface ShopInfo {
  payments_enabled: boolean // выключено — витрина «Скоро»
  products: ShopProduct[]
  spending_limit: number | null // лимит трат за 30 дней (13–17 лет)
  spent: number
}

export interface PaymentRecord {
  id: number
  product_id: string
  title: string
  stars: number
  is_recurring: boolean
  refunded: boolean
  created_at: string
}
