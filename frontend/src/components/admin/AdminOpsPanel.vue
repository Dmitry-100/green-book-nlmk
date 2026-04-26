<template>
  <div>
    <div class="ops-summary" :class="{ 'ops-summary--loading': loading }">
      <div v-if="loading" class="ops-loading">Обновляем сводку...</div>
      <div class="ops-card">
        <div class="ops-card__title">Каталог</div>
        <div class="ops-card__value">{{ summary?.catalog?.species_total ?? 0 }}</div>
        <div class="ops-card__hint">видов в справочнике</div>
      </div>
      <div
        class="ops-card"
        :class="{ 'ops-card--warning': (summary?.catalog?.latin_name_needs_review ?? 0) > 0 }"
      >
        <div class="ops-card__title">Латынь</div>
        <div class="ops-card__value">
          {{ summary?.catalog?.latin_name_exact_species ?? 0 }}/{{ summary?.catalog?.species_total ?? 0 }}
        </div>
        <div class="ops-card__hint">
          {{ summary?.catalog?.latin_name_needs_review ?? 0 }} требуют уточнения
        </div>
      </div>
      <div class="ops-card">
        <div class="ops-card__title">Очередь</div>
        <div class="ops-card__value">{{ summary?.pipeline?.on_review ?? 0 }}</div>
        <div class="ops-card__hint">на проверке</div>
      </div>
      <div class="ops-card">
        <div class="ops-card__title">Инциденты</div>
        <div class="ops-card__value">{{ summary?.incidents?.open_incidents ?? 0 }}</div>
        <div class="ops-card__hint">открытых</div>
      </div>
      <div class="ops-card">
        <div class="ops-card__title">Аудит 24ч</div>
        <div class="ops-card__value">{{ summary?.audit?.events_last_24h ?? 0 }}</div>
        <div class="ops-card__hint">событий</div>
      </div>
      <div class="ops-card">
        <div class="ops-card__title">Ошибки API</div>
        <div class="ops-card__value">{{ summary?.metrics?.error_rate_percent ?? 0 }}%</div>
        <div class="ops-card__hint">error rate</div>
      </div>
      <div class="ops-card">
        <div class="ops-card__title">API p95</div>
        <div class="ops-card__value">{{ formatMs(summary?.metrics?.p95_duration_ms) }}</div>
        <div class="ops-card__hint">хвост latency</div>
      </div>
      <div class="ops-card">
        <div class="ops-card__title">API p99</div>
        <div class="ops-card__value">{{ formatMs(summary?.metrics?.p99_duration_ms) }}</div>
        <div class="ops-card__hint">редкие пики</div>
      </div>
    </div>

    <div class="ops-alerts" :class="{ 'ops-alerts--loading': alertsLoading }">
      <div v-if="alertsLoading" class="ops-loading">Проверяем сигналы...</div>
      <div class="ops-alerts__header">
        <span class="ops-alerts__title">Пороговые оповещения</span>
        <span class="ops-status" :class="`ops-status--${alertStatus}`">
          {{ alertStatus === 'alert' ? 'Есть сигналы' : 'Норма' }}
        </span>
      </div>
      <div v-if="alerts.length === 0" class="ops-alerts__empty">
        Активных сигналов нет.
      </div>
      <div v-else class="ops-alerts__list">
        <div v-for="item in alerts" :key="item.code" class="ops-alert-item">
          <div class="ops-alert-item__message">{{ item.message }}</div>
          <div class="ops-alert-item__meta">
            <span class="ops-alert-item__code">{{ item.code }}</span>
            <span class="ops-alert-item__values">факт {{ item.value }} / порог {{ item.threshold }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
type OpsAlert = {
  code: string
  message: string
  value: number
  threshold: number
}

type OpsSummary = {
  catalog?: {
    species_total?: number
    latin_name_exact_species?: number
    latin_name_needs_review?: number
  }
  pipeline?: {
    on_review?: number
  }
  incidents?: {
    open_incidents?: number
  }
  audit?: {
    events_last_24h?: number
  }
  metrics?: {
    error_rate_percent?: number
    p95_duration_ms?: number
    p99_duration_ms?: number
  }
}

defineProps<{
  summary: OpsSummary | null
  loading: boolean
  alerts: OpsAlert[]
  alertsLoading: boolean
  alertStatus: 'ok' | 'alert'
}>()

function formatMs(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '0 мс'
  }
  return `${Math.round(value)} мс`
}
</script>

<style scoped>
.ops-summary {
  position: relative;
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.ops-summary--loading,
.ops-alerts--loading {
  opacity: 0.78;
}

.ops-loading {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(251, 252, 253, 0.76);
  color: var(--teal-dark);
  font-size: 13px;
  font-weight: 800;
}

.ops-card {
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  padding: 10px 12px;
  background: #FAFBFC;
}

.ops-card--warning {
  border-color: #E0B15A;
  background: #FFF9EA;
}

.ops-card__title {
  font-size: 12px;
  color: var(--slate-mid);
  margin-bottom: 4px;
}

.ops-card__value {
  font-size: 18px;
  font-weight: 700;
  color: var(--teal-dark);
  line-height: 1.1;
}

.ops-card__hint {
  font-size: 11px;
  color: var(--slate-mid);
  margin-top: 2px;
}

.ops-alerts {
  position: relative;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  background: #FBFCFD;
  padding: 10px 12px;
  margin-bottom: 12px;
}

.ops-alerts__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.ops-alerts__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--teal-dark);
}

.ops-status {
  border-radius: 8px;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.5;
}

.ops-status--ok {
  background: rgba(42, 122, 110, 0.12);
  color: var(--teal-dark);
}

.ops-status--alert {
  background: rgba(229, 57, 53, 0.12);
  color: #B3261E;
}

.ops-alerts__empty {
  font-size: 13px;
  color: var(--slate-mid);
}

.ops-alerts__list {
  display: grid;
  gap: 8px;
}

.ops-alert-item {
  border: 1px solid #E2E8EA;
  border-radius: 8px;
  background: var(--white);
  padding: 8px 10px;
}

.ops-alert-item__message {
  font-size: 13px;
  color: var(--teal-dark);
  line-height: 1.3;
}

.ops-alert-item__meta {
  margin-top: 4px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.ops-alert-item__code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11px;
  color: var(--teal-dark);
}

.ops-alert-item__values {
  font-size: 11px;
  color: var(--slate-mid);
}

@media (max-width: 1080px) {
  .ops-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
