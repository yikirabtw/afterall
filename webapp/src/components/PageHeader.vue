<script setup lang="ts">
import { ref } from 'vue'

import { goBack } from '../router'
import { insideTelegram, useBackButton } from '../telegram'

defineProps<{ title: string }>()

// В Telegram — системная кнопка «Назад» в шапке, в браузере — своя
useBackButton(goBack, ref(true))
</script>

<template>
  <header class="page-header">
    <button v-if="!insideTelegram" class="btn btn-ghost page-header__back" type="button" @click="goBack">
      ← Назад
    </button>
    <h1 class="page-title">{{ title }}</h1>
  </header>
</template>

<style scoped>
.page-header__back {
  padding: 0;
  min-height: 32px;
}
</style>
