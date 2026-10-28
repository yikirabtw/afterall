<script setup lang="ts">
import { computed, ref } from 'vue'

import { api, assetUrl } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Me, Photo } from '../api/types'
import PageHeader from '../components/PageHeader.vue'
import ProfileFields from '../components/ProfileFields.vue'
import { PHOTOS_MAX, profileError, profileFormFrom } from '../profile'
import { goBack } from '../router'
import { session, setMe } from '../stores/session'
import { confirmAction, haptic } from '../telegram'

const form = ref(profileFormFrom(session.me!))
const photos = computed(() => session.me!.photos)
const fileInput = ref<HTMLInputElement | null>(null)

const uploading = ref(false)
const photoBusy = ref(false)
const photoError = ref('')
const saving = ref(false)
const error = ref('')

async function photoAction(action: () => Promise<Me>) {
  photoBusy.value = true
  photoError.value = ''
  try {
    setMe(await action())
    haptic.success()
  } catch (e) {
    photoError.value = errorMessage(e)
    haptic.error()
  } finally {
    photoBusy.value = false
  }
}

function pickPhoto() {
  haptic.tap()
  fileInput.value?.click()
}

async function onFileChosen(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // чтобы то же фото можно было выбрать повторно
  if (!file) return
  uploading.value = true
  await photoAction(() => api.uploadPhoto(file))
  uploading.value = false
}

async function removePhoto(photo: Photo) {
  if (await confirmAction('Удалить это фото?')) await photoAction(() => api.deletePhoto(photo.id))
}

async function makeMain(photo: Photo) {
  const order = [photo.id, ...photos.value.filter((item) => item.id !== photo.id).map((item) => item.id)]
  await photoAction(() => api.reorderPhotos(order))
}

async function save() {
  const problem = profileError(form.value)
  if (problem) {
    error.value = problem
    haptic.error()
    return
  }
  saving.value = true
  error.value = ''
  try {
    setMe(await api.saveProfile(form.value))
    haptic.success()
    goBack()
  } catch (e) {
    error.value = errorMessage(e)
    haptic.error()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <main class="page rise-in">
    <PageHeader title="Профиль" />

    <section>
      <div class="photo-grid">
        <div v-for="slot in PHOTOS_MAX" :key="slot" class="photo-slot">
          <template v-if="photos[slot - 1]">
            <img :src="assetUrl(photos[slot - 1]!.url)" alt="" class="photo-slot__img" />
            <span v-if="slot === 1" class="photo-slot__main">Главное</span>
            <button
              v-else
              class="photo-slot__make-main"
              type="button"
              :disabled="photoBusy"
              @click="makeMain(photos[slot - 1]!)"
            >
              Сделать главным
            </button>
            <button
              class="photo-slot__remove"
              type="button"
              aria-label="Удалить фото"
              :disabled="photoBusy"
              @click="removePhoto(photos[slot - 1]!)"
            >
              ✕
            </button>
          </template>
          <button
            v-else-if="slot === photos.length + 1"
            class="photo-slot__add"
            type="button"
            :disabled="photoBusy"
            @click="pickPhoto"
          >
            <span v-if="uploading" class="spinner" />
            <template v-else>
              <b>+</b>
              <span>Фото</span>
            </template>
          </button>
          <div v-else class="photo-slot__empty" />
        </div>
      </div>
      <input ref="fileInput" type="file" accept="image/*" hidden @change="onFileChosen" />
      <p class="hint">
        До {{ PHOTOS_MAX }} фото. Главное видят первым в ленте. Перед сохранением мы убираем из фото геометку.
      </p>
      <p v-if="photoError" class="error-text">{{ photoError }}</p>
    </section>

    <h2 class="section-title">Анкета</h2>
    <ProfileFields v-model="form" />

    <p v-if="error" class="error-text">{{ error }}</p>
    <div class="actions">
      <button class="btn btn-primary" type="button" :disabled="saving" @click="save">Сохранить</button>
    </div>
  </main>
</template>

<style scoped>
.photo-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.photo-slot {
  position: relative;
  aspect-ratio: 3 / 4;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--card);
}

.photo-slot:has(.photo-slot__img) {
  border: 1px solid var(--line-strong);
}

.photo-slot__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo-slot__main,
.photo-slot__make-main {
  position: absolute;
  left: 6px;
  right: 6px;
  bottom: 6px;
  padding: 4px 6px;
  border: 0;
  border-radius: 5px;
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-align: center;
}

.photo-slot__main {
  background: var(--accent);
  color: var(--accent-ink);
  box-shadow: var(--glow-1);
}

.photo-slot__make-main {
  border: 1px solid rgb(255 255 255 / 0.3);
  background: rgb(0 0 0 / 0.6);
  color: #fff;
  cursor: pointer;
}

.photo-slot__remove {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 26px;
  height: 26px;
  border: 0;
  border-radius: 7px;
  background: rgb(0 0 0 / 0.6);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}

.photo-slot__add {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  border: 1px dashed var(--g-400);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--hint);
  cursor: pointer;
}

.photo-slot__add b {
  font-family: var(--font-pixel);
  font-size: 40px;
  font-weight: 400;
  line-height: 1;
  color: var(--text);
  text-shadow: 0 0 12px rgb(var(--glow-rgb) / 0.7);
}

.photo-slot__empty {
  width: 100%;
  height: 100%;
  border: 1px dashed var(--line-strong);
  border-radius: var(--radius-sm);
  opacity: 0.5;
}
</style>
