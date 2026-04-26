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
      <AdminSpeciesTab />
    </div>

    <!-- Zone Import -->
    <div v-if="activeTab === 'zones'" class="admin-section">
      <AdminZoneImportPanel
        :headers="authHeaders"
        :message="zoneMessage"
        :success="zoneSuccess"
        @success="onZoneUploadSuccess"
        @error="onZoneUploadError"
      />
    </div>

    <!-- Users / Roles -->
    <div v-if="activeTab === 'users'" class="admin-section">
      <AdminRolesPanel />
    </div>

    <!-- Audit trail -->
    <div v-if="activeTab === 'audit'" class="admin-section">
      <AdminAuditTab :refresh-key="auditRefreshKey" />
    </div>

  </div>
</template>

<script setup lang="ts">
import { defineAsyncComponent, ref } from 'vue'
import { clearCachedGets } from '../api/client'
import { useAuthStore } from '../stores/auth'

const AdminAuditTab = defineAsyncComponent(() => import('../components/admin/AdminAuditTab.vue'))
const AdminRolesPanel = defineAsyncComponent(() => import('../components/admin/AdminRolesPanel.vue'))
const AdminSpeciesTab = defineAsyncComponent(() => import('../components/admin/AdminSpeciesTab.vue'))
const AdminZoneImportPanel = defineAsyncComponent(() => import('../components/admin/AdminZoneImportPanel.vue'))

const auth = useAuthStore()
const activeTab = ref('species')
const zoneMessage = ref('')
const zoneSuccess = ref(false)
const auditRefreshKey = ref(0)

const tabs = [
  { key: 'species', icon: '📋', label: 'Виды' },
  { key: 'zones', icon: '🗺️', label: 'Зоны' },
  { key: 'users', icon: '👤', label: 'Роли' },
  { key: 'audit', icon: '🧾', label: 'Аудит' },
]

const authHeaders = { Authorization: `Bearer ${auth.token || ''}` }

function onZoneUploadSuccess(res: any) {
  zoneMessage.value = `Импортировано ${res.imported} зон из ${res.filename}`
  zoneSuccess.value = true
  clearCachedGets('admin:audit:')
  clearCachedGets('admin:ops:')
  if (activeTab.value === 'audit') {
    auditRefreshKey.value += 1
  }
}

function onZoneUploadError() {
  zoneMessage.value = 'Ошибка загрузки файла'
  zoneSuccess.value = false
}
</script>

<style scoped>
.admin-page { max-width: 1000px; margin: 0 auto; padding: 32px; }
.admin-page h1 { font-family: var(--font-display); font-size: 30px; font-weight: 600; color: var(--teal-dark); margin-bottom: 20px; }
.admin-tabs { display: flex; gap: 4px; margin-bottom: 24px; background: var(--slate-bg); border-radius: 12px; padding: 4px; }
.admin-tab { padding: 10px 20px; border: none; background: transparent; font-size: 13px; font-weight: 600; color: var(--slate-mid); cursor: pointer; border-radius: 8px; transition: all 0.2s; }
.admin-tab.active { background: var(--white); color: var(--teal-dark); box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.admin-section { background: var(--white); border-radius: var(--radius-lg); padding: 28px; box-shadow: var(--shadow-card); }
</style>
