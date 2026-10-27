<script setup lang="ts">
import { ref } from 'vue'

import { api } from '../../api/client'
import { errorMessage } from '../../api/errors'
import type { Me } from '../../api/types'
import ProfileFields from '../../components/ProfileFields.vue'
import { profileError, profileFormFrom } from '../../profile'
import { session } from '../../stores/session'
import { haptic } from '../../telegram'

defineProps<{ busy?: boolean }>()
const emit = defineEmits<{ done: [me?: Me] }>()

const form = ref(profileFormFrom(session.me!))
const saving = ref(false)
const error = ref('')

async function submit() {
  const problem = profileError(form.value)
  if (problem) {
    error.value = problem
    return
  }
  saving.value = true
  error.value = ''
  try {
    emit('done', await api.saveProfile(form.value))
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
    <p class="lead">Фото можно добавить потом — в профиле, по кнопке с карандашом.</p>

    <ProfileFields v-model="form" />

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
