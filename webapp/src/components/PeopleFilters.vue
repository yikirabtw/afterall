<script setup lang="ts">
import { ref, watch } from 'vue'

import type { PeopleParams } from '../api/types'
import { LANGUAGES, PLAY_STYLES } from '../labels'
import { session } from '../stores/session'
import { SHEET_MS } from '../sheet'
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
    <Transition name="sheet" :duration="SHEET_MS">
      <div v-if="open" class="sheet-backdrop" @click.self="emit('close')">
        <section class="sheet" role="dialog" aria-label="Фильтры">
          <div class="sheet__handle" aria-hidden="true" />
          <h2 class="sheet__title">Кого показывать</h2>

          <div class="stack rise-in">
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
              <div v-jelly.soft class="segmented">
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
    </Transition>
  </Teleport>
</template>

<style scoped>
.sheet__actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 20px;
}
</style>
