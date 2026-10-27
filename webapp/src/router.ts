import { createMemoryHistory, createRouter } from 'vue-router'

import { session } from './stores/session'
import CreateLobbyView from './views/CreateLobbyView.vue'
import FeedView from './views/FeedView.vue'
import HomeLayout from './views/HomeLayout.vue'
import LobbyView from './views/LobbyView.vue'
import MyLobbiesView from './views/MyLobbiesView.vue'
import OnboardingView from './views/onboarding/OnboardingView.vue'
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
        { path: 'mine', component: MyLobbiesView },
        { path: 'profile', component: ProfileView },
      ],
    },
    // Экраны без нижней навигации — с кнопкой «Назад»
    { path: '/create', component: CreateLobbyView },
    { path: '/lobby/:id(\\d+)', component: LobbyView, props: (route) => ({ id: Number(route.params.id) }) },
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

export function goBack(): void {
  if (cameFromApp) router.back()
  else void router.replace('/feed')
}
