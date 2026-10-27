import { ApiError } from './client'

// Понятные человеку тексты для кодов ошибок API
const MESSAGES: Record<string, string> = {
  network_error: 'Нет связи с сервером. Проверь интернет и попробуй ещё раз.',
  missing_init_data: 'Открой приложение через бота в Telegram.',
  invalid_init_data: 'Не получилось проверить вход. Открой приложение заново из бота.',
  init_data_expired: 'Сессия устарела. Закрой приложение и открой его заново из бота.',
  no_user: 'Открой приложение через бота в Telegram.',
  banned: 'Твой аккаунт заблокирован.',
  onboarding_required: 'Сначала заполни анкету.',
  too_young: 'Сервис доступен с 13 лет.',
  birth_date_already_set: 'Дата рождения уже указана.',
  unknown_game: 'Такой игры нет в списке. Обнови приложение.',
  rank_not_in_game: 'Этот ранг не подходит к выбранной игре.',
  role_not_in_game: 'Эта роль не подходит к выбранной игре.',
  validation_error: 'Проверь, всё ли заполнено правильно.',
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return MESSAGES[error.code] ?? 'Что-то пошло не так. Попробуй ещё раз.'
  }
  return 'Что-то пошло не так. Попробуй ещё раз.'
}
