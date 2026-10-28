<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { Game } from '../api/types'
import { gameColor } from '../lobby'
import { SHEET_MS } from '../sheet'
import { haptic } from '../telegram'

// Шторка «Выбери игру» с поиском — вместо рядов чипов со всеми играми.
// Добавление игры в профиль — справа «+»; выбор одной игры (лента, новая пати) — галочка у выбранной.
const props = withDefaults(
  defineProps<{
    open: boolean
    games: Game[]
    selectedId?: number | null // режим выбора: отмечаем выбранную
    anyLabel?: string // строка «Все игры» сверху — выбирает null
  }>(),
  { selectedId: undefined, anyLabel: undefined },
)
const emit = defineEmits<{ pick: [gameId: number | null]; close: [] }>()

// Как игры называют в разговоре — чтобы «кс» или «дота» тоже находились
const ALIASES: Record<string, string[]> = {
  cs2: ['кс', 'cs', 'контра', 'counter'],
  dota2: ['дота', 'dota'],
  valorant: ['валорант', 'валик', 'valo'],
  minecraft: ['майн', 'майнкрафт'],
}

const query = ref('')
watch(
  () => props.open,
  (open) => {
    if (open) query.value = ''
  },
)

const selecting = computed(() => props.selectedId !== undefined)

const found = computed(() => {
  const text = query.value.trim().toLowerCase()
  if (!text) return props.games
  return props.games.filter((game) =>
    [game.name, game.slug, ...(ALIASES[game.slug] ?? [])].some((name) => name.toLowerCase().includes(text)),
  )
})

function pick(gameId: number | null) {
  haptic.select()
  emit('pick', gameId)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet" :duration="SHEET_MS">
      <div v-if="open" class="sheet-backdrop" @click.self="emit('close')">
        <section class="sheet" role="dialog" aria-label="Выбор игры">
          <div class="sheet__handle" aria-hidden="true" />
          <h2 class="sheet__title">Выбери игру</h2>

          <label class="search">
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" stroke-width="2" />
              <path d="M16 16l4.5 4.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            </svg>
            <input v-model="query" class="input search__input" type="search" placeholder="Найти игру" enterkeyhint="search" />
          </label>

          <ul v-if="found.length || (anyLabel && !query.trim())" class="card list rise-in">
            <li v-if="anyLabel && !query.trim()">
              <button class="list__row" type="button" :aria-pressed="selectedId === null" @click="pick(null)">
                <span class="list__dot list__dot--any" aria-hidden="true" />
                <span class="list__name">{{ anyLabel }}</span>
                <span v-if="selectedId === null" class="list__mark list__mark--on" aria-hidden="true">✓</span>
              </button>
            </li>
            <li v-for="game in found" :key="game.id">
              <button
                class="list__row"
                type="button"
                :style="{ '--game': gameColor(game.id) }"
                :aria-pressed="selecting ? selectedId === game.id : undefined"
                @click="pick(game.id)"
              >
                <span class="list__dot" aria-hidden="true" />
                <span class="list__name">{{ game.name }}</span>
                <span v-if="!selecting" class="list__mark" aria-hidden="true">+</span>
                <span v-else-if="selectedId === game.id" class="list__mark list__mark--on" aria-hidden="true">✓</span>
              </button>
            </li>
          </ul>
          <p v-else class="hint nothing">Не нашли «{{ query.trim() }}». Пока в списке только эти игры — остальные добавим позже.</p>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.search {
  position: relative;
  display: block;
  margin-bottom: 14px;
  color: var(--hint);
}

.search svg {
  position: absolute;
  top: 50%;
  left: 14px;
  transform: translateY(-50%);
}

.search__input {
  padding-left: 42px;
}

.list {
  margin: 0;
  padding: 0 16px;
  list-style: none;
}

.list li + li {
  border-top: 1px dashed var(--line-strong);
}

.list__row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 56px;
  padding: 12px 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.list__row:active {
  opacity: 0.7;
}

/* Огонёк цвета игры — как на карточках пати */
.list__dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: var(--game);
  box-shadow: 0 0 8px 1px var(--game);
}

.list__dot--any {
  background: transparent;
  border: 1px solid var(--g-500);
  box-shadow: none;
}

.list__name {
  flex: 1;
  font-family: var(--font-title);
  font-size: 17px;
}

.list__mark {
  flex: none;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 1px solid var(--line-strong);
  border-radius: 9px;
  font-family: var(--font-pixel);
  font-size: 20px;
  line-height: 1;
}

.list__mark--on {
  border-color: var(--accent);
  background: var(--accent);
  color: var(--accent-ink);
  font-family: var(--font-body);
  font-size: 16px;
  font-weight: 700;
  box-shadow: var(--glow-1);
}

.nothing {
  padding: 8px 0 16px;
  text-align: center;
}
</style>
