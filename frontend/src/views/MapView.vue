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
        <div v-for="p in points" :key="p.properties.id" class="point-item" @click="selectedPoint = p">
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
      <div class="map-placeholder-full">
        <div class="map-overlay">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
            <circle cx="12" cy="10" r="3"/>
          </svg>
          <h3>Яндекс Карты</h3>
          <p>Промплощадка ПАО «НЛМК»</p>
          <p class="coords">52.6°N, 39.6°E — Липецк</p>
          <p class="map-note">Для подключения Яндекс Карт API v3 необходим API-ключ.<br>Добавьте YMAPS_API_KEY в .env и раскомментируйте инициализацию в коде.</p>
          <div class="map-dots">
            <div v-for="p in points.slice(0, 20)" :key="p.properties.id"
                 class="map-dot"
                 :class="{ 'map-dot--incident': p.properties.is_incident }"
                 :style="dotStyle(p)"
                 :title="'#' + p.properties.id"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'

const points = ref<any[]>([])
const selectedPoint = ref<any>(null)
const groupFilter = ref('')
const statusFilter = ref('confirmed')

const GROUP_ICONS: Record<string, string> = { plants: '🌿', fungi: '🍄', insects: '🐛', herpetofauna: '🐍', birds: '🐦', mammals: '🦔' }
function groupIcon(g: string) { return GROUP_ICONS[g] || '🌱' }

function formatDate(iso: string) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('ru', { day: 'numeric', month: 'short' })
}

function dotStyle(point: any) {
  // Pseudo-random position based on coordinates for visual representation
  const [lon, lat] = point.geometry.coordinates
  const x = ((lon - 39.5) * 800 + 100) % 90 + 5
  const y = ((52.7 - lat) * 800 + 100) % 80 + 10
  return { left: x + '%', top: y + '%' }
}

async function fetchPoints() {
  try {
    const params: any = {}
    if (groupFilter.value) params.group = groupFilter.value
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await api.get('/map/observations', { params })
    points.value = data.features || []
  } catch {
    points.value = []
  }
}

onMounted(fetchPoints)
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

/* Map area */
.map-container { position: relative; background: #c8d6db; }
.map-placeholder-full {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; align-items: center; justify-content: center;
  background:
    linear-gradient(135deg, #b8ccd3 0%, #9fb8bf 30%, #a8c0c6 60%, #c0d2d8 100%);
}
.map-overlay {
  text-align: center; color: var(--slate-mid);
  position: relative; z-index: 2;
}
.map-overlay h3 { font-family: var(--font-display); font-size: 24px; color: var(--slate-deep); margin-top: 12px; }
.map-overlay p { font-size: 14px; margin-top: 4px; }
.map-overlay .coords { font-family: monospace; font-size: 13px; color: var(--slate-light); margin-top: 8px; }
.map-overlay .map-note { font-size: 12px; color: var(--slate-light); margin-top: 16px; max-width: 400px; line-height: 1.6; }
.map-dots { position: absolute; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none; }
.map-dot {
  position: absolute; width: 10px; height: 10px; border-radius: 50%;
  background: var(--teal); border: 2px solid white; box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transform: translate(-50%, -50%);
}
.map-dot--incident { background: var(--red-reference); }

@media (max-width: 768px) {
  .map-page { grid-template-columns: 1fr; grid-template-rows: auto 1fr; }
  .map-sidebar { max-height: 40vh; }
}
</style>
