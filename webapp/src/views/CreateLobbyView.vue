<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { LobbyKind, PlayStyle } from '../api/types'
import GameSelect from '../components/GameSelect.vue'
import PageHeader from '../components/PageHeader.vue'
import { LANGUAGES, PLAY_STYLES } from '../labels'
import { gameById, session } from '../stores/session'
import { shopTab } from '../stores/ui'
import { haptic } from '../telegram'

const router = useRouter()

const MAX_HANGOUT_SLOTS = 20
const DAY_MS = 24 * 60 * 60 * 1000

const myGameIds = session.me!.games.map((game) => game.game_id)
const mainGameId = session.me!.games.find((game) => game.is_main)?.game_id ?? myGameIds[0] ?? null

// Сначала свои игры, потом остальные
const gameOptions = computed(() =>
  [...session.games].sort((a, b) => Number(myGameIds.includes(b.id)) - Number(myGameIds.includes(a.id))),
)

const kind = ref<LobbyKind>('game')
const gameId = ref<number | null>(mainGameId)
const title = ref('')
const description = ref('')
const slots = ref(defaultSlots())
const rankMin = ref<number | null>(null)
const rankMax = ref<number | null>(null)
const needMic = ref(false)
const playStyle = ref<PlayStyle | null>(null)
const language = ref(session.me!.profile?.languages[0] ?? 'ru')
const when = ref<'now' | 'today' | 'tomorrow'>('now')
const time = ref(nextFullHour())
const contactLink = ref('')

const saving = ref(false)
const error = ref('')

const game = computed(() => (kind.value === 'game' ? gameById(gameId.value) : undefined))
const maxSlots = computed(() => (kind.value === 'game' ? (game.value?.max_party_size ?? MAX_HANGOUT_SLOTS) : MAX_HANGOUT_SLOTS))

function defaultSlots(): number {
  return Math.min(gameById(mainGameId)?.max_party_size ?? 4, 5)
}

function nextFullHour(): string {
  const date = new Date()
  date.setHours(date.getHours() + 1, 0, 0, 0)
  return `${String(date.getHours()).padStart(2, '0')}:00`
}

// Другая игра — другие ранги и размер пати
watch([kind, gameId], () => {
  rankMin.value = null
  rankMax.value = null
  slots.value = Math.min(Math.max(slots.value, 2), maxSlots.value)
})

function setKind(value: LobbyKind) {
  haptic.select()
  kind.value = value
  if (value === 'game' && gameId.value === null) gameId.value = mainGameId
}

function changeSlots(delta: number) {
  haptic.select()
  slots.value = Math.min(Math.max(slots.value + delta, 2), maxSlots.value)
}

const startsAt = computed<Date | null>(() => {
  if (when.value === 'now') return null
  const [hours, minutes] = time.value.split(':').map(Number)
  const date = new Date()
  if (when.value === 'tomorrow') date.setDate(date.getDate() + 1)
  date.setHours(hours ?? 0, minutes ?? 0, 0, 0)
  return date
})

const timeError = computed(() => {
  if (!startsAt.value) return ''
  const diff = startsAt.value.getTime() - Date.now()
  if (diff <= 0) return 'Это время уже прошло — выбери позже или «Сейчас».'
  if (diff > DAY_MS) return 'Пати можно собрать максимум на сутки вперёд.'
  return ''
})

