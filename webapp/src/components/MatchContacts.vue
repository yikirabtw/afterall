<script setup lang="ts">
import { ref } from 'vue'

import type { Match } from '../api/types'
import { openFrom } from '../router'
import { haptic, openExternal } from '../telegram'

// Контакты после мэтча: «Написать» — чат в приложении; ник в Telegram — если человек его открыл; Discord копируется
const props = defineProps<{ match: Match }>()

function write(event: MouseEvent) {
  haptic.tap()
  openFrom(event.currentTarget as Element, `/chat/direct/${props.match.user_id}`, 'morph')
}

const copied = ref(false)

async function copyDiscord(tag: string) {
  try {
    await navigator.clipboard.writeText(tag)
    copied.value = true
    haptic.success()
  } catch {
    copied.value = false
  }
}
</script>

<template>
  <div class="contacts">
    <button class="btn btn-primary btn-small" type="button" @click="write">Написать</button>
    <button v-if="match.username" class="chip" type="button" @click="openExternal(`https://t.me/${match.username}`)">
      <span class="contacts__nick">@{{ match.username }}</span> ↗
    </button>
    <button v-if="match.discord_tag" class="chip" type="button" @click="copyDiscord(match.discord_tag)">
      {{ copied ? 'Скопировано' : `Discord: ${match.discord_tag}` }}
    </button>
  </div>
</template>

<style scoped>
/* Ник — как есть, без капса кнопки */
.contacts__nick {
  text-transform: none;
  letter-spacing: 0.02em;
}

.contacts {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
</style>
