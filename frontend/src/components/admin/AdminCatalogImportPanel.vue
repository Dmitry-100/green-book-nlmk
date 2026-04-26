<template>
  <div class="catalog-import">
    <div class="catalog-import__header">
      <div>
        <h4>Предпросмотр CSV-правок</h4>
        <p>Файл проверяется без записи в справочник.</p>
      </div>
      <label class="catalog-import__upload" :class="{ disabled: importLoading }">
        <input
          type="file"
          accept=".csv,text/csv"
          :disabled="importLoading"
          @change="handleFileChange"
        />
        {{ importLoading ? 'Проверяем...' : 'Проверить CSV' }}
      </label>
    </div>

    <div v-if="preview" class="catalog-import__preview">
      <div class="catalog-import__stats">
        <span><strong>{{ preview.total_rows }}</strong> строк</span>
        <span><strong>{{ preview.changed_rows }}</strong> с изменениями</span>
        <span><strong>{{ preview.unchanged_rows }}</strong> без изменений</span>
        <span :class="{ 'catalog-import__danger': preview.error_rows > 0 }">
          <strong>{{ preview.error_rows }}</strong> с ошибками
        </span>
      </div>

      <div v-if="changes.length" class="catalog-import__table-wrap catalog-import__table-wrap--wide">
        <table class="catalog-import__table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Вид</th>
              <th>Поля</th>
              <th>Было</th>
              <th>Станет</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in changes" :key="`change-${row.row}-${row.id}`">
              <td>{{ row.id }}</td>
              <td>{{ row.name_ru }}</td>
              <td>{{ formatChangedFields(row.changed_fields) }}</td>
              <td>{{ formatImportDelta(row.before) }}</td>
              <td>{{ formatImportDelta(row.after) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="errors.length" class="catalog-import__table-wrap">
        <table class="catalog-import__table">
          <thead>
            <tr>
              <th>Строка</th>
              <th>ID</th>
              <th>Ошибки</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in errors" :key="`error-${row.row}-${row.id}`">
              <td>{{ row.row }}</td>
              <td>{{ row.id }}</td>
              <td>{{ row.errors.join('; ') }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="canApply" class="catalog-import__apply">
        <button
          class="catalog-import__button catalog-import__button--primary"
          type="button"
          :disabled="applyLoading"
          @click="$emit('apply')"
        >
          {{ applyLoading ? 'Применяем...' : 'Применить CSV' }}
        </button>
        <span>Будет обновлено {{ preview.changed_rows }} строк.</span>
      </div>
    </div>

    <div class="catalog-import__history" :class="{ 'catalog-import__history--loading': batchLoading }">
      <div v-if="batchLoading" class="catalog-import__loading">Загружаем историю...</div>
      <div class="catalog-import__history-header">
        <h4>История CSV-импортов</h4>
        <div class="catalog-import__history-actions">
          <select
            :value="statusFilter"
            class="catalog-import-native-select"
            @change="handleStatusSelectChange"
          >
            <option value="">Все статусы</option>
            <option value="applied">Примененные</option>
            <option value="rolled_back">Откатанные</option>
          </select>
          <button class="catalog-import__button" type="button" @click="$emit('refresh-batches')">
            Обновить
          </button>
        </div>
      </div>

      <div v-if="batches.length" class="catalog-import__table-wrap">
        <table class="catalog-import__table">
          <thead>
            <tr>
              <th>Batch</th>
              <th>Файл</th>
              <th>Дата</th>
              <th>Статус</th>
              <th>Изменений</th>
              <th><span class="sr-only">Действия</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in batches" :key="row.id">
              <td>{{ row.id }}</td>
              <td>{{ row.filename }}</td>
              <td>{{ formatDateTime(row.created_at) }}</td>
              <td>
                <span class="catalog-import-status" :class="`catalog-import-status--${row.status}`">
                  {{ batchStatusLabel(row.status) }}
                </span>
              </td>
              <td>{{ row.changed_rows }}</td>
              <td class="catalog-import__row-actions">
                <button
                  class="catalog-import__link-button"
                  type="button"
                  :disabled="batchDetailLoading === row.id"
                  @click="$emit('load-detail', row.id)"
                >
                  {{ batchDetailLoading === row.id ? 'Грузим...' : 'Детали' }}
                </button>
                <button
                  v-if="row.status === 'applied'"
                  class="catalog-import__link-button catalog-import__link-button--danger"
                  type="button"
                  :disabled="rollbackLoading === row.id"
                  @click="$emit('rollback', row)"
                >
                  {{ rollbackLoading === row.id ? 'Откат...' : 'Откатить' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="catalog-import__empty">Импортов пока нет.</div>

      <div v-if="total > pageSize" class="catalog-import__pagination">
        <button
          class="catalog-import__page"
          type="button"
          :disabled="page <= 1"
          @click="goToPage(page - 1)"
        >
          Назад
        </button>
        <button
          v-for="pageNumber in visiblePages"
          :key="pageNumber"
          class="catalog-import__page"
          :class="{ active: pageNumber === page }"
          type="button"
          @click="goToPage(pageNumber)"
        >
          {{ pageNumber }}
        </button>
        <button
          class="catalog-import__page"
          type="button"
          :disabled="page >= totalPages"
          @click="goToPage(page + 1)"
        >
          Вперед
        </button>
        <span class="catalog-import__pagination-total">Всего: {{ total }}</span>
      </div>

      <div v-if="details" class="catalog-import__details">
        <div class="catalog-import__details-title">
          Batch #{{ details.id }}: {{ details.filename }}
        </div>
        <div class="catalog-import__table-wrap catalog-import__table-wrap--wide">
          <table class="catalog-import__table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Вид</th>
                <th>Поля</th>
                <th>Было</th>
                <th>Стало</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in details.changes" :key="`detail-${row.row}-${row.id}`">
                <td>{{ row.id }}</td>
                <td>{{ row.name_ru }}</td>
                <td>{{ formatChangedFields(row.changed_fields) }}</td>
                <td>{{ formatImportDelta(row.before) }}</td>
                <td>{{ formatImportDelta(row.after) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  formatCatalogImportDelta,
  formatCatalogImportFields,
} from '../../utils/catalogImportFormatting'

type CatalogImportChange = {
  row: number
  id: number
  name_ru: string
  changed_fields: string[]
  before: Record<string, unknown>
  after: Record<string, unknown>
}

type CatalogImportRowError = {
  row: number
  id: string
  errors: string[]
}

type CatalogImportPreview = {
  total_rows: number
  changed_rows: number
  unchanged_rows: number
  error_rows: number
  changes: CatalogImportChange[]
  errors: CatalogImportRowError[]
}

type CatalogImportBatch = {
  id: number
  filename: string
  status: 'applied' | 'rolled_back'
  actor_user_id: number | null
  rolled_back_by_user_id: number | null
  total_rows: number
  changed_rows: number
  unchanged_rows: number
  error_rows: number
  applied_rows: number
  created_at: string
  rolled_back_at: string | null
}

type CatalogImportBatchDetail = CatalogImportBatch & {
  changes: CatalogImportChange[]
}

const props = defineProps<{
  preview: CatalogImportPreview | null
  importLoading: boolean
  applyLoading: boolean
  batches: CatalogImportBatch[]
  batchLoading: boolean
  batchDetailLoading: number | null
  rollbackLoading: number | null
  statusFilter: string
  page: number
  pageSize: number
  total: number
  details: CatalogImportBatchDetail | null
}>()

const emit = defineEmits<{
  preview: [options: { file: File }]
  apply: []
  'refresh-batches': []
  'update:statusFilter': [status: string]
  'status-change': []
  'page-change': [page: number]
  'load-detail': [batchId: number]
  rollback: [batch: CatalogImportBatch]
}>()

const changes = computed(() => props.preview?.changes || [])
const errors = computed(() => props.preview?.errors || [])
const canApply = computed(() =>
  Boolean(props.preview && props.preview.error_rows === 0 && props.preview.changed_rows > 0)
)
const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const visiblePages = computed(() => {
  const maxButtons = 5
  const total = totalPages.value
  const start = Math.max(1, Math.min(props.page - 2, total - maxButtons + 1))
  const end = Math.min(total, start + maxButtons - 1)
  return Array.from({ length: end - start + 1 }, (_, index) => start + index)
})

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) {
    return
  }
  emit('preview', { file })
  input.value = ''
}

function handleStatusChange(value: string) {
  emit('update:statusFilter', value)
  emit('status-change')
}

function handleStatusSelectChange(event: Event) {
  handleStatusChange((event.target as HTMLSelectElement).value)
}

function goToPage(nextPage: number) {
  const normalizedPage = Math.min(totalPages.value, Math.max(1, nextPage))
  if (normalizedPage !== props.page) {
    emit('page-change', normalizedPage)
  }
}

function formatChangedFields(fields: string[]): string {
  return formatCatalogImportFields(fields)
}

function formatImportDelta(values: Record<string, unknown>): string {
  return formatCatalogImportDelta(values)
}

function batchStatusLabel(status: string): string {
  if (status === 'applied') return 'Применен'
  if (status === 'rolled_back') return 'Откатан'
  return status
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('ru-RU')
}
</script>

<style scoped>
.catalog-import {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #E2E8EA;
}

.catalog-import__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.catalog-import__header h4,
.catalog-import__history-header h4 {
  margin: 0 0 4px;
  color: var(--teal-dark);
  font-size: 14px;
  font-weight: 700;
}

.catalog-import__header p {
  margin: 0;
  color: var(--slate-mid);
  font-size: 12px;
}

.catalog-import__upload,
.catalog-import__button,
.catalog-import__page {
  min-height: 28px;
  border: 1px solid #C9D7DA;
  border-radius: 8px;
  padding: 0 10px;
  background: #FFFFFF;
  color: var(--teal-dark);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  font-weight: 800;
}

.catalog-import__upload {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}

.catalog-import__upload input {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.catalog-import__upload:hover:not(.disabled),
.catalog-import__button:hover:not(:disabled),
.catalog-import__page:hover:not(:disabled) {
  border-color: var(--teal-accent);
  background: #F4F8F9;
}

.catalog-import__upload:focus-within,
.catalog-import__button:focus-visible,
.catalog-import__page:focus-visible,
.catalog-import__link-button:focus-visible {
  outline: 2px solid var(--teal-accent);
  outline-offset: 2px;
}

.catalog-import__upload.disabled,
.catalog-import__button:disabled,
.catalog-import__page:disabled,
.catalog-import__link-button:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.catalog-import__button--primary {
  border-color: var(--teal-accent);
  background: var(--teal-accent);
  color: #FFFFFF;
}

.catalog-import__button--primary:hover:not(:disabled) {
  background: var(--teal-dark);
  color: #FFFFFF;
}

.catalog-import__preview {
  display: grid;
  gap: 10px;
}

.catalog-import__stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.catalog-import__stats span {
  display: inline-flex;
  gap: 4px;
  align-items: baseline;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  padding: 5px 8px;
  background: #FAFBFC;
  color: var(--slate-mid);
  font-size: 12px;
}

.catalog-import__stats strong {
  color: var(--teal-dark);
  font-size: 14px;
}

.catalog-import__danger strong {
  color: var(--red-reference);
}

.catalog-import__table-wrap {
  max-height: 220px;
  overflow: auto;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  background: #FFFFFF;
}

.catalog-import__table-wrap--wide .catalog-import__table {
  min-width: 920px;
}

.catalog-import__table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
  color: var(--slate-deep, #2C3E4A);
  font-size: 12px;
}

.catalog-import__table th,
.catalog-import__table td {
  border-bottom: 1px solid #E6ECEE;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

.catalog-import__table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #F4F8F9;
  color: var(--slate-mid);
  font-size: 12px;
  font-weight: 800;
}

.catalog-import__table tbody tr:nth-child(even) {
  background: #FAFBFC;
}

.catalog-import__apply {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.catalog-import__apply span,
.catalog-import__pagination-total {
  color: var(--slate-mid);
  font-size: 12px;
}

.catalog-import__history {
  position: relative;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #E2E8EA;
}

.catalog-import__history--loading {
  opacity: 0.78;
}

.catalog-import__loading {
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

.catalog-import__history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.catalog-import__history-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.catalog-import-native-select {
  width: 150px;
  height: 28px;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  padding: 0 28px 0 10px;
  background: #fff;
  color: var(--slate-deep, #2C3E4A);
  font: inherit;
  font-size: 12px;
}

.catalog-import-native-select:focus {
  outline: none;
  border-color: var(--teal-accent, #2A7A6E);
  box-shadow: 0 0 0 2px rgba(42, 122, 110, 0.12);
}

.catalog-import-status {
  border-radius: 8px;
  padding: 1px 7px;
  font-size: 12px;
  line-height: 1.5;
  font-weight: 600;
}

.catalog-import-status--applied {
  background: #FFF3D6;
  color: #8A5A00;
}

.catalog-import-status--rolled_back {
  background: #EAF3F5;
  color: var(--teal-dark);
}

.catalog-import__row-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
  white-space: nowrap;
}

.catalog-import__link-button {
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--teal-accent);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  font-weight: 800;
  min-height: 26px;
  padding: 0 6px;
}

.catalog-import__link-button:hover:not(:disabled) {
  background: #EAF3F5;
  color: var(--teal-dark);
}

.catalog-import__link-button--danger {
  color: #A33A3A;
}

.catalog-import__link-button--danger:hover:not(:disabled) {
  background: #F9E7E7;
  color: #8F2727;
}

.catalog-import__empty {
  color: var(--slate-mid);
  font-size: 13px;
  padding: 8px 0;
}

.catalog-import__pagination {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
}

.catalog-import__page.active {
  border-color: var(--teal-accent);
  background: var(--teal-accent);
  color: #FFFFFF;
}

.catalog-import__details {
  margin-top: 10px;
}

.catalog-import__details-title {
  color: var(--teal-dark);
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 8px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 760px) {
  .catalog-import__header,
  .catalog-import__history-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .catalog-import__pagination {
    justify-content: flex-start;
    overflow-x: auto;
    padding-bottom: 4px;
  }
}
</style>
