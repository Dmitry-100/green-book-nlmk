<template>
  <div class="map-page">
    <div class="map-sidebar">
      <h2>Карта наблюдений</h2>
      <div class="map-filters">
        <el-select v-model="groupFilter" placeholder="Группа" clearable @change="fetchPoints" size="small">
          <el-option label="Растения" value="plants" />
          <el-option label="Грибы" value="fungi" />
          <el-option label="Насекомые" value="insects" />
          <el-option label="Герпетофауна" value="herpetofauna" />
          <el-option label="Птицы" value="birds" />
          <el-option label="Млекопитающие" value="mammals" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="Статус" @change="fetchPoints" size="small">
          <el-option label="Подтверждено" value="confirmed" />
          <el-option v-if="auth.isEcologist()" label="На проверке" value="on_review" />
        </el-select>
      </div>
      <div class="map-stats">
        <div class="map-stat">
          <span class="map-stat__number">{{ points.length }}</span>
          <span class="map-stat__label">точек на карте</span>
        </div>
      </div>
      <div v-if="isMapSampled" class="map-hint">
        Для текущего масштаба отображается {{ renderedPointsCount }} из {{ points.length }} точек.
      </div>
      <div class="map-legend">
        <h3>Легенда</h3>
        <div class="legend-item">
          <span class="legend-dot" style="background: #2A7A6E"></span> Подтверждено
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background: #FFC107"></span> На проверке
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background: #E53935"></span> Инцидент
        </div>
      </div>
      <div class="map-points-list">
        <h3>Наблюдения</h3>
        <div v-for="p in sidebarPoints" :key="p.properties.id" class="point-item">
          <span class="point-icon">{{ groupIcon(p.properties.group) }}</span>
          <div class="point-info">
            <span class="point-id">#{{ p.properties.id }}</span>
            <span class="point-date">{{ formatDate(p.properties.observed_at) }}</span>
          </div>
          <span class="point-status" :class="'point-status--' + p.properties.status">
            {{ p.properties.is_incident ? '!' : '' }}
          </span>
        </div>
        <div v-if="isSidebarTruncated" class="list-truncated-hint">
          Показаны последние {{ sidebarPoints.length }} из {{ points.length }} наблюдений.
        </div>
        <div v-if="points.length === 0" class="no-points">Нет наблюдений</div>
      </div>
    </div>
    <div class="map-container">
      <div id="ymap" ref="mapEl"></div>
      <div v-if="mapLoading" class="map-loading">Загрузка карты...</div>
      <div v-if="mapError" class="map-error">
        <span style="font-size: 48px; opacity: 0.3">🗺️</span>
        <h3>Не удалось загрузить карту</h3>
        <p>{{ mapError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import axios from 'axios'
import api, { getCached } from '../api/client'
import { loadYmaps } from '../services/ymapsLoader'
import { useAuthStore } from '../stores/auth'

const mapEl = ref<HTMLElement>()
const points = ref<any[]>([])
const mapLoading = ref(true)
const mapError = ref('')
const groupFilter = ref('')
const statusFilter = ref('confirmed')
const auth = useAuthStore()

let ymaps: any = null
let map: any = null
let clusterer: any = null
let boundsDebounceTimer: number | null = null
let pointsAbortController: AbortController | null = null
let pointsRequestSeq = 0
let activeQueryKey = ''
let lastCompletedQueryKey = ''
const renderedPointsCount = ref(0)
const MAX_SIDEBAR_POINTS = 250
const sidebarPoints = computed(() => points.value.slice(0, MAX_SIDEBAR_POINTS))
const isSidebarTruncated = computed(() => points.value.length > MAX_SIDEBAR_POINTS)
const isMapSampled = computed(() => renderedPointsCount.value > 0 && renderedPointsCount.value < points.value.length)

const GROUP_ICONS: Record<string, string> = { plants: '🌿', fungi: '🍄', insects: '🐛', herpetofauna: '🐍', birds: '🐦', mammals: '🦔' }
function groupIcon(g: string) { return GROUP_ICONS[g] || '🌱' }

function formatDate(iso: string) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('ru', { day: 'numeric', month: 'short' })
}

function getMarkerColor(props: any): string {
  if (props.is_incident) return '#E53935'
  if (props.status === 'on_review') return '#FFC107'
  return '#2A7A6E'
}

async function initMap(apiKey: string) {
  try {
    ymaps = await loadYmaps(apiKey)

    map = new ymaps.Map(mapEl.value!, {
      center: [52.59, 39.60],
      zoom: 13,
      controls: ['zoomControl', 'typeSelector', 'fullscreenControl'],
    })

    // Clusterer for observation points
    clusterer = new ymaps.Clusterer({
      preset: 'islands#greenClusterIcons',
      clusterDisableClickZoom: false,
      clusterBalloonContentLayout: 'cluster#balloonCarousel',
    })
    map.geoObjects.add(clusterer)
    map.events.add('boundschange', () => {
      if (boundsDebounceTimer) {
        window.clearTimeout(boundsDebounceTimer)
      }
      boundsDebounceTimer = window.setTimeout(() => {
        fetchPoints()
      }, 250)
    })

    mapLoading.value = false
    await updateMarkers()
  } catch (e: any) {
    console.error('Map init error:', e)
    mapError.value = e?.message || 'Ошибка инициализации карты'
    mapLoading.value = false
  }
}

async function updateMarkers() {
  if (!map || !ymaps || !clusterer) return

  clusterer.removeAll()

  const renderLimit = resolveRenderablePointLimit()
  const renderPoints = downsamplePoints(points.value, renderLimit)
  renderedPointsCount.value = renderPoints.length
  const zoom = Number(map.getZoom?.())
  if (!Number.isNaN(zoom) && clusterer?.options?.set) {
    clusterer.options.set('gridSize', resolveClusterGridSize(zoom, renderPoints.length))
  }

  const placemarks = renderPoints.map(p => {
    const [lon, lat] = p.geometry.coordinates
    const icon = groupIcon(p.properties.group)

    const placemark = new ymaps.Placemark(
      [lat, lon],
      {
        balloonContentHeader: `${icon} Наблюдение #${p.properties.id}`,
        balloonContentBody: `Группа: ${p.properties.group}<br>Статус: ${p.properties.status}`,
        hintContent: `${icon} #${p.properties.id}`,
      },
      {
        preset: p.properties.is_incident
          ? 'islands#redCircleDotIcon'
          : p.properties.status === 'on_review'
            ? 'islands#yellowCircleDotIcon'
            : 'islands#greenCircleDotIcon',
      }
    )
    return placemark
  })

  clusterer.add(placemarks)
}

function getCurrentBboxParam(): string | null {
  if (!map) return null
  const bounds = map.getBounds?.()
  if (!Array.isArray(bounds) || bounds.length !== 2) return null
  const southWest = bounds[0]
  const northEast = bounds[1]
  if (!Array.isArray(southWest) || !Array.isArray(northEast)) return null
  const minLat = Number(southWest[0])
  const minLon = Number(southWest[1])
  const maxLat = Number(northEast[0])
  const maxLon = Number(northEast[1])
  if ([minLon, minLat, maxLon, maxLat].some((value) => Number.isNaN(value))) return null
  const quantize = (value: number) => Number(value.toFixed(4))
  return `${quantize(minLon)},${quantize(minLat)},${quantize(maxLon)},${quantize(maxLat)}`
}

function resolvePointLimit(): number {
  if (!map) return 1200
  const zoom = Number(map.getZoom?.())
  if (Number.isNaN(zoom)) return 1200
  if (zoom <= 11) return 600
  if (zoom <= 13) return 900
  return 1200
}

function resolveRenderablePointLimit(): number {
  if (!map) return 1000
  const zoom = Number(map.getZoom?.())
  if (Number.isNaN(zoom)) return 1000
  if (zoom <= 11) return 500
  if (zoom <= 13) return 800
  return 1200
}

function resolveClusterGridSize(zoom: number, pointCount: number): number {
  if (zoom <= 11 || pointCount > 900) return 96
  if (zoom <= 13 || pointCount > 600) return 72
  return 56
}

function downsamplePoints<T>(items: T[], maxItems: number): T[] {
  if (items.length <= maxItems) return items
  const sampled: T[] = []
  const step = items.length / maxItems
  for (let i = 0; i < maxItems; i += 1) {
    sampled.push(items[Math.floor(i * step)])
  }
  return sampled
}

function buildQueryParams() {
  const params: any = {}
  if (groupFilter.value) params.group = groupFilter.value
  if (statusFilter.value) params.status = statusFilter.value
  const bbox = getCurrentBboxParam()
  if (bbox) params.bbox = bbox
  params.limit = resolvePointLimit()
  const queryKey = [
    params.group || '',
    params.status || '',
    params.bbox || '',
    String(params.limit),
  ].join('|')
  return { params, queryKey }
}

async function fetchPoints(force = false) {
  const { params, queryKey } = buildQueryParams()
  if (!force && (queryKey === lastCompletedQueryKey || queryKey === activeQueryKey)) {
    return
  }

  const requestSeq = ++pointsRequestSeq
  activeQueryKey = queryKey
  pointsAbortController?.abort()
  const controller = new AbortController()
  pointsAbortController = controller

  try {
    const { data } = await api.get('/map/observations', {
      params,
      signal: controller.signal,
    })
    if (requestSeq !== pointsRequestSeq) return
    points.value = data.features || []
    renderedPointsCount.value = 0
    lastCompletedQueryKey = queryKey
    await updateMarkers()
  } catch (error: any) {
    if (axios.isCancel(error) || error?.code === 'ERR_CANCELED') {
      return
    }
    if (requestSeq !== pointsRequestSeq) return
    points.value = []
    renderedPointsCount.value = 0
  } finally {
    if (pointsAbortController === controller) {
      pointsAbortController = null
    }
    if (activeQueryKey === queryKey) {
      activeQueryKey = ''
    }
  }
}

onMounted(async () => {
  try {
    const { data } = await getCached(
      '/config/ymaps',
      {},
      60 * 60 * 1000,
      'config:ymaps'
    )
    if (data.apiKey) {
      await initMap(data.apiKey)
    } else {
      mapError.value = 'API-ключ не настроен'
      mapLoading.value = false
    }
  } catch {
    mapError.value = 'Не удалось получить конфигурацию'
    mapLoading.value = false
  }
  await fetchPoints(true)
})

onUnmounted(() => {
  if (boundsDebounceTimer) {
    window.clearTimeout(boundsDebounceTimer)
  }
  pointsAbortController?.abort()
  if (map) {
    map.destroy?.()
  }
})
</script>

<style scoped>
.map-page {
  display: grid;
  grid-template-columns: 320px 1fr;
  height: calc(100vh - 56px - 49px);
  overflow: hidden;
}
.map-sidebar {
  background: var(--white);
  border-right: 1px solid var(--slate-wash);
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.map-sidebar h2 {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 600;
  color: var(--teal-dark);
}
.map-filters { display: flex; flex-direction: column; gap: 8px; }
.map-stats { display: flex; gap: 12px; }
.map-stat {
  background: var(--slate-bg);
  padding: 12px 16px;
  border-radius: 8px;
  flex: 1;
}
.map-stat__number { font-family: var(--font-display); font-size: 28px; font-weight: 700; color: var(--teal); display: block; }
.map-stat__label { font-size: 11px; color: var(--slate-mid); }
.map-hint {
  font-size: 12px;
  color: var(--slate-mid);
  line-height: 1.35;
}
.map-legend h3, .map-points-list h3 {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--slate-light);
  margin-bottom: 8px;
}
.legend-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--slate-mid); margin-bottom: 4px; }
.legend-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
.map-points-list { flex: 1; overflow-y: auto; }
.point-item {
  display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px;
  cursor: pointer; transition: background 0.2s; font-size: 13px;
}
.point-item:hover { background: var(--slate-bg); }
.point-icon { font-size: 18px; }
.point-info { flex: 1; }
.point-id { font-weight: 700; color: var(--slate-deep); margin-right: 6px; }
.point-date { color: var(--slate-light); font-size: 12px; }
.point-status { width: 8px; height: 8px; border-radius: 50%; }
.point-status--confirmed { background: var(--teal); }
.point-status--on_review { background: var(--yellow-potential); }
.list-truncated-hint {
  font-size: 12px;
  color: var(--slate-mid);
  padding: 8px 10px;
}
.no-points { text-align: center; padding: 20px; color: var(--slate-light); font-size: 13px; }

.map-container { position: relative; }
#ymap { width: 100%; height: 100%; }
.map-loading, .map-error {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: var(--slate-bg);
  color: var(--slate-mid);
  font-size: 16px;
  gap: 8px;
}
.map-error h3 { font-family: var(--font-display); font-size: 20px; color: var(--slate-deep); }
.map-error p { font-size: 14px; }

@media (max-width: 768px) {
  .map-page { grid-template-columns: 1fr; grid-template-rows: auto 1fr; }
  .map-sidebar { max-height: 40vh; }
}
</style>
