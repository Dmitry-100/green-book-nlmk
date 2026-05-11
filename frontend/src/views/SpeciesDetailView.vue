<template>
  <div class="detail-page" v-if="species">
    <div class="detail-header">
      <div class="detail-gallery">
        <div class="detail-gallery__main" :style="imgStyle">
          <div class="detail-gallery__no-photo" v-if="!species.photo_urls?.length">{{ groupIcon }}</div>
          <div class="detail-gallery__badges">
            <span class="detail-badge detail-badge--status">{{ groupLabel }}</span>
            <span v-if="species.conservation_status" class="detail-badge detail-badge--redbook">{{ species.conservation_status }}</span>
            <span v-if="species.is_poisonous" class="detail-badge detail-badge--poison">Ядовито</span>
          </div>
        </div>
      </div>
      <div class="detail-info">
        <h1>{{ species.name_ru }}</h1>
        <div class="latin">{{ species.name_latin }}</div>
        <div class="detail-meta">
          <div class="meta-item"><div class="meta-item__label">Группа</div><div class="meta-item__value">{{ groupLabel }}</div></div>
          <div class="meta-item"><div class="meta-item__label">Категория</div><div class="meta-item__value">{{ categoryLabel }}</div></div>
          <div class="meta-item" v-if="species.season_info"><div class="meta-item__label">Сезонность</div><div class="meta-item__value">{{ species.season_info }}</div></div>
          <div class="meta-item" v-if="species.conservation_status"><div class="meta-item__label">Охранный статус</div><div class="meta-item__value">{{ species.conservation_status }}</div></div>
        </div>
        <p v-if="species.description" class="detail-description">{{ species.description }}</p>
        <div v-if="editorialSections.length" class="field-guide">
          <div
            v-for="section in editorialSections"
            :key="section.key"
            class="field-guide__item"
          >
            <div class="field-guide__eyebrow">{{ section.eyebrow }}</div>
            <h2>{{ section.title }}</h2>
            <p>{{ section.body }}</p>
          </div>
        </div>
        <div v-if="species.audio_url" class="species-audio">
          <div class="species-audio__header">
            <div>
              <div class="species-audio__label">Голос вида</div>
              <div class="species-audio__title">{{ species.audio_title || species.name_ru }}</div>
            </div>
          </div>
          <audio class="species-audio__player" controls preload="none" :src="species.audio_url">
            Ваш браузер не поддерживает воспроизведение аудио.
          </audio>
          <div class="species-audio__source">
            <span v-if="species.audio_source">{{ species.audio_source }}</span>
            <span v-if="species.audio_source && species.audio_license"> · </span>
            <span v-if="species.audio_license">{{ species.audio_license }}</span>
          </div>
        </div>
        <div v-if="species.do_dont_rules" class="detail-rules">
          <div class="rule-card"><span class="rule-card__icon">&#9888;</span><span>{{ species.do_dont_rules }}</span></div>
        </div>
        <div v-if="discoverer" class="discoverer-block">
          <span class="discoverer-icon">🏅</span>
          <span>Первое наблюдение: <strong>{{ discoverer.display_name }}</strong>, {{ formatDate(discoverer.discovered_at) }}</span>
        </div>
        <div class="detail-actions"><router-link to="/species" class="btn btn-outline">&larr; К списку видов</router-link></div>
      </div>
    </div>

    <section class="species-observations">
      <div class="species-observations__header">
        <div>
          <div class="species-observations__eyebrow">Наблюдения пользователей</div>
          <h2>
            Находки этого вида
            <span v-if="observationsTotal !== null">{{ observationsTotal }}</span>
          </h2>
          <p>Подтвержденные находки видны всем, ваши записи на проверке тоже останутся под рукой.</p>
        </div>
        <router-link :to="observeLink" class="btn btn-primary">Сообщить наблюдение</router-link>
      </div>

      <div v-if="observationsLoading && !speciesObservations.length" class="species-observations__state">
        Загружаем наблюдения...
      </div>
      <div v-else-if="observationsError && !speciesObservations.length" class="species-observations__state species-observations__state--error">
        {{ observationsError }}
      </div>
      <div v-else-if="!speciesObservations.length" class="species-observations__empty">
        Пока нет наблюдений этого вида. Можно стать первым.
      </div>
      <div v-else class="species-observations__list">
        <router-link
          v-for="observation in speciesObservations"
          :key="observation.id"
          :to="`/observations/${observation.id}`"
          class="species-observation-card"
        >
          <div
            v-if="observation.media?.length"
            class="species-observation-card__thumb"
            :style="{ backgroundImage: `url(${observationPreviewUrl(observation)})` }"
          ></div>
          <div v-else class="species-observation-card__icon">{{ groupIcon }}</div>
          <div class="species-observation-card__body">
            <div class="species-observation-card__meta">
              <span>{{ formatDateTime(observation.observed_at) }}</span>
              <span>{{ observation.author_display_name || 'Наблюдатель' }}</span>
            </div>
            <div v-if="observation.comment" class="species-observation-card__comment">
              {{ truncateComment(observation.comment) }}
            </div>
          </div>
          <span class="species-observation-card__status" :class="'species-observation-card__status--' + observation.status">
            {{ statusLabel(observation.status) }}
          </span>
        </router-link>
      </div>
      <div v-if="observationsError && speciesObservations.length" class="species-observations__state species-observations__state--error">
        {{ observationsError }}
      </div>

      <button
        v-if="hasMoreObservations"
        type="button"
        class="species-observations__more"
        :disabled="observationsLoading"
        @click="fetchSpeciesObservations()"
      >
        {{ observationsLoading ? 'Загружаем...' : 'Показать еще' }}
      </button>
    </section>
  </div>
  <div v-else class="detail-loading">Загрузка...</div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api/client'
