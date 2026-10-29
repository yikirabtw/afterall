<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'

import { answer, confirmState } from '../stores/confirm'

// Окно «Точно?» вне Telegram (в Telegram — его собственное showConfirm). Поверх шторок; Esc — отмена
function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') answer(false)
}

watch(
  () => confirmState.open,
  (open) => {
    if (open) window.addEventListener('keydown', onKey)
    else window.removeEventListener('keydown', onKey)
  },
)

onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <Transition name="confirm">
      <div v-if="confirmState.open" class="confirm-backdrop" @click.self="answer(false)">
        <section class="card card--lit confirm" role="alertdialog" aria-modal="true" :aria-label="confirmState.message">
          <p class="confirm__text">{{ confirmState.message }}</p>
          <div class="confirm__actions">
            <button class="btn btn-ghost" type="button" @click="answer(false)">Отмена</button>
            <button class="btn btn-primary" type="button" @click="answer(true)">Подтвердить</button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.confirm-backdrop {
  position: fixed;
  inset: 0;
  z-index: 60; /* выше шторок (50) */
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgb(0 0 0 / 0.7);
}

.confirm {
  width: 100%;
  max-width: 360px;
  padding: 20px;
}

.confirm__text {
  margin: 0;
  font-size: 15px;
  line-height: 1.45;
}

.confirm__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 18px;
}

.confirm__actions .btn {
  min-height: 44px;
  padding: 0 12px;
  font-size: 13px;
}

.confirm-enter-active,
.confirm-leave-active {
  transition: opacity 0.2s ease;
}

.confirm-enter-active .confirm,
.confirm-leave-active .confirm {
  transition: transform 0.2s ease;
}

.confirm-enter-from,
.confirm-leave-to {
  opacity: 0;
}

.confirm-enter-from .confirm,
.confirm-leave-to .confirm {
  transform: scale(0.96);
}
</style>
