<template>
  <div class="admin-page">
    <h1>Администрирование</h1>

    <div class="admin-tabs">
      <button v-for="t in tabs" :key="t.key" class="admin-tab" :class="{ active: activeTab === t.key }" @click="activeTab = t.key">
        {{ t.icon }} {{ t.label }}
      </button>
    </div>

    <!-- Species Management -->
    <div v-if="activeTab === 'species'" class="admin-section">
      <div class="admin-section__header">
        <h2>Справочник видов</h2>
        <el-button type="primary" size="small" @click="showAddSpecies = true">+ Добавить вид</el-button>
      </div>
      <el-table :data="speciesList" stripe style="width: 100%" max-height="500">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name_ru" label="Название (RU)" min-width="180" />
        <el-table-column prop="name_latin" label="Латинское" min-width="180" />
        <el-table-column prop="group" label="Группа" width="130">
          <template #default="{ row }">{{ groupLabel(row.group) }}</template>
        </el-table-column>
        <el-table-column prop="category" label="Категория" width="130" />
        <el-table-column prop="is_poisonous" label="Ядовит" width="80">
          <template #default="{ row }">{{ row.is_poisonous ? '⚠️' : '' }}</template>
        </el-table-column>
        <el-table-column label="" width="80">
          <template #default="{ row }">
            <el-button type="danger" size="small" text @click="deleteSpecies(row.id)">✕</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Zone Import -->
    <div v-if="activeTab === 'zones'" class="admin-section">
      <h2>Импорт зон площадки</h2>
      <p class="admin-hint">Загрузите GeoJSON-файл с полигонами зон промплощадки.</p>
      <div class="upload-area">
        <el-upload
          action="/api/admin/zones/import"
          :headers="authHeaders"
          accept=".geojson,.json"
          :on-success="onZoneUploadSuccess"
          :on-error="onZoneUploadError"
          drag
        >
          <div class="upload-content">
            <span style="font-size: 36px">📁</span>
            <p>Перетащите GeoJSON-файл или нажмите для выбора</p>
            <p class="upload-hint">Поддерживаемые форматы: .geojson, .json</p>
          </div>
        </el-upload>
      </div>
      <div v-if="zoneMessage" class="zone-message" :class="{ success: zoneSuccess }">{{ zoneMessage }}</div>
    </div>

    <!-- Users / Roles -->
    <div v-if="activeTab === 'users'" class="admin-section">
      <h2>Управление ролями</h2>
      <p class="admin-hint">Роли назначаются при первом входе через SSO. Здесь можно повысить сотрудника до эколога или администратора.</p>
      <div class="role-info">
        <div class="role-card">
          <h4>Employee</h4>
          <p>Создаёт наблюдения, видит карту и справочник</p>
        </div>
        <div class="role-card">
          <h4>Ecologist</h4>
          <p>Валидирует наблюдения, экспорт данных, управление чувствительностью</p>
        </div>
        <div class="role-card">
          <h4>Admin</h4>
          <p>Управление справочниками, ролями, импорт зон</p>
        </div>
      </div>
    </div>

    <!-- Add Species Dialog -->
    <el-dialog v-model="showAddSpecies" title="Добавить вид" width="500px">
      <el-form label-position="top">
        <el-form-item label="Название (RU)">
          <el-input v-model="newSpecies.name_ru" />
        </el-form-item>
        <el-form-item label="Латинское название">
          <el-input v-model="newSpecies.name_latin" />
        </el-form-item>
        <el-form-item label="Группа">
          <el-select v-model="newSpecies.group" style="width: 100%">
            <el-option label="Растения" value="plants" />
            <el-option label="Грибы" value="fungi" />
            <el-option label="Насекомые" value="insects" />
            <el-option label="Герпетофауна" value="herpetofauna" />
            <el-option label="Птицы" value="birds" />
            <el-option label="Млекопитающие" value="mammals" />
          </el-select>
        </el-form-item>
        <el-form-item label="Категория">
          <el-select v-model="newSpecies.category" style="width: 100%">
            <el-option label="Рудеральный" value="ruderal" />
            <el-option label="Типичный" value="typical" />
            <el-option label="Редкий" value="rare" />
            <el-option label="Красная книга" value="red_book" />
            <el-option label="Синантроп" value="synanthropic" />
          </el-select>
        </el-form-item>
        <el-form-item label="Ядовит">
          <el-checkbox v-model="newSpecies.is_poisonous" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddSpecies = false">Отмена</el-button>
        <el-button type="primary" @click="addSpecies">Добавить</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const activeTab = ref('species')
