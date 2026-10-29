import { getInitData } from '../telegram'
import type {
  BlockedUser,
  BoostKind,
  BoostStatus,
  Chat,
  ChatKind,
  ChatMessage,
  ChatSummary,
  FeedParams,
  FeedPreset,
  Game,
  LikesInfo,
  Lobby,
  LobbyDetail,
  LobbyFeed,
  LobbyInput,
  Match,
  Meta,
  Me,
  MemberDecision,
  PeopleParams,
  PaymentRecord,
  Person,
  ProfileInput,
  ReactionKind,
  ReportInput,
  RewindResult,
  ShopInfo,
  UserGameInput,
} from './types'

const BASE_URL = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly detail: unknown

  constructor(status: number, code: string, detail: unknown = null) {
    super(code)
    this.status = status
    this.code = code
    this.detail = detail
  }
}

/** Код ошибки из ответа API: строка, {"code": ...} или список ошибок полей от FastAPI */
function errorCode(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return 'validation_error'
  if (detail && typeof detail === 'object' && 'code' in detail) return String(detail.code)
  return 'unknown_error'
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Authorization: `tma ${getInitData()}` }
  // Файлы (FormData) браузер оформляет сам — заголовок с границей частей ставить нельзя
  const isForm = body instanceof FormData
  if (body !== undefined && !isForm) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(`${BASE_URL}/api${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'network_error')
  }

  if (!response.ok) {
    let detail: unknown = null
    try {
      detail = ((await response.json()) as { detail?: unknown }).detail
    } catch {
      // ответ без JSON — оставляем detail пустым
    }
    throw new ApiError(response.status, errorCode(detail), detail)
  }
  if (response.status === 204) return undefined as T // «готово, без тела» — например, удаление
  return (await response.json()) as T
}

function toQuery(params: object): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== false) query.set(key, String(value))
  }
  return query.toString()
}

/** Ссылки на фото API отдаёт относительными — дополняем адресом API, если он на другом домене */
export function assetUrl(path: string): string {
  return `${BASE_URL}${path}`
}

function inviteQuery(invite?: string): string {
  return invite ? `?invite=${encodeURIComponent(invite)}` : ''
}

export const api = {
  me: () => request<Me>('GET', '/me'),
  games: () => request<Game[]>('GET', '/games'),

  setBirthDate: (birthDate: string) => request<Me>('PUT', '/me/birth-date', { birth_date: birthDate }),
  saveProfile: (profile: ProfileInput) => request<Me>('PUT', '/me/profile', profile),
  saveGames: (games: UserGameInput[]) => request<Me>('PUT', '/me/games', { games }),
  // Возраст поиска в ленте людей, взаимный; null — до самой рамки
  saveSearchAge: (min: number | null, max: number | null) =>
    request<Me>('PUT', '/me/search-age', { age_min: min, age_max: max }),
  completeOnboarding: () => request<Me>('POST', '/me/onboarding/complete'),

  uploadPhoto: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Me>('POST', '/me/photos', form)
  },
  deletePhoto: (id: number) => request<Me>('DELETE', `/me/photos/${id}`),
  reorderPhotos: (ids: number[]) => request<Me>('PUT', '/me/photos/order', { photo_ids: ids }),

  people: (params: PeopleParams) => request<Person[]>('GET', `/people?${toQuery(params)}`),
  react: (userId: number, kind: ReactionKind) =>
    request<{ match: Match | null }>('POST', `/people/${userId}/react`, { kind }),
  matches: () => request<Match[]>('GET', '/matches'),
  // Кто лайкнул: число — всем, список — с Plus и Premium
  likes: () => request<LikesInfo>('GET', '/people/likes'),
  // Бусты: поднять свою пати на час или анкету на вечер
  boosts: () => request<BoostStatus>('GET', '/boosts'),
  useBoost: (kind: BoostKind, lobbyId?: number) =>
    request<BoostStatus>('POST', '/boosts', { kind, lobby_id: lobbyId ?? null }),
  // Вернуть последнюю пропущенную анкету: Plus — 3 в сутки, Premium — без лимита
  rewind: () => request<RewindResult>('POST', '/people/rewind'),

  // Жалоба сразу блокирует человека и уходит модераторам; блокировка — взаимная невидимость
  report: (input: ReportInput) => request<void>('POST', '/reports', input),
  block: (userId: number) => request<void>('POST', `/blocks/${userId}`),
  unblock: (userId: number) => request<void>('DELETE', `/blocks/${userId}`),
  blocks: () => request<BlockedUser[]>('GET', '/blocks'),
  // Мэтч удаляется у обоих вместе с личным чатом; человек больше не появится в ленте
  deleteMatch: (userId: number) => request<void>('DELETE', `/matches/${userId}`),

  chats: () => request<ChatSummary[]>('GET', '/chats'),
  chat: (kind: ChatKind, ref: number, params: { after?: number; before?: number } = {}) =>
    request<Chat>('GET', `/chats/${kind}/${ref}?${toQuery(params)}`),
  sendMessage: (kind: ChatKind, ref: number, body: string) =>
    request<ChatMessage>('POST', `/chats/${kind}/${ref}/messages`, { body }),

  feed: (params: FeedParams) => request<LobbyFeed>('GET', `/lobbies?${toQuery(params)}`),
  myLobbies: () => request<Lobby[]>('GET', '/lobbies/mine'),

  // Все действия с пати возвращают свежую карточку — экран просто подменяет её
  createLobby: (lobby: LobbyInput) => request<LobbyDetail>('POST', '/lobbies', lobby),
  // invite — код из ссылки-приглашения: без него закрытую пати видят только участники
  lobby: (id: number, invite?: string) => request<LobbyDetail>('GET', `/lobbies/${id}${inviteQuery(invite)}`),
  lobbyByInvite: (code: string) => request<LobbyDetail>('GET', `/lobbies/invite/${encodeURIComponent(code)}`),
  apply: (id: number, note: string | null, invite?: string) =>
    request<LobbyDetail>('POST', `/lobbies/${id}/apply${inviteQuery(invite)}`, { note }),
  meta: () => request<Meta>('GET', '/meta'),
  // Магазин: цены с сервера, счёт на оплату звёздами, история, отмена продления
  shop: () => request<ShopInfo>('GET', '/shop'),
  invoice: (productId: string) => request<{ url: string }>('POST', '/shop/invoice', { product_id: productId }),
  payments: () => request<PaymentRecord[]>('GET', '/shop/payments'),
  cancelSubscription: () => request<void>('POST', '/shop/subscription/cancel'),
  // Косметика: надеть свои вещи (null — снять), подарок Premium раз в 30 дней
  equip: (slots: Record<string, string | null>) => request<Me>('PUT', '/me/equipped', slots),
  takeGift: (itemId: string) => request<Me>('POST', '/me/gift', { item_id: itemId }),
  // Наборы настроек ленты (Premium) — заменяются целиком
  saveFeedPresets: (presets: FeedPreset[]) => request<Me>('PUT', '/me/feed-presets', { presets }),
  leave: (id: number) => request<LobbyDetail>('POST', `/lobbies/${id}/leave`),
  decide: (id: number, memberId: number, decision: MemberDecision) =>
    request<LobbyDetail>('POST', `/lobbies/${id}/members/${memberId}/${decision}`),
  cancelLobby: (id: number) => request<LobbyDetail>('POST', `/lobbies/${id}/cancel`),
}
