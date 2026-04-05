<template>
  <div class="identify-page">
    <h1>Определитель видов</h1>
    <p class="subtitle">Не знаете, что встретили? Ответьте на несколько вопросов</p>

    <!-- Step 1: Select group -->
    <div v-if="step === 1" class="step-card">
      <h2>Шаг 1: Что вы видели?</h2>
      <div class="id-group-selector">
        <div v-for="g in groups" :key="g.value" class="id-group-card" @click="selectGroup(g.value)"
             :style="{ backgroundImage: `linear-gradient(to top, rgba(27,77,79,0.9) 0%, rgba(27,77,79,0.3) 60%, transparent 100%), url(${g.photo})` }">
          <div class="id-group-card__content">
            <div class="id-group-card__label">{{ g.label }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 2: Show species for selected group -->
    <div v-if="step === 2" class="step-card">
      <h2>Шаг 2: Похож ли на один из этих видов?</h2>
      <p class="step-hint">Группа: {{ selectedGroupLabel }}</p>
      <div class="species-grid">
        <div v-for="s in suggestions" :key="s.id" class="species-tile" @click="selectSpecies(s)">
          <div class="species-tile__img" :style="s.photo_urls?.length ? { backgroundImage: `url(${s.photo_urls[0]})` } : {}">
            <div v-if="!s.photo_urls?.length" class="species-tile__fallback">🔍</div>
            <div class="species-tile__badges">
              <span v-if="s.is_poisonous" class="tile-badge tile-badge--poison">Ядовит</span>
              <span v-if="s.conservation_status" class="tile-badge tile-badge--redbook">КК</span>
            </div>
          </div>
          <div class="species-tile__body">
            <strong>{{ s.name_ru }}</strong>
            <span class="species-tile__latin">{{ s.name_latin }}</span>
          </div>
        </div>
      </div>
      <div class="step-actions">
        <el-button @click="step = 1">Назад</el-button>
        <el-button type="primary" @click="createWithUnknown">Не нашёл — создать наблюдение</el-button>
      </div>
    </div>

    <!-- Step 3: Selected -->
    <div v-if="step === 3" class="step-card">
      <h2>Отлично!</h2>
      <p>Вы выбрали: <strong>{{ selectedSpecies?.name_ru }}</strong> ({{ selectedSpecies?.name_latin }})</p>
      <div class="step-actions">
        <el-button @click="step = 2">Назад</el-button>
        <router-link :to="`/observe?species=${selectedSpecies?.id}&group=${selectedGroup}`" class="btn-primary">
          Создать наблюдение с этим видом
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '../api/client'

const step = ref(1)
const selectedGroup = ref('')
const selectedGroupLabel = ref('')
const suggestions = ref<any[]>([])
const selectedSpecies = ref<any>(null)

const groups = [
  { value: 'plants', icon: '🌿', label: 'Растение', photo: '/api/media/species-pdf/page05_img02.png' },
  { value: 'fungi', icon: '🍄', label: 'Гриб', photo: '/api/media/species-pdf/page12_img00.png' },
  { value: 'insects', icon: '🐛', label: 'Насекомое', photo: '/api/media/species-pdf/page20_img04.png' },
  { value: 'herpetofauna', icon: '🐍', label: 'Герпетофауна', photo: '/api/media/species-pdf/page21_img03.png' },
  { value: 'birds', icon: '🐦', label: 'Птица', photo: '/api/media/species-pdf/page23_img07.png' },
  { value: 'mammals', icon: '🦔', label: 'Млекопитающее', photo: '/api/media/species-pdf/page29_img00.png' },
]

async function selectGroup(group: string) {
  selectedGroup.value = group
  selectedGroupLabel.value = groups.find(g => g.value === group)?.label || group
  const { data } = await api.get('/species', { params: { group, limit: 200 } })
  suggestions.value = data.items
  step.value = 2
}

function selectSpecies(species: any) {
  selectedSpecies.value = species
  step.value = 3
}

function createWithUnknown() {
  window.location.href = `/observe?group=${selectedGroup.value}`
}
</script>

<style scoped>
.identify-page { max-width: 800px; margin: 0 auto; padding: 32px; }
.identify-page h1 { font-family: 'Cormorant Garamond', serif; font-size: 30px; font-weight: 600; color: #1B4D4F; }
.subtitle { font-size: 14px; color: #8FA5AB; margin-bottom: 24px; }
.step-card { background: #FAFBFC; border-radius: 20px; padding: 32px; box-shadow: 0 2px 12px rgba(44,62,74,0.08); }
.step-card h2 { font-family: 'Cormorant Garamond', serif; font-size: 22px; color: #1B4D4F; margin-bottom: 20px; }
.step-hint { font-size: 13px; color: #8FA5AB; margin-bottom: 16px; }
.id-group-selector { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.id-group-card {
  border-radius: 16px; overflow: hidden; cursor: pointer;
  background-size: cover; background-position: center;
  aspect-ratio: 1.3; display: flex; align-items: flex-end;
  transition: all 0.3s; box-shadow: 0 2px 12px rgba(44,62,74,0.1);
}
.id-group-card:hover { transform: translateY(-4px); box-shadow: 0 8px 32px rgba(44,62,74,0.2); }
.id-group-card__content { width: 100%; padding: 20px; }
.id-group-card__label { font-size: 16px; font-weight: 700; color: white; text-transform: uppercase; letter-spacing: 0.5px; }
.species-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px;
  max-height: 500px; overflow-y: auto; padding: 4px;
}
.species-tile {
  background: #FAFBFC; border-radius: 12px; overflow: hidden;
  box-shadow: 0 2px 8px rgba(44,62,74,0.06); cursor: pointer;
  transition: all 0.3s; border: 2px solid transparent;
}
.species-tile:hover { border-color: #2A7A6E; box-shadow: 0 6px 24px rgba(44,62,74,0.12); transform: translateY(-3px); }
.species-tile__img {
  height: 140px; background-size: cover; background-position: center;
  background-color: #D6E0E3; position: relative;
}
.species-tile__fallback { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 40px; opacity: 0.25; }
.species-tile__badges { position: absolute; top: 6px; right: 6px; display: flex; gap: 4px; }
.tile-badge { padding: 2px 8px; border-radius: 4px; font-size: 9px; font-weight: 700; backdrop-filter: blur(4px); }
.tile-badge--poison { background: rgba(255,152,0,0.85); color: white; }
.tile-badge--redbook { background: rgba(229,57,53,0.85); color: white; }
.species-tile__body { padding: 10px 12px; }
.species-tile__body strong { display: block; font-size: 13px; color: #2C3E4A; margin-bottom: 2px; }
.species-tile__latin { font-style: italic; font-size: 11px; color: #8FA5AB; font-family: 'Cormorant Garamond', serif; }
.step-actions { display: flex; gap: 12px; margin-top: 24px; justify-content: flex-end; }
.btn-primary { padding: 10px 20px; background: #2A7A6E; color: white; border-radius: 6px; text-decoration: none; font-size: 14px; font-weight: 600; display: inline-flex; align-items: center; }
.btn-primary:hover { background: #3DAA8E; }
</style>
