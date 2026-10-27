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

  // Фото и люди
  too_many_photos: 'Можно добавить не больше 3 фото.',
  photo_too_large: 'Фото слишком большое — до 10 МБ.',
  photo_format_not_supported: 'Подойдёт фото в JPEG, PNG или WebP.',
  photo_unreadable: 'Не получилось открыть это фото. Попробуй другое.',
  photo_not_found: 'Фото уже удалено.',
  person_not_found: 'Этого человека уже нет в ленте.',

  // Пати
  too_many_active_lobbies: 'У тебя уже 2 активные пати. Отмени одну или дождись, пока она закончится.',
  starts_at_out_of_range: 'Пати можно собрать максимум на сутки вперёд.',
  party_too_big: 'В этой игре в пати не бывает столько людей.',
  invalid_rank_range: 'Ранг «от» должен быть не выше ранга «до».',
  lobby_not_found: 'Пати не найдена — возможно, её уже отменили.',
  lobby_full: 'Мест уже нет.',
  lobby_not_active: 'Пати уже закончилась или отменена.',
  already_applied: 'Ты уже откликнулся на эту пати.',
  application_declined: 'Создатель отклонил твой отклик.',
  kicked_from_lobby: 'Создатель убрал тебя из этой пати.',
  cannot_apply_own_lobby: 'Это твоя пати.',
  owner_cannot_leave: 'Создатель не может выйти — пати можно только отменить.',
  not_a_member: 'Ты не участвуешь в этой пати.',
  too_many_applications: 'У тебя много откликов без ответа. Подожди решения или отзови лишние.',
  mic_required: 'Для этой пати нужен микрофон.',
  rank_out_of_range: 'Твой ранг не подходит под требования этой пати.',
  not_lobby_owner: 'Это может делать только создатель пати.',
  member_not_found: 'Этого человека уже нет в пати.',
  member_not_pending: 'Этот отклик уже обработан.',
  member_not_accepted: 'Этого человека уже нет в пати.',
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return MESSAGES[error.code] ?? 'Что-то пошло не так. Попробуй ещё раз.'
  }
  return 'Что-то пошло не так. Попробуй ещё раз.'
}
