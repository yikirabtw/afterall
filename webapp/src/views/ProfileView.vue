<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import PhotoCarousel from '../components/PhotoCarousel.vue'
import { formatAge } from '../format'
import { LANGUAGES, LOOKING_FOR, PLAY_STYLE_LABELS } from '../labels'
import { faceitLabel } from '../lobby'
import { PHOTOS_MAX } from '../profile'
import { gameById, session } from '../stores/session'
import { haptic } from '../telegram'

const router = useRouter()
const me = computed(() => session.me!)
const profile = computed(() => me.value.profile!)

const age = computed(() => {
  if (!me.value.birth_date) return null
  const birth = new Date(me.value.birth_date)
  const today = new Date()
  const hadBirthday =
    today.getMonth() > birth.getMonth() || (today.getMonth() === birth.getMonth() && today.getDate() >= birth.getDate())
  return today.getFullYear() - birth.getFullYear() - (hadBirthday ? 0 : 1)
})

// Выключенные игры (их нет в справочнике) не показываем — выбрать их уже нельзя
const games = computed(() =>
  me.value.games.flatMap((userGame) => {
    const game = gameById(userGame.game_id)
    if (!game) return []
    return [
      {
        id: userGame.game_id,
        name: game.name,
        isMain: userGame.is_main,
        rank: game.ranks.find((rank) => rank.id === userGame.rank_id)?.name ?? null,
        faceit: userGame.faceit_elo !== null ? faceitLabel(userGame.faceit_elo) : null,
        roles: game.roles.filter((role) => userGame.role_ids.includes(role.id)).map((role) => role.name),
      },
    ]
  }),
)

// Полоса цифр под шапкой — как блок статистики в референсе
const stats = computed(() => [
  { value: String(games.value.length), label: 'игры' },
  { value: `${profile.value.reputation > 0 ? '+' : ''}${profile.value.reputation}`, label: 'репутация' },
  { value: `${me.value.photos.length}/${PHOTOS_MAX}`, label: 'фото' },
])

const lookingFor = computed(() => LOOKING_FOR.find((option) => option.value === profile.value.looking_for)?.label)
const languages = computed(() =>
  profile.value.languages.map((code) => LANGUAGES.find((lang) => lang.value === code)?.label ?? code).join(', '),
)

function edit(event: Event) {
  event.stopPropagation() // иначе нажатие ещё и перелистнёт фото
  haptic.tap()
  void router.push('/profile/edit')
}
</script>

<template>
  <main class="page profile">
    <PhotoCarousel class="hero" :photos="me.photos" :name="profile.display_name">
      <h1 class="hero__name">{{ profile.display_name }}</h1>
      <p class="hero__meta">
        <span v-if="age !== null">{{ formatAge(age) }}</span>
        <span v-if="profile.city">{{ profile.city }}</span>
        <span v-if="me.username">@{{ me.username }}</span>
      </p>
    </PhotoCarousel>
    <button class="edit" type="button" aria-label="Редактировать профиль" @click="edit">
      <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
        <path
          d="M4 20h4L19 9l-4-4L4 16v4zM14 6l4 4"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </button>

    <p v-if="!me.photos.length" class="hint add-photo">
      Добавь фото — с ним тебя заметят в ленте.
      <button class="btn btn-ghost link" type="button" @click="edit">Добавить</button>
    </p>

    <dl class="stats">
      <div v-for="stat in stats" :key="stat.label" class="stats__item">
        <dt>{{ stat.label }}</dt>
        <dd>{{ stat.value }}</dd>
      </div>
    </dl>

    <div class="chips tags">
      <span class="badge badge--accent">Ищу: {{ lookingFor }}</span>
      <span class="badge">{{ PLAY_STYLE_LABELS[profile.play_style] }}</span>
      <span class="badge">{{ profile.has_mic ? 'С микрофоном' : 'Без микрофона' }}</span>
    </div>

    <p v-if="profile.bio" class="card card--lit bio">{{ profile.bio }}</p>

    <!-- Разделы нажимаются целиком: «Игры» — редактор игр, «Ещё» — анкета -->
    <h2 class="section-title">Игры</h2>
    <RouterLink to="/profile/games" class="card list tappable" @click="haptic.tap()">
      <div v-for="game in games" :key="game.id" class="list__row">
        <div>
          <b>{{ game.name }}</b>
          <span v-if="game.isMain" class="badge badge--accent main">Основная</span>
          <p v-if="game.roles.length" class="hint row-hint">{{ game.roles.join(', ') }}</p>
        </div>
        <span class="row-end">
          <span class="hint row-value">
            {{ game.rank ?? (game.faceit ? '' : 'без ранга') }}
            <span v-if="game.faceit" class="faceit">{{ game.faceit }}</span>
          </span>
          <span class="chevron" aria-hidden="true">›</span>
        </span>
      </div>
      <div v-if="!games.length" class="list__row">
        <span class="hint">Игры не выбраны</span>
        <span class="chevron" aria-hidden="true">›</span>
      </div>
    </RouterLink>

    <h2 class="section-title">Ещё</h2>
    <div class="card list">
      <RouterLink to="/profile/edit" class="list__row tappable" @click="haptic.tap()">
        <span>Языки</span>
        <span class="row-end"><span class="hint">{{ languages }}</span><span class="chevron" aria-hidden="true">›</span></span>
      </RouterLink>
      <RouterLink to="/profile/edit" class="list__row tappable" @click="haptic.tap()">
        <span>Discord</span>
        <span class="row-end">
          <span class="hint">{{ profile.discord_tag ?? 'не указан' }}</span>
          <span class="chevron" aria-hidden="true">›</span>
        </span>
      </RouterLink>
      <RouterLink to="/profile/edit" class="list__row tappable" @click="haptic.tap()">
        <span>Кого ищу, стиль, микрофон</span>
        <span class="row-end"><span class="hint">{{ lookingFor }}</span><span class="chevron" aria-hidden="true">›</span></span>
      </RouterLink>
    </div>
    <p class="hint">Discord и ник в Telegram видны только после взаимного лайка или в общей пати.</p>
  </main>
