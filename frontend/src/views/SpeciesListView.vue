<template>
  <div class="species-page">
    <div class="species-page__header">
      <h1>Справочник видов</h1>
      <p>{{ total }} видов в каталоге</p>
    </div>
    <div class="species-page__filters">
      <el-input v-model="search" placeholder="Поиск по названию..." clearable @input="debouncedFetch" style="max-width: 300px" />
      <el-select v-model="groupFilter" placeholder="Группа" clearable @change="fetchSpecies">
        <el-option label="Растения" value="plants" />
        <el-option label="Грибы" value="fungi" />
        <el-option label="Насекомые" value="insects" />
        <el-option label="Герпетофауна" value="herpetofauna" />
        <el-option label="Птицы" value="birds" />
        <el-option label="Млекопитающие" value="mammals" />
      </el-select>
      <el-select v-model="categoryFilter" placeholder="Категория" clearable @change="fetchSpecies">
        <el-option label="Рудеральный" value="ruderal" />
        <el-option label="Типичный" value="typical" />
        <el-option label="Редкий" value="rare" />
        <el-option label="Красная книга" value="red_book" />
        <el-option label="Синантроп" value="synanthropic" />
      </el-select>
      <el-checkbox v-model="hasAudio" class="species-page__audio-filter" @change="fetchSpecies">
        С голосом
      </el-checkbox>
    </div>
    <div class="species-grid">
      <SpeciesCard v-for="s in species" :key="s.id" :species="s" />
    </div>
    <div v-if="species.length === 0 && !loading" class="species-page__empty">Виды не найдены</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getCached } from '../api/client'
import SpeciesCard from '../components/SpeciesCard.vue'

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

async function fetchSpecies() {
  loading.value = true
  const params: any = { limit: 200 }
  if (groupFilter.value) params.group = groupFilter.value
  if (categoryFilter.value) params.category = categoryFilter.value
  if (search.value && search.value.length >= 2) params.search = search.value
  if (hasAudio.value) params.has_audio = true
  const cacheKey = `species:list:${params.group || ''}:${params.category || ''}:${params.search || ''}:${params.has_audio || ''}:${params.limit}`
  try {
    const { data } = await getCached('/species', { params }, SPECIES_LIST_CACHE_TTL_MS, cacheKey)
    species.value = data.items || []
    total.value = data.total || 0
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
.species-page { max-width: 1200px; margin: 0 auto; padding: 32px; }
.species-page__header { margin-bottom: 24px; }
.species-page__header h1 { font-family: 'Cormorant Garamond', serif; font-size: 30px; font-weight: 600; color: #1B4D4F; }
.species-page__header p { font-size: 14px; color: #8FA5AB; margin-top: 4px; }
.species-page__filters { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
.species-page__audio-filter { min-height: 32px; display: inline-flex; align-items: center; }
.species-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
.species-page__empty { text-align: center; padding: 60px 20px; color: #8FA5AB; font-size: 16px; }
</style>
