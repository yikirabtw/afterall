<script setup lang="ts">
import { computed } from 'vue'

import { assetUrl } from '../api/client'
import type { Match } from '../api/types'
import { session } from '../stores/session'
import MatchContacts from './MatchContacts.vue'

// «Это мэтч!» — показывается сразу после взаимного лайка
defineProps<{ match: Match }>()
const emit = defineEmits<{ close: [] }>()

const myPhoto = computed(() => session.me?.photos[0] ?? null)
const myInitial = computed(() => session.me?.profile?.display_name.charAt(0).toUpperCase() ?? '?')
</script>

<template>
  <Teleport to="body">
    <div class="overlay" role="dialog" aria-label="Взаимный лайк">
      <div class="overlay__avatars">
        <span class="avatar">
          <img v-if="myPhoto" :src="assetUrl(myPhoto.url)" alt="" />
          <template v-else>{{ myInitial }}</template>
        </span>
        <span class="avatar avatar--them">
          <img v-if="match.photos[0]" :src="assetUrl(match.photos[0].url)" alt="" />
          <template v-else>{{ match.display_name.charAt(0).toUpperCase() }}</template>
        </span>
      </div>
      <h2 class="overlay__title">Это мэтч!</h2>
      <!-- «Ты и Лера», а не «Вы с Лера»: имена не склоняются -->
      <p class="overlay__text">Ты и {{ match.display_name }} понравились друг другу. Напиши первым — договоритесь о катке.</p>
      <MatchContacts :match="match" class="overlay__contacts" />
      <button class="btn btn-ghost" type="button" @click="emit('close')">Смотреть дальше</button>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  background: color-mix(in srgb, var(--page) 94%, var(--accent));
  text-align: center;
}

.overlay__avatars {
  display: flex;
  margin-bottom: 8px;
}

.avatar {
  display: grid;
  place-items: center;
  width: 108px;
  height: 108px;
  border: 4px solid var(--page);
  border-radius: 50%;
  overflow: hidden;
  background: linear-gradient(140deg, var(--accent), var(--warm));
  color: var(--accent-ink);
  font-size: 44px;
  font-weight: 900;
}

.avatar--them {
  margin-left: -24px;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.overlay__title {
  margin: 0;
  font-size: 36px;
  font-weight: 900;
  letter-spacing: -0.03em;
  color: var(--accent);
}

.overlay__text {
  margin: 0;
  max-width: 320px;
  color: var(--hint);
}

.overlay__contacts {
  justify-content: center;
  margin: 8px 0;
}
</style>
