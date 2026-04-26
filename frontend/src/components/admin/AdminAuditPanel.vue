<template>
  <div>
    <div class="admin-section__header">
      <h2>Журнал действий</h2>
      <div class="audit-header-actions">
        <button
          class="audit-button"
          type="button"
          :disabled="opsLoading || opsAlertsLoading"
          @click="$emit('refresh-ops')"
        >
          {{ opsLoading || opsAlertsLoading ? 'Обновляем...' : 'Обновить сводку' }}
        </button>
        <button class="audit-button" type="button" @click="$emit('reload-audit')">
          Обновить журнал
        </button>
      </div>
    </div>

    <AdminOpsPanel
      :summary="opsSummary"
      :loading="opsLoading"
      :alerts="opsAlerts"
      :alerts-loading="opsAlertsLoading"
      :alert-status="opsAlertStatus"
    />

    <div class="audit-filters">
      <input
        v-model="auditFilters.action"
        class="audit-native-input"
        placeholder="action (например, species.create)"
      />
      <input
        v-model="auditFilters.target_type"
        class="audit-native-input"
        placeholder="target_type (species, observation...)"
      />
      <input
        v-model="auditFilters.actor_user_id"
        class="audit-native-input"
        placeholder="actor_user_id"
      />
      <select v-model="auditFilters.outcome" class="audit-native-select">
        <option value="">outcome</option>
        <option value="success">success</option>
        <option value="noop">noop</option>
        <option value="failed">failed</option>
      </select>
      <input
        v-model="auditFilters.request_id"
        class="audit-native-input"
        placeholder="request_id"
      />
    </div>
    <div class="audit-actions">
      <div class="audit-maintenance">
        <span class="audit-maintenance__label">Ретеншн (дни)</span>
        <input
          class="audit-retention-input"
          type="number"
          :value="auditRetentionDays"
          :min="1"
          :max="36500"
          @input="onRetentionDaysInput"
        />
        <button
          class="audit-button"
          type="button"
          :disabled="auditPurgeLoading"
          @click="$emit('preview-purge')"
        >
          {{ auditPurgeLoading ? 'Проверяем...' : 'Проверить очистку' }}
        </button>
        <button
          class="audit-button audit-button--danger"
          type="button"
          :disabled="auditPurgeLoading"
          @click="$emit('confirm-purge')"
        >
          {{ auditPurgeLoading ? 'Очищаем...' : 'Очистить старые' }}
        </button>
      </div>
      <button class="audit-button" type="button" @click="$emit('reset-filters')">
        Сбросить фильтры
      </button>
      <button
        class="audit-button audit-button--primary"
        type="button"
        :disabled="auditLoading"
        @click="$emit('apply-filters')"
      >
        {{ auditLoading ? 'Применяем...' : 'Применить' }}
      </button>
    </div>

    <div class="audit-table-wrap" :class="{ 'audit-table-wrap--loading': auditLoading }">
      <div v-if="auditLoading" class="audit-table-loading">Загружаем журнал...</div>
      <table class="audit-table">
        <thead>
          <tr>
            <th>Время</th>
            <th>Action</th>
            <th>Actor</th>
            <th>Target</th>
            <th>Outcome</th>
            <th>Details</th>
            <th>Request ID</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in auditEvents" :key="row.id">
            <td>{{ formatDateTime(row.created_at) }}</td>
            <td>{{ row.action }}</td>
            <td>{{ row.actor_user_id ?? '—' }}</td>
            <td>{{ row.target_type }}#{{ row.target_id ?? '—' }}</td>
            <td>{{ row.outcome }}</td>
            <td><span class="audit-details">{{ formatDetails(row.details) }}</span></td>
            <td><span class="audit-request-id">{{ row.request_id || '—' }}</span></td>
          </tr>
          <tr v-if="auditEvents.length === 0">
            <td class="audit-table__empty" colspan="7">Событий не найдено.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="auditTotal > auditPageSize" class="audit-pagination">
      <button
        class="audit-page-button"
        type="button"
        :disabled="auditPage <= 1"
        @click="goToAuditPage(auditPage - 1)"
      >
        Назад
      </button>
      <button
        v-for="pageNumber in visibleAuditPages"
        :key="pageNumber"
        class="audit-page-button"
        :class="{ active: pageNumber === auditPage }"
        type="button"
        @click="goToAuditPage(pageNumber)"
      >
        {{ pageNumber }}
      </button>
      <button
        class="audit-page-button"
        type="button"
        :disabled="auditPage >= auditTotalPages"
        @click="goToAuditPage(auditPage + 1)"
      >
        Вперед
      </button>
      <span class="audit-pagination__total">Всего: {{ auditTotal }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AdminOpsPanel from './AdminOpsPanel.vue'
import type { AuditEvent, OpsAlert } from '../../composables/admin/useAdminAuditOps'

type AuditFilters = {
  action: string
  target_type: string
  actor_user_id: string
  outcome: string
  request_id: string
}

const props = defineProps<{
  auditEvents: AuditEvent[]
  auditLoading: boolean
  auditPurgeLoading: boolean
  auditRetentionDays: number
  auditPage: number
  auditPageSize: number
  auditTotal: number
  auditFilters: AuditFilters
  opsSummary: any | null
  opsLoading: boolean
  opsAlerts: OpsAlert[]
  opsAlertsLoading: boolean
  opsAlertStatus: 'ok' | 'alert'
}>()

const emit = defineEmits<{
  'refresh-ops': []
  'reload-audit': []
  'preview-purge': []
  'confirm-purge': []
  'apply-filters': []
  'reset-filters': []
  'page-change': [page: number]
  'update:auditRetentionDays': [days: number]
}>()

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('ru-RU')
}

