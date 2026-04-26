<template>
  <div>
    <div class="admin-section__header">
      <h2>Справочник видов</h2>
      <button class="admin-add-button" type="button" @click="openAddSpecies">
        + Добавить вид
      </button>
    </div>

    <AdminCatalogQualityPanel
      :quality="catalogQuality"
      :loading="catalogQualityLoading"
      :export-loading="catalogExportLoading"
      :active-gap="adminSpeciesFilters.quality_gap"
      :gap-items="catalogQualityGapItems"
      :groups="catalogQualityGroups"
      :candidates="catalogQualityCandidates"
      @export-all="downloadCatalogExport(true)"
      @export-gap="downloadActiveCatalogQualityGapExport"
      @refresh="loadCatalogQuality(true)"
      @apply-gap="applyCatalogQualityGapFromPanel"
    >
      <div class="admin-import-toggle">
        <button class="admin-secondary-button" type="button" @click="toggleCatalogImportPanel">
          {{ showCatalogImportPanel ? 'Скрыть CSV импорт' : 'Открыть CSV импорт' }}
        </button>
        <span>Проверка и откат CSV загружаются только при необходимости.</span>
      </div>
      <AdminCatalogImportPanel
        v-if="showCatalogImportPanel"
        v-model:status-filter="catalogBatchStatusFilter"
        :preview="catalogImportPreview"
        :import-loading="catalogImportLoading"
        :apply-loading="catalogApplyLoading"
        :batches="catalogImportBatches"
        :batch-loading="catalogBatchLoading"
        :batch-detail-loading="catalogBatchDetailLoading"
        :rollback-loading="catalogRollbackLoading"
        :page="catalogBatchPage"
        :page-size="catalogBatchPageSize"
        :total="catalogBatchTotal"
        :details="catalogBatchDetails"
        @preview="previewCatalogImport"
        @apply="applyCatalogImport"
        @refresh-batches="loadCatalogImportBatches(true)"
        @status-change="onCatalogBatchStatusChange"
        @page-change="onCatalogBatchPageChange"
        @load-detail="loadCatalogImportBatchDetail"
        @rollback="rollbackCatalogImportBatch"
      />
    </AdminCatalogQualityPanel>

    <AdminSpeciesCatalogTable
      :filters="adminSpeciesFilters"
      :species="speciesList"
      :total="adminSpeciesTotal"
      :page="adminSpeciesPage"
      :page-size="adminSpeciesPageSize"
      @search-input="debouncedFetchSpecies"
      @apply-filters="applyAdminSpeciesFilters"
      @quality-gap-change="onAdminSpeciesQualityGapChange"
      @has-audio-change="onAdminSpeciesHasAudioChange"
      @reset-filters="resetAdminSpeciesFilters"
      @page-change="onAdminSpeciesPageChange"
      @edit="openEditSpecies"
      @delete="deleteSpecies"
    />

    <AdminSpeciesFormDialog
      v-if="showAddSpecies"
      v-model="showAddSpecies"
      v-model:active-tab="addSpeciesFormTab"
      title="Добавить вид"
      submit-label="Добавить"
      :form="newSpecies"
      @submit="addSpecies"
    />

    <AdminSpeciesFormDialog
      v-if="showEditSpecies"
      v-model="showEditSpecies"
      v-model:active-tab="editSpeciesFormTab"
      title="Редактировать вид"
      submit-label="Сохранить"
      :saving="editSpeciesSaving"
      :form="editSpeciesForm"
      @submit="saveSpeciesEdit"
    />
  </div>
</template>

<script setup lang="ts">
import { defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAdminCatalogImport } from '../../composables/admin/useAdminCatalogImport'
import { useAdminCatalogQuality } from '../../composables/admin/useAdminCatalogQuality'
import { useAdminSpeciesCatalog } from '../../composables/admin/useAdminSpeciesCatalog'

const AdminCatalogImportPanel = defineAsyncComponent(() => import('./AdminCatalogImportPanel.vue'))
const AdminCatalogQualityPanel = defineAsyncComponent(() => import('./AdminCatalogQualityPanel.vue'))
const AdminSpeciesCatalogTable = defineAsyncComponent(() => import('./AdminSpeciesCatalogTable.vue'))
const AdminSpeciesFormDialog = defineAsyncComponent(() => import('./AdminSpeciesFormDialog.vue'))

