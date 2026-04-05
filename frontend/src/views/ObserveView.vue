<template>
  <div class="observe-page">
    <h1>{{ form.is_incident ? 'Сообщить об инциденте' : 'Сообщить наблюдение' }}</h1>
    <p class="subtitle">{{ form.is_incident ? 'Раненое, погибшее животное или другая экстренная ситуация' : 'Расскажите, что вы встретили на территории площадки' }}</p>
    <div class="form-card">
      <!-- Group selector: 3 columns, bigger cards -->
      <div class="form-section">
        <div class="form-section__title">Что вы наблюдали? *</div>
        <div class="obs-group-grid">
          <div v-for="g in groups" :key="g.value"
               class="obs-group-card"
               :class="{ selected: form.group === g.value }"
               @click="form.group = g.value"
               :style="{ backgroundImage: `linear-gradient(to top, rgba(27,77,79,0.88) 0%, rgba(27,77,79,0.3) 60%, transparent 100%), url(${g.photo})` }">
            <span class="obs-group-card__label">{{ g.label }}</span>
          </div>
        </div>
      </div>

      <!-- Details -->
      <div class="form-section">
        <div class="form-section__title">Детали</div>
        <div class="form-row">
          <div class="form-group">
            <label>Дата и время *</label>
            <el-date-picker v-model="form.observed_at" type="datetime" style="width:100%" />
          </div>
          <div class="form-group">
            <label>Предполагаемый вид</label>
            <el-input v-model="form.species_name" placeholder="Начните вводить..." />
          </div>
        </div>
        <div class="form-group" style="margin-top:16px">
          <label>Комментарий</label>
          <el-input v-model="form.comment" type="textarea" :rows="3" placeholder="Описание: что делало, сколько особей..." />
        </div>
      </div>

      <!-- Map -->
      <div class="form-section">
        <div class="form-section__title">Место наблюдения *</div>
        <div id="observe-map" ref="mapEl" class="observe-map"></div>
        <div class="zone-info">📌 Координаты: {{ form.lat.toFixed(4) }}, {{ form.lon.toFixed(4) }}</div>
      </div>

      <!-- Photo upload -->
      <div class="form-section">
        <div class="form-section__title">Фото / Видео *</div>
        <div class="photo-upload-area">
          <div v-for="(photo, i) in photos" :key="i" class="photo-preview">
            <img :src="photo.preview" alt="photo" />
            <button class="photo-remove" @click="photos.splice(i, 1)">&times;</button>
          </div>
          <label class="photo-add">
            <input type="file" accept="image/*" multiple @change="onFileSelect" hidden />
            <span class="photo-add__icon">+</span>
            <span class="photo-add__text">Добавить фото</span>
          </label>
        </div>
      </div>

      <!-- Incident toggle -->
      <div class="form-section">
        <el-checkbox v-model="form.is_incident" label="Это инцидент (раненое/погибшее животное)" />
        <div v-if="form.is_incident" class="incident-fields">
          <el-select v-model="form.incident_type" placeholder="Тип инцидента" style="width:200px">
            <el-option label="Раненое" value="injured" />
            <el-option label="Погибшее" value="dead" />
            <el-option label="Массовая гибель" value="mass_death" />
            <el-option label="Другое" value="other" />
          </el-select>
          <el-select v-model="form.incident_severity" placeholder="Серьёзность" style="width:200px">
            <el-option label="Низкая" value="low" />
            <el-option label="Средняя" value="medium" />
            <el-option label="Высокая" value="high" />
            <el-option label="Критическая" value="critical" />
          </el-select>
        </div>
      </div>

      <!-- Safety -->
      <div class="form-section">
        <div class="safety-check">
          <el-checkbox v-model="form.safety_checked">
            <strong>Техника безопасности:</strong> Я подтверждаю соблюдение правил ТБ на территории промплощадки.
          </el-checkbox>
        </div>
      </div>

      <div class="form-actions">
        <el-button @click="$router.back()">Отмена</el-button>
        <el-button type="primary" @click="submit" :disabled="!canSubmit" :loading="submitting">
          Отправить на проверку
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '../api/client'

const router = useRouter()
const route = useRoute()
const submitting = ref(false)
const mapEl = ref<HTMLElement>()
const photos = ref<{ file: File; preview: string }[]>([])

const groups = [
  { value: 'plants', label: 'Растение', photo: '/api/media/species-pdf/page05_img02.png' },
  { value: 'fungi', label: 'Гриб', photo: '/api/media/species-pdf/page12_img00.png' },
  { value: 'insects', label: 'Насекомое', photo: '/api/media/species-pdf/page20_img04.png' },
  { value: 'herpetofauna', label: 'Герпетофауна', photo: '/api/media/species-pdf/page21_img03.png' },
  { value: 'birds', label: 'Птица', photo: '/api/media/species-pdf/page23_img07.png' },
  { value: 'mammals', label: 'Млекопитающее', photo: '/api/media/species-pdf/page29_img00.png' },
]

const form = reactive({
  group: (route.query.group as string) || '',
  observed_at: new Date(),
  species_name: '',
  comment: '',
  lat: 52.59,
  lon: 39.60,
  is_incident: route.query.incident === '1',
  incident_type: '',
  incident_severity: '',
  safety_checked: false,
})

const canSubmit = computed(() => form.group && form.safety_checked)

function onFileSelect(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (!files) return
  for (const f of Array.from(files)) {
    photos.value.push({ file: f, preview: URL.createObjectURL(f) })
  }
}

