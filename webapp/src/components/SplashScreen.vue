<script setup lang="ts">
import bgPoster from '../assets/splash-bg-poster.jpg'
import bgVideo from '../assets/splash-bg.mp4'
import lightImage from '../assets/splash-light.jpg'
import AsciiLogo from './AsciiLogo.vue'

// Загрузочный экран: дымный фон (видео из референсов), полоса света сверху, зерно и ASCII-логотип.
// В слот кладётся то, что под логотипом: по умолчанию — индикатор загрузки, при ошибке — текст и кнопка.
</script>

<template>
  <div class="splash theme-dark">
    <div class="splash__bg" aria-hidden="true">
      <video class="splash__video" :src="bgVideo" :poster="bgPoster" autoplay muted loop playsinline />
      <img class="splash__light" :src="lightImage" alt="" />
      <div class="splash__vignette" />
      <div class="splash__grain" />
    </div>

    <div class="splash__content">
      <AsciiLogo />
      <p class="splash__tagline">собери пати на вечер</p>
      <slot>
        <span class="dots-loader" role="status" aria-label="Загрузка"><i /><i /><i /></span>
      </slot>
    </div>
  </div>
</template>

<style scoped>
.splash {
  position: fixed;
  inset: 0;
  z-index: 100;
  overflow: hidden;
  background: var(--g-0);
}

.splash__bg > * {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.splash__video {
  opacity: 0.2;
  filter: contrast(1.15) brightness(0.85);
}

/* Мягкая дуга света из второго референса фона — поверх дыма, медленно «дышит» */
.splash__light {
  opacity: 0.4;
  mix-blend-mode: screen;
  object-position: 72% 0%;
  transform-origin: 70% 30%;
  animation: breathe 6s ease-in-out infinite alternate;
}

.splash__vignette {
  background:
    radial-gradient(ellipse 90% 50% at 50% 44%, transparent 0 30%, rgb(0 0 0 / 0.8) 85%),
    linear-gradient(to top, rgb(0 0 0 / 0.95), transparent 45%);
}

/* Зерно: шум SVG, перескакивает по кадрам */
.splash__grain {
  inset: -50% !important;
  width: 200% !important;
  height: 200% !important;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  opacity: 0.06;
  mix-blend-mode: screen;
  animation: grain 0.5s steps(3) infinite;
}

.splash__content {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 24px 16px calc(24px + var(--safe-bottom));
  text-align: center;
}

/* Подпись разрядкой, как подписи на листе со шрифтами */
.splash__tagline {
  margin: -8px 0 18px;
  font-family: var(--font-pixel);
  font-size: 13px;
  letter-spacing: 0.42em;
  text-transform: uppercase;
  color: var(--text-2);
  text-shadow: 0 0 10px rgb(255 255 255 / 0.35);
}

@keyframes breathe {
  from {
    transform: scale(1);
    opacity: 0.3;
  }

  to {
    transform: scale(1.08);
    opacity: 0.45;
  }
}

@keyframes grain {
  0% {
    transform: translate(0, 0);
  }

  33% {
    transform: translate(-7%, 4%);
  }

  66% {
    transform: translate(5%, -6%);
  }

  100% {
    transform: translate(-3%, 8%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .splash__light,
  .splash__grain {
    animation: none;
  }
}
</style>
