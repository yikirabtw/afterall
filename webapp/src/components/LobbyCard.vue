<script setup lang="ts">
import { computed } from 'vue'

import type { Lobby } from '../api/types'
import { formatStart } from '../format'
import { LOBBY_STATUS_LABELS, MEMBER_STATUS_LABELS, PLAY_STYLE_LABELS } from '../labels'
import { gameById } from '../stores/session'

const props = defineProps<{ lobby: Lobby; showMyStatus?: boolean }>()

const game = computed(() => gameById(props.lobby.game_id))

const rankRange = computed(() => {
  const ranks = game.value?.ranks ?? []
  const min = ranks.find((rank) => rank.id === props.lobby.rank_min_id)
  const max = ranks.find((rank) => rank.id === props.lobby.rank_max_id)
  if (min && max) return min.id === max.id ? min.name : `${min.name} – ${max.name}`
  if (min) return `от ${min.name}`
  if (max) return `до ${max.name}`
  return null
})

const freeSlots = computed(() => props.lobby.slots_total - props.lobby.slots_taken)

const statusBadge = computed(() => {
  if (props.lobby.is_owner) return 'Твоя пати'
  if (props.showMyStatus && props.lobby.my_status) return MEMBER_STATUS_LABELS[props.lobby.my_status] ?? null
  return null
})
</script>

<template>
  <article class="lobby card">
    <header class="lobby__top">
      <span class="lobby__game">{{ game?.name ?? 'Просто посидеть' }}</span>
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
        <span class="lobby__dots" aria-hidden="true">
          <i v-for="n in lobby.slots_total" :key="n" :class="{ taken: n <= lobby.slots_taken }" />
        </span>
        {{ lobby.slots_taken }}/{{ lobby.slots_total }}
      </span>
    </footer>
  </article>
</template>

<style scoped>
.lobby__top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
}

.lobby__game {
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.lobby__when {
  color: var(--warm);
}

.lobby__title {
  margin: 8px 0 0;
  font-size: 18px;
  font-weight: 800;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.lobby__description {
  margin: 6px 0 0;
  font-size: 15px;
  color: var(--hint);
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
  border-top: 1px solid var(--line);
  font-size: 14px;
}

.lobby__owner {
  color: var(--hint);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lobby__rep {
  margin-left: 4px;
  color: var(--accent);
  font-weight: 700;
}

.lobby__slots {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.lobby__dots {
  display: inline-flex;
  gap: 3px;
}

.lobby__dots i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1.5px solid var(--hint);
}

.lobby__dots i.taken {
  border-color: var(--accent);
  background: var(--accent);
}

/* Осталось одно место — подсвечиваем тёплым, чтобы цепляло взгляд */
.lobby__slots--last {
  color: var(--warm);
}
</style>
