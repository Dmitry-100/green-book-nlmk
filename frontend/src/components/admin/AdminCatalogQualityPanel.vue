<template>
  <div class="catalog-quality" :class="{ 'catalog-quality--loading': loading }">
    <div v-if="loading" class="catalog-quality__loading">Обновляем проверку...</div>
    <div class="catalog-quality__header">
      <div>
        <h3>Проверка латинских названий</h3>
        <p>Родовые и семейные записи лучше уточнять по первичным источникам.</p>
      </div>
      <div class="catalog-quality__actions">
        <button
          class="catalog-quality__button"
          type="button"
          :disabled="exportLoading"
          @click="$emit('export-all')"
        >
          {{ exportLoading ? 'Готовим...' : 'Скачать CSV' }}
        </button>
        <button
          class="catalog-quality__button"
          type="button"
          :disabled="!activeGap"
          @click="$emit('export-gap')"
        >
          CSV очереди
        </button>
        <button class="catalog-quality__button" type="button" @click="$emit('refresh')">Обновить</button>
      </div>
    </div>
    <div class="catalog-quality__stats">
      <span>
        <strong>{{ quality?.latin_name_exact_species ?? 0 }}/{{ quality?.species_total ?? 0 }}</strong>
        точных
      </span>
      <span>
        <strong>{{ quality?.latin_name_needs_review ?? 0 }}</strong>
        на проверку
      </span>
      <span :class="{ 'catalog-quality__danger': (quality?.latin_name_suspicious_chars ?? 0) > 0 }">
        <strong>{{ quality?.latin_name_suspicious_chars ?? 0 }}</strong>
        с подозрительными символами
      </span>
    </div>
    <div class="catalog-quality__gap-actions">
      <button
        v-for="item in gapItems"
        :key="item.code"
        type="button"
        class="catalog-quality__gap"
        :class="{
          active: activeGap === item.code,
          'catalog-quality__gap--empty': item.count === 0,
        }"
        @click="$emit('apply-gap', item.code)"
      >
        <strong>{{ item.count }}</strong>
        {{ item.label.toLowerCase() }}
      </button>
    </div>
    <div v-if="groups.length" class="catalog-quality__groups">
      <span v-for="item in groups" :key="item.group">
        {{ groupLabel(item.group) }}: {{ item.total }}
      </span>
    </div>
    <div v-if="candidates.length" class="catalog-quality__table-wrap">
      <table class="catalog-quality__table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Название</th>
            <th>Латынь</th>
            <th>Группа</th>
            <th><span class="sr-only">Действия</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in candidates" :key="row.id">
            <td>{{ row.id }}</td>
            <td>{{ row.name_ru }}</td>
            <td class="catalog-quality__latin">{{ row.name_latin }}</td>
            <td>{{ groupLabel(row.group) }}</td>
            <td>
              <router-link class="catalog-quality__link" :to="`/species/${row.id}`">Открыть</router-link>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="catalog-quality__empty">Нет записей на проверку.</div>

    <slot />
  </div>
</template>

<script setup lang="ts">
type CatalogQuality = {
  species_total?: number
  latin_name_exact_species?: number
  latin_name_needs_review?: number
  latin_name_suspicious_chars?: number
}

type CatalogQualityGapItem = {
  code: string
  label: string
  count: number
}

type CatalogQualityGroup = {
  group: string
  total: unknown
}

type CatalogQualityCandidate = {
  id: number
  name_ru: string
  name_latin: string
  group: string
}

defineProps<{
  quality: CatalogQuality | null
  loading: boolean
  exportLoading: boolean
  activeGap: string
  gapItems: CatalogQualityGapItem[]
  groups: CatalogQualityGroup[]
  candidates: CatalogQualityCandidate[]
}>()

defineEmits<{
  'export-all': []
  'export-gap': []
  refresh: []
  'apply-gap': [code: string]
}>()

const GROUP_LABELS: Record<string, string> = {
  plants: 'Растения',
  fungi: 'Грибы',
  insects: 'Насекомые',
  herpetofauna: 'Герпетофауна',
  birds: 'Птицы',
  mammals: 'Млекопитающие',
}

function groupLabel(group: string): string {
  return GROUP_LABELS[group] || group
}
</script>

<style scoped>
.catalog-quality {
  position: relative;
  margin-bottom: 18px;
  padding: 14px;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  background: #FBFCFD;
}

.catalog-quality--loading {
  opacity: 0.78;
}

.catalog-quality__loading {
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

.catalog-quality__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}

.catalog-quality__header h3 {
  margin: 0 0 4px;
  color: var(--teal-dark);
  font-size: 16px;
}

.catalog-quality__header p {
  margin: 0;
  color: var(--slate-mid);
  font-size: 13px;
}

.catalog-quality__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.catalog-quality__button {
  min-height: 28px;
  border: 1px solid #C9D7DA;
  border-radius: 8px;
  padding: 0 10px;
  background: #FFFFFF;
  color: var(--teal-dark);
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
}

.catalog-quality__button:hover:not(:disabled) {
  border-color: var(--teal-accent);
  background: #F4F8F9;
}

.catalog-quality__button:focus-visible,
.catalog-quality__gap:focus-visible {
  outline: 2px solid var(--teal-accent);
  outline-offset: 2px;
}

.catalog-quality__button:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.catalog-quality__stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.catalog-quality__stats span {
  display: inline-flex;
  gap: 4px;
  align-items: baseline;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  padding: 5px 8px;
  font-size: 12px;
  color: var(--slate-mid);
  background: #FFFFFF;
}

.catalog-quality__stats strong {
  color: var(--teal-dark);
  font-size: 14px;
}

.catalog-quality__gap-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 10px;
}

.catalog-quality__gap {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  padding: 5px 8px;
  background: #FFFFFF;
  color: var(--slate-mid);
  font-size: 12px;
  cursor: pointer;
}

.catalog-quality__gap strong {
  color: var(--teal-dark);
  font-size: 14px;
}

.catalog-quality__gap.active {
  border-color: var(--teal-accent);
  background: rgba(42, 122, 110, 0.10);
  color: var(--teal-dark);
}

.catalog-quality__gap--empty {
  opacity: 0.62;
}

.catalog-quality__danger strong {
  color: var(--red-reference);
}

.catalog-quality__groups {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.catalog-quality__table-wrap {
  max-height: 260px;
  overflow: auto;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  background: #FFFFFF;
}

.catalog-quality__table {
  width: 100%;
  min-width: 620px;
  border-collapse: collapse;
  color: var(--slate-deep, #2C3E4A);
  font-size: 13px;
}

.catalog-quality__table th,
.catalog-quality__table td {
  border-bottom: 1px solid #E6ECEE;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

.catalog-quality__table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #F4F8F9;
  color: var(--slate-mid);
  font-size: 12px;
  font-weight: 800;
}

.catalog-quality__table tbody tr:nth-child(even) {
  background: #FAFBFC;
}

.catalog-quality__latin {
  font-style: italic;
}

.catalog-quality__link {
  color: var(--teal-accent);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
}

.catalog-quality__link:hover {
  text-decoration: underline;
}

.catalog-quality__empty {
  color: var(--slate-mid);
  font-size: 13px;
  padding: 8px 0;
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
</style>
