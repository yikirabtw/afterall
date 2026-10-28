<script setup lang="ts">
import { ref, watch } from 'vue'

import type { PeopleParams } from '../api/types'
import { LANGUAGES, PLAY_STYLES } from '../labels'
import { session } from '../stores/session'
import { haptic } from '../telegram'

// Нижняя шторка с фильтрами ленты людей (кнопка ⋮)
const props = defineProps<{ open: boolean; filters: PeopleParams }>()
const emit = defineEmits<{ apply: [filters: PeopleParams]; close: [] }>()

// Правим черновик — в ленту он попадёт только по «Показать»
const draft = ref<PeopleParams>({ ...props.filters })
watch(
  () => props.open,
  (open) => {
    if (open) draft.value = { ...props.filters }
  },
)

function setGame(gameId: number | undefined) {
  haptic.select()
  draft.value.game_id = gameId
}

function apply() {
  haptic.tap()
  emit('apply', { ...draft.value })
}

function reset() {
  haptic.select()
  draft.value = {}
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="backdrop" @click.self="emit('close')">
      <section class="sheet" role="dialog" aria-label="Фильтры">
        <div class="sheet__handle" aria-hidden="true" />
        <h2 class="sheet__title">Кого показывать</h2>

        <div class="stack">
          <div class="field">
            <span class="field__label">Игра</span>
            <div class="chips">
              <button type="button" class="chip" :class="{ 'chip--on': !draft.game_id }" @click="setGame(undefined)">
                Любая
              </button>
              <button
                v-for="game in session.games"
                :key="game.id"
                type="button"
                class="chip"
                :class="{ 'chip--on': draft.game_id === game.id }"
                @click="setGame(game.id)"
              >
                {{ game.name }}
              </button>
            </div>
          </div>

          <div class="field">
            <span class="field__label">Стиль</span>
            <div class="segmented">
              <button type="button" :aria-pressed="!draft.play_style" @click="draft.play_style = undefined">Любой</button>
              <button
                v-for="option in PLAY_STYLES"
                :key="option.value"
                type="button"
                :aria-pressed="draft.play_style === option.value"
                @click="draft.play_style = option.value"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <div class="field">
            <span class="field__label">Язык</span>
            <div class="chips">
              <button type="button" class="chip" :class="{ 'chip--on': !draft.language }" @click="draft.language = undefined">
                Любой
              </button>
              <button
                v-for="language in LANGUAGES"
                :key="language.value"
                type="button"
                class="chip"
                :class="{ 'chip--on': draft.language === language.value }"
                @click="draft.language = language.value"
              >
                {{ language.label }}
              </button>
            </div>
          </div>

          <label class="card toggle-row">
            <b>Только с микрофоном</b>
            <input v-model="draft.need_mic" class="switch" type="checkbox" />
          </label>
        </div>

        <div class="sheet__actions">
          <button class="btn btn-primary" type="button" @click="apply">Показать</button>
          <button class="btn btn-ghost" type="button" @click="reset">Сбросить</button>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: flex-end;
  background: rgb(0 0 0 / 0.7);
}

.sheet {
  width: 100%;
  max-width: 560px;
  max-height: 85vh;
  margin: 0 auto;
  padding: 8px 16px calc(16px + var(--safe-bottom));
  overflow-y: auto;
  border: 1px solid var(--line);
  border-bottom: 0;
  border-radius: 22px 22px 0 0;
  background: var(--g-50);
  box-shadow: 0 -1px 0 rgb(255 255 255 / 0.06), 0 -20px 60px rgb(0 0 0 / 0.6);
}

.sheet__handle {
  width: 40px;
  height: 4px;
  margin: 0 auto 12px;
  border-radius: 2px;
  background: var(--g-400);
}

.sheet__title {
  margin: 0 0 18px;
  font-family: var(--font-pixel);
  font-size: 24px;
  font-weight: 400;
  text-transform: uppercase;
}

.sheet__actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 20px;
}
</style>
