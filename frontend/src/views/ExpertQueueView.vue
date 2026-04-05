<template>
  <div class="expert-page">
    <h1>Кабинет эколога</h1>
    <p class="subtitle">Очередь валидации наблюдений</p>

    <div class="queue-tabs">
      <button v-for="t in tabs" :key="t.value" class="queue-tab" :class="{ active: activeTab === t.value }" @click="activeTab = t.value; fetchQueue()">
        {{ t.label }} <span class="queue-tab__count" v-if="t.count">{{ t.count }}</span>
      </button>
    </div>

    <div class="queue-list">
      <div v-for="obs in observations" :key="obs.id" class="queue-item">
        <div class="queue-item__header">
          <span class="queue-item__icon">{{ groupIcon(obs.group) }}</span>
          <div class="queue-item__info">
            <h4>#{{ obs.id }} — {{ groupLabel(obs.group) }}</h4>
            <p>{{ new Date(obs.observed_at).toLocaleDateString('ru') }} | {{ obs.comment || 'Без комментария' }}</p>
          </div>
          <span v-if="obs.is_incident" class="incident-badge">Инцидент</span>
        </div>

        <div v-if="activeTab === 'on_review'" class="queue-item__actions">
          <el-button type="success" size="small" @click="confirm(obs.id)">Подтвердить</el-button>
          <el-button type="warning" size="small" @click="openRequestData(obs.id)">Запросить данные</el-button>
          <el-button type="danger" size="small" @click="openReject(obs.id)">Отклонить</el-button>
        </div>
      </div>
    </div>

    <div v-if="observations.length === 0 && !loading" class="empty">Очередь пуста</div>

    <!-- Request Data Dialog -->
    <el-dialog v-model="showRequestDialog" title="Запросить уточнения" width="400px">
      <el-input v-model="actionComment" type="textarea" :rows="3" placeholder="Что нужно уточнить?" />
      <template #footer>
        <el-button @click="showRequestDialog = false">Отмена</el-button>
        <el-button type="primary" @click="requestData()">Отправить</el-button>
      </template>
    </el-dialog>

    <!-- Reject Dialog -->
    <el-dialog v-model="showRejectDialog" title="Отклонить наблюдение" width="400px">
      <el-input v-model="actionComment" type="textarea" :rows="3" placeholder="Причина отклонения" />
      <template #footer>
        <el-button @click="showRejectDialog = false">Отмена</el-button>
        <el-button type="danger" @click="reject()">Отклонить</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import api from '../api/client'

const observations = ref<any[]>([])
const loading = ref(false)
const activeTab = ref('on_review')
const showRequestDialog = ref(false)
const showRejectDialog = ref(false)
const actionComment = ref('')
const selectedObsId = ref<number>(0)

const tabs = reactive([
  { value: 'on_review', label: 'Новые', count: 0 },
  { value: 'needs_data', label: 'На уточнении', count: 0 },
  { value: 'confirmed', label: 'Подтверждено', count: 0 },
  { value: 'rejected', label: 'Отклонено', count: 0 },
])

const GROUP_ICONS: Record<string, string> = { plants: '🌿', fungi: '🍄', insects: '🐛', herpetofauna: '🐍', birds: '🐦', mammals: '🦔' }
const GROUP_LABELS: Record<string, string> = { plants: 'Растение', fungi: 'Гриб', insects: 'Насекомое', herpetofauna: 'Герпетофауна', birds: 'Птица', mammals: 'Млекопитающее' }

function groupIcon(g: string) { return GROUP_ICONS[g] || '🌱' }
function groupLabel(g: string) { return GROUP_LABELS[g] || g }

async function fetchQueue() {
  loading.value = true
  const { data } = await api.get('/validation/queue', { params: { status: activeTab.value } })
  observations.value = data.items
  loading.value = false
}

async function confirm(obsId: number) {
  await api.post(`/validation/${obsId}/confirm`, { comment: 'Подтверждено' })
  fetchQueue()
}

function openRequestData(obsId: number) {
  selectedObsId.value = obsId
  actionComment.value = ''
  showRequestDialog.value = true
}

async function requestData() {
  await api.post(`/validation/${selectedObsId.value}/request-data`, { comment: actionComment.value })
  showRequestDialog.value = false
  fetchQueue()
}

function openReject(obsId: number) {
  selectedObsId.value = obsId
  actionComment.value = ''
  showRejectDialog.value = true
}

async function reject() {
  await api.post(`/validation/${selectedObsId.value}/reject`, { comment: actionComment.value })
  showRejectDialog.value = false
  fetchQueue()
}

onMounted(fetchQueue)
</script>

<style scoped>
.expert-page { max-width: 900px; margin: 0 auto; padding: 32px; }
.expert-page h1 { font-family: 'Cormorant Garamond', serif; font-size: 30px; font-weight: 600; color: #1B4D4F; }
.subtitle { font-size: 14px; color: #8FA5AB; margin-bottom: 20px; }
.queue-tabs { display: flex; gap: 4px; margin-bottom: 24px; background: #E8EEF0; border-radius: 12px; padding: 4px; }
.queue-tab { padding: 10px 20px; border: none; background: transparent; font-size: 13px; font-weight: 600; color: #4A6572; cursor: pointer; border-radius: 8px; transition: all 0.2s; display: flex; align-items: center; gap: 6px; }
.queue-tab.active { background: #FAFBFC; color: #1B4D4F; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.queue-tab__count { background: rgba(42,122,110,0.15); color: #2A7A6E; padding: 1px 8px; border-radius: 10px; font-size: 11px; }
.queue-list { display: flex; flex-direction: column; gap: 12px; }
.queue-item { background: #FAFBFC; border-radius: 12px; padding: 20px; box-shadow: 0 2px 12px rgba(44,62,74,0.08); }
.queue-item__header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.queue-item__icon { font-size: 28px; }
.queue-item__info h4 { font-size: 15px; font-weight: 700; color: #2C3E4A; }
.queue-item__info p { font-size: 12px; color: #8FA5AB; margin-top: 2px; }
.incident-badge { background: rgba(229,57,53,0.1); color: #E53935; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; margin-left: auto; }
.queue-item__actions { display: flex; gap: 8px; }
.empty { text-align: center; padding: 60px; color: #8FA5AB; font-size: 16px; }
</style>