</template>

<style scoped>
.profile {
  position: relative;
  padding-top: 0;
}

/* Шапка — примерно треть экрана, от края до края */
.hero {
  height: 38vh;
  min-height: 280px;
  max-height: 440px;
  margin: 0 -16px;
  border-bottom: 1px solid var(--line);
  border-radius: 0 0 24px 24px;
}

.hero__name {
  margin: 0;
  font-family: var(--font-title);
  font-size: 32px;
  font-weight: 400;
  line-height: 1.1;
  overflow-wrap: anywhere;
}

.hero__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 12px;
  margin: 6px 0 0;
  font-size: 15px;
  opacity: 0.85;
}

.edit {
  position: absolute;
  top: calc(12px + var(--tg-content-safe-area-inset-top, 0px));
  right: 12px;
  z-index: 3;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 1px solid rgb(255 255 255 / 0.25);
  border-radius: 12px;
  background: rgb(0 0 0 / 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  color: #fff;
  cursor: pointer;
}

.add-photo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.link {
  min-height: 32px;
  padding: 0;
  color: var(--text);
  text-decoration: underline;
  text-underline-offset: 3px;
}

/* Цифры пиксельным шрифтом, между ними пунктирные разделители */
.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin: 18px 0 0;
  padding: 14px 0;
  border-top: 1px dashed var(--line-strong);
  border-bottom: 1px dashed var(--line-strong);
}

.stats__item {
  display: flex;
  flex-direction: column-reverse;
  align-items: center;
  gap: 4px;
}

.stats__item + .stats__item {
  border-left: 1px dashed var(--line-strong);
}

.stats dd {
  margin: 0;
  font-family: var(--font-pixel);
  font-size: 30px;
  line-height: 1;
  text-shadow: 0 0 6px rgb(255 255 255 / 0.4);
}

.stats dt {
  font-size: 12px;
  color: var(--hint);
}

.tags {
  margin-top: 16px;
}

.bio {
  margin: 20px 0 0;
  white-space: pre-line;
  overflow-wrap: anywhere;
}

.list {
  padding: 4px 16px;
}

.list__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
}

.list__row + .list__row {
  border-top: 1px dashed var(--line-strong);
}

.main {
  margin-left: 8px;
}

.tappable {
  display: block;
  color: inherit;
  text-decoration: none;
  cursor: pointer;
}

a.list__row.tappable {
  display: flex;
}

.tappable:active {
  opacity: 0.7;
}

.row-end {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  text-align: right;
}

.row-value {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.faceit {
  color: var(--warn);
  font-weight: 700;
}

.chevron {
  flex: none;
  color: var(--hint);
  font-size: 22px;
  line-height: 1;
}

.row-hint {
  margin: 2px 0 0;
}
</style>
