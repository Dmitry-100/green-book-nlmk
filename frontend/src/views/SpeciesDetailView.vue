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
        <div v-if="species.do_dont_rules" class="detail-rules">
          <div class="rule-card"><span class="rule-card__icon">&#9888;</span><span>{{ species.do_dont_rules }}</span></div>
        </div>
        <div class="detail-actions"><router-link to="/species" class="btn btn-outline">&larr; К списку видов</router-link></div>
      </div>
    </div>
  </div>
  <div v-else class="detail-loading">Загрузка...</div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api/client'

const route = useRoute()
const species = ref<any>(null)

const GROUP_ICONS: Record<string, string> = { plants: '🌿', fungi: '🍄', insects: '🐛', herpetofauna: '🐍', birds: '🐦', mammals: '🦔' }
const GROUP_LABELS: Record<string, string> = { plants: 'Растения', fungi: 'Грибы', insects: 'Насекомые', herpetofauna: 'Герпетофауна', birds: 'Птицы', mammals: 'Млекопитающие' }
const CATEGORY_LABELS: Record<string, string> = { ruderal: 'Рудеральный', typical: 'Типичный', rare: 'Редкий', red_book: 'Красная книга', synanthropic: 'Синантроп' }

const groupIcon = computed(() => GROUP_ICONS[species.value?.group] || '🌱')
const groupLabel = computed(() => GROUP_LABELS[species.value?.group] || '')
const categoryLabel = computed(() => CATEGORY_LABELS[species.value?.category] || '')
const imgStyle = computed(() => species.value?.photo_urls?.length ? { backgroundImage: `url(${species.value.photo_urls[0]})` } : {})

onMounted(async () => { const { data } = await api.get(`/species/${route.params.id}`); species.value = data })
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
.detail-rules { margin-top: 24px; }
.rule-card { padding: 16px; border-radius: 6px; font-size: 13px; font-weight: 600; display: flex; align-items: flex-start; gap: 10px; background: rgba(255,152,0,0.08); color: #E65100; border-left: 3px solid #FF9800; }
.rule-card__icon { font-size: 18px; flex-shrink: 0; }
.detail-actions { margin-top: 24px; }
.btn { display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px; border-radius: 6px; font-size: 14px; font-weight: 600; text-decoration: none; }
.btn-outline { background: transparent; color: #2A7A6E; border: 1.5px solid #2A7A6E; }
.btn-outline:hover { background: #2A7A6E; color: white; }
.detail-loading { text-align: center; padding: 60px; color: #8FA5AB; }
@media (max-width: 768px) { .detail-header { grid-template-columns: 1fr; } }
</style>
