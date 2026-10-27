<script setup lang="ts">
import { ref } from 'vue'

import type { Match } from '../api/types'
import { haptic, openExternal } from '../telegram'

// Контакты после мэтча: ник в Telegram открывает чат, Discord копируется
defineProps<{ match: Match }>()

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
    <button
      v-if="match.username"
      class="btn btn-primary btn-small"
      type="button"
      @click="openExternal(`https://t.me/${match.username}`)"
    >
      Написать @{{ match.username }}
    </button>
    <button v-if="match.discord_tag" class="chip" type="button" @click="copyDiscord(match.discord_tag)">
      {{ copied ? 'Скопировано' : `Discord: ${match.discord_tag}` }}
    </button>
    <p v-if="!match.username && !match.discord_tag" class="hint">
      У человека не указан ни ник в Telegram, ни Discord — позовите друг друга в пати.
    </p>
  </div>
</template>

<style scoped>
.contacts {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
</style>
