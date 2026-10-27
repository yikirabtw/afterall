<script setup lang="ts">
import { reactive, ref } from 'vue'

import { api } from '../../api/client'
import { errorMessage } from '../../api/errors'
import type { Me, ProfileInput } from '../../api/types'
import { LANGUAGES, LOOKING_FOR, PLAY_STYLES } from '../../labels'
import { session } from '../../stores/session'
import { haptic } from '../../telegram'

defineProps<{ busy?: boolean }>()
const emit = defineEmits<{ done: [me?: Me] }>()

const existing = session.me!.profile
const form = reactive<ProfileInput>({
  display_name: existing?.display_name ?? session.me!.first_name.slice(0, 32),
  bio: existing?.bio ?? null,
  has_mic: existing?.has_mic ?? true,
  play_style: existing?.play_style ?? 'balanced',
  looking_for: existing?.looking_for ?? 'both',
  languages: existing?.languages ?? ['ru'],
  city: existing?.city ?? null,
  // Часовой пояс берём с телефона — нужен, чтобы «вечер» был вечером именно у тебя
  timezone: existing?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'Europe/Moscow',
  discord_tag: existing?.discord_tag ?? null,
  is_visible: existing?.is_visible ?? true,
})
const saving = ref(false)
const error = ref('')

function toggleLanguage(code: string) {
  haptic.select()
  const has = form.languages.includes(code)
  if (has && form.languages.length === 1) return // хотя бы один язык нужен
  form.languages = has ? form.languages.filter((lang) => lang !== code) : [...form.languages, code]
}

async function submit() {
  if (!form.display_name.trim()) {
    error.value = 'Как тебя называть? Имя обязательно.'
    return
  }
  saving.value = true
  error.value = ''
  try {
    emit('done', await api.saveProfile(form))
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
    <h1 class="page-title">Анкета</h1>

    <div class="stack">
      <label class="field">
        <span class="field__label">Как тебя называть</span>
        <input v-model="form.display_name" class="input" maxlength="32" autocomplete="nickname" />
      </label>

      <div class="field">
        <span class="field__label">Кого ищешь</span>
        <div class="segmented">
          <button
            v-for="option in LOOKING_FOR"
            :key="option.value"
            type="button"
            :aria-pressed="form.looking_for === option.value"
            @click="(form.looking_for = option.value), haptic.select()"
          >
            {{ option.label }}
          </button>
        </div>
      </div>

      <div class="field">
        <span class="field__label">Стиль игры</span>
        <div class="segmented">
          <button
            v-for="option in PLAY_STYLES"
            :key="option.value"
            type="button"
            :aria-pressed="form.play_style === option.value"
            @click="(form.play_style = option.value), haptic.select()"
          >
            {{ option.label }}
          </button>
        </div>
      </div>

      <label class="card toggle-row">
        <span>
          <b>Есть микрофон</b>
          <span class="hint block">Многие пати собираются только с голосом</span>
        </span>
        <input v-model="form.has_mic" class="switch" type="checkbox" />
      </label>

      <div class="field">
        <span class="field__label">Языки</span>
        <div class="chips">
          <button
            v-for="language in LANGUAGES"
            :key="language.value"
            type="button"
            class="chip"
            :class="{ 'chip--on': form.languages.includes(language.value) }"
            @click="toggleLanguage(language.value)"
          >
            {{ language.label }}
          </button>
        </div>
      </div>

      <label class="field">
        <span class="field__label">Город — по желанию</span>
        <input v-model="form.city" class="input" maxlength="64" placeholder="Например, Казань" />
      </label>

      <label class="field">
        <span class="field__label">О себе — по желанию</span>
        <textarea v-model="form.bio" class="input" maxlength="300" placeholder="Во что играешь, когда, чего ждёшь от пати" />
      </label>

      <label class="field">
        <span class="field__label">Discord — по желанию</span>
        <input v-model="form.discord_tag" class="input" maxlength="64" placeholder="ник в Discord" autocomplete="off" />
        <span class="hint">Увидят только те, с кем ты окажешься в одной пати.</span>
      </label>
    </div>

    <p v-if="error" class="error-text">{{ error }}</p>
    <div class="actions">
      <button class="btn btn-primary" type="button" :disabled="saving" @click="submit">Далее</button>
    </div>
  </section>
</template>

<style scoped>
.block {
  display: block;
  margin-top: 2px;
}
</style>
