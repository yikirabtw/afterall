<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import PageHeader from '../components/PageHeader.vue'
import WireCubes from '../components/WireCubes.vue'
import { router } from '../router'

// Приглашение в закрытую пати (кнопка из бота по ссылке t.me/<бот>?start=join_<код>):
// находим пати по коду и открываем её карточку с этим кодом — тогда в неё можно откликнуться
const props = defineProps<{ code: string }>()

const error = ref('')

onMounted(async () => {
  try {
    const lobby = await api.lobbyByInvite(props.code)
    await router.replace({ path: `/lobby/${lobby.id}`, query: { invite: props.code } })
  } catch (e) {
    error.value = errorMessage(e)
  }
})
</script>

<template>
  <main class="page">
    <PageHeader title="Приглашение" />
    <div v-if="!error" class="center"><span class="dots-loader"><i /><i /><i /></span></div>
    <div v-else class="empty">
      <WireCubes class="empty__art" />
      <p class="empty__title">Пати недоступна</p>
      <p class="hint">Её уже нет, или она не для твоего возраста. Попроси у друга новую ссылку.</p>
    </div>
  </main>
</template>

<style scoped>
.center {
  display: flex;
  justify-content: center;
  padding: 32px 0;
}
</style>