// Init Yandex Map for point selection
onMounted(async () => {
  try {
    const { data } = await api.get('/config/ymaps')
    if (!data.apiKey) return

    const loadScript = () => new Promise<void>((resolve, reject) => {
      if ((window as any).ymaps) {
        (window as any).ymaps.ready(() => resolve())
        return
      }
      const s = document.createElement('script')
      s.src = `https://api-maps.yandex.ru/2.1/?apikey=${data.apiKey}&lang=ru_RU`
      s.async = true
      s.onload = () => (window as any).ymaps.ready(() => resolve())
      s.onerror = () => reject()
      document.head.appendChild(s)
    })

    await loadScript()
    const ymaps = (window as any).ymaps

    const map = new ymaps.Map(mapEl.value!, {
      center: [form.lat, form.lon],
      zoom: 14,
      controls: ['zoomControl'],
    })

    const placemark = new ymaps.Placemark([form.lat, form.lon], {}, {
      draggable: true,
      preset: 'islands#greenDotIcon',
    })

    placemark.events.add('dragend', () => {
      const coords = placemark.geometry.getCoordinates()
      form.lat = coords[0]
      form.lon = coords[1]
    })

    map.events.add('click', (e: any) => {
      const coords = e.get('coords')
      placemark.geometry.setCoordinates(coords)
      form.lat = coords[0]
      form.lon = coords[1]
    })

    map.geoObjects.add(placemark)
  } catch {}
})

async function submit() {
  submitting.value = true
  try {
    const payload: any = {
      group: form.group,
      observed_at: new Date(form.observed_at).toISOString(),
      lat: form.lat,
      lon: form.lon,
      comment: form.comment || null,
      is_incident: form.is_incident,
      safety_checked: form.safety_checked,
    }
    if (form.is_incident) {
      payload.incident_type = form.incident_type || null
      payload.incident_severity = form.incident_severity || null
    }
    await api.post('/observations', payload)
    router.push('/my')
  } catch (e: any) {
    console.error(e)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.observe-page { max-width: 760px; margin: 0 auto; padding: 32px; }
.observe-page h1 { font-family: 'Cormorant Garamond', serif; font-size: 30px; font-weight: 600; color: #1B4D4F; }
.subtitle { font-size: 14px; color: #8FA5AB; margin-bottom: 24px; }
.form-card { background: #FAFBFC; border-radius: 20px; padding: 32px; box-shadow: 0 2px 12px rgba(44,62,74,0.08); }
.form-section { margin-bottom: 24px; padding-bottom: 24px; border-bottom: 1px solid #D6E0E3; }
.form-section:last-child { border-bottom: none; margin-bottom: 0; }
.form-section__title { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #8FA5AB; margin-bottom: 16px; }

/* Group selector — 3 columns */
.obs-group-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.obs-group-card {
  border-radius: 14px; overflow: hidden; cursor: pointer;
  background-size: cover; background-position: center;
  aspect-ratio: 1.4; display: flex; align-items: flex-end;
  transition: all 0.3s; border: 3px solid transparent;
  box-shadow: 0 2px 8px rgba(44,62,74,0.08);
}
.obs-group-card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(44,62,74,0.15); }
.obs-group-card.selected { border-color: #2A7A6E; box-shadow: 0 0 0 3px rgba(42,122,110,0.2), 0 6px 20px rgba(44,62,74,0.15); }
.obs-group-card__label { width: 100%; padding: 12px; font-size: 13px; font-weight: 700; color: white; text-transform: uppercase; letter-spacing: 0.3px; text-align: center; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-group label { font-size: 13px; font-weight: 600; color: #2C3E4A; }

/* Map */
.observe-map { width: 100%; height: 280px; border-radius: 12px; overflow: hidden; background: #D6E0E3; }
.zone-info { margin-top: 12px; padding: 10px 14px; background: rgba(42,122,110,0.06); border-radius: 6px; font-size: 13px; color: #1B4D4F; font-weight: 600; }

/* Photo upload */
.photo-upload-area { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.photo-preview {
  aspect-ratio: 1; border-radius: 12px; overflow: hidden; position: relative;
  box-shadow: 0 2px 8px rgba(44,62,74,0.1);
}
.photo-preview img { width: 100%; height: 100%; object-fit: cover; }
.photo-remove {
  position: absolute; top: 6px; right: 6px; width: 24px; height: 24px;
  border-radius: 50%; background: rgba(0,0,0,0.5); color: white; border: none;
  cursor: pointer; font-size: 14px; display: flex; align-items: center; justify-content: center;
}
.photo-add {
  aspect-ratio: 1; border: 2px dashed #B8C8CE; border-radius: 12px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 6px; cursor: pointer; transition: all 0.2s; color: #8FA5AB;
}
.photo-add:hover { border-color: #2A7A6E; color: #2A7A6E; }
.photo-add__icon { font-size: 28px; }
.photo-add__text { font-size: 11px; font-weight: 600; }

.incident-fields { display: flex; gap: 12px; margin-top: 12px; flex-wrap: wrap; }
.safety-check { padding: 16px; background: rgba(255,152,0,0.06); border: 1px solid rgba(255,152,0,0.15); border-radius: 12px; }
.safety-check :deep(.el-checkbox__label) { white-space: normal; word-break: break-word; line-height: 1.5; }
.form-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; }

@media (max-width: 768px) {
  .obs-group-grid { grid-template-columns: repeat(2, 1fr); }
  .form-row { grid-template-columns: 1fr; }
  .photo-upload-area { grid-template-columns: repeat(3, 1fr); }
}
</style>
