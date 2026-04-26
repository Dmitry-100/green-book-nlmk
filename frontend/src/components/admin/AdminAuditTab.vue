<template>
  <AdminAuditPanel
    v-model:audit-retention-days="auditRetentionDays"
    :audit-events="auditEvents"
    :audit-loading="auditLoading"
    :audit-purge-loading="auditPurgeLoading"
    :audit-page="auditPage"
    :audit-page-size="auditPageSize"
    :audit-total="auditTotal"
    :audit-filters="auditFilters"
    :ops-summary="opsSummary"
    :ops-loading="opsLoading"
    :ops-alerts="opsAlerts"
    :ops-alerts-loading="opsAlertsLoading"
    :ops-alert-status="opsAlertStatus"
    @refresh-ops="loadOpsSnapshot(true)"
    @reload-audit="reloadAudit(true)"
    @preview-purge="previewAuditPurge"
    @confirm-purge="confirmAndPurgeAudit"
    @apply-filters="applyAuditFilters"
    @reset-filters="resetAuditFilters"
    @page-change="onAuditPageChange"
  />
</template>

<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useAdminAuditOps } from '../../composables/admin/useAdminAuditOps'
import AdminAuditPanel from './AdminAuditPanel.vue'

const props = defineProps<{
  refreshKey: number
}>()

const {
  auditEvents,
  auditLoading,
  auditPurgeLoading,
  auditRetentionDays,
  auditPage,
  auditPageSize,
  auditTotal,
  opsSummary,
  opsLoading,
  opsAlerts,
  opsAlertsLoading,
  opsAlertStatus,
  auditFilters,
  reloadAudit,
  loadOpsSnapshot,
  previewAuditPurge,
  confirmAndPurgeAudit,
  applyAuditFilters,
  resetAuditFilters,
  onAuditPageChange,
} = useAdminAuditOps()

async function reloadAuditTab(force = false) {
  await Promise.all([loadOpsSnapshot(force), reloadAudit(force)])
}

watch(
  () => props.refreshKey,
  () => {
    void reloadAuditTab(true)
  }
)

onMounted(() => {
  void reloadAuditTab()
})
</script>
