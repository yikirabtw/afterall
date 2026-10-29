<script setup lang="ts">
import { computed, ref } from 'vue'

import CosmeticPreview from '../components/CosmeticPreview.vue'
import { formatDate } from '../format'
import { SHEET_MS } from '../sheet'
import {
  BOOST_RULES,
  BOOSTS,
  COSMETIC_KINDS,
  COSMETICS,
  PLAN_TABLE,
  PLANS,
  SEASON_PASS,
  type Cosmetic,
  type CosmeticKind,
} from '../shop'
import { session } from '../stores/session'
import { shopTab } from '../stores/ui'
import { haptic } from '../telegram'

// Магазин — пока витрина (решение пользователя): всё с ценами, но покупки «Скоро».
// Оплату звёздами подключим вместе с самими функциями подписки — брать деньги за то, чего нет, нечестно

const TABS = [
  { value: 'plans', label: 'Подписки' },
  { value: 'boosts', label: 'Бусты' },
  { value: 'cosmetics', label: 'Косметика' },
] as const

const SUBSCRIBER_DISCOUNT = 0.2

// Свой тариф: на его карточке вместо «Оформить» — до какого числа он действует
const myPlan = computed(() => session.me!.plan)

const compare = ref(false)
const kind = ref<CosmeticKind>('frame')
const items = computed(() => COSMETICS.filter((item) => item.kind === kind.value))
const picked = ref<Cosmetic | null>(null)

function pick(item: Cosmetic) {
  haptic.tap()
  picked.value = item
}

function withDiscount(price: number): number {
  return Math.round(price * (1 - SUBSCRIBER_DISCOUNT))
}

function soon() {
  haptic.select()
}
</script>

