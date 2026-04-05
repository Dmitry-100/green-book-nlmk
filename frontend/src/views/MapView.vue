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
        <el-select v-model="statusFilter" placeholder="Статус" clearable @change="fetchPoints" size="small">
          <el-option label="Подтверждено" value="confirmed" />
          <el-option label="На проверке" value="on_review" />
          <el-option label="Все" value="" />
        </el-select>
      </div>
      <div class="map-stats">
        <div class="map-stat">
          <span class="map-stat__number">{{ points.length }}</span>
          <span class="map-stat__label">точек на карте</span>
        </div>
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
        <div v-for="p in points" :key="p.properties.id" class="point-item">
          <span class="point-icon">{{ groupIcon(p.properties.group) }}</span>
          <div class="point-info">
            <span class="point-id">#{{ p.properties.id }}</span>
            <span class="point-date">{{ formatDate(p.properties.observed_at) }}</span>
          </div>
          <span class="point-status" :class="'point-status--' + p.properties.status">
            {{ p.properties.is_incident ? '!' : '' }}
          </span>
        </div>
        <div v-if="points.length === 0" class="no-points">Нет наблюдений</div>
      </div>
    </div>
    <div class="map-container">
      <div id="ymap" ref="mapEl"></div>
      <div v-if="mapLoading" class="map-loading">
        <span>Загрузка карты...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import api from '../api/client'

const mapEl = ref<HTMLElement>()
const points = ref<any[]>([])
const mapLoading = ref(true)
const groupFilter = ref('')
const statusFilter = ref('confirmed')

let ymaps3: any = null
let map: any = null
let markerLayer: any = null

const GROUP_ICONS: Record<string, string> = { plants: '🌿', fungi: '🍄', insects: '🐛', herpetofauna: '🐍', birds: '🐦', mammals: '🦔' }
function groupIcon(g: string) { return GROUP_ICONS[g] || '🌱' }

function formatDate(iso: string) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('ru', { day: 'numeric', month: 'short' })
}

async function loadYmaps(apiKey: string) {
  return new Promise<void>((resolve, reject) => {
    if ((window as any).ymaps3) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = `https://api-maps.yandex.ru/v3/?apikey=${apiKey}&lang=ru_RU`
    script.onload = () => {
      (window as any).ymaps3.ready.then(() => resolve())
    }
    script.onerror = reject
    document.head.appendChild(script)
  })
}

async function initMap(apiKey: string) {
  try {
    await loadYmaps(apiKey)
    ymaps3 = (window as any).ymaps3

    const { YMap, YMapDefaultSchemeLayer, YMapDefaultFeaturesLayer, YMapMarker } = ymaps3

    map = new YMap(mapEl.value!, {
      location: {
        center: [39.60, 52.59],
        zoom: 13,
      },
    })

    map.addChild(new YMapDefaultSchemeLayer({}))
    map.addChild(new YMapDefaultFeaturesLayer({}))

    mapLoading.value = false
    await updateMarkers()
  } catch (e) {
    console.error('Failed to init Yandex Maps:', e)
    mapLoading.value = false
  }
}

async function updateMarkers() {
  if (!map || !ymaps3) return

  const { YMapMarker } = ymaps3

  // Remove old markers
  if (markerLayer && markerLayer.length) {
    markerLayer.forEach((m: any) => {
      try { map.removeChild(m) } catch {}
    })
  }
  markerLayer = []

  for (const p of points.value) {
    const [lon, lat] = p.geometry.coordinates
    const el = document.createElement('div')
    el.className = 'ymap-marker'
    if (p.properties.is_incident) {
      el.classList.add('ymap-marker--incident')
    } else if (p.properties.status === 'on_review') {
      el.classList.add('ymap-marker--review')
    }
    el.innerHTML = groupIcon(p.properties.group)
    el.title = `#${p.properties.id} — ${p.properties.group}`

    const marker = new YMapMarker(
      { coordinates: [lon, lat] },
      el
    )
    map.addChild(marker)
    markerLayer.push(marker)
  }
}

async function fetchPoints() {
  try {
    const params: any = {}
    if (groupFilter.value) params.group = groupFilter.value
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await api.get('/map/observations', { params })
    points.value = data.features || []
    await updateMarkers()
  } catch {
    points.value = []
  }
}

onMounted(async () => {
  try {
    const { data } = await api.get('/config/ymaps')
    if (data.apiKey) {
      await initMap(data.apiKey)
    } else {
      mapLoading.value = false
    }
  } catch {
    mapLoading.value = false
  }
  await fetchPoints()
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
.no-points { text-align: center; padding: 20px; color: var(--slate-light); font-size: 13px; }

/* Map */
.map-container { position: relative; }
#ymap { width: 100%; height: 100%; }
.map-loading {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--slate-bg);
  color: var(--slate-mid);
  font-size: 16px;
}

@media (max-width: 768px) {
  .map-page { grid-template-columns: 1fr; grid-template-rows: auto 1fr; }
  .map-sidebar { max-height: 40vh; }
}
</style>

<style>
/* Global marker styles (not scoped — injected into map DOM) */
.ymap-marker {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #2A7A6E;
  border: 3px solid white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  cursor: pointer;
  transform: translate(-50%, -50%);
  transition: transform 0.2s;
}
.ymap-marker:hover {
  transform: translate(-50%, -50%) scale(1.2);
  z-index: 10;
}
.ymap-marker--incident {
  background: #E53935;
}
.ymap-marker--review {
  background: #FFC107;
}
</style>
