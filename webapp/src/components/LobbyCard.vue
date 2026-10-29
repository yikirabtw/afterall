<script setup lang="ts">
import { computed } from 'vue'

import type { Lobby } from '../api/types'
import reflection from '../assets/reflection.jpg'
import { formatStart } from '../format'
import { LOBBY_STATUS_LABELS, MEMBER_STATUS_LABELS, PLAY_STYLE_LABELS } from '../labels'
import { gameColor, gameTitle, rankRangeLabel } from '../lobby'
import { haptic } from '../telegram'

const props = defineProps<{ lobby: Lobby; showMyStatus?: boolean }>()

const rankRange = computed(() => rankRangeLabel(props.lobby))

const freeSlots = computed(() => props.lobby.slots_total - props.lobby.slots_taken)

const statusBadge = computed(() => {
  if (props.lobby.is_owner) return 'Твоя пати'
  if (props.showMyStatus && props.lobby.my_status) return MEMBER_STATUS_LABELS[props.lobby.my_status] ?? null
  return null
})
</script>

<template>
  <RouterLink
    v-reflect
    :to="`/lobby/${lobby.id}`"
    class="lobby card"
    :style="{ '--game': gameColor(lobby.game_id) }"
    @click="haptic.tap()"
  >
    <!-- Металл: размытое отражение «полосы света», полоса блеска и блик под пальцем (v-reflect) -->
    <span class="lobby__fx" aria-hidden="true">
      <span class="lobby__reflection" data-reflect="reflection" :style="{ backgroundImage: `url(${reflection})` }" />
      <span class="lobby__sheen" data-reflect="sheen" />
      <span class="lobby__glare" />
    </span>
    <header class="lobby__top">
      <span class="lobby__game">{{ gameTitle(lobby) }}</span>
      <span class="lobby__when">{{ formatStart(lobby.starts_at) }}</span>
    </header>

    <h3 class="lobby__title">{{ lobby.title }}</h3>
    <p v-if="lobby.description" class="lobby__description">{{ lobby.description }}</p>

    <div class="chips lobby__tags">
      <span v-if="statusBadge" class="badge badge--accent">{{ statusBadge }}</span>
      <span v-if="LOBBY_STATUS_LABELS[lobby.status]" class="badge">{{ LOBBY_STATUS_LABELS[lobby.status] }}</span>
      <span v-if="rankRange" class="badge">{{ rankRange }}</span>
      <span v-if="lobby.need_mic" class="badge">С микрофоном</span>
      <span v-if="lobby.play_style" class="badge">{{ PLAY_STYLE_LABELS[lobby.play_style] }}</span>
      <span v-if="lobby.language !== 'ru'" class="badge">{{ lobby.language.toUpperCase() }}</span>
    </div>

    <footer class="lobby__bottom">
      <span class="lobby__owner">
        {{ lobby.owner.display_name }}
        <span v-if="lobby.owner.reputation > 0" class="lobby__rep">+{{ lobby.owner.reputation }}</span>
      </span>
      <span class="lobby__slots" :class="{ 'lobby__slots--last': freeSlots === 1 }">
        <span class="lobby__cells" aria-hidden="true">
          <i v-for="n in lobby.slots_total" :key="n" :class="{ taken: n <= lobby.slots_taken }" />
        </span>
        {{ lobby.slots_taken }}/{{ lobby.slots_total }}
      </span>
    </footer>
  </RouterLink>
</template>

<style scoped>
.lobby {
  position: relative;
  display: block;
  overflow: hidden;
  padding-left: 20px;
  color: inherit;
  text-decoration: none;
  transform: perspective(800px) rotateX(var(--rx, 0deg)) rotateY(var(--ry, 0deg)) scale(var(--press, 1));
  transition:
    transform 0.5s cubic-bezier(0.22, 1, 0.36, 1),
    border-color 0.15s ease;
}

/* Пока палец или курсор на карточке — наклон без запаздывания */
.lobby.is-tilting {
  transition:
    transform 0.1s linear,
    border-color 0.15s ease;
}

.lobby:active {
  --press: 0.99;
  border-color: var(--line-strong);
}

/* Содержимое — над слоями металла */
.lobby > :not(.lobby__fx) {
  position: relative;
  z-index: 1;
}

.lobby__fx,
.lobby__fx > * {
  position: absolute;
  pointer-events: none;
}

.lobby__fx {
  inset: 0;
  overflow: hidden;
  border-radius: inherit;
}

/* Отражение едет при прокрутке и чуть против наклона — transform ставит v-reflect */
.lobby__reflection {
  inset: -45% -20%;
  background-position: center;
  background-size: cover;
  opacity: var(--reflect-opacity);
  filter: var(--reflect-filter);
  mix-blend-mode: var(--reflect-blend);
  will-change: transform;
  transition: transform 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}

.lobby.is-tilting .lobby__reflection {
  transition: transform 0.1s linear;
}

/* Полоса блеска, как на шлифованном металле, — проходит по карточке при прокрутке */
.lobby__sheen {
  inset: 0;
  background: linear-gradient(105deg, transparent 38%, rgb(var(--glow-rgb) / 0.07) 50%, transparent 62%);
  will-change: transform;
}

.lobby__glare {
  inset: 0;
  background: radial-gradient(circle at var(--gx, 50%) var(--gy, 50%), rgb(var(--glow-rgb) / 0.3), transparent 55%);
  opacity: var(--glare, 0);
  transition: opacity 0.35s ease;
}

@media (prefers-reduced-motion: reduce) {
  .lobby,
  .lobby__reflection {
    transition: none;
  }
}

/* Светящаяся полоска цвета игры слева — как в шпаргалке по цветам; над слоями металла */
.lobby::before {
  z-index: 2;
  content: '';
  position: absolute;
  top: 14px;
  bottom: 14px;
  left: 0;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--game);
  box-shadow: 0 0 10px 1px var(--game), 0 0 36px 6px color-mix(in srgb, var(--game) 35%, transparent);
}

.lobby__top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.lobby__game {
  color: var(--text);
}

.lobby__when {
  color: var(--text-2);
}

.lobby__title {
  margin: 8px 0 0;
  font-family: var(--font-title);
  font-size: 19px;
  font-weight: 400;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.lobby__description {
  margin: 6px 0 0;
  font-size: 15px;
  color: var(--text-2);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.lobby__tags {
  margin-top: 12px;
  gap: 6px;
}

.lobby__tags:empty {
  display: none;
}

.lobby__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--line-strong);
  font-size: 14px;
}

.lobby__owner {
  color: var(--text-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lobby__rep {
  margin-left: 4px;
  color: var(--ok);
  font-weight: 700;
}

.lobby__slots {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-pixel);
  font-size: 16px;
}

/* Места — пиксельные клетки: занятые светятся */
.lobby__cells {
  display: inline-flex;
  gap: 3px;
}

.lobby__cells i {
  width: 8px;
  height: 8px;
  border: 1px solid var(--g-400);
}

.lobby__cells i.taken {
  border-color: var(--accent);
  background: var(--accent);
  box-shadow: 0 0 6px rgb(var(--glow-rgb) / 0.7);
}

/* Осталось одно место — подсвечиваем жёлтым, чтобы цепляло взгляд */
.lobby__slots--last {
  color: var(--warn);
  text-shadow: 0 0 10px color-mix(in srgb, var(--warn) 60%, transparent);
}
</style>
