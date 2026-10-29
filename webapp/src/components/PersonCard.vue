<script setup lang="ts">
import { computed } from 'vue'

import type { Person } from '../api/types'
import { PLAY_STYLE_LABELS } from '../labels'
import { rankName } from '../lobby'
import { gameById } from '../stores/session'
import FaceitLevel from './FaceitLevel.vue'
import PhotoCarousel from './PhotoCarousel.vue'

const props = defineProps<{ person: Person }>()

// Блик слабее, чем у карточек пати: он ложится на фото человека
const REFLECT = { glare: 0.22 }

// Сначала общие игры — их и подсвечиваем; выключенных игр (нет в справочнике) не показываем
const games = computed(() =>
  [...props.person.games]
    .filter((game) => gameById(game.game_id))
    .sort((a, b) => Number(props.person.common_game_ids.includes(b.game_id)) - Number(props.person.common_game_ids.includes(a.game_id)))
    .map((game) => ({
      id: game.game_id,
      label: [gameById(game.game_id)?.name, rankName(game.game_id, game.rank_id)].filter(Boolean).join(' · '),
      faceit: game.faceit_elo,
      common: props.person.common_game_ids.includes(game.game_id),
    })),
)

const meta = computed(() =>
  [props.person.city, PLAY_STYLE_LABELS[props.person.play_style], props.person.has_mic ? 'с микрофоном' : 'без микрофона']
    .filter(Boolean)
    .join(' · '),
)
</script>

<template>
  <!-- Наклон и блик от пальца — как у «металла» пати, но без отражения поверх фото (v-reflect без слоёв) -->
  <PhotoCarousel v-reflect="REFLECT" class="person" :photos="person.photos" :name="person.display_name">
    <span class="person__match">
      <b>{{ person.compatibility }}%</b>
      <span>совпадение</span>
    </span>
    <h2 class="person__name">
      {{ person.display_name }}<span v-if="person.age !== null" class="person__age">, {{ person.age }}</span>
    </h2>
    <p class="person__meta">{{ meta }}</p>
    <div class="person__games">
      <span v-for="game in games" :key="game.id" class="person__game" :class="{ 'person__game--common': game.common }">
        {{ game.label }}
        <span v-if="game.faceit !== null" class="person__faceit">
          <FaceitLevel :elo="game.faceit" :size="20" />
          {{ game.faceit }}
        </span>
      </span>
    </div>
    <p v-if="person.reasons.length" class="person__reasons">{{ person.reasons.join(' · ') }}</p>
    <p v-if="person.bio" class="person__bio">{{ person.bio }}</p>
  </PhotoCarousel>
</template>

<style scoped>
.person {
  width: 100%;
  height: 100%;
  border: 1px solid var(--line);
  border-radius: 20px;
  box-shadow: var(--edge-light);
  transform: perspective(900px) rotateX(var(--rx, 0deg)) rotateY(var(--ry, 0deg));
  transition: transform 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}

.person.is-tilting {
  transition: transform 0.1s linear;
}

/* Блик в точке касания — только пока палец на карточке */
.person::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 3;
  background: radial-gradient(circle at var(--gx, 50%) var(--gy, 50%), rgb(255 255 255 / 0.5), transparent 55%);
  opacity: var(--glare, 0);
  pointer-events: none;
  transition: opacity 0.35s ease;
}

@media (prefers-reduced-motion: reduce) {
  .person {
    transition: none;
  }
}

/* «Совпадение N%» — наша изюминка: крупные цифры со свечением */
.person__match {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 10px;
  padding: 5px 10px 4px;
  border: 1px solid rgb(255 255 255 / 0.55);
  border-radius: 6px;
  background: rgb(0 0 0 / 0.45);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: 0 0 16px rgb(255 255 255 / 0.25);
}

/* Цифры — тем же шрифтом, что имя: пиксельный на маленьком размере читался плохо */
.person__match b {
  font-family: var(--font-title);
  font-size: 22px;
  font-weight: 400;
  line-height: 1;
  text-shadow: 0 0 6px rgb(255 255 255 / 0.35);
}

.person__match span {
  font-family: var(--font-display);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  opacity: 0.8;
}

.person__name {
  margin: 0;
  font-family: var(--font-title);
  font-size: 30px;
  font-weight: 400;
  line-height: 1.1;
  overflow-wrap: anywhere;
}

.person__age {
  font-weight: 500;
  opacity: 0.8;
}

.person__meta {
  margin: 4px 0 0;
  font-size: 14px;
  opacity: 0.8;
}

.person__games {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.person__game {
  padding: 4px 10px;
  border: 1px solid rgb(255 255 255 / 0.16);
  border-radius: 6px;
  background: rgb(0 0 0 / 0.4);
  font-size: 13px;
  font-weight: 600;
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

/* Общие игры — белая рамка со свечением */
/* FACEIT в плашке игры: значок уровня и ELO */
.person__faceit {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-left: 4px;
  vertical-align: middle;
}

.person__game--common {
  border-color: #fff;
  box-shadow: 0 0 10px rgb(255 255 255 / 0.35), inset 0 0 8px rgb(255 255 255 / 0.12);
}

.person__reasons {
  margin: 10px 0 0;
  font-size: 13px;
  font-weight: 600;
  color: rgb(255 255 255 / 0.8); /* поверх фото — всегда светлый, в любой теме */
}

.person__reasons::before {
  content: '✦ ';
}

.person__bio {
  margin: 8px 0 0;
  font-size: 15px;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  overflow-wrap: anywhere;
}
</style>