import { buildSpeciesEditorialSections } from '../utils/speciesEditorialSections'
import { buildObservationMediaUrl } from '../services/observationMedia'

const route = useRoute()
interface SpeciesDetail {
  id: number
  name_ru: string
  name_latin: string
  group: string
  category: string
  conservation_status?: string | null
  is_poisonous: boolean
  season_info?: string | null
  biotopes?: string | null
  description?: string | null
  do_dont_rules?: string | null
  photo_urls?: string[] | null
  audio_url?: string | null
  audio_title?: string | null
  audio_source?: string | null
  audio_license?: string | null
}
interface ObservationMedia {
  s3_key: string
  thumbnail_key?: string | null
}

interface SpeciesObservation {
  id: number
  observed_at: string
  status: string
  comment?: string | null
  author_display_name?: string | null
  media?: ObservationMedia[]
}

const species = ref<SpeciesDetail | null>(null)
const discoverer = ref<any>(null)
const speciesObservations = ref<SpeciesObservation[]>([])
const observationsTotal = ref<number | null>(null)
const observationsLoading = ref(false)
const observationsError = ref('')
const OBSERVATIONS_LIMIT = 20

const GROUP_ICONS: Record<string, string> = { plants: '🌿', fungi: '🍄', insects: '🐛', herpetofauna: '🐍', birds: '🐦', mammals: '🦔' }
const GROUP_LABELS: Record<string, string> = { plants: 'Растения', fungi: 'Грибы', insects: 'Насекомые', herpetofauna: 'Герпетофауна', birds: 'Птицы', mammals: 'Млекопитающие' }
const CATEGORY_LABELS: Record<string, string> = { ruderal: 'Рудеральный', typical: 'Типичный', rare: 'Редкий', red_book: 'Красная книга', synanthropic: 'Синантроп' }

const groupIcon = computed(() => {
  const group = species.value?.group
  return group ? GROUP_ICONS[group] || '🌱' : '🌱'
})
const groupLabel = computed(() => {
  const group = species.value?.group
  return group ? GROUP_LABELS[group] || '' : ''
})
const categoryLabel = computed(() => {
  const category = species.value?.category
  return category ? CATEGORY_LABELS[category] || '' : ''
})
const imgStyle = computed(() => species.value?.photo_urls?.length ? { backgroundImage: `url(${species.value.photo_urls[0]})` } : {})
const editorialSections = computed(() => species.value ? buildSpeciesEditorialSections(species.value) : [])
const observeLink = computed(() => species.value ? `/observe?species=${species.value.id}&group=${species.value.group}` : '/observe')
const hasMoreObservations = computed(() => (
  observationsTotal.value !== null && speciesObservations.value.length < observationsTotal.value
))

