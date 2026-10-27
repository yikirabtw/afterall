<script setup lang="ts">
import { computed } from 'vue'

import { formatSchedule } from '../format'
import { AGE_GROUP_LABELS, LANGUAGES, LOOKING_FOR, PLAY_STYLE_LABELS } from '../labels'
import { gameById, session } from '../stores/session'

const me = computed(() => session.me!)
const profile = computed(() => me.value.profile!)

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
const initial = computed(() => profile.value.display_name.trim().charAt(0).toUpperCase() || '?')
</script>

<template>
  <main class="page">
    <section class="hero">
      <div class="avatar" aria-hidden="true">{{ initial }}</div>
      <div>
        <h1 class="hero__name">{{ profile.display_name }}</h1>
        <p class="hint hero__meta">
          <span v-if="me.username">@{{ me.username }}</span>
          <span v-if="me.age_group">{{ AGE_GROUP_LABELS[me.age_group] }}</span>
          <span v-if="profile.city">{{ profile.city }}</span>
        </p>
      </div>
    </section>

    <div class="chips">
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

    <h2 class="section-title">Когда играю</h2>
    <div class="card">
      <div v-if="me.availability.length" class="chips">
        <span v-for="line in formatSchedule(me.availability)" :key="line" class="badge">{{ line }}</span>
      </div>
      <p v-else class="hint no-margin">Не указано</p>
    </div>

    <h2 class="section-title">Ещё</h2>
    <div class="card list">
      <div class="list__row"><span>Языки</span><span class="hint">{{ languages }}</span></div>
      <div class="list__row"><span>Discord</span><span class="hint">{{ profile.discord_tag ?? 'не указан' }}</span></div>
    </div>
    <p class="hint">Discord и ник в Telegram видят только участники твоих пати.</p>
  </main>
</template>

<style scoped>
.hero {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 8px 0 16px;
}

.avatar {
  flex: none;
  display: grid;
  place-items: center;
  width: 72px;
  height: 72px;
  border-radius: 24px;
  background: linear-gradient(135deg, var(--accent), var(--warm));
  color: var(--accent-ink);
  font-size: 32px;
  font-weight: 900;
}

.hero__name {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.02em;
  overflow-wrap: anywhere;
}

.hero__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin: 4px 0 0;
}

.bio {
  margin: 16px 0 0;
  white-space: pre-line;
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

.row-hint,
.no-margin {
  margin: 2px 0 0;
}
</style>
