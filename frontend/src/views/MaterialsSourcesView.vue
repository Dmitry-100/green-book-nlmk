<template>
  <div class="sources-page">
    <PageHero
      title="Источники материалов"
      subtitle="Авторы, лицензии и условия использования фото и аудио"
      icon="i"
      kicker="Материалы"
      compact
    />

    <div class="sources-page__content">
      <section class="sources-intro">
        <h2>Атрибуция открытых материалов</h2>
        <p>
          Фото и аудио из открытых источников используются с указанием автора,
          страницы файла и лицензии. Материалы с ограничениями NC/ND или без
          разрешения не публикуются до отдельного согласования.
        </p>
      </section>

      <div class="sources-toolbar">
        <label>
          <span>Поиск</span>
          <input v-model.trim="query" type="search" placeholder="Вид, автор, лицензия" />
        </label>
        <label>
          <span>Тип</span>
          <select v-model="selectedType">
            <option value="all">Все материалы</option>
            <option value="species_image">Фото видов</option>
            <option value="exhibition_image">Фото выставки</option>
            <option value="species_audio">Аудио видов</option>
            <option value="frontend_image">Оформление</option>
          </select>
        </label>
      </div>

      <div class="sources-summary">
        <div>
          <strong>{{ filteredAttributions.length }}</strong>
          <span>записей</span>
        </div>
        <div>
          <strong>{{ attributionRequiredCount }}</strong>
          <span>требуют атрибуции</span>
        </div>
        <div>
          <strong>{{ shareAlikeCount }}</strong>
          <span>CC BY-SA / GFDL</span>
        </div>
      </div>

      <div class="sources-list">
        <article v-for="item in filteredAttributions" :key="item.assetId" class="source-row">
          <div class="source-row__main">
            <div class="source-row__type">{{ typeLabel(item.type) }}</div>
            <h3>{{ item.nameRu || sectionLabel(item.section) }}</h3>
            <div v-if="item.nameLatin" class="source-row__latin">{{ item.nameLatin }}</div>
            <p v-if="item.author"><strong>Автор:</strong> {{ item.author }}</p>
            <p v-if="item.changeNote"><strong>Изменения:</strong> {{ item.changeNote }}</p>
          </div>
          <div class="source-row__links">
            <a
              v-if="sourceHref(item)"
              :href="sourceHref(item)"
              target="_blank"
              rel="noopener noreferrer"
            >
              Страница источника
            </a>
            <a
              v-if="item.licenseUrl"
              :href="item.licenseUrl"
              target="_blank"
              rel="noopener noreferrer"
            >
              {{ item.license }}
            </a>
            <span v-else>{{ item.license || 'Лицензия не указана' }}</span>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHero from '../components/PageHero.vue'
import { mediaAttributions, type MediaAttribution } from '../data/mediaAttributionsGenerated'

const route = useRoute()
const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
const selectedType = ref('all')

const filteredAttributions = computed(() => {
  const needle = query.value.toLocaleLowerCase('ru-RU')
  return mediaAttributions.filter((item) => {
    if (selectedType.value !== 'all' && item.type !== selectedType.value) return false
    if (!needle) return true
    return [
      item.nameRu,
      item.nameLatin,
      item.author,
      item.license,
      item.sourcePage,
      item.sourceUrl,
    ].some((value) => value.toLocaleLowerCase('ru-RU').includes(needle))
  })
})

const attributionRequiredCount = computed(() => (
  mediaAttributions.filter((item) => item.attributionRequired).length
))
const shareAlikeCount = computed(() => (
  mediaAttributions.filter((item) => /BY-SA|GFDL/i.test(item.license)).length
))

function sourceHref(item: MediaAttribution): string {
  if (item.sourcePage?.startsWith('http')) return item.sourcePage
  if (item.sourceUrl?.startsWith('http')) return item.sourceUrl
  return ''
}

function typeLabel(type: string): string {
  const labels: Record<string, string> = {
    species_image: 'Фото вида',
    exhibition_image: 'Фото выставки',
    species_audio: 'Аудио',
    frontend_image: 'Оформление',
  }
  return labels[type] || type
}

function sectionLabel(section: string): string {
  const labels: Record<string, string> = {
    'home hero': 'Титульный экран',
    'group cover': 'Обложка группы',
    'photo exhibition': 'Выставка',
    'species catalog': 'Каталог видов',
  }
  return labels[section] || section
}
</script>

<style scoped>
.sources-page { padding: 0 0 32px; }
.sources-page__content { max-width: 1120px; margin: 0 auto; padding: 28px 32px 32px; }
.sources-intro { margin-bottom: 20px; }
.sources-intro h2 { margin: 0 0 8px; font-family: var(--font-display); font-size: 30px; color: var(--teal-dark); }
.sources-intro p { margin: 0; max-width: 780px; color: var(--slate-mid); font-size: 15px; line-height: 1.7; }
.sources-toolbar { display: grid; grid-template-columns: 1fr 240px; gap: 14px; margin: 22px 0; }
.sources-toolbar label { display: flex; flex-direction: column; gap: 6px; color: var(--slate-deep); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; }
.sources-toolbar input,
.sources-toolbar select {
  min-height: 42px;
  border: 1px solid #D6E0E3;
  border-radius: 8px;
  padding: 0 12px;
  background: #FFFFFF;
  color: var(--slate-deep);
  font: inherit;
  font-size: 14px;
  text-transform: none;
  letter-spacing: 0;
}
.sources-summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 18px; }
.sources-summary div { padding: 16px; border-radius: 8px; background: #F3F7F8; border: 1px solid rgba(42,122,110,0.14); }
.sources-summary strong { display: block; color: var(--teal-dark); font-size: 26px; line-height: 1; }
.sources-summary span { display: block; margin-top: 6px; color: var(--slate-mid); font-size: 13px; font-weight: 700; }
.sources-list { display: flex; flex-direction: column; gap: 10px; }
.source-row {
  display: grid;
  grid-template-columns: 1fr minmax(220px, 280px);
  gap: 16px;
  padding: 16px;
  border: 1px solid rgba(42,122,110,0.14);
  border-radius: 8px;
  background: #FFFFFF;
  box-shadow: var(--shadow-soft);
}
.source-row__type { margin-bottom: 6px; color: var(--teal); font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.7px; }
.source-row h3 { margin: 0; color: var(--teal-dark); font-size: 18px; line-height: 1.3; }
.source-row__latin { margin-top: 3px; color: var(--slate-light); font-family: var(--font-display); font-size: 15px; font-style: italic; }
.source-row p { margin: 8px 0 0; color: var(--slate-mid); font-size: 13px; line-height: 1.55; }
.source-row__links { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; font-size: 13px; }
.source-row__links a { color: var(--teal); font-weight: 800; overflow-wrap: anywhere; }
.source-row__links span { color: var(--slate-mid); font-weight: 700; }
@media (max-width: 768px) {
  .sources-page__content { padding: 24px 18px 28px; }
  .sources-toolbar,
  .sources-summary,
  .source-row { grid-template-columns: 1fr; }
}
</style>
