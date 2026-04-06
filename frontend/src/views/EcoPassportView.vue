<template>
  <div class="passport-page">
    <h1>Экологический паспорт площадки</h1>
    <p class="subtitle">Аналитика биоразнообразия промышленной площадки ПАО «НЛМК»</p>

    <!-- Key metrics -->
    <div class="metrics-grid">
      <div class="metric-card metric-card--accent">
        <div class="metric-card__value">{{ stats.shannon_index }}</div>
        <div class="metric-card__label">Индекс Шеннона</div>
        <div class="metric-card__hint">{{ shannonLevel }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-card__value">{{ stats.total_species_in_catalog }}</div>
        <div class="metric-card__label">Видов в каталоге</div>
      </div>
      <div class="metric-card">
        <div class="metric-card__value">{{ stats.confirmed_species }}</div>
        <div class="metric-card__label">Подтверждено видов</div>
      </div>
      <div class="metric-card">
        <div class="metric-card__value">{{ stats.total_confirmed_observations }}</div>
        <div class="metric-card__label">Наблюдений</div>
      </div>
      <div class="metric-card">
        <div class="metric-card__value">{{ stats.biodiversity_coverage }}%</div>
        <div class="metric-card__label">Покрытие каталога</div>
      </div>
    </div>

    <!-- Species by group -->
    <div class="section-card">
      <h2>Видовой состав по группам</h2>
      <div class="group-bars">
        <div v-for="(count, group) in stats.species_by_group" :key="group" class="group-bar">
          <div class="group-bar__label">{{ groupLabels[group] || group }}</div>
          <div class="group-bar__track">
            <div class="group-bar__fill" :style="{ width: barWidth(count) }"></div>
          </div>
          <div class="group-bar__count">{{ count }}</div>
        </div>
      </div>
    </div>

    <!-- Seasonal dynamics -->
    <div class="section-card">
      <h2>Сезонная динамика</h2>
      <p class="section-hint">Количество уникальных видов, наблюдаемых по месяцам</p>
      <div class="season-chart">
        <div v-for="m in monthsData" :key="m.month" class="season-bar">
          <div class="season-bar__fill" :style="{ height: seasonBarHeight(m.species_count) }"></div>
          <div class="season-bar__label">{{ monthNames[m.month - 1] }}</div>
          <div class="season-bar__value" v-if="m.species_count > 0">{{ m.species_count }}</div>
        </div>
      </div>
    </div>

    <!-- Heatmap placeholder -->
    <div class="section-card" v-if="stats.heatmap?.length">
      <h2>Точки наблюдений</h2>
      <p class="section-hint">{{ stats.heatmap.length }} подтверждённых наблюдений на карте</p>
      <div id="passport-map" ref="mapEl" class="passport-map"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import api from '../api/client'

const stats = ref<any>({
  shannon_index: 0, total_species_in_catalog: 0, confirmed_species: 0,
  total_confirmed_observations: 0, biodiversity_coverage: 0,
  species_by_group: {}, seasonal_dynamics: [], heatmap: [],
})
const mapEl = ref<HTMLElement>()

const groupLabels: Record<string, string> = {
  plants: 'Растения', fungi: 'Грибы', insects: 'Насекомые',
  herpetofauna: 'Герпетофауна', birds: 'Птицы', mammals: 'Млекопитающие',
}
const monthNames = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']

const shannonLevel = computed(() => {
  const h = stats.value.shannon_index
  if (h === 0) return 'Нет данных'
  if (h < 1) return 'Низкое разнообразие'
  if (h < 2) return 'Среднее разнообразие'
  if (h < 3) return 'Высокое разнообразие'
  return 'Очень высокое разнообразие'
})

const monthsData = computed(() => {
  const data = Array.from({ length: 12 }, (_, i) => ({ month: i + 1, species_count: 0 }))
  for (const s of stats.value.seasonal_dynamics || []) {
    data[s.month - 1].species_count = s.species_count
  }
  return data
})

const maxGroupCount = computed(() => Math.max(...Object.values(stats.value.species_by_group || {}).map(Number), 1))
const maxSeasonCount = computed(() => Math.max(...monthsData.value.map(m => m.species_count), 1))

function barWidth(count: number) { return `${(count / maxGroupCount.value) * 100}%` }
function seasonBarHeight(count: number) { return `${(count / maxSeasonCount.value) * 100}%` }

onMounted(async () => {
  try {
    const { data } = await api.get('/gamification/stats')
    stats.value = data
  } catch {}

  // Init map if heatmap data exists
  await nextTick()
  if (stats.value.heatmap?.length && mapEl.value) {
    try {
      const configRes = await api.get('/config/ymaps')
      if (!configRes.data.apiKey) return

      const loadScript = () => new Promise<void>((resolve, reject) => {
        if ((window as any).ymaps) {
          (window as any).ymaps.ready(() => resolve())
          return
        }
        const s = document.createElement('script')
        s.src = `https://api-maps.yandex.ru/2.1/?apikey=${configRes.data.apiKey}&lang=ru_RU`
        s.async = true
        s.onload = () => (window as any).ymaps.ready(() => resolve())
        s.onerror = () => reject()
        document.head.appendChild(s)
      })

      await loadScript()
      const ymaps = (window as any).ymaps

      const map = new ymaps.Map(mapEl.value, {
        center: [52.59, 39.60],
        zoom: 13,
        controls: ['zoomControl'],
      })

      const groupColors: Record<string, string> = {
        plants: 'islands#greenDotIcon',
        fungi: 'islands#brownDotIcon',
        insects: 'islands#yellowDotIcon',
        herpetofauna: 'islands#oliveDotIcon',
        birds: 'islands#blueDotIcon',
        mammals: 'islands#redDotIcon',
      }

      for (const point of stats.value.heatmap) {
        const placemark = new ymaps.Placemark([point.lat, point.lon], {}, {
          preset: groupColors[point.group] || 'islands#grayDotIcon',
        })
        map.geoObjects.add(placemark)
      }
    } catch {}
  }
})
</script>

<style scoped>
.passport-page { max-width: 1000px; margin: 0 auto; padding: 32px; }
.passport-page h1 { font-family: 'Cormorant Garamond', serif; font-size: 30px; font-weight: 600; color: #1B4D4F; }
.subtitle { font-size: 14px; color: #8FA5AB; margin-bottom: 28px; }

.metrics-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 24px; }
.metric-card {
  background: #FAFBFC; border-radius: 14px; padding: 20px; text-align: center;
  box-shadow: 0 2px 12px rgba(44,62,74,0.08);
}
.metric-card--accent { background: linear-gradient(135deg, #1B4D4F, #2A7A6E); color: white; }
.metric-card--accent .metric-card__label { color: rgba(255,255,255,0.8); }
.metric-card--accent .metric-card__hint { color: rgba(255,255,255,0.65); }
.metric-card__value { font-family: 'Cormorant Garamond', serif; font-size: 32px; font-weight: 700; color: #1B4D4F; }
.metric-card--accent .metric-card__value { color: white; }
.metric-card__label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #8FA5AB; margin-top: 4px; }
.metric-card__hint { font-size: 11px; color: #4A6572; margin-top: 4px; }

.section-card { background: #FAFBFC; border-radius: 16px; padding: 28px; margin-bottom: 20px; box-shadow: 0 2px 12px rgba(44,62,74,0.08); }
.section-card h2 { font-family: 'Cormorant Garamond', serif; font-size: 22px; color: #1B4D4F; margin-bottom: 16px; }
.section-hint { font-size: 13px; color: #8FA5AB; margin-bottom: 16px; }

.group-bars { display: flex; flex-direction: column; gap: 10px; }
.group-bar { display: flex; align-items: center; gap: 12px; }
.group-bar__label { width: 130px; font-size: 13px; font-weight: 600; color: #2C3E4A; }
.group-bar__track { flex: 1; height: 24px; background: #E8EEF0; border-radius: 6px; overflow: hidden; }
.group-bar__fill { height: 100%; background: linear-gradient(90deg, #2A7A6E, #3D9B8F); border-radius: 6px; transition: width 0.8s ease; }
.group-bar__count { width: 32px; font-size: 14px; font-weight: 700; color: #2A7A6E; text-align: right; }

.season-chart { display: flex; gap: 8px; height: 180px; align-items: flex-end; padding-top: 20px; }
.season-bar { flex: 1; display: flex; flex-direction: column; align-items: center; height: 100%; justify-content: flex-end; position: relative; }
.season-bar__fill { width: 100%; background: linear-gradient(to top, #2A7A6E, #3D9B8F); border-radius: 4px 4px 0 0; transition: height 0.8s ease; min-height: 2px; }
.season-bar__label { font-size: 10px; color: #8FA5AB; margin-top: 6px; font-weight: 600; }
.season-bar__value { position: absolute; top: -18px; font-size: 11px; font-weight: 700; color: #2A7A6E; }

.passport-map { width: 100%; height: 350px; border-radius: 12px; overflow: hidden; background: #D6E0E3; }

@media (max-width: 768px) {
  .metrics-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
