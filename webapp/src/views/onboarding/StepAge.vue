<script setup lang="ts">
import { computed, ref } from 'vue'

import { ApiError, api } from '../../api/client'
import { errorMessage } from '../../api/errors'
import type { Me } from '../../api/types'
import { session } from '../../stores/session'
import { haptic } from '../../telegram'

defineProps<{ busy?: boolean }>()
const emit = defineEmits<{ done: [me?: Me] }>()

const birthDate = ref('')
const saving = ref(false)
const error = ref('')

const alreadySet = computed(() => session.me?.birth_date ?? null)
const today = new Date().toISOString().slice(0, 10)

async function submit() {
  if (alreadySet.value) return emit('done')
  if (!birthDate.value) {
    error.value = 'Укажи дату рождения.'
    return
  }
  saving.value = true
  error.value = ''
  try {
    emit('done', await api.setBirthDate(birthDate.value))
  } catch (e) {
    if (e instanceof ApiError && e.code === 'birth_date_already_set') {
      emit('done', await api.me())
      return
    }
    error.value = errorMessage(e)
    haptic.error()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section>
    <h1 class="page-title">Сколько тебе лет?</h1>
    <p class="lead">
      Подбираем пати среди сверстников: подростки и взрослые друг друга в приложении не видят.
    </p>

    <div v-if="alreadySet" class="card">
      Дата рождения указана: <b>{{ new Date(alreadySet).toLocaleDateString('ru-RU') }}</b>
    </div>
    <template v-else>
      <label class="field">
        <span class="field__label">Дата рождения</span>
        <input v-model="birthDate" class="input" type="date" min="1926-01-01" :max="today" />
      </label>
      <p class="hint">
        Другим пользователям дату не показываем. Изменить её потом можно будет только через поддержку.
      </p>
    </template>
    <p v-if="error" class="error-text">{{ error }}</p>

    <div class="actions">
      <button class="btn btn-primary" type="button" :disabled="saving" @click="submit">Далее</button>
    </div>
  </section>
</template>

<style scoped>
.lead {
  margin: -8px 0 20px;
  color: var(--hint);
}
</style>