function formatDate(iso: string): string {
  const d = new Date(iso)
  const months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`
}

function formatDateTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    on_review: 'На проверке',
    needs_data: 'Нужны данные',
    confirmed: 'Подтверждено',
    rejected: 'Отклонено',
  }
  return labels[status] || status
}

function truncateComment(comment: string): string {
  return comment.length > 110 ? `${comment.slice(0, 110)}...` : comment
}

function observationPreviewUrl(observation: SpeciesObservation): string {
  const media = observation.media?.[0]
  if (!media) return ''
  return buildObservationMediaUrl(media.thumbnail_key || media.s3_key)
}

async function fetchSpeciesObservations(reset = false) {
  if (!species.value) return
  observationsLoading.value = true
  observationsError.value = ''
  const skip = reset ? 0 : speciesObservations.value.length
  try {
    const { data } = await api.get('/observations', {
      params: {
        species_id: species.value.id,
        visibility: 'accessible',
        skip,
        limit: OBSERVATIONS_LIMIT,
      },
    })
    observationsTotal.value = data.total
    speciesObservations.value = reset ? data.items : [...speciesObservations.value, ...data.items]
  } catch {
    observationsError.value = 'Не удалось загрузить наблюдения. Попробуйте обновить страницу.'
  } finally {
    observationsLoading.value = false
  }
}

onMounted(async () => {
  const { data } = await api.get(`/species/${route.params.id}`)
  species.value = data
  await fetchSpeciesObservations(true)
  try {
    const res = await api.get(`/gamification/species/${route.params.id}/discoverer`)
    if (res.data.discoverer) {
      discoverer.value = res.data.discoverer
    }
  } catch {}
})
</script>

<style scoped>
.detail-page { max-width: 1200px; margin: 0 auto; padding: 32px; }
.detail-header { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; }
.detail-gallery { border-radius: 20px; overflow: hidden; }
.detail-gallery__main { width: 100%; height: 380px; background-size: cover; background-position: center; position: relative; background-color: #D6E0E3; }
.detail-gallery__no-photo { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; font-size: 80px; opacity: 0.3; }
.detail-gallery__badges { position: absolute; top: 16px; left: 16px; display: flex; gap: 8px; }
.detail-badge { padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; backdrop-filter: blur(8px); }
.detail-badge--status { background: rgba(42,122,110,0.85); color: white; }
.detail-badge--redbook { background: rgba(229,57,53,0.85); color: white; }
.detail-badge--poison { background: rgba(255,152,0,0.85); color: white; }
.detail-info h1 { font-family: 'Cormorant Garamond', serif; font-size: 38px; font-weight: 700; color: #1B4D4F; line-height: 1.2; }
.latin { font-family: 'Cormorant Garamond', serif; font-style: italic; font-size: 20px; color: #4A6572; margin: 4px 0 20px; }
.detail-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px; }
.meta-item { background: #E8EEF0; padding: 14px 16px; border-radius: 6px; }
.meta-item__label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #8FA5AB; margin-bottom: 4px; }
.meta-item__value { font-size: 14px; font-weight: 600; color: #2C3E4A; }
.detail-description { font-size: 15px; color: #4A6572; line-height: 1.8; }
.field-guide { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 22px; }
.field-guide__item { padding: 16px; border-radius: 8px; background: #F3F7F8; border: 1px solid rgba(42,122,110,0.14); }
.field-guide__eyebrow { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #2A7A6E; margin-bottom: 6px; }
.field-guide__item h2 { margin: 0 0 8px; font-family: var(--font-body); font-size: 15px; line-height: 1.3; color: #1B4D4F; }
.field-guide__item p { margin: 0; font-size: 13px; line-height: 1.6; color: #4A6572; overflow-wrap: anywhere; }
.species-audio { margin-top: 22px; padding: 16px; border-radius: 8px; background: #E8EEF0; border: 1px solid rgba(42,122,110,0.16); }
.species-audio__header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.species-audio__label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #2A7A6E; margin-bottom: 4px; }
.species-audio__title { font-size: 15px; font-weight: 700; color: #1B4D4F; }
.species-audio__player { width: 100%; display: block; height: 36px; }
.species-audio__source { margin-top: 10px; font-size: 12px; line-height: 1.5; color: #4A6572; }
.detail-rules { margin-top: 24px; }
.rule-card { padding: 16px; border-radius: 6px; font-size: 13px; font-weight: 600; display: flex; align-items: flex-start; gap: 10px; background: rgba(255,152,0,0.08); color: #E65100; border-left: 3px solid #FF9800; }
.rule-card__icon { font-size: 18px; flex-shrink: 0; }
.detail-actions { margin-top: 24px; }
.btn { display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px; border-radius: 6px; font-size: 14px; font-weight: 600; text-decoration: none; }
.btn-outline { background: transparent; color: #2A7A6E; border: 1.5px solid #2A7A6E; }
.btn-outline:hover { background: #2A7A6E; color: white; }
.btn-primary { background: #2A7A6E; color: white; border: 1.5px solid #2A7A6E; }
.btn-primary:hover { background: #1B4D4F; border-color: #1B4D4F; }
.detail-loading { text-align: center; padding: 60px; color: #8FA5AB; }
.discoverer-block { display: flex; align-items: center; gap: 10px; margin-top: 20px; padding: 14px 16px; background: rgba(42,122,110,0.06); border-radius: 8px; border-left: 3px solid #2A7A6E; font-size: 14px; color: #1B4D4F; }
.discoverer-icon { font-size: 22px; flex-shrink: 0; }
.species-observations { margin-top: 34px; padding-top: 28px; border-top: 1px solid #D6E0E3; }
.species-observations__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 18px; }
.species-observations__eyebrow { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #2A7A6E; margin-bottom: 6px; }
.species-observations h2 { margin: 0; font-family: var(--font-display); font-size: 30px; line-height: 1.2; color: #1B4D4F; }
.species-observations h2 span { margin-left: 8px; font-family: var(--font-body); font-size: 14px; color: #8FA5AB; vertical-align: middle; }
.species-observations p { margin: 8px 0 0; color: #4A6572; font-size: 14px; line-height: 1.6; }
.species-observations__list { display: flex; flex-direction: column; gap: 10px; }
.species-observation-card { display: grid; grid-template-columns: 64px 1fr auto; gap: 14px; align-items: center; min-height: 82px; padding: 12px 14px; border: 1px solid rgba(42,122,110,0.12); border-radius: 8px; background: #FAFBFC; color: inherit; text-decoration: none; transition: box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease; }
.species-observation-card:hover { border-color: rgba(42,122,110,0.34); box-shadow: 0 8px 28px rgba(44,62,74,0.12); transform: translateY(-1px); }
.species-observation-card__thumb { width: 64px; height: 58px; border-radius: 8px; background-size: cover; background-position: center; background-color: #D6E0E3; }
.species-observation-card__icon { width: 64px; height: 58px; display: flex; align-items: center; justify-content: center; border-radius: 8px; background: #E8EEF0; font-size: 28px; }
.species-observation-card__body { min-width: 0; }
.species-observation-card__meta { display: flex; flex-wrap: wrap; gap: 8px 14px; color: #8FA5AB; font-size: 12px; font-weight: 700; }
.species-observation-card__comment { margin-top: 6px; color: #2C3E4A; font-size: 14px; line-height: 1.45; overflow-wrap: anywhere; }
.species-observation-card__status { justify-self: end; padding: 5px 12px; border-radius: 8px; font-size: 11px; font-weight: 800; white-space: nowrap; }
.species-observation-card__status--on_review { background: rgba(255,193,7,0.15); color: #F57F17; }
.species-observation-card__status--needs_data { background: rgba(33,150,243,0.12); color: #1565C0; }
.species-observation-card__status--confirmed { background: rgba(76,175,80,0.12); color: #2E7D32; }
.species-observation-card__status--rejected { background: rgba(229,57,53,0.1); color: #E53935; }
.species-observations__state,
.species-observations__empty { padding: 24px; border-radius: 8px; background: #F3F7F8; color: #4A6572; font-size: 14px; text-align: center; }
.species-observations__state--error { color: #A63A3A; background: rgba(229,57,53,0.08); }
.species-observations__more { display: block; min-height: 38px; margin: 16px auto 0; padding: 0 18px; border: 1.5px solid #2A7A6E; border-radius: 8px; background: transparent; color: #2A7A6E; font: inherit; font-size: 14px; font-weight: 800; cursor: pointer; }
.species-observations__more:hover:not(:disabled) { background: rgba(42,122,110,0.08); }
.species-observations__more:disabled { opacity: 0.6; cursor: progress; }
@media (max-width: 900px) { .field-guide { grid-template-columns: 1fr; } }
@media (max-width: 768px) {
  .detail-header { grid-template-columns: 1fr; }
  .species-observations__header { flex-direction: column; }
  .species-observation-card { grid-template-columns: 56px 1fr; align-items: start; }
  .species-observation-card__thumb,
  .species-observation-card__icon { width: 56px; height: 56px; }
  .species-observation-card__status { grid-column: 2; justify-self: start; }
}
</style>
