// Каталог магазина (решения пользователя 29.10.2026, docs/ROADMAP.md → «Монетизация»).
// Пока витрина: оплаты нет, кнопки «Скоро». Цены в звёздах Telegram ⭐ — предварительные, поправим.
// Когда подключим оплату Stars, каталог и цены переедут на сервер — платить по цене с клиента нельзя.
// Без лутбоксов и случайных наград: всё, что продаётся, видно заранее и стоит одинаково для всех.

export type PlanId = 'plus' | 'premium'

export interface PlanOffer {
  id: PlanId
  name: string
  price: number // ⭐ в месяц
  tagline: string
  perks: string[]
}

export const PLANS: PlanOffer[] = [
  {
    id: 'plus',
    name: 'Plus',
    price: 99,
    tagline: 'Больше пати и фото, видно, кто лайкнул',
    perks: [
      '3 фото в профиле',
      'До 5 активных пати',
      'Кто лайкнул тебя — списком, ещё до мэтча',
      'Вернуть пропущенную анкету — 3 раза в день',
      '1 бесплатный буст в неделю',
      'Команды: стрик и недельный итог',
      'Значок Plus у ника',
      '−20% на косметику',
    ],
  },
  {
    id: 'premium',
    name: 'Premium',
    price: 199,
    tagline: 'Всё из Plus, а ещё…',
    perks: [
      'Видео вместо одного из 3 фото (когда заработает модерация)',
      'До 10 активных пати',
      'Возвращать пропущенные анкеты без лимита',
      '3 бесплатных буста в неделю',
      'Закрытая пати по ссылке — только для своих',
      'Сохранённые наборы настроек ленты',
      'Расширенная статистика команд',
      'Вещь из косметики в подарок каждый месяц',
      'Значок Premium у ника',
    ],
  },
]

// Сравнение тарифов. Мэтчи, чаты, жалобы и защита по возрасту — у всех одинаково, их в таблице нет
export const PLAN_TABLE: { label: string; free: string; plus: string; premium: string }[] = [
  { label: 'Фото в профиле', free: '1', plus: '3', premium: '3 + видео' },
  { label: 'Активных пати', free: '2', plus: '5', premium: '10' },
  { label: 'Кто лайкнул', free: 'число', plus: 'список', premium: 'список' },
  { label: 'Вернуть анкету', free: '—', plus: '3 в день', premium: 'без лимита' },
  { label: 'Бусты в неделю', free: '—', plus: '1', premium: '3' },
  { label: 'Закрытая пати', free: '—', plus: '—', premium: '✓' },
  { label: 'Наборы ленты', free: '—', plus: '—', premium: '✓' },
  { label: 'Косметика', free: 'цена', plus: '−20%', premium: '−20% + подарок' },
]

export interface BoostOffer {
  id: string
  name: string
  description: string
  price: number
  icon: 'party' | 'profile' | 'pack'
}

export const BOOSTS: BoostOffer[] = [
  {
    id: 'party-hour',
    name: 'Поднять пати',
    description: 'Твоя пати первой в ленте у подходящих игроков — на 1 час. Чтобы собрать состав прямо сейчас.',
    price: 15,
    icon: 'party',
  },
  {
    id: 'profile-evening',
    name: 'Анкета первой',
    description: 'Тебя показывают первым в ленте людей весь вечер — до 6 часов, только тем, кто подходит по возрасту.',
    price: 25,
    icon: 'profile',
  },
  {
    id: 'party-pack',
    name: '5 подъёмов пати',
    description: 'Набор на неделю активных вечеров. Не сгорает.',
    price: 59,
    icon: 'pack',
  },
]

// Ограничения бустов — показываем рядом, чтобы было понятно заранее
export const BOOST_RULES = [
  'Не чаще раза в час на одну пати и не больше трёх в день',
  'На поднятой карточке — честная пометка «поднята»',
  'Буст не обходит возраст и блокировки: показываем только тем, кому ты и так виден',
]

export type CosmeticKind = 'frame' | 'background' | 'badge' | 'match' | 'theme'

export interface Cosmetic {
  id: string
  kind: CosmeticKind
  name: string
  description: string
  price: number | null // null — не продаётся, только за активность
  earn?: string // как получить бесплатно
  style: string // вариант оформления для превью (CosmeticPreview.vue)
}

export const COSMETIC_KINDS: { kind: CosmeticKind; label: string }[] = [
  { kind: 'frame', label: 'Рамки' },
  { kind: 'background', label: 'Фоны' },
  { kind: 'badge', label: 'Значки' },
  { kind: 'match', label: 'Мэтч' },
  { kind: 'theme', label: 'Темы' },
]

export const COSMETICS: Cosmetic[] = [
  { id: 'frame-neon', kind: 'frame', name: 'Неон', description: 'Двойное белое свечение вокруг аватара.', price: 35, style: 'neon' },
  { id: 'frame-pixel', kind: 'frame', name: 'Пиксель', description: 'Ступенчатая рамка, как в старых играх.', price: 25, style: 'pixel' },
  { id: 'frame-spikes', kind: 'frame', name: 'Шипы', description: 'Колючая рамка — как у логотипа на заставке.', price: 45, style: 'spikes' },
  { id: 'frame-lamp', kind: 'frame', name: 'Лампа', description: 'Свет падает на аватар сверху.', price: 45, style: 'lamp' },

  { id: 'bg-smoke', kind: 'background', name: 'Дым', description: 'Дым с заставки за твоей карточкой.', price: 49, style: 'smoke' },
  { id: 'bg-light', kind: 'background', name: 'Полоса света', description: 'Металлический отблеск, как у карточек пати.', price: 39, style: 'light' },
  { id: 'bg-grid', kind: 'background', name: 'Сетка', description: 'Тонкая пиксельная сетка.', price: 29, style: 'grid' },

  { id: 'badge-night', kind: 'badge', name: 'Ночной игрок', description: 'Значок у ника: луна.', price: 15, style: 'night' },
  { id: 'badge-heart', kind: 'badge', name: 'Пиксельное сердце', description: 'Значок у ника: сердце.', price: 19, style: 'heart' },
  {
    id: 'badge-first',
    kind: 'badge',
    name: 'Первая пати',
    description: 'Значок у ника: звезда.',
    price: null,
    earn: 'Сыграй первую пати',
    style: 'star',
  },
  {
    id: 'badge-veteran',
    kind: 'badge',
    name: 'Ветеран',
    description: 'Значок у ника: корона.',
    price: null,
    earn: 'Сыграй 50 пати',
    style: 'crown',
  },

  { id: 'match-red', kind: 'match', name: 'Красная лампа', description: 'Сцена мэтча в красном свете.', price: 39, style: 'red' },
  { id: 'match-neon', kind: 'match', name: 'Неоновая вывеска', description: 'Вместо лампы — мигающая вывеска.', price: 49, style: 'sign' },

  { id: 'theme-blue', kind: 'theme', name: 'Синий час', description: 'Тёмно-синяя тема интерфейса.', price: 49, style: 'blue' },
  { id: 'theme-sepia', kind: 'theme', name: 'Сепия', description: 'Тёплая тема под старую плёнку.', price: 49, style: 'sepia' },
]

export const SEASON_PASS = {
  name: 'Сезон 1',
  price: 149, // ⭐ за платную дорожку на весь сезон
  points: [
    'Уровни — за сыгранные пати и соцквесты, не за деньги',
    'Бесплатная дорожка — у всех, платная добавляет только косметику',
    'Все награды видны заранее, без рандома',
  ],
}
