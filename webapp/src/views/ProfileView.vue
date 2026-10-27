<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import PhotoCarousel from '../components/PhotoCarousel.vue'
import { formatAge } from '../format'
import { LANGUAGES, LOOKING_FOR, PLAY_STYLE_LABELS } from '../labels'
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

const games = computed(() =>
  me.value.games.map((userGame) => {
    const game = gameById(userGame.game_id)
    return {
      id: userGame.game_id,
      name: game?.name ?? '—',
      isMain: userGame.is_main,
      rank: game?.ranks.find((rank) => rank.id === userGame.rank_id)?.name ?? null,
      roles: game?.roles.filter((role) => userGame.role_ids.includes(role.id)).map((role) => role.name) ?? [],
    }
  }),
)

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

    <div class="chips tags">
      <span class="badge badge--accent">Ищу: {{ lookingFor }}</span>
      <span class="badge">{{ PLAY_STYLE_LABELS[profile.play_style] }}</span>
      <span class="badge">{{ profile.has_mic ? 'С микрофоном' : 'Без микрофона' }}</span>
      <span class="badge">Репутация {{ profile.reputation > 0 ? '+' : '' }}{{ profile.reputation }}</span>
    </div>

    <p v-if="profile.bio" class="card bio">{{ profile.bio }}</p>

    <h2 class="section-title">Игры</h2>
    <div class="card list">
      <div v-for="game in games" :key="game.id" class="list__row">
        <div>
          <b>{{ game.name }}</b>
          <span v-if="game.isMain" class="badge badge--accent main">Основная</span>
          <p v-if="game.roles.length" class="hint row-hint">{{ game.roles.join(', ') }}</p>
        </div>
        <span class="hint">{{ game.rank ?? 'без ранга' }}</span>
      </div>
    </div>

    <h2 class="section-title">Ещё</h2>
    <div class="card list">
      <div class="list__row"><span>Языки</span><span class="hint">{{ languages }}</span></div>
      <div class="list__row"><span>Discord</span><span class="hint">{{ profile.discord_tag ?? 'не указан' }}</span></div>
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
  border-radius: 0 0 28px 28px;
}

.hero__name {
  margin: 0;
  font-size: 32px;
  font-weight: 900;
  letter-spacing: -0.02em;
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
  border: 0;
  border-radius: 50%;
  background: rgb(0 0 0 / 0.45);
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
  color: var(--accent);
}

.tags {
  margin-top: 16px;
}

.bio {
  margin: 16px 0 0;
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
  border-top: 1px solid var(--line);
}

.main {
  margin-left: 8px;
}

.row-hint {
  margin: 2px 0 0;
}
</style>
