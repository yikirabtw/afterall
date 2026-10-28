<script setup lang="ts">
import { computed, ref } from 'vue'

import type { Game } from '../api/types'
import { gameColor } from '../lobby'
import { haptic } from '../telegram'
import GameSheet from './GameSheet.vue'

// Поле «Игра»: одна строка с выбранной игрой, выбор — в шторке с поиском (лента пати, новая пати)
const gameId = defineModel<number | null>({ required: true })
const props = defineProps<{
  games: Game[]
  anyLabel?: string // если задано — можно выбрать «все игры» (null) и сбросить выбор крестиком
  placeholder?: string
}>()

const open = ref(false)
const selected = computed(() => props.games.find((game) => game.id === gameId.value) ?? null)

function openSheet() {
  haptic.tap()
  open.value = true
}

function pick(id: number | null) {
  gameId.value = id
  open.value = false
}

function clear() {
  haptic.select()
  gameId.value = null
}
</script>

<template>
  <div class="game-select">
    <button
      class="game-select__field"
      :class="{ 'game-select__field--clearable': selected && anyLabel }"
      type="button"
      @click="openSheet"
    >
      <span
        class="game-select__dot"
        :class="{ 'game-select__dot--any': !selected }"
        :style="selected ? { '--game': gameColor(selected.id) } : undefined"
        aria-hidden="true"
      />
      <span class="game-select__value" :class="{ 'game-select__value--empty': !selected && !anyLabel }">
        {{ selected?.name ?? anyLabel ?? placeholder ?? 'Выбрать игру' }}
      </span>
      <svg v-if="!(selected && anyLabel)" class="game-select__chevron" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <path d="M7 10l5 5 5-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </button>
    <!-- Сброс фильтра — отдельной кнопкой поверх поля, чтобы не открывать шторку -->
    <button v-if="selected && anyLabel" class="game-select__clear" type="button" aria-label="Все игры" @click="clear">
      <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
        <path d="M7 7l10 10M17 7L7 17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      </svg>
    </button>

    <GameSheet :open="open" :games="games" :selected-id="gameId" :any-label="anyLabel" @pick="pick" @close="open = false" />
  </div>
</template>

<style scoped>
.game-select {
  position: relative;
}

.game-select__field {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 52px;
  padding: 0 14px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-sm);
  background: var(--card);
  box-shadow: var(--edge-light);
  text-align: left;
  cursor: pointer;
}

/* Место под крестик сброса справа */
.game-select__field--clearable {
  padding-right: 52px;
}

.game-select__field:active {
  border-color: var(--g-600);
}

.game-select__dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: var(--game);
  box-shadow: 0 0 8px 1px var(--game);
}

.game-select__dot--any {
  background: transparent;
  border: 1px solid var(--g-500);
  box-shadow: none;
}

.game-select__value {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-title);
  font-size: 16px;
}

.game-select__value--empty {
  color: var(--hint);
}

.game-select__chevron {
  flex: none;
  color: var(--text-2);
}

.game-select__clear {
  position: absolute;
  top: 50%;
  right: 10px;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  transform: translateY(-50%);
  border: 1px solid var(--line-strong);
  border-radius: 9px;
  background: var(--raised);
  color: var(--text-2);
  cursor: pointer;
}
</style>
