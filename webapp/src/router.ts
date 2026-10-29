import { createMemoryHistory, createRouter } from 'vue-router'

import { originOf, rememberOrigin, reveal, takeOrigin, type RevealShape } from './reveal'
import { session } from './stores/session'
import BlockedView from './views/BlockedView.vue'
import ChatsView from './views/ChatsView.vue'
import ChatView from './views/ChatView.vue'
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
import ShopView from './views/ShopView.vue'

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
        { path: 'shop', component: ShopView },
        { path: 'chats', component: ChatsView },
        { path: 'profile', component: ProfileView },
      ],
    },
    // Экраны без нижней навигации — с кнопкой «Назад»
    { path: '/create', component: CreateLobbyView },
    { path: '/lobby/:id(\\d+)', component: LobbyView, props: (route) => ({ id: Number(route.params.id) }) },
    { path: '/matches', component: MatchesView },
    {
      path: '/chat/:kind(direct|lobby)/:target(\\d+)',
      component: ChatView,
      props: (route) => ({ kind: route.params.kind, target: Number(route.params.target) }),
    },
    { path: '/profile/edit', component: EditProfileView },
    { path: '/profile/games', component: EditGamesView },
    { path: '/profile/blocked', component: BlockedView },
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

// Кнопка в уведомлении бота открывает приложение сразу на нужном экране: ссылка вида …/?open=chat/direct/12
// (её собирает сервер, services/notify.py). Берём только знакомые экраны и только при первом запуске
const START_LINK = /^(chat\/(direct|lobby)\/\d+|lobby\/\d+|matches|feed|people|chats)$/
let startLinkUsed = false

export async function openStartLink(): Promise<void> {
  if (startLinkUsed) return
  startLinkUsed = true
  const target = new URLSearchParams(window.location.search).get('open')
  // Лента к этому моменту уже открыта (App.vue) — «Назад» с этого экрана вернёт в приложение, а не закроет его
  if (target && START_LINK.test(target)) await router.push(`/${target}`)
}