/** «t.me/party» → «https://t.me/party»; null — если ссылка не из Telegram или Discord */
function normalizeContact(raw: string): string | null {
  let link = raw.trim()
  if (/^(t\.me|telegram\.me|discord\.gg|discord\.com)\//.test(link)) link = `https://${link}`
  const allowed = /^https:\/\/(t\.me|telegram\.me|discord\.gg)\/\S+$|^https:\/\/discord\.com\/invite\/\S+$/
  return allowed.test(link) ? link : null
}

// Закрытая пати по ссылке — только Premium (сервер проверит сам); без него переключатель ведёт к подпискам
const isPrivate = ref(false)
const canPrivate = computed(() => session.me!.plan.plan === 'premium')

function onPrivateClick(event: Event) {
  if (canPrivate.value) {
    haptic.select()
    return
  }
  event.preventDefault()
  haptic.tap()
  shopTab.value = 'plans'
  void router.push('/shop')
}

async function submit() {
  const contact = contactLink.value.trim() ? normalizeContact(contactLink.value) : null
  if (title.value.trim().length < 3) error.value = 'Назови пати — хотя бы 3 символа.'
  else if (kind.value === 'game' && !gameId.value) error.value = 'Выбери игру.'
  else if (timeError.value) error.value = timeError.value
  else if (contactLink.value.trim() && !contact) error.value = 'Ссылка — только на Telegram (t.me/…) или приглашение в Discord.'
  else error.value = ''
  if (error.value) {
    haptic.error()
    return
  }

  saving.value = true
  try {
    const lobby = await api.createLobby({
      kind: kind.value,
      game_id: kind.value === 'game' ? gameId.value : null,
      title: title.value.trim(),
      description: description.value.trim() || null,
      slots_total: slots.value,
      rank_min_id: rankMin.value,
      rank_max_id: rankMax.value,
      need_mic: needMic.value,
      play_style: kind.value === 'game' ? playStyle.value : null,
      is_private: isPrivate.value,
      language: language.value,
      starts_at: startsAt.value?.toISOString() ?? null,
      contact_link: contact,
    })
    haptic.success()
    // replace: «Назад» из готовой пати ведёт в ленту, а не обратно в форму
    await router.replace(`/lobby/${lobby.id}`)
  } catch (e) {
    error.value = errorMessage(e)
    haptic.error()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <main class="page rise-in">
    <PageHeader title="Новая пати" />

    <div class="stack">
      <div v-jelly.soft class="segmented">
        <button type="button" :aria-pressed="kind === 'game'" @click="setKind('game')">В игру</button>
        <button type="button" :aria-pressed="kind === 'hangout'" @click="setKind('hangout')">Просто посидеть</button>
      </div>

      <div v-if="kind === 'game'" class="field">
        <span class="field__label">Игра</span>
        <GameSelect v-model="gameId" :games="gameOptions" placeholder="Выбрать игру" />
      </div>

      <label class="field">
        <span class="field__label">Название</span>
        <input
          v-model="title"
          class="input"
          maxlength="80"
          :placeholder="kind === 'game' ? 'Например, нужны 2 на пару каток' : 'Например, смотрим кино в Discord'"
        />
      </label>

      <label class="field">
        <span class="field__label">Подробнее — по желанию</span>
        <textarea v-model="description" class="input" maxlength="500" placeholder="Что за пати, кого ждёте, какие правила" />
      </label>

      <div class="card toggle-row">
        <span>
          <b>Сколько вас будет</b>
          <span class="hint block">Вместе с тобой</span>
        </span>
        <span class="stepper">
          <button type="button" :disabled="slots <= 2" aria-label="Меньше" @click="changeSlots(-1)">−</button>
          <b>{{ slots }}</b>
          <button type="button" :disabled="slots >= maxSlots" aria-label="Больше" @click="changeSlots(1)">+</button>
        </span>
      </div>

      <div class="field">
        <span class="field__label">Когда</span>
        <div v-jelly.soft class="segmented">
          <button type="button" :aria-pressed="when === 'now'" @click="(when = 'now'), haptic.select()">Сейчас</button>
          <button type="button" :aria-pressed="when === 'today'" @click="(when = 'today'), haptic.select()">Сегодня</button>
          <button type="button" :aria-pressed="when === 'tomorrow'" @click="(when = 'tomorrow'), haptic.select()">
            Завтра
          </button>
        </div>
        <input v-if="when !== 'now'" v-model="time" class="input" type="time" aria-label="Время начала" />
        <span v-if="timeError" class="error-text">{{ timeError }}</span>
      </div>

      <template v-if="game?.ranks.length">
        <div class="field">
          <span class="field__label">Ранг — по желанию</span>
          <div class="rank-range">
            <!-- Названия рангов не склоняются («от Герой» звучит коряво) — поэтому «и выше» / «и ниже» -->
            <select v-model="rankMin" class="input" aria-label="Самый низкий ранг">
              <option :value="null">Любой снизу</option>
              <option v-for="rank in game.ranks" :key="rank.id" :value="rank.id">{{ rank.name }} и выше</option>
            </select>
            <select v-model="rankMax" class="input" aria-label="Самый высокий ранг">
              <option :value="null">Любой сверху</option>
              <option v-for="rank in game.ranks" :key="rank.id" :value="rank.id">{{ rank.name }} и ниже</option>
            </select>
          </div>
        </div>
      </template>

      <label class="card toggle-row">
        <span>
          <b>Только с микрофоном</b>
          <span class="hint block">Без микрофона откликнуться не получится</span>
        </span>
        <input v-model="needMic" class="switch" type="checkbox" @change="haptic.select()" />
      </label>

      <label class="card toggle-row">
        <span>
          <b>Закрытая — по ссылке</b>
          <span class="hint block">
            {{ canPrivate ? 'В ленте её не будет — позовёшь друзей ссылкой' : 'Только для своих — с Premium' }}
          </span>
        </span>
        <input v-model="isPrivate" class="switch" type="checkbox" @click="onPrivateClick" />
      </label>

      <!-- Стиль игры — только для пати в игру: у «Просто посидеть» он не нужен -->
      <div v-if="kind === 'game'" class="field">
        <span class="field__label">Стиль</span>
        <div v-jelly.soft class="segmented">
          <button type="button" :aria-pressed="playStyle === null" @click="(playStyle = null), haptic.select()">Любой</button>
          <button
            v-for="option in PLAY_STYLES"
            :key="option.value"
            type="button"
            :aria-pressed="playStyle === option.value"
            @click="(playStyle = option.value), haptic.select()"
          >
            {{ option.label }}
          </button>
        </div>
      </div>

      <div class="field">
        <span class="field__label">Язык общения</span>
        <div class="chips">
          <button
            v-for="option in LANGUAGES"
            :key="option.value"
            type="button"
            class="chip"
            :class="{ 'chip--on': language === option.value }"
            @click="(language = option.value), haptic.select()"
          >
            {{ option.label }}
          </button>
        </div>
      </div>

      <label class="field">
        <span class="field__label">Где собираемся — по желанию</span>
        <input
          v-model="contactLink"
          class="input"
          inputmode="url"
          autocomplete="off"
          placeholder="t.me/… или discord.gg/…"
        />
        <span class="hint">Ссылку увидят только те, кого ты примешь в пати.</span>
      </label>
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>
    <div class="actions">
      <button class="btn btn-primary" type="button" :disabled="saving" @click="submit">Создать пати</button>
    </div>
  </main>
</template>

<style scoped>
.block {
  display: block;
  margin-top: 2px;
}

.stepper {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  font-size: 18px;
  font-variant-numeric: tabular-nums;
}

.stepper button {
  width: 36px;
  height: 36px;
  border: 1px solid var(--line);
  border-radius: 50%;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}

.stepper button:disabled {
  opacity: 0.35;
  cursor: default;
}

.rank-range {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.segmented + .input {
  margin-top: 8px;
}
</style>
