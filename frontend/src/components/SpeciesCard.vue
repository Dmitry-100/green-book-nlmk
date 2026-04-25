<template>
  <div class="species-card" @click="$router.push(`/species/${species.id}`)">
    <div class="species-card__img" :style="imgStyle">
      <div class="species-card__no-photo" v-if="!species.photo_urls?.length">{{ groupIcon }}</div>
      <div class="species-card__status" :class="statusClass" :title="statusLabel"></div>
      <div v-if="species.is_poisonous" class="species-card__poison" title="Ядовито">&#9888;</div>
    </div>
    <div class="species-card__body">
      <div class="species-card__name-ru">{{ species.name_ru }}</div>
      <div class="species-card__name-lat">{{ species.name_latin }}</div>
      <div class="species-card__tags">
        <span class="tag tag--group">{{ groupLabel }}</span>
        <span v-if="species.category === 'red_book'" class="tag tag--redbook">Красная книга</span>
        <span v-else-if="species.category === 'rare'" class="tag tag--rare">Редкий</span>
        <span v-else class="tag tag--typical">{{ categoryLabel }}</span>
        <span v-if="species.audio_url" class="tag tag--audio">Есть голос</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ species: any }>()

const GROUP_ICONS: Record<string, string> = { plants: '🌿', fungi: '🍄', insects: '🐛', herpetofauna: '🐍', birds: '🐦', mammals: '🦔' }
const GROUP_LABELS: Record<string, string> = { plants: 'Растения', fungi: 'Грибы', insects: 'Насекомые', herpetofauna: 'Герпетофауна', birds: 'Птицы', mammals: 'Млекопитающие' }
const CATEGORY_LABELS: Record<string, string> = { ruderal: 'Рудеральный', typical: 'Типичный', rare: 'Редкий', red_book: 'Красная книга', synanthropic: 'Синантроп' }

const groupIcon = computed(() => GROUP_ICONS[props.species.group] || '🌱')
const groupLabel = computed(() => GROUP_LABELS[props.species.group] || props.species.group)
const categoryLabel = computed(() => CATEGORY_LABELS[props.species.category] || props.species.category)
const imgStyle = computed(() => props.species.photo_urls?.length ? { backgroundImage: `url(${props.species.photo_urls[0]})` } : {})
const statusClass = computed(() => {
  if (props.species.category === 'red_book') return 'species-card__status--reference'
  if (props.species.category === 'rare') return 'species-card__status--potential'
  return 'species-card__status--confirmed'
})
const statusLabel = computed(() => {
  if (props.species.category === 'red_book') return 'Красная книга'
  if (props.species.category === 'rare') return 'Редкий'
  return 'Подтверждено'
})
</script>

<style scoped>
.species-card { background: #FAFBFC; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(44,62,74,0.08); cursor: pointer; transition: all 0.3s; }
.species-card:hover { box-shadow: 0 8px 32px rgba(44,62,74,0.14); transform: translateY(-4px); }
.species-card__img { height: 180px; background-size: cover; background-position: center; position: relative; background-color: #D6E0E3; }
.species-card__no-photo { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; font-size: 56px; opacity: 0.3; }
.species-card__status { position: absolute; bottom: 8px; left: 8px; width: 24px; height: 24px; border-radius: 50%; border: 2px solid white; box-shadow: 0 1px 4px rgba(0,0,0,0.2); }
.species-card__status--confirmed { background: #2A7A6E; }
.species-card__status--potential { background: #FFC107; }
.species-card__status--reference { background: #E53935; }
.species-card__poison { position: absolute; top: 8px; right: 8px; background: #FF9800; color: white; width: 26px; height: 26px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 14px; }
.species-card__body { padding: 14px 16px; }
.species-card__name-ru { font-weight: 700; font-size: 14px; color: #2C3E4A; margin-bottom: 2px; }
.species-card__name-lat { font-style: italic; font-size: 12px; color: #4A6572; font-family: 'Cormorant Garamond', serif; }
.species-card__tags { display: flex; gap: 6px; margin-top: 10px; flex-wrap: wrap; }
.tag { padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; letter-spacing: 0.3px; text-transform: uppercase; }
.tag--group { background: rgba(42,122,110,0.1); color: #2A7A6E; }
.tag--redbook { background: rgba(229,57,53,0.1); color: #E53935; }
.tag--rare { background: rgba(255,193,7,0.15); color: #F57F17; }
.tag--typical { background: rgba(139,195,74,0.15); color: #558B2F; }
.tag--audio { background: rgba(72,111,125,0.14); color: #1B4D4F; }
</style>