const speciesList = ref<any[]>([])
const showAddSpecies = ref(false)
const zoneMessage = ref('')
const zoneSuccess = ref(false)

const tabs = [
  { key: 'species', icon: '📋', label: 'Виды' },
  { key: 'zones', icon: '🗺️', label: 'Зоны' },
  { key: 'users', icon: '👤', label: 'Роли' },
]

const GROUP_LABELS: Record<string, string> = { plants: 'Растения', fungi: 'Грибы', insects: 'Насекомые', herpetofauna: 'Герпетофауна', birds: 'Птицы', mammals: 'Млекопитающие' }
function groupLabel(g: string) { return GROUP_LABELS[g] || g }

const authHeaders = { Authorization: `Bearer ${auth.token || ''}` }

const newSpecies = reactive({
  name_ru: '', name_latin: '', group: 'plants', category: 'typical', is_poisonous: false,
})

async function fetchSpecies() {
  const { data } = await api.get('/species', { params: { limit: 200 } })
  speciesList.value = data.items
}

async function addSpecies() {
  try {
    await api.post('/species', newSpecies)
    showAddSpecies.value = false
    ElMessage.success('Вид добавлен')
    fetchSpecies()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Ошибка')
  }
}

async function deleteSpecies(id: number) {
  try {
    await api.delete(`/species/${id}`)
    ElMessage.success('Вид удалён')
    fetchSpecies()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Ошибка')
  }
}

function onZoneUploadSuccess(res: any) {
  zoneMessage.value = `Импортировано ${res.imported} зон из ${res.filename}`
  zoneSuccess.value = true
}

function onZoneUploadError() {
  zoneMessage.value = 'Ошибка загрузки файла'
  zoneSuccess.value = false
}

onMounted(fetchSpecies)
</script>

<style scoped>
.admin-page { max-width: 1000px; margin: 0 auto; padding: 32px; }
.admin-page h1 { font-family: var(--font-display); font-size: 30px; font-weight: 600; color: var(--teal-dark); margin-bottom: 20px; }
.admin-tabs { display: flex; gap: 4px; margin-bottom: 24px; background: var(--slate-bg); border-radius: 12px; padding: 4px; }
.admin-tab { padding: 10px 20px; border: none; background: transparent; font-size: 13px; font-weight: 600; color: var(--slate-mid); cursor: pointer; border-radius: 8px; transition: all 0.2s; }
.admin-tab.active { background: var(--white); color: var(--teal-dark); box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.admin-section { background: var(--white); border-radius: var(--radius-lg); padding: 28px; box-shadow: var(--shadow-card); }
.admin-section__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.admin-section h2 { font-family: var(--font-display); font-size: 22px; font-weight: 600; color: var(--teal-dark); margin-bottom: 12px; }
.admin-hint { font-size: 14px; color: var(--slate-mid); margin-bottom: 20px; }
.upload-area { margin-bottom: 16px; }
.upload-content { padding: 40px; text-align: center; color: var(--slate-mid); }
.upload-content p { margin-top: 8px; font-size: 14px; }
.upload-hint { font-size: 12px; color: var(--slate-light); }
.zone-message { padding: 12px 16px; border-radius: 8px; font-size: 14px; margin-top: 12px; background: rgba(229,57,53,0.1); color: var(--red-reference); }
.zone-message.success { background: rgba(76,175,80,0.1); color: #2E7D32; }
.role-info { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.role-card { background: var(--slate-bg); padding: 20px; border-radius: 12px; }
.role-card h4 { font-size: 16px; font-weight: 700; color: var(--teal-dark); margin-bottom: 8px; }
.role-card p { font-size: 13px; color: var(--slate-mid); }
@media (max-width: 768px) { .role-info { grid-template-columns: 1fr; } }
</style>
