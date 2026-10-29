<script setup lang="ts">
import WireCubes from '../components/WireCubes.vue'

// Магазин — пока витрина «скоро»: что продавать, решим отдельно. Никаких лутбоксов — только честные покупки
</script>

<template>
  <main class="page">
    <header class="page-top">
      <h1 class="page-title">Магазин</h1>
    </header>

    <section class="card card--lit soon">
      <WireCubes class="soon__art" />
      <p class="soon__title">Скоро</p>
      <p class="hint soon__text">
        Здесь появятся штуки для профиля и подписка — по честной цене, без лутбоксов и сюрпризов мелким шрифтом.
      </p>
    </section>
  </main>
</template>

<style scoped>
.soon {
  margin-top: 8px;
  padding: 36px 20px 32px;
  text-align: center;
}

.soon__art {
  width: 150px;
  margin: 0 auto 20px;
}

.soon__title {
  margin: 0;
  font-family: var(--font-pixel);
  font-size: 44px;
  line-height: 1;
  text-transform: uppercase;
  text-shadow: 0 0 14px rgb(var(--glow-rgb) / 0.45);
}

.soon__text {
  max-width: 300px;
  margin: 12px auto 0;
}
</style>
