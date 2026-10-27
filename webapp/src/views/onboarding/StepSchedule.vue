<script setup lang="ts">
import { ref } from 'vue'

import { api } from '../../api/client'
import { errorMessage } from '../../api/errors'
import type { Me, Slot } from '../../api/types'
import { mergeSlots } from '../../format'
import { haptic } from '../../telegram'

defineProps<{ busy?: boolean }>()
const emit = defineEmits<{ done: [me?: Me] }>()

const WEEKDAYS = [0, 1, 2, 3, 4]
const WEEKEND = [5, 6]
const EVERY_DAY = [0, 1, 2, 3, 4, 5, 6]

function slots(days: number[], start: number, end: number): Slot[] {
  return days.map((weekday) => ({ weekday, start_minute: start, end_minute: end }))
}

// Готовые варианты вместо таблицы часов — так быстрее. Точное расписание можно будет настроить в профиле.
const PRESETS: { id: string; title: string; hint: string; slots: Slot[] }[] = [
  { id: 'weekday_evening', title: 'Будни вечером', hint: 'Пн–Пт, 18:00–23:00', slots: slots(WEEKDAYS, 18 * 60, 23 * 60) },
  { id: 'weekend_day', title: 'Выходные днём', hint: 'Сб–Вс, 12:00–18:00', slots: slots(WEEKEND, 12 * 60, 18 * 60) },
  { id: 'weekend_evening', title: 'Выходные вечером', hint: 'Сб–Вс, 18:00–24:00', slots: slots(WEEKEND, 18 * 60, 24 * 60) },
  {
    id: 'night',
    title: 'Ночью',
    hint: 'Каждый день, 23:00–02:00',
    // Через полночь — два слота: до конца суток и начало следующего дня
    slots: [
      ...slots(EVERY_DAY, 23 * 60, 24 * 60),
      ...EVERY_DAY.map((day) => ({ weekday: (day + 1) % 7, start_minute: 0, end_minute: 2 * 60 })),
    ],
  },
]

const selected = ref<string[]>([])
const saving = ref(false)
const error = ref('')

function toggle(id: string) {
  haptic.select()
  selected.value = selected.value.includes(id) ? selected.value.filter((item) => item !== id) : [...selected.value, id]
}

async function submit() {
  if (selected.value.length === 0) return emit('done')
  saving.value = true
  error.value = ''
  try {
    const chosen = PRESETS.filter((preset) => selected.value.includes(preset.id)).flatMap((preset) => preset.slots)
    emit('done', await api.saveAvailability(mergeSlots(chosen)))
  } catch (e) {
    error.value = errorMessage(e)
    haptic.error()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section>
    <h1 class="page-title">Когда обычно играешь?</h1>
    <p class="lead">Будем звать в пати именно в это время. Можно выбрать несколько вариантов или пропустить.</p>

    <div class="stack">
      <button
        v-for="preset in PRESETS"
        :key="preset.id"
        type="button"
        class="card preset"
        :aria-pressed="selected.includes(preset.id)"
        @click="toggle(preset.id)"
      >
        <span>
          <b>{{ preset.title }}</b>
          <span class="hint">{{ preset.hint }}</span>
        </span>
        <span class="preset__check" aria-hidden="true" />
      </button>
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>
    <div class="actions">
      <button class="btn btn-primary" type="button" :disabled="saving || busy" @click="submit">
        {{ selected.length ? 'Готово' : 'Пропустить и закончить' }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.lead {
  margin: -8px 0 20px;
  color: var(--hint);
}

.preset {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  border: 2px solid transparent;
  text-align: left;
  cursor: pointer;
}

.preset .hint {
  display: block;
  margin-top: 2px;
}

.preset[aria-pressed='true'] {
  border-color: var(--accent);
}

.preset__check {
  flex: none;
  width: 24px;
  height: 24px;
  border: 2px solid var(--line);
  border-radius: 50%;
}

.preset[aria-pressed='true'] .preset__check {
  border-color: var(--accent);
  background: var(--accent) radial-gradient(circle, var(--accent-ink) 30%, transparent 32%);
}
</style>
