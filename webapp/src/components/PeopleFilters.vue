<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { FeedPreset, PeopleParams } from '../api/types'
import { LANGUAGES, PLAY_STYLES } from '../labels'
import { router } from '../router'
import { session, setMe } from '../stores/session'
import { SHEET_MS } from '../sheet'
import { shopTab } from '../stores/ui'
import { haptic } from '../telegram'
import AgeRange from './AgeRange.vue'

// Нижняя шторка с фильтрами ленты людей (кнопка ⋮)
const props = defineProps<{ open: boolean; filters: PeopleParams }>()
const emit = defineEmits<{ apply: [filters: PeopleParams]; close: [] }>()

// Правим черновик — в ленту он попадёт только по «Показать»
const draft = ref<PeopleParams>({ ...props.filters })

// Возраст хранится не на телефоне, а на сервере: он взаимный — по нему и тебя показывают другим
function savedAge() {
  const profile = session.me?.profile
  return { min: profile?.search_age_min ?? null, max: profile?.search_age_max ?? null }
}

const age = ref(savedAge())
const saving = ref(false)
const ageError = ref('')

watch(
  () => props.open,
  (open) => {
    if (!open) return
    draft.value = { ...props.filters }
    age.value = savedAge()
    ageError.value = ''
  },
)

function setGame(gameId: number | undefined) {
  haptic.select()
  draft.value.game_id = gameId
}

// --- Наборы настроек (Premium): режим и фильтры под именем, включаются одним нажатием ---

const PRESET_NAME_MAX = 20
const PRESETS_MAX = 5
const presets = computed(() => session.me?.profile?.feed_presets ?? [])
const canPresets = computed(() => session.me?.plan.plan === 'premium')
const naming = ref(false)
const presetName = ref('')
const presetError = ref('')

function usePreset(preset: FeedPreset) {
  haptic.select()
  emit('apply', {
    mode: preset.mode ?? undefined,
    game_id: preset.game_id ?? undefined,
    need_mic: preset.need_mic || undefined,
    play_style: preset.play_style ?? undefined,
    language: preset.language ?? undefined,
  })
}

async function savePresets(next: FeedPreset[]) {
  presetError.value = ''
  try {
    setMe(await api.saveFeedPresets(next))
    return true
  } catch (e) {
    presetError.value = errorMessage(e)
    haptic.error()
    return false
  }
}

async function saveCurrent() {
  const name = presetName.value.trim()
  if (!name) return
  const current: FeedPreset = {
    name,
    mode: draft.value.mode ?? null,
    game_id: draft.value.game_id ?? null,
    need_mic: Boolean(draft.value.need_mic),
    play_style: draft.value.play_style ?? null,
    language: draft.value.language ?? null,
  }
  if (await savePresets([...presets.value.filter((p) => p.name !== name), current].slice(-PRESETS_MAX))) {
    haptic.success()
    naming.value = false
    presetName.value = ''
  }
}

async function removePreset(preset: FeedPreset) {
  haptic.tap()
  await savePresets(presets.value.filter((p) => p !== preset))
}

function openPlans() {
  haptic.tap()
  shopTab.value = 'plans'
  emit('close')
  void router.push('/shop')
}

async function apply() {
  haptic.tap()
  const saved = savedAge()
  if (age.value.min !== saved.min || age.value.max !== saved.max) {
    saving.value = true
    ageError.value = ''
    try {
      setMe(await api.saveSearchAge(age.value.min, age.value.max))
    } catch (e) {
      ageError.value = errorMessage(e)
      haptic.error()
      return
    } finally {
      saving.value = false
    }
  }
  emit('apply', { ...draft.value })
}

function reset() {
  haptic.select()
  draft.value = { mode: draft.value.mode } // режим «Кого ищу» — не фильтр, выбирается над лентой
  age.value = { min: null, max: null }
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
              <span class="field__label">Мои наборы</span>
              <template v-if="canPresets">
                <div class="chips">
                  <span v-for="preset in presets" :key="preset.name" class="preset">
                    <button type="button" class="chip" @click="usePreset(preset)">{{ preset.name }}</button>
                    <button type="button" class="preset__remove" :aria-label="`Удалить «${preset.name}»`" @click="removePreset(preset)">
                      ✕
                    </button>
                  </span>
                  <button v-if="!naming && presets.length < PRESETS_MAX" type="button" class="chip chip--add" @click="naming = true">
                    + Сохранить текущие
                  </button>
                </div>
                <form v-if="naming" class="preset-form" @submit.prevent="saveCurrent">
                  <input
                    v-model="presetName"
                    class="input"
                    :maxlength="PRESET_NAME_MAX"
                    placeholder="Название, например «Вечер доты»"
                    enterkeyhint="done"
                  />
                  <button class="btn btn-primary btn-small" type="submit" :disabled="!presetName.trim()">Сохранить</button>
                </form>
                <p v-if="presetError" class="error-text">{{ presetError }}</p>
              </template>
              <button v-else type="button" class="card locked" @click="openPlans">
                🔒 Сохранять наборы настроек — в Premium
              </button>
            </div>

            <div v-if="session.me?.search_age_limits" class="field">
              <AgeRange v-model="age" :limits="session.me.search_age_limits" />
              <p v-if="ageError" class="error-text">{{ ageError }}</p>
            </div>

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
            <button class="btn btn-primary" type="button" :disabled="saving" @click="apply">Показать</button>
            <button class="btn btn-ghost" type="button" @click="reset">Сбросить</button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.preset {
  display: inline-flex;
  align-items: center;
}

.preset .chip {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.preset__remove {
  align-self: stretch;
  padding: 0 9px;
  border: 1px solid var(--line-strong);
  border-left: 0;
  border-radius: 0 8px 8px 0;
  background: var(--card);
  color: var(--text-2);
  cursor: pointer;
}

.chip--add {
  border-style: dashed;
  color: var(--text-2);
}

.preset-form {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.preset-form .input {
  flex: 1;
  min-width: 0;
}

.locked {
  width: 100%;
  color: var(--text-2);
  font: inherit;
  font-size: 14px;
  text-align: left;
  cursor: pointer;
}

.sheet__actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 20px;
}
</style>
