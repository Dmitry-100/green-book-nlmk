<template>
  <div class="species-page">
    <PageHero
      title="Справочник видов"
      :subtitle="`${total} видов в каталоге`"
      icon="🌿"
      kicker="Каталог"
      compact
      ambient
    />
    <div class="species-page__content">
    <div class="species-page__filters">
      <label class="species-search">
        <input
          v-model="search"
          class="native-input"
          type="text"
          placeholder="Поиск по названию..."
          @input="debouncedFetch"
          @keydown.esc="clearSearch"
        />
        <button
          v-if="search"
          class="species-search__clear"
          type="button"
          aria-label="Очистить поиск"
          @click="clearSearch"
        >
          ×
        </button>
      </label>
      <select v-model="groupFilter" class="native-select" @change="fetchSpecies">
        <option value="">Все группы</option>
        <option value="plants">Растения</option>
        <option value="fungi">Грибы</option>
        <option value="insects">Насекомые</option>
        <option value="herpetofauna">Герпетофауна</option>
        <option value="birds">Птицы</option>
        <option value="mammals">Млекопитающие</option>
      </select>
      <select v-model="categoryFilter" class="native-select" @change="fetchSpecies">
        <option value="">Все категории</option>
        <option value="ruderal">Рудеральный</option>
        <option value="typical">Типичный</option>
        <option value="rare">Редкий</option>
        <option value="red_book">Красная книга</option>
        <option value="synanthropic">Синантроп</option>
      </select>
      <label class="native-checkbox">
        <input v-model="hasAudio" type="checkbox" @change="fetchSpecies" />
        <span>С голосом</span>
      </label>
    </div>
    <div class="species-grid">
      <SpeciesCard v-for="s in species" :key="s.id" :species="s" />
    </div>
    <EmptyState
      v-if="species.length === 0 && !loading"
      icon="🔍"
      title="Виды не найдены"
      text="Попробуйте изменить фильтры или очистить поиск."
    />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getCached } from '../api/client'
import SpeciesCard from '../components/SpeciesCard.vue'
import PageHero from '../components/PageHero.vue'
import EmptyState from '../components/EmptyState.vue'

const route = useRoute()
const species = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const search = ref('')
const groupFilter = ref('')
const categoryFilter = ref('')
const hasAudio = ref(false)
let debounceTimer: ReturnType<typeof setTimeout>
const SPECIES_LIST_CACHE_TTL_MS = 60 * 1000
const SPECIES_LIST_PAGE_SIZE = 200

async function fetchSpecies() {
  loading.value = true
  const params: any = { limit: SPECIES_LIST_PAGE_SIZE }
  if (groupFilter.value) params.group = groupFilter.value
  if (categoryFilter.value) params.category = categoryFilter.value
  if (search.value && search.value.length >= 2) params.search = search.value
  if (hasAudio.value) params.has_audio = true
  const cacheKeyBase = `species:list:${params.group || ''}:${params.category || ''}:${params.search || ''}:${params.has_audio || ''}:${params.limit}`
  try {
    const { data } = await getCached('/species', { params }, SPECIES_LIST_CACHE_TTL_MS, `${cacheKeyBase}:0`)
    const items = data.items || []
    const totalItems = data.total || items.length

    while (items.length < totalItems) {
      const skip = items.length
      const { data: nextData } = await getCached(
        '/species',
        { params: { ...params, skip } },
        SPECIES_LIST_CACHE_TTL_MS,
        `${cacheKeyBase}:${skip}`
      )
      const nextItems = nextData.items || []
      if (!nextItems.length) break
      items.push(...nextItems)
    }

    species.value = items
    total.value = totalItems
  } catch {
    species.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function debouncedFetch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchSpecies, 300)
}

function clearSearch() {
  if (!search.value) return
  search.value = ''
  clearTimeout(debounceTimer)
  fetchSpecies()
}

// Read group filter from URL query param
watch(() => route.query.group, (val) => {
  groupFilter.value = (val as string) || ''
  fetchSpecies()
})

onMounted(() => {
  if (route.query.group) {
    groupFilter.value = route.query.group as string
  }
  hasAudio.value = route.query.has_audio === 'true'
  fetchSpecies()
})
</script>

<style scoped>
.species-page { padding: 0 0 32px; }
.species-page__content { max-width: 1200px; margin: 0 auto; padding: 24px 32px; }
.species-page__filters { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
.species-search {
  position: relative;
  display: inline-flex;
  align-items: center;
  width: min(300px, 100%);
}
.native-input {
  width: 100%;
  height: 32px;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  padding: 0 32px 0 11px;
  background: #FFFFFF;
  color: #2C3E4A;
  font: inherit;
}
.native-input:focus {
  outline: none;
  border-color: #2A7A6E;
  box-shadow: 0 0 0 2px rgba(42,122,110,0.12);
}
.species-search__clear {
  position: absolute;
  right: 6px;
  width: 22px;
  height: 22px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #8FA5AB;
  cursor: pointer;
  font: inherit;
  line-height: 1;
}
.species-search__clear:hover {
  background: #E8EEF0;
  color: #2C3E4A;
}
.native-select {
  min-width: 170px;
  height: 32px;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  padding: 0 32px 0 11px;
  background: #FFFFFF;
  color: #2C3E4A;
  font: inherit;
}
.native-select:focus {
  outline: none;
  border-color: #2A7A6E;
  box-shadow: 0 0 0 2px rgba(42,122,110,0.12);
}
.native-checkbox {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #2C3E4A;
  font-size: 14px;
  cursor: pointer;
}
.native-checkbox input {
  width: 16px;
  height: 16px;
  accent-color: #2A7A6E;
}
.species-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
.species-page__empty { text-align: center; padding: 60px 20px; color: #8FA5AB; font-size: 16px; }
</style>