const route = useRoute()
const router = useRouter()
const showCatalogImportPanel = ref(false)
const catalogImportPanelLoaded = ref(false)

const {
  catalogQuality,
  catalogQualityLoading,
  catalogExportLoading,
  catalogQualityCandidates,
  catalogQualityGroups,
  catalogQualityGapItems,
  loadCatalogQuality,
  downloadCatalogExport,
  downloadCatalogQualityGapExport,
} = useAdminCatalogQuality()

const {
  speciesList,
  adminSpeciesTotal,
  adminSpeciesPage,
  adminSpeciesPageSize,
  adminSpeciesFilters,
  showAddSpecies,
  showEditSpecies,
  editSpeciesSaving,
  editSpeciesForm,
  addSpeciesFormTab,
  editSpeciesFormTab,
  newSpecies,
  applyAdminSpeciesStateFromUrl,
  fetchSpecies,
  applyAdminSpeciesFilters,
  onAdminSpeciesHasAudioChange,
  onAdminSpeciesQualityGapChange,
  applyCatalogQualityGapFromPanel,
  debouncedFetchSpecies,
  resetAdminSpeciesFilters,
  onAdminSpeciesPageChange,
  addSpecies,
  openAddSpecies,
  openEditSpecies,
  saveSpeciesEdit,
  deleteSpecies,
} = useAdminSpeciesCatalog({
  route,
  router,
  refreshCatalogQuality: loadCatalogQuality,
})

const {
  catalogImportPreview,
  catalogImportLoading,
  catalogApplyLoading,
  catalogImportBatches,
  catalogBatchDetails,
  catalogBatchLoading,
  catalogBatchDetailLoading,
  catalogRollbackLoading,
  catalogBatchStatusFilter,
  catalogBatchPage,
  catalogBatchPageSize,
  catalogBatchTotal,
  loadCatalogImportBatches,
  onCatalogBatchStatusChange,
  onCatalogBatchPageChange,
  loadCatalogImportBatchDetail,
  previewCatalogImport,
  applyCatalogImport,
  rollbackCatalogImportBatch,
} = useAdminCatalogImport({
  refreshSpecies: fetchSpecies,
  refreshCatalogQuality: loadCatalogQuality,
})

async function downloadActiveCatalogQualityGapExport() {
  return downloadCatalogQualityGapExport(adminSpeciesFilters.quality_gap)
}

async function toggleCatalogImportPanel() {
  showCatalogImportPanel.value = !showCatalogImportPanel.value
  if (!showCatalogImportPanel.value || catalogImportPanelLoaded.value) {
    return
  }
  catalogImportPanelLoaded.value = true
  await loadCatalogImportBatches()
}

watch(
  () => route.query,
  () => {
    if (applyAdminSpeciesStateFromUrl()) {
      void fetchSpecies(true)
    }
  }
)

onMounted(() => {
  applyAdminSpeciesStateFromUrl()
  void fetchSpecies()
  void loadCatalogQuality()
})
</script>

<style scoped>
.admin-section__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.admin-section__header h2 { font-family: var(--font-display); font-size: 22px; font-weight: 600; color: var(--teal-dark); margin-bottom: 12px; }
.admin-add-button { border: 0; border-radius: 8px; background: var(--teal); color: var(--white); cursor: pointer; font-size: 13px; font-weight: 700; padding: 8px 14px; transition: background 0.2s ease, transform 0.2s ease; }
.admin-add-button:hover { background: var(--teal-dark); transform: translateY(-1px); }
.admin-add-button:focus-visible { outline: 2px solid var(--teal-dark); outline-offset: 2px; }
.admin-import-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 14px 0 0;
  color: var(--slate-mid, #6B7C86);
  font-size: 12px;
}
.admin-secondary-button {
  border: 1px solid #C9D7DA;
  border-radius: 8px;
  background: #fff;
  color: var(--teal-dark, #1E5F57);
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
  min-height: 32px;
  padding: 0 12px;
}
.admin-secondary-button:hover {
  border-color: var(--teal-accent, #2A7A6E);
  background: #F4F8F9;
}
.admin-secondary-button:focus-visible {
  outline: 2px solid var(--teal-accent, #2A7A6E);
  outline-offset: 2px;
}
@media (max-width: 760px) {
  .admin-import-toggle {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