<template>
  <main class="page">
    <header class="page-top">
      <h1 class="page-title">Магазин</h1>
    </header>
    <p class="hint intro">Цены в звёздах Telegram ⭐. Без лутбоксов и сюрпризов: всё, что продаётся, видно заранее.</p>

    <div v-jelly.soft class="segmented tabs">
      <button
        v-for="tab in TABS"
        :key="tab.value"
        type="button"
        :aria-pressed="shopTab === tab.value"
        @click="(shopTab = tab.value), haptic.select()"
      >
        {{ tab.label }}
      </button>
    </div>

    <p class="soon-strip"><span class="soon-strip__dot" aria-hidden="true" />Покупки откроются скоро — пока смотри и выбирай</p>

    <!-- Подписки -->
    <section v-if="shopTab === 'plans'" :key="'plans'" class="stack rise-in">
      <p class="card my-plan" :class="`my-plan--${myPlan.plan}`">
        <span class="hint">Твой тариф</span>
        <b v-if="myPlan.plan === 'free'">Бесплатный</b>
        <b v-else>{{ myPlan.plan === 'plus' ? 'Plus' : 'Premium' }} · до {{ formatDate(myPlan.until!) }}</b>
      </p>
      <article v-for="plan in PLANS" :key="plan.id" class="card card--lit plan" :class="`plan--${plan.id}`">
        <header class="plan__head">
          <span class="plan__name">{{ plan.name }}</span>
          <span class="plan__price"><b>{{ plan.price }}</b> ⭐<small>/ месяц</small></span>
        </header>
        <p class="hint plan__tagline">{{ plan.tagline }}</p>
        <ul class="perks">
          <li v-for="perk in plan.perks" :key="perk">{{ perk }}</li>
        </ul>
        <p v-if="myPlan.plan === plan.id" class="plan__active">Активен до {{ formatDate(myPlan.until!) }}</p>
        <button v-else class="btn btn-outline plan__buy" type="button" aria-disabled="true" @click="soon">
          Оформить {{ plan.name }} — скоро
        </button>
      </article>

      <button class="compare-toggle" type="button" :aria-expanded="compare" @click="(compare = !compare), haptic.select()">
        {{ compare ? 'Скрыть сравнение' : 'Сравнить тарифы' }}
        <span class="compare-toggle__arrow" :class="{ 'compare-toggle__arrow--up': compare }" aria-hidden="true">›</span>
      </button>
      <div v-if="compare" class="card compare">
        <table>
          <thead>
            <tr>
              <th />
              <th>Бесплатно</th>
              <th>Plus</th>
              <th class="compare__premium">Premium</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in PLAN_TABLE" :key="row.label">
              <th scope="row">{{ row.label }}</th>
              <td>{{ row.free }}</td>
              <td>{{ row.plus }}</td>
              <td>{{ row.premium }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <section class="card honest">
        <h2 class="honest__title">Честно</h2>
        <ul class="perks">
          <li>Продление раз в месяц. Отменить — в один тап в Telegram, без писем и звонков</li>
          <li>Бесплатно у всех: мэтчи, чаты, пати, жалобы и защита по возрасту — подписка их не меняет</li>
          <li>Подписка не показывает тебя тем, кому ты и так не виден</li>
        </ul>
      </section>
    </section>

    <!-- Бусты -->
    <section v-else-if="shopTab === 'boosts'" :key="'boosts'" class="stack rise-in">
      <article v-for="boost in BOOSTS" :key="boost.id" class="card boost">
        <span class="boost__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="24" height="24">
            <g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path v-if="boost.icon === 'party'" d="M12 19V5M6 11l6-6 6 6" />
              <template v-else-if="boost.icon === 'profile'">
                <circle cx="10" cy="8" r="3.5" />
                <path d="M3.5 20c.8-3.6 3.4-5.5 6.5-5.5 1.5 0 2.9.4 4 1.3M19 21v-7M16 17l3-3 3 3" />
              </template>
              <path v-else d="M12 3l9 5-9 5-9-5 9-5zM3 13l9 5 9-5M3 18l9 5 9-5" />
            </g>
          </svg>
        </span>
        <div class="boost__body">
          <b class="boost__name">{{ boost.name }}</b>
          <p class="hint boost__text">{{ boost.description }}</p>
        </div>
        <button class="price" type="button" aria-disabled="true" :aria-label="`${boost.name}: ${boost.price} звёзд, скоро`" @click="soon">
          {{ boost.price }} ⭐
        </button>
      </article>

      <p class="hint">В подписке бусты бесплатные: Plus — 1 в неделю, Premium — 3.</p>
      <section class="card honest">
        <h2 class="honest__title">Правила</h2>
        <ul class="perks">
          <li v-for="rule in BOOST_RULES" :key="rule">{{ rule }}</li>
        </ul>
      </section>
    </section>

    <!-- Косметика -->
    <section v-else :key="'cosmetics'" class="stack rise-in">
      <article class="card card--lit season">
        <p class="season__label">{{ SEASON_PASS.name }} · скоро</p>
        <b class="season__title">Сезонный пасс</b>
        <ul class="perks">
          <li v-for="point in SEASON_PASS.points" :key="point">{{ point }}</li>
        </ul>
        <p class="hint season__price">Платная дорожка — {{ SEASON_PASS.price }} ⭐ за весь сезон</p>
      </article>

      <div class="chips chips--scroll" role="tablist" aria-label="Что украсить">
        <button
          v-for="option in COSMETIC_KINDS"
          :key="option.kind"
          type="button"
          role="tab"
          class="chip"
          :class="{ 'chip--on': kind === option.kind }"
          :aria-selected="kind === option.kind"
          @click="(kind = option.kind), haptic.select()"
        >
          {{ option.label }}
        </button>
      </div>

      <div :key="kind" class="grid rise-in">
        <button v-for="item in items" :key="item.id" class="tile" type="button" @click="pick(item)">
          <CosmeticPreview :item="item" />
          <span class="tile__name">{{ item.name }}</span>
          <span class="tile__price" :class="{ 'tile__price--earn': item.price === null }">
            {{ item.price === null ? 'За активность' : `${item.price} ⭐` }}
          </span>
        </button>
      </div>
      <p class="hint">Подписчикам Plus и Premium — скидка 20%. Значки за активность не продаются — их только зарабатывают.</p>
    </section>

    <!-- Вещь крупно: как она будет выглядеть у тебя -->
    <Teleport to="body">
      <Transition name="sheet" :duration="SHEET_MS">
        <div v-if="picked" class="sheet-backdrop" @click.self="picked = null">
          <section class="sheet" role="dialog" :aria-label="picked.name">
            <div class="sheet__handle" aria-hidden="true" />
            <h2 class="sheet__title">{{ picked.name }}</h2>
            <div class="stack rise-in">
              <CosmeticPreview :item="picked" large />
              <p class="hint item-text">{{ picked.description }}</p>
              <p v-if="picked.price === null" class="item-earn">Как получить: {{ picked.earn }}</p>
              <p v-else class="item-price">
                <b>{{ picked.price }} ⭐</b>
                <span class="hint">с подпиской — {{ withDiscount(picked.price) }} ⭐</span>
              </p>
              <button v-if="picked.price !== null" class="btn btn-primary" type="button" aria-disabled="true" @click="soon">
                Купить — скоро
              </button>
            </div>
          </section>
        </div>
      </Transition>
    </Teleport>
  </main>
</template>

<style scoped>
.intro {
  margin: -8px 0 14px;
}

.tabs {
  margin-bottom: 10px;
}

/* «Скоро»: честная плашка, что купить пока нельзя */
.soon-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px;
  font-family: var(--font-display);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-2);
}

.soon-strip__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--warn);
  box-shadow: 0 0 8px var(--warn);
}

/* --- Подписки --- */

.my-plan {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin: 0;
  padding: 12px 16px;
}

.my-plan .hint {
  margin: 0;
}

.my-plan b {
  font-family: var(--font-title);
  font-weight: 400;
}

.my-plan--premium b {
  color: var(--warn);
}

.plan__active {
  margin: 16px 0 0;
  padding: 12px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-btn);
  font-family: var(--font-display);
  font-size: 13px;
  letter-spacing: 0.06em;
  text-align: center;
  text-transform: uppercase;
}

