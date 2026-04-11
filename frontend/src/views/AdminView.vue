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

    <!-- Audit trail -->
    <div v-if="activeTab === 'audit'" class="admin-section">
      <div class="admin-section__header">
        <h2>Журнал действий</h2>
        <div class="audit-header-actions">
          <el-button size="small" :loading="opsLoading || opsAlertsLoading" @click="loadOpsSnapshot(true)">Обновить сводку</el-button>
          <el-button size="small" @click="reloadAudit(true)">Обновить журнал</el-button>
        </div>
      </div>

      <div class="ops-summary" v-loading="opsLoading">
        <div class="ops-card">
          <div class="ops-card__title">Каталог</div>
          <div class="ops-card__value">{{ opsSummary?.catalog?.species_total ?? 0 }}</div>
          <div class="ops-card__hint">видов в справочнике</div>
        </div>
        <div class="ops-card">
          <div class="ops-card__title">Очередь</div>
          <div class="ops-card__value">{{ opsSummary?.pipeline?.on_review ?? 0 }}</div>
          <div class="ops-card__hint">на проверке</div>
        </div>
        <div class="ops-card">
          <div class="ops-card__title">Инциденты</div>
          <div class="ops-card__value">{{ opsSummary?.incidents?.open_incidents ?? 0 }}</div>
          <div class="ops-card__hint">открытых</div>
        </div>
        <div class="ops-card">
          <div class="ops-card__title">Аудит 24ч</div>
          <div class="ops-card__value">{{ opsSummary?.audit?.events_last_24h ?? 0 }}</div>
          <div class="ops-card__hint">событий</div>
        </div>
        <div class="ops-card">
          <div class="ops-card__title">Ошибки API</div>
          <div class="ops-card__value">{{ opsSummary?.metrics?.error_rate_percent ?? 0 }}%</div>
          <div class="ops-card__hint">error rate</div>
        </div>
      </div>

      <div class="ops-alerts" v-loading="opsAlertsLoading">
        <div class="ops-alerts__header">
          <span class="ops-alerts__title">Пороговые оповещения</span>
          <el-tag size="small" :type="opsAlertStatus === 'alert' ? 'danger' : 'success'">
            {{ opsAlertStatus === 'alert' ? 'Есть сигналы' : 'Норма' }}
          </el-tag>
        </div>
        <div v-if="opsAlerts.length === 0" class="ops-alerts__empty">
          Активных сигналов нет.
        </div>
        <div v-else class="ops-alerts__list">
          <div v-for="item in opsAlerts" :key="item.code" class="ops-alert-item">
            <div class="ops-alert-item__message">{{ item.message }}</div>
            <div class="ops-alert-item__meta">
              <span class="ops-alert-item__code">{{ item.code }}</span>
              <span class="ops-alert-item__values">факт {{ item.value }} / порог {{ item.threshold }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="audit-filters">
        <el-input
          v-model="auditFilters.action"
          placeholder="action (например, species.create)"
          clearable
          size="small"
        />
        <el-input
          v-model="auditFilters.target_type"
          placeholder="target_type (species, observation...)"
          clearable
          size="small"
        />
        <el-input
          v-model="auditFilters.actor_user_id"
          placeholder="actor_user_id"
          clearable
          size="small"
        />
        <el-select
          v-model="auditFilters.outcome"
          placeholder="outcome"
          clearable
          size="small"
        >
          <el-option label="success" value="success" />
          <el-option label="noop" value="noop" />
          <el-option label="failed" value="failed" />
        </el-select>
        <el-input
          v-model="auditFilters.request_id"
          placeholder="request_id"
          clearable
          size="small"
        />
      </div>
      <div class="audit-actions">
        <div class="audit-maintenance">
          <span class="audit-maintenance__label">Ретеншн (дни)</span>
          <el-input-number
            v-model="auditRetentionDays"
            :min="1"
            :max="36500"
            size="small"
            controls-position="right"
          />
          <el-button size="small" :loading="auditPurgeLoading" @click="previewAuditPurge">
            Проверить очистку
          </el-button>
          <el-button type="danger" size="small" :loading="auditPurgeLoading" @click="confirmAndPurgeAudit">
            Очистить старые
          </el-button>
        </div>
        <el-button size="small" @click="resetAuditFilters">Сбросить фильтры</el-button>
        <el-button type="primary" size="small" :loading="auditLoading" @click="applyAuditFilters">Применить</el-button>
      </div>

      <el-table :data="auditEvents" stripe style="width: 100%" max-height="520" v-loading="auditLoading">
        <el-table-column prop="created_at" label="Время" width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="action" label="Action" min-width="180" />
        <el-table-column prop="actor_user_id" label="Actor" width="84">
          <template #default="{ row }">
            {{ row.actor_user_id ?? '—' }}
          </template>
        </el-table-column>
        <el-table-column label="Target" min-width="150">
          <template #default="{ row }">
            {{ row.target_type }}#{{ row.target_id ?? '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="outcome" label="Outcome" width="90" />
        <el-table-column prop="details" label="Details" min-width="220">
          <template #default="{ row }">
            <span class="audit-details">{{ formatDetails(row.details) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="request_id" label="Request ID" min-width="140">
          <template #default="{ row }">
            <span class="audit-request-id">{{ row.request_id || '—' }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="audit-pagination">
        <el-pagination
          background
          layout="prev, pager, next, total"
          :current-page="auditPage"
          :page-size="auditPageSize"
          :total="auditTotal"
          @current-change="onAuditPageChange"
        />
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
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api, { clearCachedGets, getCached } from '../api/client'
import { useAuthStore } from '../stores/auth'

type AuditEvent = {
  id: number
  created_at: string
  action: string
  actor_user_id: number | null
  actor_role: string | null
  target_type: string
  target_id: number | null
  outcome: string
  details: Record<string, unknown>
  request_id: string | null
}

type OpsAlert = {
  code: string
  severity: string
  message: string
  value: number
  threshold: number
}

const auth = useAuthStore()
const activeTab = ref('species')
const speciesList = ref<any[]>([])
const showAddSpecies = ref(false)
const zoneMessage = ref('')
const zoneSuccess = ref(false)
const auditEvents = ref<AuditEvent[]>([])
const auditLoading = ref(false)
const auditPurgeLoading = ref(false)
const auditRetentionDays = ref(180)
const auditPage = ref(1)
const auditPageSize = 20
const auditTotal = ref(0)
const opsSummary = ref<any | null>(null)
const opsLoading = ref(false)
const opsAlerts = ref<OpsAlert[]>([])
const opsAlertsLoading = ref(false)
const opsAlertStatus = ref<'ok' | 'alert'>('ok')
const auditFilters = reactive({
  action: '',
  target_type: '',
  actor_user_id: '',
  outcome: '',
  request_id: '',
})

const tabs = [
  { key: 'species', icon: '📋', label: 'Виды' },
  { key: 'zones', icon: '🗺️', label: 'Зоны' },
  { key: 'users', icon: '👤', label: 'Роли' },
  { key: 'audit', icon: '🧾', label: 'Аудит' },
]

const GROUP_LABELS: Record<string, string> = { plants: 'Растения', fungi: 'Грибы', insects: 'Насекомые', herpetofauna: 'Герпетофауна', birds: 'Птицы', mammals: 'Млекопитающие' }
function groupLabel(g: string) { return GROUP_LABELS[g] || g }

const authHeaders = { Authorization: `Bearer ${auth.token || ''}` }

const newSpecies = reactive({
  name_ru: '', name_latin: '', group: 'plants', category: 'typical', is_poisonous: false,
})

async function fetchSpecies(force = false) {
  const params = { limit: 200, include_total: false }
  if (force) {
    const { data } = await api.get('/species', { params })
    speciesList.value = data.items || []
    return
  }
  const { data } = await getCached(
    '/species',
    { params },
    5 * 60 * 1000,
    'species:list:admin:200'
  )
  speciesList.value = data.items || []
}

async function addSpecies() {
  try {
    await api.post('/species', newSpecies)
    showAddSpecies.value = false
    ElMessage.success('Вид добавлен')
    clearCachedGets('species:list:')
    clearCachedGets('admin:audit:')
    clearCachedGets('admin:ops:')
    fetchSpecies(true)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Ошибка')
  }
}

async function deleteSpecies(id: number) {
  try {
    await api.delete(`/species/${id}`)
    ElMessage.success('Вид удалён')
    clearCachedGets('species:list:')
    clearCachedGets('admin:audit:')
    clearCachedGets('admin:ops:')
    fetchSpecies(true)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Ошибка')
  }
}

function buildAuditParams(): Record<string, string | number | boolean> {
  const params: Record<string, string | number | boolean> = {
    skip: (auditPage.value - 1) * auditPageSize,
    limit: auditPageSize,
    include_total: true,
  }
  const action = auditFilters.action.trim()
  if (action) {
    params.action = action
  }
  const targetType = auditFilters.target_type.trim()
  if (targetType) {
    params.target_type = targetType
  }
  const outcome = auditFilters.outcome.trim()
  if (outcome) {
    params.outcome = outcome
  }
  const requestId = auditFilters.request_id.trim()
  if (requestId) {
    params.request_id = requestId
  }
  const actorUserId = Number.parseInt(auditFilters.actor_user_id.trim(), 10)
  if (Number.isInteger(actorUserId) && actorUserId > 0) {
    params.actor_user_id = actorUserId
  }
  return params
}

function buildAuditCacheKey(params: Record<string, string | number | boolean>): string {
  const safe = {
    action: params.action || '',
    target_type: params.target_type || '',
    actor_user_id: params.actor_user_id || '',
    outcome: params.outcome || '',
    request_id: params.request_id || '',
    skip: params.skip,
    limit: params.limit,
  }
  return `admin:audit:${JSON.stringify(safe)}`
}

async function reloadAudit(force = false) {
  auditLoading.value = true
  const params = buildAuditParams()
  try {
    const response = force
      ? await api.get('/admin/audit/events', { params })
      : await getCached(
          '/admin/audit/events',
          { params },
          10 * 1000,
          buildAuditCacheKey(params)
        )
    auditEvents.value = response.data.items || []
    auditTotal.value = response.data.total ?? auditEvents.value.length
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось загрузить журнал аудита')
  } finally {
    auditLoading.value = false
  }
}

async function loadOpsSummary(force = false) {
  opsLoading.value = true
  try {
    const response = force
      ? await api.get('/admin/ops/summary')
      : await getCached(
          '/admin/ops/summary',
          {},
          10 * 1000,
          'admin:ops:summary'
        )
    opsSummary.value = response.data
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось загрузить операционную сводку')
  } finally {
    opsLoading.value = false
  }
}

async function loadOpsAlerts(force = false) {
  opsAlertsLoading.value = true
  try {
    const response = force
      ? await api.get('/admin/ops/alerts')
      : await getCached(
          '/admin/ops/alerts',
          {},
          10 * 1000,
          'admin:ops:alerts'
        )
    opsAlertStatus.value = response.data.status === 'alert' ? 'alert' : 'ok'
    opsAlerts.value = response.data.alerts || []
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось загрузить пороговые оповещения')
  } finally {
    opsAlertsLoading.value = false
  }
}

async function loadOpsSnapshot(force = false) {
  await Promise.all([loadOpsSummary(force), loadOpsAlerts(force)])
}

async function runAuditPurge(dryRun: boolean) {
  auditPurgeLoading.value = true
  try {
    const { data } = await api.post(
      '/admin/audit/purge',
      null,
      {
        params: {
          older_than_days: auditRetentionDays.value,
          dry_run: dryRun,
        },
      }
    )
    if (dryRun) {
      ElMessage.info(`Кандидатов на удаление: ${data.candidates}`)
      return
    }
    ElMessage.success(`Удалено записей: ${data.deleted}`)
    clearCachedGets('admin:audit:')
    clearCachedGets('admin:ops:')
    loadOpsSnapshot(true)
    reloadAudit(true)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Не удалось очистить audit logs')
  } finally {
    auditPurgeLoading.value = false
  }
}

function previewAuditPurge() {
  runAuditPurge(true)
}

function confirmAndPurgeAudit() {
  const confirmed = window.confirm(
    `Удалить audit-события старше ${auditRetentionDays.value} дней?`
  )
  if (!confirmed) {
    return
  }
  runAuditPurge(false)
}

function applyAuditFilters() {
  auditPage.value = 1
  clearCachedGets('admin:audit:')
  reloadAudit(true)
}

function resetAuditFilters() {
  auditFilters.action = ''
  auditFilters.target_type = ''
  auditFilters.actor_user_id = ''
  auditFilters.outcome = ''
  auditFilters.request_id = ''
  applyAuditFilters()
}

function onAuditPageChange(page: number) {
  auditPage.value = page
  reloadAudit()
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('ru-RU')
}

function formatDetails(details: Record<string, unknown> | null | undefined): string {
  if (!details || Object.keys(details).length === 0) {
    return '—'
  }
  const payload = JSON.stringify(details)
  if (payload.length <= 120) {
    return payload
  }
  return `${payload.slice(0, 117)}...`
}

function onZoneUploadSuccess(res: any) {
  zoneMessage.value = `Импортировано ${res.imported} зон из ${res.filename}`
  zoneSuccess.value = true
  clearCachedGets('admin:audit:')
  clearCachedGets('admin:ops:')
  if (activeTab.value === 'audit') {
    loadOpsSnapshot(true)
    reloadAudit(true)
  }
}

function onZoneUploadError() {
  zoneMessage.value = 'Ошибка загрузки файла'
  zoneSuccess.value = false
}

watch(activeTab, (tab) => {
  if (tab === 'species') {
    fetchSpecies()
  }
  if (tab === 'audit') {
    loadOpsSnapshot()
    reloadAudit()
  }
})

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
.audit-header-actions { display: flex; gap: 8px; }
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
.ops-summary { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; margin-bottom: 12px; }
.ops-card { border: 1px solid #D6E0E3; border-radius: 8px; padding: 10px 12px; background: #FAFBFC; }
.ops-card__title { font-size: 12px; color: var(--slate-mid); margin-bottom: 4px; }
.ops-card__value { font-size: 18px; font-weight: 700; color: var(--teal-dark); line-height: 1.1; }
.ops-card__hint { font-size: 11px; color: var(--slate-mid); margin-top: 2px; }
.ops-alerts { border: 1px solid #D6E0E3; border-radius: 8px; background: #FBFCFD; padding: 10px 12px; margin-bottom: 12px; }
.ops-alerts__header { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.ops-alerts__title { font-size: 13px; font-weight: 600; color: var(--teal-dark); }
.ops-alerts__empty { font-size: 13px; color: var(--slate-mid); }
.ops-alerts__list { display: grid; gap: 8px; }
.ops-alert-item { border: 1px solid #E2E8EA; border-radius: 8px; background: var(--white); padding: 8px 10px; }
.ops-alert-item__message { font-size: 13px; color: var(--teal-dark); line-height: 1.3; }
.ops-alert-item__meta { margin-top: 4px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.ops-alert-item__code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 11px; color: var(--teal-dark); }
.ops-alert-item__values { font-size: 11px; color: var(--slate-mid); }
.audit-filters { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; margin-bottom: 10px; }
.audit-actions { display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 12px; }
.audit-maintenance { display: flex; align-items: center; gap: 8px; margin-right: auto; }
.audit-maintenance__label { font-size: 12px; color: var(--slate-mid); }
.audit-details { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; color: var(--slate-mid); }
.audit-request-id { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; color: var(--slate-mid); }
.audit-pagination { display: flex; justify-content: flex-end; margin-top: 12px; }
@media (max-width: 1080px) {
  .ops-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .audit-filters { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 920px) {
  .audit-actions {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
  .audit-maintenance {
    width: 100%;
    flex-wrap: wrap;
  }
}
@media (max-width: 768px) { .role-info { grid-template-columns: 1fr; } }
</style>
