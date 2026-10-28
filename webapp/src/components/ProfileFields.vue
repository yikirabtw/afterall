<script setup lang="ts">
import type { ProfileInput } from '../api/types'
import { LANGUAGES, LOOKING_FOR, PLAY_STYLES } from '../labels'
import { BIO_MAX, NAME_MAX } from '../profile'
import { haptic } from '../telegram'

// Поля анкеты: одни и те же в регистрации и в редактировании профиля
const form = defineModel<ProfileInput>({ required: true })

function toggleLanguage(code: string) {
  haptic.select()
  const has = form.value.languages.includes(code)
  if (has && form.value.languages.length === 1) return // хотя бы один язык нужен
  form.value.languages = has ? form.value.languages.filter((lang) => lang !== code) : [...form.value.languages, code]
}
</script>

<template>
  <div class="stack">
    <label class="field">
      <span class="field__label field__label--count">
        Ник
        <span>{{ form.display_name.length }}/{{ NAME_MAX }}</span>
      </span>
      <input v-model="form.display_name" class="input" :maxlength="NAME_MAX" autocomplete="nickname" />
    </label>

    <label class="field">
      <span class="field__label field__label--count">
        О себе — по желанию
        <span>{{ form.bio?.length ?? 0 }}/{{ BIO_MAX }}</span>
      </span>
      <textarea
        v-model="form.bio"
        class="input"
        :maxlength="BIO_MAX"
        rows="3"
        placeholder="Во что играешь, кого ищешь, чем зацепить"
      />
    </label>

    <div class="field">
      <span class="field__label">Кого ищешь</span>
      <div v-jelly.soft class="segmented">
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
      <div v-jelly.soft class="segmented">
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
      <span class="field__label">Discord — по желанию</span>
      <input v-model="form.discord_tag" class="input" maxlength="64" placeholder="ник в Discord" autocomplete="off" />
      <span class="hint">Увидят только после взаимного лайка или когда вы окажетесь в одной пати.</span>
    </label>
  </div>
</template>

<style scoped>
.block {
  display: block;
  margin-top: 2px;
}

.field__label--count {
  display: flex;
  justify-content: space-between;
}

.field__label--count span {
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
</style>