.plan--premium .plan__active {
  border-color: color-mix(in srgb, var(--warn) 50%, transparent);
  color: var(--warn);
}

.plan__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.plan__name {
  font-family: var(--font-pixel);
  font-size: 30px;
  line-height: 1;
  text-transform: uppercase;
  text-shadow: 0 0 14px rgb(var(--glow-rgb) / 0.4);
}

.plan__price {
  white-space: nowrap;
  font-size: 15px;
}

.plan__price b {
  font-family: var(--font-pixel);
  font-size: 26px;
  font-weight: 400;
}

.plan__price small {
  margin-left: 4px;
  color: var(--text-2);
  font-size: 12px;
}

.plan__tagline {
  margin: 6px 0 12px;
}

/* Premium — тёплый свет: и полоса «лампы», и имя */
.plan--premium {
  border-color: color-mix(in srgb, var(--warn) 35%, var(--line));
}

.plan--premium.card--lit::before {
  background: linear-gradient(90deg, transparent, var(--warn) 30%, var(--warn) 70%, transparent);
  box-shadow:
    0 0 12px 1px color-mix(in srgb, var(--warn) 60%, transparent),
    0 0 40px 6px color-mix(in srgb, var(--warn) 15%, transparent);
}

.plan--premium .plan__name {
  color: var(--warn);
  text-shadow: 0 0 14px color-mix(in srgb, var(--warn) 55%, transparent);
}

.perks {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 14px;
}

.perks li {
  position: relative;
  padding-left: 18px;
}

.perks li::before {
  content: '+';
  position: absolute;
  left: 0;
  top: -1px;
  font-family: var(--font-pixel);
  color: var(--text-2);
}

.plan__buy {
  width: 100%;
  margin-top: 16px;
  opacity: 0.6;
}

.compare-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 40px;
  border: 0;
  background: none;
  color: var(--text-2);
  font-family: var(--font-display);
  font-size: 12px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  cursor: pointer;
}

.compare-toggle__arrow {
  display: inline-block;
  transform: rotate(90deg);
  transition: transform 0.2s ease;
}

.compare-toggle__arrow--up {
  transform: rotate(-90deg);
}

.compare {
  padding: 8px 4px;
  overflow-x: auto;
}

.compare table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.compare th,
.compare td {
  padding: 8px 6px;
  border-bottom: 1px dashed var(--line);
  text-align: center;
  white-space: nowrap;
}

.compare tbody tr:last-child th,
.compare tbody tr:last-child td {
  border-bottom: 0;
}

.compare thead th {
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-2);
}

.compare tbody th {
  text-align: left;
  font-weight: 400;
  color: var(--text-2);
  white-space: normal;
}

.compare__premium {
  color: var(--warn) !important;
}

.honest__title {
  margin: 0 0 10px;
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-2);
}

/* --- Бусты --- */

.boost {
  display: flex;
  align-items: center;
  gap: 14px;
}

.boost__icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border: 1px solid var(--line-strong);
  border-radius: 12px;
  color: var(--lamp);
  filter: drop-shadow(0 0 6px rgb(var(--glow-rgb) / 0.45));
}

.boost__body {
  flex: 1;
  min-width: 0;
}

.boost__name {
  font-family: var(--font-title);
  font-size: 16px;
  font-weight: 400;
}

.boost__text {
  margin-top: 4px;
  font-size: 13px;
}

.price {
  flex: none;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
  background: var(--raised);
  color: var(--text);
  font-family: var(--font-pixel);
  font-size: 16px;
  white-space: nowrap;
  cursor: pointer;
}

/* --- Косметика --- */

.season__label {
  margin: 0;
  font-family: var(--font-display);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--warn);
}

.season__title {
  display: block;
  margin: 4px 0 12px;
  font-family: var(--font-pixel);
  font-size: 26px;
  font-weight: 400;
  text-transform: uppercase;
  text-shadow: 0 0 14px rgb(var(--glow-rgb) / 0.35);
}

.season__price {
  margin-top: 12px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

@media (min-width: 520px) {
  .grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.tile {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 8px 10px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--card);
  box-shadow: var(--edge-light);
  color: var(--text);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: transform 0.12s ease;
}

.tile:active {
  transform: scale(0.97);
}

.tile__name {
  padding: 0 2px;
  font-family: var(--font-title);
  font-size: 14px;
}

.tile__price {
  padding: 0 2px;
  font-family: var(--font-pixel);
  font-size: 15px;
}

.tile__price--earn {
  font-family: var(--font-display);
  font-size: 11px;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--ok);
}

.item-text {
  margin: 0;
}

.item-price {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 0;
}

.item-price b {
  font-family: var(--font-pixel);
  font-size: 26px;
  font-weight: 400;
}

.item-earn {
  margin: 0;
  color: var(--ok);
}

[aria-disabled='true'] {
  cursor: default;
}
</style>
