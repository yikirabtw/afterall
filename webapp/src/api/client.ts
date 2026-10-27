import { getInitData } from '../telegram'
import type {
  FeedParams,
  Game,
  Lobby,
  LobbyDetail,
  LobbyFeed,
  LobbyInput,
  Me,
  MemberDecision,
  ProfileInput,
  Slot,
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
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(`${BASE_URL}/api${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
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
  return (await response.json()) as T
}

function toQuery(params: object): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== false) query.set(key, String(value))
  }
  return query.toString()
}

export const api = {
  me: () => request<Me>('GET', '/me'),
  games: () => request<Game[]>('GET', '/games'),

  setBirthDate: (birthDate: string) => request<Me>('PUT', '/me/birth-date', { birth_date: birthDate }),
  saveProfile: (profile: ProfileInput) => request<Me>('PUT', '/me/profile', profile),
  saveGames: (games: UserGameInput[]) => request<Me>('PUT', '/me/games', { games }),
  saveAvailability: (slots: Slot[]) => request<Me>('PUT', '/me/availability', { slots }),
  completeOnboarding: () => request<Me>('POST', '/me/onboarding/complete'),

  feed: (params: FeedParams) => request<LobbyFeed>('GET', `/lobbies?${toQuery(params)}`),
  myLobbies: () => request<Lobby[]>('GET', '/lobbies/mine'),

  // Все действия с пати возвращают свежую карточку — экран просто подменяет её
  createLobby: (lobby: LobbyInput) => request<LobbyDetail>('POST', '/lobbies', lobby),
  lobby: (id: number) => request<LobbyDetail>('GET', `/lobbies/${id}`),
  apply: (id: number, note: string | null) => request<LobbyDetail>('POST', `/lobbies/${id}/apply`, { note }),
  leave: (id: number) => request<LobbyDetail>('POST', `/lobbies/${id}/leave`),
  decide: (id: number, memberId: number, decision: MemberDecision) =>
    request<LobbyDetail>('POST', `/lobbies/${id}/members/${memberId}/${decision}`),
  cancelLobby: (id: number) => request<LobbyDetail>('POST', `/lobbies/${id}/cancel`),
}
