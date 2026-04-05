<template>
  <div class="my-obs-page">
    <h1>Мои наблюдения</h1>
    <div class="filters">
      <el-select v-model="statusFilter" placeholder="Статус" clearable @change="fetchObs">
        <el-option label="На проверке" value="on_review" />
        <el-option label="Нужны данные" value="needs_data" />
        <el-option label="Подтверждено" value="confirmed" />
        <el-option label="Отклонено" value="rejected" />
      </el-select>
      <router-link to="/observe" class="btn-add">+ Новое наблюдение</router-link>
    </div>
    <div class="obs-list">
      <div v-for="obs in observations" :key="obs.id" class="obs-item" @click="$router.push(`/observations/${obs.id}`)">
        <div class="obs-item__icon">{{ groupIcon(obs.group) }}</div>
        <div class="obs-item__info">
          <h4>{{ obs.group_label }} {{ obs.comment ? '— ' + obs.comment.slice(0, 50) : '' }}</h4>
          <p>{{ new Date(obs.observed_at).toLocaleDateString('ru') }} {{ new Date(obs.observed_at).toLocaleTimeString('ru', {hour:'2-digit', minute:'2-digit'}) }}</p>
        </div>
        <span class="obs-status" :class="'obs-status--' + obs.status">{{ statusLabel(obs.status) }}</span>
      </div>
    </div>
    <div v-if="observations.length === 0 && !loading" class="empty">
      Наблюдений пока нет. <router-link to="/observe">Создать первое?</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'

const observations = ref<any[]>([])
const loading = ref(false)
const statusFilter = ref('')

const GROUP_ICONS: Record<string, string> = { plants: '🌿', fungi: '🍄', insects: '🐛', herpetofauna: '🐍', birds: '🐦', mammals: '🦔' }
const GROUP_LABELS: Record<string, string> = { plants: 'Растение', fungi: 'Гриб', insects: 'Насекомое', herpetofauna: 'Герпетофауна', birds: 'Птица', mammals: 'Млекопитающее' }
const STATUS_LABELS: Record<string, string> = { on_review: 'На проверке', needs_data: 'Нужны данные', confirmed: 'Подтверждено', rejected: 'Отклонено' }

function groupIcon(g: string) { return GROUP_ICONS[g] || '🌱' }
function statusLabel(s: string) { return STATUS_LABELS[s] || s }

async function fetchObs() {
  loading.value = true
  const params: any = {}
  if (statusFilter.value) params.status = statusFilter.value
  try {
    const { data } = await api.get('/observations/my', { params })
    observations.value = data.items.map((o: any) => ({ ...o, group_label: GROUP_LABELS[o.group] || o.group }))
  } catch { observations.value = [] }
  loading.value = false
}

onMounted(fetchObs)
</script>

<style scoped>
.my-obs-page { max-width: 800px; margin: 0 auto; padding: 32px; }
.my-obs-page h1 { font-family: 'Cormorant Garamond', serif; font-size: 30px; font-weight: 600; color: #1B4D4F; margin-bottom: 20px; }
.filters { display: flex; gap: 12px; margin-bottom: 24px; align-items: center; }
.btn-add { padding: 8px 16px; background: #2A7A6E; color: white; border-radius: 6px; text-decoration: none; font-size: 14px; font-weight: 600; margin-left: auto; }
.btn-add:hover { background: #3DAA8E; }
.obs-list { display: flex; flex-direction: column; gap: 8px; }
.obs-item { background: #FAFBFC; border-radius: 12px; padding: 16px 20px; display: grid; grid-template-columns: 48px 1fr auto; gap: 16px; align-items: center; box-shadow: 0 2px 12px rgba(44,62,74,0.08); cursor: pointer; transition: all 0.2s; }
.obs-item:hover { box-shadow: 0 8px 32px rgba(44,62,74,0.14); transform: translateX(4px); }
.obs-item__icon { font-size: 28px; text-align: center; }
.obs-item__info h4 { font-size: 14px; font-weight: 700; color: #2C3E4A; }
.obs-item__info p { font-size: 12px; color: #8FA5AB; margin-top: 2px; }
.obs-status { padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; white-space: nowrap; }
.obs-status--on_review { background: rgba(255,193,7,0.15); color: #F57F17; }
.obs-status--needs_data { background: rgba(33,150,243,0.12); color: #1565C0; }
.obs-status--confirmed { background: rgba(76,175,80,0.12); color: #2E7D32; }
.obs-status--rejected { background: rgba(229,57,53,0.1); color: #E53935; }
.empty { text-align: center; padding: 60px; color: #8FA5AB; font-size: 16px; }
.empty a { color: #2A7A6E; }
</style>
