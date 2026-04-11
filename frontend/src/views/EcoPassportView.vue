<template>
  <div class="passport-page">
    <!-- Hero banner -->
    <div class="passport-hero">
      <div class="passport-hero__overlay"></div>
      <div class="passport-hero__content">
        <h1>Экологический паспорт площадки</h1>
        <p>Аналитика биоразнообразия промышленной площадки ПАО «НЛМК», г. Липецк</p>
      </div>
    </div>

    <!-- Key metrics -->
    <div class="metrics-grid">
      <div class="metric-card metric-card--accent" @mouseenter="showTooltip = true" @mouseleave="showTooltip = false">
        <div class="metric-card__value">{{ stats.shannon_index }}</div>
        <div class="metric-card__label">Индекс Шеннона</div>
        <div class="metric-card__hint">{{ shannonLevel }}</div>
        <div v-if="showTooltip" class="shannon-tooltip">
          <strong>Индекс Шеннона (H')</strong> — мера биоразнообразия, учитывающая число видов и равномерность их представленности.
          H' = -&Sigma;(p<sub>i</sub> &times; ln p<sub>i</sub>), где p<sub>i</sub> — доля наблюдений вида i.
          <br><br>
          <span>0–1: низкое</span> &bull; <span>1–2: среднее</span> &bull; <span>2–3: высокое</span> &bull; <span>&gt;3: очень высокое</span>
        </div>
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

    <!-- Species by group with photos -->
    <div class="section-card">
      <h2>Видовой состав по группам</h2>
      <div class="group-bars">
        <div v-for="g in groupsOrdered" :key="g.key" class="group-bar">
          <div class="group-bar__photo" :style="{ backgroundImage: `url(${g.photo})` }"></div>
          <div class="group-bar__label">{{ g.label }}</div>
          <div class="group-bar__track">
            <div class="group-bar__fill" :style="{ width: barWidth(g.count) }"></div>
          </div>
          <div class="group-bar__count">{{ g.count }}</div>
        </div>
      </div>
    </div>

    <!-- Seasonal dynamics -->
    <div class="section-card">
      <h2>Сезонная динамика</h2>
      <p class="section-hint">Количество уникальных видов, наблюдаемых по месяцам</p>
      <div class="season-chart">
        <div v-for="m in monthsData" :key="m.month" class="season-bar" :class="{ 'season-bar--current': m.month === currentMonth }">
          <div class="season-bar__fill" :style="{ height: seasonBarHeight(m.species_count) }"></div>
          <div class="season-bar__label">{{ monthNames[m.month - 1] }}</div>
          <div class="season-bar__value" v-if="m.species_count > 0">{{ m.species_count }}</div>
        </div>
      </div>
    </div>

    <!-- Photo gallery of groups -->
    <div class="section-card section-card--gallery">
      <h2>Биоразнообразие площадки</h2>
      <p class="section-hint">Представители флоры и фауны, обнаруженные на территории</p>
      <div class="gallery-grid">
        <div v-for="s in gallerySpecies" :key="s.id" class="gallery-item" @click="$router.push(`/species/${s.id}`)">
          <div class="gallery-item__photo" :style="{ backgroundImage: `url(${s.photo_urls[0]})` }"></div>
          <div class="gallery-item__overlay">
            <div class="gallery-item__name">{{ s.name_ru }}</div>
            <div class="gallery-item__latin">{{ s.name_latin }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Heatmap -->
    <div class="section-card" v-if="stats.heatmap?.length">
      <h2>Карта наблюдений</h2>
      <p class="section-hint">{{ heatmapHint }}</p>
      <div id="passport-map" ref="mapEl" class="passport-map"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { getCached } from '../api/client'
import { loadYmaps } from '../services/ymapsLoader'

const stats = ref<any>({
  shannon_index: 0, total_species_in_catalog: 0, confirmed_species: 0,
  total_confirmed_observations: 0, biodiversity_coverage: 0,
  species_by_group: {}, seasonal_dynamics: [], heatmap: [],
  heatmap_total: 0, heatmap_limit: 0, heatmap_limited: false,
})
const mapEl = ref<HTMLElement>()
const showTooltip = ref(false)
const gallerySpecies = ref<any[]>([])
const currentMonth = new Date().getMonth() + 1

const groupLabels: Record<string, string> = {
  plants: 'Растения', fungi: 'Грибы', insects: 'Насекомые',
  herpetofauna: 'Герпетофауна', birds: 'Птицы', mammals: 'Млекопитающие',
}
const groupPhotos: Record<string, string> = {
  plants: '/api/media/species-pdf/page05_img02.png',
  fungi: '/api/media/species-pdf/page12_img00.png',
  insects: '/api/media/species-pdf/page20_img04.png',
  herpetofauna: '/api/media/species-pdf/page21_img03.png',
  birds: '/api/media/species-pdf/page23_img07.png',
  mammals: '/api/media/species-pdf/page29_img00.png',
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

const groupsOrdered = computed(() => {
  const entries = Object.entries(stats.value.species_by_group || {})
  return entries
    .map(([key, count]) => ({ key, label: groupLabels[key] || key, count: count as number, photo: groupPhotos[key] || '' }))
    .sort((a, b) => b.count - a.count)
})

const monthsData = computed(() => {
  const data = Array.from({ length: 12 }, (_, i) => ({ month: i + 1, species_count: 0 }))
  for (const s of stats.value.seasonal_dynamics || []) {
    data[s.month - 1].species_count = s.species_count
  }
  return data
})

const maxGroupCount = computed(() => Math.max(...groupsOrdered.value.map(g => g.count), 1))
const maxSeasonCount = computed(() => Math.max(...monthsData.value.map(m => m.species_count), 1))
const heatmapHint = computed(() => {
  const shown = stats.value.heatmap?.length || 0
  const total = Number(stats.value.heatmap_total || shown)
  if (!shown) return 'Нет данных о наблюдениях'
  if (stats.value.heatmap_limited && total > shown) {
    return `Показаны ${shown} из ${total} подтверждённых наблюдений на территории площадки`
  }
  return `${shown} подтверждённых наблюдений на территории площадки`
})

function barWidth(count: number) { return `${(count / maxGroupCount.value) * 100}%` }
function seasonBarHeight(count: number) { return `${(count / maxSeasonCount.value) * 100}%` }

function buildGallerySpecies(items: any[]): any[] {
  const withPhotos = items.filter((s: any) => s.photo_urls?.length)
  const byGroup: Record<string, any[]> = {}
  for (const species of withPhotos) {
    if (!byGroup[species.group]) byGroup[species.group] = []
    byGroup[species.group].push(species)
  }
  const picked: any[] = []
  for (const group of Object.keys(byGroup)) {
    const groupItems = byGroup[group]
    picked.push(groupItems[Math.floor(Math.random() * groupItems.length)])
  }
  return picked.slice(0, 6)
}

onMounted(async () => {
  const [statsResult, speciesResult] = await Promise.allSettled([
    getCached(
      '/gamification/stats',
      { params: { heatmap_limit: 1200 } },
      30 * 1000,
      'passport:stats:1200'
    ),
    getCached(
      '/species',
      { params: { limit: 80, include_total: false } },
      5 * 60 * 1000,
      'passport:species:gallery:v1'
    ),
  ])

  if (statsResult.status === 'fulfilled') {
    stats.value = statsResult.value.data
  }
  if (speciesResult.status === 'fulfilled') {
    gallerySpecies.value = buildGallerySpecies(speciesResult.value.data.items || [])
  }

  // Init map
  await nextTick()
  if (stats.value.heatmap?.length && mapEl.value) {
    try {
      const configRes = await getCached(
        '/config/ymaps',
        {},
        60 * 60 * 1000,
        'config:ymaps'
      )
      if (!configRes.data.apiKey) return

      const ymaps = await loadYmaps(configRes.data.apiKey)

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

      const clusterer = new ymaps.Clusterer({
        preset: 'islands#greenClusterIcons',
        clusterDisableClickZoom: false,
        clusterBalloonContentLayout: 'cluster#balloonCarousel',
      })
      const placemarks = stats.value.heatmap.map((point: any) => {
        return new ymaps.Placemark([point.lat, point.lon], {}, {
          preset: groupColors[point.group] || 'islands#grayDotIcon',
        })
      })
      clusterer.add(placemarks)
      map.geoObjects.add(clusterer)
    } catch {}
  }
})
</script>

<style scoped>
.passport-page { max-width: 1000px; margin: 0 auto; padding: 0 32px 32px; }

/* Hero */
.passport-hero {
  position: relative; border-radius: 0 0 24px 24px; overflow: hidden;
  height: 200px; margin: 0 -32px 28px; display: flex; align-items: center;
  background: url('/api/media/species-pdf/page23_img07.png') center/cover;
}
.passport-hero__overlay {
  position: absolute; inset: 0;
  background: linear-gradient(135deg, rgba(27,77,79,0.92) 0%, rgba(42,122,110,0.8) 60%, rgba(27,77,79,0.6) 100%);
}
.passport-hero__content { position: relative; z-index: 1; padding: 0 48px; }
.passport-hero__content h1 { font-family: 'Cormorant Garamond', serif; font-size: 34px; font-weight: 700; color: white; margin: 0 0 6px; }
.passport-hero__content p { font-size: 15px; color: rgba(255,255,255,0.8); margin: 0; }

/* Metrics */
.metrics-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 24px; }
.metric-card {
  background: #FAFBFC; border-radius: 14px; padding: 20px; text-align: center;
  box-shadow: 0 2px 12px rgba(44,62,74,0.08); position: relative;
}
.metric-card--accent { background: linear-gradient(135deg, #1B4D4F, #2A7A6E); color: white; cursor: help; }
.metric-card--accent .metric-card__label { color: rgba(255,255,255,0.8); }
.metric-card--accent .metric-card__hint { color: rgba(255,255,255,0.65); }
.metric-card__value { font-family: 'Cormorant Garamond', serif; font-size: 32px; font-weight: 700; color: #1B4D4F; }
.metric-card--accent .metric-card__value { color: white; }
.metric-card__label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #8FA5AB; margin-top: 4px; }
.metric-card__hint { font-size: 11px; color: #4A6572; margin-top: 4px; }

/* Shannon tooltip */
.shannon-tooltip {
  position: absolute; top: calc(100% + 8px); left: 50%; transform: translateX(-50%);
  width: 320px; padding: 16px; background: #1B4D4F; color: rgba(255,255,255,0.9);
  border-radius: 12px; font-size: 12px; line-height: 1.6; z-index: 20;
  box-shadow: 0 8px 32px rgba(0,0,0,0.25); text-align: left;
}
.shannon-tooltip strong { color: white; display: block; margin-bottom: 6px; font-size: 13px; }
.shannon-tooltip::before {
  content: ''; position: absolute; top: -6px; left: 50%; transform: translateX(-50%);
  border: 6px solid transparent; border-bottom-color: #1B4D4F;
}

/* Section cards */
.section-card { background: #FAFBFC; border-radius: 16px; padding: 28px; margin-bottom: 20px; box-shadow: 0 2px 12px rgba(44,62,74,0.08); }
.section-card h2 { font-family: 'Cormorant Garamond', serif; font-size: 22px; color: #1B4D4F; margin-bottom: 16px; }
.section-hint { font-size: 13px; color: #8FA5AB; margin-bottom: 16px; }

/* Group bars with photos */
.group-bars { display: flex; flex-direction: column; gap: 12px; }
.group-bar { display: flex; align-items: center; gap: 12px; }
.group-bar__photo { width: 36px; height: 36px; border-radius: 8px; background-size: cover; background-position: center; flex-shrink: 0; background-color: #D6E0E3; }
.group-bar__label { width: 120px; font-size: 13px; font-weight: 600; color: #2C3E4A; }
.group-bar__track { flex: 1; height: 28px; background: #E8EEF0; border-radius: 6px; overflow: hidden; }
.group-bar__fill { height: 100%; background: linear-gradient(90deg, #2A7A6E, #3D9B8F); border-radius: 6px; transition: width 0.8s ease; }
.group-bar__count { width: 32px; font-size: 14px; font-weight: 700; color: #2A7A6E; text-align: right; }

/* Season chart */
.season-chart { display: flex; gap: 8px; height: 180px; align-items: flex-end; padding-top: 20px; }
.season-bar { flex: 1; display: flex; flex-direction: column; align-items: center; height: 100%; justify-content: flex-end; position: relative; }
.season-bar__fill { width: 100%; background: linear-gradient(to top, #2A7A6E, #3D9B8F); border-radius: 4px 4px 0 0; transition: height 0.8s ease; min-height: 2px; }
.season-bar--current .season-bar__fill { background: linear-gradient(to top, #E65100, #FF9800); }
.season-bar--current .season-bar__label { color: #E65100; font-weight: 700; }
.season-bar__label { font-size: 10px; color: #8FA5AB; margin-top: 6px; font-weight: 600; }
.season-bar__value { position: absolute; top: -18px; font-size: 11px; font-weight: 700; color: #2A7A6E; }

/* Gallery */
.gallery-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.gallery-item { position: relative; border-radius: 12px; overflow: hidden; cursor: pointer; aspect-ratio: 1.4; }
.gallery-item__photo { width: 100%; height: 100%; background-size: cover; background-position: center; transition: transform 0.4s; }
.gallery-item:hover .gallery-item__photo { transform: scale(1.08); }
.gallery-item__overlay {
  position: absolute; bottom: 0; left: 0; right: 0;
  padding: 14px; background: linear-gradient(to top, rgba(27,77,79,0.85) 0%, transparent 100%);
}
.gallery-item__name { font-size: 14px; font-weight: 700; color: white; }
.gallery-item__latin { font-size: 11px; font-style: italic; color: rgba(255,255,255,0.7); }

/* Map */
.passport-map { width: 100%; height: 350px; border-radius: 12px; overflow: hidden; background: #D6E0E3; }

@media (max-width: 768px) {
  .metrics-grid { grid-template-columns: repeat(2, 1fr); }
  .gallery-grid { grid-template-columns: repeat(2, 1fr); }
  .passport-hero { height: 160px; }
  .passport-hero__content h1 { font-size: 24px; }
}
</style>
