<template>
  <div>
    <div class="admin-species-filters">
      <div class="admin-search-field">
        <input
          v-model="filters.search"
          class="admin-native-input"
          placeholder="Поиск по названию или латыни"
          @input="$emit('search-input')"
        />
        <button
          v-if="filters.search"
          class="admin-search-field__clear"
          type="button"
          aria-label="Очистить поиск"
          @click="clearSearch"
        >
          x
        </button>
      </div>
      <select v-model="filters.group" class="admin-native-select" @change="$emit('apply-filters')">
        <option value="">Группа</option>
        <option value="plants">Растения</option>
        <option value="fungi">Грибы</option>
        <option value="insects">Насекомые</option>
        <option value="herpetofauna">Герпетофауна</option>
        <option value="birds">Птицы</option>
        <option value="mammals">Млекопитающие</option>
      </select>
      <select v-model="filters.category" class="admin-native-select" @change="$emit('apply-filters')">
        <option value="">Категория</option>
        <option value="ruderal">Рудеральный</option>
        <option value="typical">Типичный</option>
        <option value="rare">Редкий</option>
        <option value="red_book">Красная книга</option>
        <option value="synanthropic">Синантроп</option>
      </select>
      <select v-model="filters.quality_gap" class="admin-native-select" @change="$emit('quality-gap-change')">
        <option value="">Пробел</option>
        <option value="missing_photo">Без фото</option>
        <option value="missing_description">Без описания</option>
        <option value="short_description">Короткое описание</option>
        <option value="missing_audio">Без аудио</option>
      </select>
      <label class="admin-species-filters__checkbox">
        <input
          type="checkbox"
          :checked="filters.has_audio"
          @change="onHasAudioChange"
        />
        С голосом
      </label>
      <button class="admin-filter-button" type="button" @click="$emit('reset-filters')">
        Сбросить
      </button>
      <span class="admin-species-filters__meta">
        Найдено: {{ total }}
        <template v-if="total > pageSize">, страница {{ page }}</template>
      </span>
    </div>

    <div class="admin-species-table-wrap">
      <table class="admin-species-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Название (RU)</th>
            <th>Латинское</th>
            <th>Группа</th>
            <th>Категория</th>
            <th>Ядовит</th>
            <th>Пробелы</th>
            <th><span class="sr-only">Действия</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in species" :key="row.id">
            <td class="admin-species-table__id">{{ row.id }}</td>
            <td>{{ row.name_ru }}</td>
            <td class="admin-species-table__latin">{{ row.name_latin }}</td>
            <td>{{ groupLabel(row.group) }}</td>
            <td>{{ categoryLabel(row.category) }}</td>
            <td class="admin-species-table__poison">{{ row.is_poisonous ? '⚠️' : '' }}</td>
            <td>
              <div class="admin-species-quality">
                <span
                  v-for="badge in buildSpeciesAdminQualityBadges(row)"
                  :key="badge.code"
                  class="admin-species-quality__badge"
                  :class="`admin-species-quality__badge--${badge.type}`"
                >
                  {{ badge.label }}
                </span>
                <span v-if="buildSpeciesAdminQualityBadges(row).length === 0" class="admin-species-quality__ok">
                  заполнено
                </span>
              </div>
            </td>
            <td class="admin-species-table__actions">
              <button class="admin-table-action admin-table-action--primary" type="button" @click="$emit('edit', row)">
                Править
              </button>
              <button class="admin-table-action admin-table-action--danger" type="button" @click="$emit('delete', row.id)">
                Удалить
              </button>
            </td>
          </tr>
          <tr v-if="species.length === 0">
            <td class="admin-species-table__empty" colspan="8">Виды не найдены.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="total > pageSize" class="admin-species-pagination">
      <button
        class="admin-page-button"
        type="button"
        :disabled="page <= 1"
        @click="goToPage(page - 1)"
      >
        Назад
      </button>
      <button
        v-for="pageNumber in visiblePages"
        :key="pageNumber"
        class="admin-page-button"
        :class="{ active: pageNumber === page }"
        type="button"
        @click="goToPage(pageNumber)"
      >
        {{ pageNumber }}
      </button>
      <button
        class="admin-page-button"
        type="button"
        :disabled="page >= totalPages"
        @click="goToPage(page + 1)"
      >
        Вперед
      </button>
      <span class="admin-species-pagination__total">Всего: {{ total }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  buildSpeciesAdminQualityBadges,
  type AdminSpeciesListFilters,
  type AdminSpeciesRow,
} from '../../utils/speciesAdminForm'

const props = defineProps<{
  filters: AdminSpeciesListFilters
  species: AdminSpeciesRow[]
  total: number
  page: number
  pageSize: number
}>()

const emit = defineEmits<{
  'search-input': []
  'apply-filters': []
  'quality-gap-change': []
  'has-audio-change': []
  'reset-filters': []
  'page-change': [page: number]
  edit: [row: AdminSpeciesRow]
  delete: [id: number]
}>()

const GROUP_LABELS: Record<string, string> = {
  plants: 'Растения',
  fungi: 'Грибы',
  insects: 'Насекомые',
  herpetofauna: 'Герпетофауна',
  birds: 'Птицы',
  mammals: 'Млекопитающие',
}

const CATEGORY_LABELS: Record<string, string> = {
  ruderal: 'Рудеральный',
  typical: 'Типичный',
  rare: 'Редкий',
  red_book: 'Красная книга',
  synanthropic: 'Синантроп',
}

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

const visiblePages = computed(() => {
  const maxButtons = 5
  const total = totalPages.value
  const start = Math.max(1, Math.min(props.page - 2, total - maxButtons + 1))
  const end = Math.min(total, start + maxButtons - 1)
  return Array.from({ length: end - start + 1 }, (_, index) => start + index)
})

