import { reactive } from 'vue'

import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Game, Me } from '../api/types'

// Общее состояние приложения: кто вошёл и справочник игр. Хватает reactive — отдельный стор не нужен.
export const session = reactive({
  status: 'loading' as 'loading' | 'ready' | 'error',
  error: '',
  me: null as Me | null,
  games: [] as Game[],
})

export async function loadSession(): Promise<void> {
  session.status = 'loading'
  try {
    const [me, games] = await Promise.all([api.me(), api.games()])
    session.me = me
    session.games = games
    session.status = 'ready'
  } catch (error) {
    session.error = errorMessage(error)
    session.status = 'error'
  }
}

export function setMe(me: Me): void {
  session.me = me
}

export function gameById(id: number | null): Game | undefined {
  return session.games.find((game) => game.id === id)
}