function formatDetails(details: Record<string, unknown> | null | undefined): string {
  if (!details || Object.keys(details).length === 0) {
    return '—'
  }
  const payload = JSON.stringify(details)
  if (payload.length <= 120) {
    return payload
  }
  return `${payload.slice(0, 117)}...`
}

const auditTotalPages = computed(() => Math.max(1, Math.ceil(props.auditTotal / props.auditPageSize)))
const visibleAuditPages = computed(() => {
  const maxButtons = 5
  const total = auditTotalPages.value
  const start = Math.max(1, Math.min(props.auditPage - 2, total - maxButtons + 1))
  const end = Math.min(total, start + maxButtons - 1)
  return Array.from({ length: end - start + 1 }, (_, index) => start + index)
})

function goToAuditPage(nextPage: number) {
  const normalizedPage = Math.min(auditTotalPages.value, Math.max(1, nextPage))
  if (normalizedPage !== props.auditPage) {
    emit('page-change', normalizedPage)
  }
}

function onRetentionDaysInput(event: Event) {
  const input = event.target as HTMLInputElement
  const value = Number(input.value)
  if (!Number.isFinite(value)) {
    return
  }
  emit('update:auditRetentionDays', Math.min(36500, Math.max(1, Math.trunc(value))))
}
</script>

<style scoped>
.admin-section__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.audit-header-actions { display: flex; gap: 8px; }
.audit-filters { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; margin-bottom: 10px; }
.audit-native-input,
.audit-native-select {
  width: 100%;
  min-width: 0;
  height: 32px;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  padding: 0 28px 0 10px;
  background: #fff;
  color: var(--slate-deep, #2C3E4A);
  font: inherit;
  font-size: 12px;
}
.audit-retention-input {
  width: 92px;
  height: 32px;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  color: var(--slate-deep, #2C3E4A);
  font: inherit;
  font-size: 12px;
  padding: 0 8px;
}
.audit-native-input:focus,
.audit-retention-input:focus,
.audit-native-select:focus {
  outline: none;
  border-color: var(--teal-accent, #2A7A6E);
  box-shadow: 0 0 0 2px rgba(42, 122, 110, 0.12);
}
.audit-button {
  border: 1px solid #C9D7DA;
  border-radius: 8px;
  background: #fff;
  color: var(--slate-deep, #2C3E4A);
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  min-height: 32px;
  padding: 0 12px;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}
.audit-button:hover:not(:disabled) {
  border-color: var(--teal-accent, #2A7A6E);
  color: var(--teal-dark, #1E5F57);
}
.audit-button:focus-visible {
  outline: 2px solid var(--teal-accent, #2A7A6E);
  outline-offset: 2px;
}
.audit-button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
.audit-button--primary {
  border-color: var(--teal, #2F7D62);
  background: var(--teal, #2F7D62);
  color: #fff;
}
.audit-button--primary:hover:not(:disabled) {
  background: var(--teal-dark, #1E5F57);
  color: #fff;
}
.audit-button--danger {
  border-color: #B42318;
  color: #B42318;
}
.audit-button--danger:hover:not(:disabled) {
  background: #B42318;
  color: #fff;
}
.audit-actions { display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 12px; }
.audit-maintenance { display: flex; align-items: center; gap: 8px; margin-right: auto; }
.audit-maintenance__label { font-size: 12px; color: var(--slate-mid); }
.audit-table-wrap {
  position: relative;
  max-height: 520px;
  overflow: auto;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  background: #fff;
}
.audit-table-wrap--loading {
  opacity: 0.78;
}
.audit-table-loading {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(251, 252, 253, 0.74);
  color: var(--teal-dark);
  font-size: 13px;
  font-weight: 800;
}
.audit-table {
  width: 100%;
  min-width: 980px;
  border-collapse: collapse;
  color: var(--slate-deep, #2C3E4A);
  font-size: 12px;
}
.audit-table th,
.audit-table td {
  border-bottom: 1px solid #E6ECEE;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}
.audit-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #F4F8F9;
  color: var(--slate-mid);
  font-size: 12px;
  font-weight: 800;
}
.audit-table tbody tr:nth-child(even) {
  background: #FAFBFC;
}
.audit-table__empty {
  color: var(--slate-mid);
  padding: 18px 10px;
  text-align: center;
}
.audit-details { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; color: var(--slate-mid); }
.audit-request-id { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; color: var(--slate-mid); }
.audit-pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 12px;
}
.audit-page-button {
  min-height: 28px;
  border: 1px solid #C9D7DA;
  border-radius: 8px;
  padding: 0 10px;
  background: #fff;
  color: var(--slate-deep, #2C3E4A);
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
}
.audit-page-button:hover:not(:disabled) {
  border-color: var(--teal-accent, #2A7A6E);
  color: var(--teal-dark, #1E5F57);
}
.audit-page-button:focus-visible {
  outline: 2px solid var(--teal-accent, #2A7A6E);
  outline-offset: 2px;
}
.audit-page-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.audit-page-button.active {
  border-color: var(--teal-accent, #2A7A6E);
  background: var(--teal-accent, #2A7A6E);
  color: #fff;
}
.audit-pagination__total {
  color: var(--slate-mid);
  font-size: 12px;
  margin-left: 4px;
}
@media (max-width: 1080px) {
  .audit-filters { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 920px) {
  .audit-actions {
    flex-wrap: wrap;
  }
  .audit-maintenance {
    width: 100%;
    flex-wrap: wrap;
  }
  .audit-pagination {
    justify-content: flex-start;
    overflow-x: auto;
    padding-bottom: 4px;
  }
}
</style>