function groupLabel(group: string): string {
  return GROUP_LABELS[group] || group
}

function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] || category
}

function clearSearch() {
  props.filters.search = ''
  emit('apply-filters')
}

function goToPage(nextPage: number) {
  const normalizedPage = Math.min(totalPages.value, Math.max(1, nextPage))
  if (normalizedPage !== props.page) {
    emit('page-change', normalizedPage)
  }
}

function onHasAudioChange(event: Event) {
  props.filters.has_audio = (event.target as HTMLInputElement).checked
  emit('has-audio-change')
}
</script>

<style scoped>
.admin-species-filters {
  display: grid;
  grid-template-columns: minmax(220px, 1.4fr) minmax(140px, 1fr) minmax(150px, 1fr) minmax(150px, 1fr) auto auto auto;
  gap: 8px;
  align-items: center;
  margin: 14px 0;
  padding: 10px;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  background: #FAFBFC;
}

.admin-species-filters__checkbox {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--slate-deep, #2C3E4A);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.admin-species-filters__checkbox input {
  accent-color: var(--teal-accent, #2A7A6E);
}

.admin-search-field {
  position: relative;
  min-width: 0;
}

.admin-native-input,
.admin-native-select {
  width: 100%;
  min-width: 0;
  height: 28px;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  padding: 0 28px 0 10px;
  background: #fff;
  color: var(--slate-deep, #2C3E4A);
  font: inherit;
  font-size: 12px;
}

.admin-native-input {
  padding-right: 30px;
}

.admin-search-field__clear {
  position: absolute;
  top: 50%;
  right: 5px;
  width: 20px;
  height: 20px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--slate-mid, #6B7C86);
  cursor: pointer;
  transform: translateY(-50%);
}

.admin-search-field__clear:hover {
  background: #EAF3F5;
  color: var(--teal-dark, #1E5F57);
}

.admin-filter-button,
.admin-page-button,
.admin-table-action {
  border: 1px solid #C9D7DA;
  border-radius: 8px;
  background: #fff;
  color: var(--slate-deep, #2C3E4A);
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  min-height: 28px;
  padding: 0 10px;
}

.admin-filter-button:hover,
.admin-page-button:hover:not(:disabled),
.admin-table-action:hover {
  border-color: var(--teal-accent, #2A7A6E);
  color: var(--teal-dark, #1E5F57);
}

.admin-filter-button:focus-visible,
.admin-page-button:focus-visible,
.admin-table-action:focus-visible,
.admin-search-field__clear:focus-visible {
  outline: 2px solid var(--teal-accent, #2A7A6E);
  outline-offset: 2px;
}

.admin-page-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.admin-page-button.active {
  border-color: var(--teal-accent, #2A7A6E);
  background: var(--teal-accent, #2A7A6E);
  color: #fff;
}

.admin-native-select:focus {
  outline: none;
  border-color: var(--teal-accent, #2A7A6E);
  box-shadow: 0 0 0 2px rgba(42, 122, 110, 0.12);
}

.admin-native-input:focus {
  outline: none;
  border-color: var(--teal-accent, #2A7A6E);
  box-shadow: 0 0 0 2px rgba(42, 122, 110, 0.12);
}

.admin-species-filters__meta {
  font-size: 12px;
  color: var(--slate-mid);
  white-space: nowrap;
}

.admin-species-table-wrap {
  max-height: 500px;
  overflow: auto;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
}

.admin-species-table {
  width: 100%;
  min-width: 980px;
  border-collapse: collapse;
  background: #fff;
  color: var(--slate-deep, #2C3E4A);
  font-size: 13px;
}

.admin-species-table th,
.admin-species-table td {
  border-bottom: 1px solid #E6ECEE;
  padding: 9px 10px;
  text-align: left;
  vertical-align: top;
}

.admin-species-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #F4F8F9;
  color: var(--slate-mid, #6B7C86);
  font-size: 12px;
  font-weight: 800;
}

.admin-species-table tbody tr:nth-child(even) {
  background: #FAFBFC;
}

.admin-species-table__id,
.admin-species-table__poison {
  width: 60px;
  white-space: nowrap;
}

.admin-species-table__latin {
  font-style: italic;
}

.admin-species-table__actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
  white-space: nowrap;
}

.admin-table-action {
  min-height: 26px;
  padding: 0 8px;
}

.admin-table-action--primary {
  color: var(--teal-dark, #1E5F57);
}

.admin-table-action--danger {
  color: #A33A3A;
}

.admin-table-action--danger:hover {
  border-color: #C76969;
  color: #8F2727;
}

.admin-species-table__empty {
  color: var(--slate-mid, #6B7C86);
  padding: 18px 10px;
  text-align: center;
}

.admin-species-quality {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}

.admin-species-quality__badge {
  border-radius: 8px;
  padding: 1px 7px;
  font-size: 12px;
  line-height: 1.5;
  font-weight: 600;
}

.admin-species-quality__badge--warning {
  background: #FFF3D6;
  color: #8A5A00;
}

.admin-species-quality__badge--info {
  background: #EAF3F5;
  color: var(--teal-dark);
}

.admin-species-quality__ok {
  color: var(--slate-mid);
  font-size: 12px;
}

.admin-species-pagination {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
  align-items: center;
  margin-top: 12px;
}

.admin-species-pagination__total {
  color: var(--slate-mid, #6B7C86);
  font-size: 12px;
  margin-left: 4px;
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

@media (max-width: 1080px) {
  .admin-species-filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .admin-species-filters {
    grid-template-columns: 1fr;
  }

  .admin-species-pagination {
    justify-content: flex-start;
    overflow-x: auto;
    padding-bottom: 4px;
  }
}
</style>
