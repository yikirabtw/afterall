import { createMemoryHistory, createRouter } from 'vue-router'

import { originOf, rememberOrigin, reveal, takeOrigin, type RevealShape } from './reveal'
import { session } from './stores/session'
import CreateLobbyView from './views/CreateLobbyView.vue'
import EditGamesView from './views/EditGamesView.vue'
import EditProfileView from './views/EditProfileView.vue'
import FeedView from './views/FeedView.vue'
import HomeLayout from './views/HomeLayout.vue'
import LobbyView from './views/LobbyView.vue'
import MatchesView from './views/MatchesView.vue'
import OnboardingView from './views/onboarding/OnboardingView.vue'
import PeopleView from './views/PeopleView.vue'
import ProfileView from './views/ProfileView.vue'

export const router = createRouter({
  // Адресная строка в мини-приложении не видна, а в её #-части Telegram передаёт initData —
  // поэтому храним маршрут в памяти и не трогаем URL
  history: createMemoryHistory(),
  routes: [
    { path: '/onboarding', component: OnboardingView },
    {
      path: '/',
      component: HomeLayout,
      redirect: '/feed',
      children: [
        { path: 'feed', component: FeedView },
        { path: 'people', component: PeopleView },
        { path: 'profile', component: ProfileView },
      ],
    },
    // Экраны без нижней навигации — с кнопкой «Назад»
    { path: '/create', component: CreateLobbyView },
    { path: '/lobby/:id(\\d+)', component: LobbyView, props: (route) => ({ id: Number(route.params.id) }) },
    { path: '/matches', component: MatchesView },
    { path: '/profile/edit', component: EditProfileView },
    { path: '/profile/games', component: EditGamesView },
    { path: '/:pathMatch(.*)*', redirect: '/feed' },
  ],
})

// Пока анкета не заполнена — только онбординг; после — обратно в него не попасть
router.beforeEach((to) => {
  if (!session.me) return true
  if (!session.me.is_onboarded && to.path !== '/onboarding') return '/onboarding'
  if (session.me.is_onboarded && to.path === '/onboarding') return '/feed'
  return true
})

// Было ли куда возвращаться: если экран открыт первым (например, по ссылке из бота), «Назад» ведёт в ленту
let cameFromApp = false
router.afterEach((_to, from) => {
  cameFromApp = from.matched.length > 0
})

/** Шаг назад в истории; промис — когда новый экран уже выбран */
function back(): Promise<unknown> {
  if (!cameFromApp) return router.replace('/feed')
  return new Promise<void>((resolve) => {
    const stop = router.afterEach(() => {
      stop()
      resolve()
    })
    router.back()
  })
}

export function goBack(): void {
  // Экран открыт «расплытием» — сворачиваем его обратно туда, откуда вырос
  const saved = takeOrigin(router.currentRoute.value.path)
  if (saved) void reveal(saved.origin, back, 'close', saved.shape)
  else void back()
}

/** Открыть экран «расплытием» из нажатого элемента; «Назад» свернёт его обратно */
export function openFrom(el: Element, path: string, shape: RevealShape = 'circle'): void {
  const origin = originOf(el)
  rememberOrigin(path, origin, shape)
  void reveal(origin, () => router.push(path), 'open', shape)
}
