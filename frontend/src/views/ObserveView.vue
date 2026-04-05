<template>
  <div class="observe-page">
    <h1>{{ form.is_incident ? 'Сообщить об инциденте' : 'Сообщить наблюдение' }}</h1>
    <p class="subtitle">{{ form.is_incident ? 'Раненое, погибшее животное или другая экстренная ситуация' : 'Расскажите, что вы встретили на территории площадки' }}</p>
    <div class="form-card">
      <div class="form-section">
        <div class="form-section__title">Что вы наблюдали? *</div>
        <div class="obs-group-selector">
          <div v-for="g in groups" :key="g.value"
               class="obs-group-card"
               :class="{ selected: form.group === g.value }"
               @click="form.group = g.value"
               :style="{ backgroundImage: `linear-gradient(to top, rgba(27,77,79,0.85) 0%, rgba(27,77,79,0.3) 55%, transparent 100%), url(${g.photo})` }">
            <span class="obs-group-card__label">{{ g.label }}</span>
          </div>
        </div>
      </div>
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
      <div class="form-section">
        <div class="form-section__title">Место наблюдения *</div>
        <div class="map-placeholder">
          <span style="font-size:32px">📍</span>
          <span>Нажмите на карту или используйте геолокацию</span>
          <span class="hint">Яндекс Карты будут подключены позже</span>
        </div>
        <div class="zone-info">📌 Координаты: {{ form.lat.toFixed(4) }}, {{ form.lon.toFixed(4) }}</div>
      </div>
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
import { ref, reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '../api/client'

const router = useRouter()
const submitting = ref(false)

const groups = [
  { value: 'plants', icon: '🌿', label: 'Растение', photo: '/api/media/species-pdf/page05_img02.png' },
  { value: 'fungi', icon: '🍄', label: 'Гриб', photo: '/api/media/species-pdf/page12_img00.png' },
  { value: 'insects', icon: '🐛', label: 'Насекомое', photo: '/api/media/species-pdf/page20_img04.png' },
  { value: 'herpetofauna', icon: '🐍', label: 'Герпетофауна', photo: '/api/media/species-pdf/page21_img03.png' },
  { value: 'birds', icon: '🐦', label: 'Птица', photo: '/api/media/species-pdf/page23_img07.png' },
  { value: 'mammals', icon: '🦔', label: 'Млекопитающее', photo: '/api/media/species-pdf/page29_img00.png' },
]

const route = useRoute()

const form = reactive({
  group: (route.query.group as string) || '',
  observed_at: new Date(),
  species_name: '',
  comment: '',
  lat: 52.6,
  lon: 39.6,
  is_incident: route.query.incident === '1',
  incident_type: '',
  incident_severity: '',
  safety_checked: false,
})

const canSubmit = computed(() => form.group && form.safety_checked)

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
.observe-page { max-width: 720px; margin: 0 auto; padding: 32px; }
.observe-page h1 { font-family: 'Cormorant Garamond', serif; font-size: 30px; font-weight: 600; color: #1B4D4F; }
.subtitle { font-size: 14px; color: #8FA5AB; margin-bottom: 24px; }
.form-card { background: #FAFBFC; border-radius: 20px; padding: 32px; box-shadow: 0 2px 12px rgba(44,62,74,0.08); }
.form-section { margin-bottom: 24px; padding-bottom: 24px; border-bottom: 1px solid #D6E0E3; }
.form-section:last-child { border-bottom: none; margin-bottom: 0; }
.form-section__title { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #8FA5AB; margin-bottom: 16px; }
.obs-group-selector { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; }
.obs-group-card {
  border-radius: 12px; overflow: hidden; cursor: pointer;
  background-size: cover; background-position: center;
  aspect-ratio: 1; display: flex; align-items: flex-end;
  transition: all 0.3s; border: 3px solid transparent;
  box-shadow: 0 2px 8px rgba(44,62,74,0.08);
}
.obs-group-card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(44,62,74,0.15); }
.obs-group-card.selected { border-color: #2A7A6E; box-shadow: 0 0 0 3px rgba(42,122,110,0.2), 0 6px 20px rgba(44,62,74,0.15); }
.obs-group-card__label { width: 100%; padding: 10px; font-size: 11px; font-weight: 700; color: white; text-transform: uppercase; letter-spacing: 0.3px; text-align: center; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-group label { font-size: 13px; font-weight: 600; color: #2C3E4A; }
.map-placeholder { width: 100%; height: 200px; background: linear-gradient(135deg, #D6E0E3, #B8C8CE); border-radius: 12px; border: 1.5px dashed #B8C8CE; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: #4A6572; font-size: 13px; font-weight: 600; }
.map-placeholder .hint { font-size: 11px; color: #8FA5AB; font-weight: 400; }
.zone-info { margin-top: 12px; padding: 10px 14px; background: rgba(42,122,110,0.06); border-radius: 6px; font-size: 13px; color: #1B4D4F; font-weight: 600; }
.incident-fields { display: flex; gap: 12px; margin-top: 12px; }
.safety-check { padding: 16px; background: rgba(255,152,0,0.06); border: 1px solid rgba(255,152,0,0.15); border-radius: 12px; }
.form-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; }
@media (max-width: 768px) { .group-selector { grid-template-columns: repeat(3, 1fr); } .form-row { grid-template-columns: 1fr; } }
</style>
