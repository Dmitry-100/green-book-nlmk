import { ref } from 'vue'
import api, { clearCachedGets, getCached } from '../../api/client'
import { defaultAdminMessages, type AdminMessages } from './adminMessages'

export type CatalogImportChange = {
  row: number
  id: number
  name_ru: string
  changed_fields: string[]
  before: Record<string, unknown>
  after: Record<string, unknown>
}

export type CatalogImportRowError = {
  row: number
  id: string
  errors: string[]
}

export type CatalogImportPreview = {
  filename: string
  dry_run: boolean
  batch_id?: number
  total_rows: number
  changed_rows: number
  unchanged_rows: number
  error_rows: number
  applied_rows?: number
  changes: CatalogImportChange[]
  errors: CatalogImportRowError[]
}

export type CatalogImportBatch = {
  id: number
  filename: string
  status: 'applied' | 'rolled_back'
  actor_user_id: number | null
  rolled_back_by_user_id: number | null
  total_rows: number
  changed_rows: number
  unchanged_rows: number
  error_rows: number
  applied_rows: number
  created_at: string
  rolled_back_at: string | null
}

export type CatalogImportBatchDetail = CatalogImportBatch & {
  changes: CatalogImportChange[]
}

type ApiClient = {
  get: (url: string, config?: Record<string, unknown>) => Promise<any>
  post: (url: string, data?: unknown, config?: Record<string, unknown>) => Promise<any>
}

type CatalogImportMessages = Pick<AdminMessages, 'success' | 'error' | 'warning'>

export type CatalogImportUploadOptions = {
  file: Blob
  onSuccess?: (data: CatalogImportPreview) => unknown
  onError?: (error: unknown) => unknown
}

type UseAdminCatalogImportOptions = {
  refreshSpecies: (force?: boolean) => Promise<unknown> | unknown
  refreshCatalogQuality: (force?: boolean) => Promise<unknown> | unknown
  apiClient?: ApiClient
  getCachedGet?: typeof getCached
  clearCache?: typeof clearCachedGets
  messages?: CatalogImportMessages
  confirm?: (message: string) => boolean
}

function defaultConfirm(message: string): boolean {
  return typeof window !== 'undefined' ? window.confirm(message) : false
}

function asUploadOptions(uploadOptions: unknown): CatalogImportUploadOptions | null {
  if (!uploadOptions || typeof uploadOptions !== 'object' || !('file' in uploadOptions)) {
    return null
  }
  return uploadOptions as CatalogImportUploadOptions
}

export function useAdminCatalogImport(options: UseAdminCatalogImportOptions) {
  const apiClient = options.apiClient || api
  const cachedGet = options.getCachedGet || getCached
  const clearCache = options.clearCache || clearCachedGets
  const messages = options.messages || defaultAdminMessages
  const confirm = options.confirm || defaultConfirm

  const catalogImportPreview = ref<CatalogImportPreview | null>(null)
  const catalogImportLoading = ref(false)
  const catalogApplyLoading = ref(false)
  const catalogImportFile = ref<Blob | null>(null)
  const catalogImportBatches = ref<CatalogImportBatch[]>([])
  const catalogBatchDetails = ref<CatalogImportBatchDetail | null>(null)
  const catalogBatchLoading = ref(false)
  const catalogBatchDetailLoading = ref<number | null>(null)
  const catalogRollbackLoading = ref<number | null>(null)
  const catalogBatchStatusFilter = ref('')
  const catalogBatchPage = ref(1)
  const catalogBatchPageSize = 5
  const catalogBatchTotal = ref(0)

  function buildCatalogBatchParams(): Record<string, string | number> {
    const params: Record<string, string | number> = {
      skip: (catalogBatchPage.value - 1) * catalogBatchPageSize,
      limit: catalogBatchPageSize,
    }
    if (catalogBatchStatusFilter.value) {
      params.status = catalogBatchStatusFilter.value
    }
    return params
  }

  function buildCatalogBatchCacheKey(params: Record<string, string | number>) {
    return `admin:catalog:import:batches:${JSON.stringify(params)}`
  }

  async function loadCatalogImportBatches(force = false) {
    catalogBatchLoading.value = true
    const params = buildCatalogBatchParams()
    try {
      const response = force
        ? await apiClient.get('/admin/catalog/import/batches', { params })
        : await cachedGet(
            '/admin/catalog/import/batches',
            { params },
            10 * 1000,
            buildCatalogBatchCacheKey(params)
          )
      catalogImportBatches.value = response.data.items || []
      catalogBatchTotal.value = response.data.total ?? catalogImportBatches.value.length
    } catch (e: any) {
      messages.error(e.response?.data?.detail || 'Не удалось загрузить историю импортов')
    } finally {
      catalogBatchLoading.value = false
    }
  }

  async function onCatalogBatchStatusChange() {
    catalogBatchPage.value = 1
    catalogBatchDetails.value = null
    clearCache('admin:catalog:import:batches:')
    await loadCatalogImportBatches(true)
  }

  async function onCatalogBatchPageChange(page: number) {
    catalogBatchPage.value = page
    catalogBatchDetails.value = null
    await loadCatalogImportBatches()
  }

  async function loadCatalogImportBatchDetail(batchId: number) {
    catalogBatchDetailLoading.value = batchId
    try {
      const { data } = await apiClient.get(`/admin/catalog/import/batches/${batchId}`)
      catalogBatchDetails.value = data
    } catch (e: any) {
      messages.error(e.response?.data?.detail || 'Не удалось загрузить детали импорта')
    } finally {
      catalogBatchDetailLoading.value = null
    }
  }

  async function previewCatalogImport(rawUploadOptions: unknown) {
    const uploadOptions = asUploadOptions(rawUploadOptions)
    if (!uploadOptions) {
      messages.error('Не удалось прочитать CSV')
      return
    }
    catalogImportLoading.value = true
    catalogImportFile.value = uploadOptions.file
    const formData = new FormData()
    formData.append('file', uploadOptions.file)
    try {
      const { data } = await apiClient.post('/admin/catalog/import/preview', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      catalogImportPreview.value = data
      uploadOptions.onSuccess?.(data)
      if (data.error_rows > 0) {
        messages.warning(`Проверка завершена: ошибок ${data.error_rows}`)
        return
      }
      messages.success(`Проверка завершена: изменений ${data.changed_rows}`)
    } catch (e: any) {
      uploadOptions.onError?.(e)
      messages.error(e.response?.data?.detail || 'Не удалось проверить CSV')
    } finally {
      catalogImportLoading.value = false
    }
  }

  function clearCatalogMutationCaches() {
    clearCache('species:list:')
    clearCache('admin:audit:')
    clearCache('admin:ops:')
    clearCache('admin:catalog:')
  }

  async function refreshAfterCatalogImportMutation() {
    await Promise.all([
      Promise.resolve(options.refreshSpecies(true)),
      Promise.resolve(options.refreshCatalogQuality(true)),
      loadCatalogImportBatches(true),
    ])
  }

  async function applyCatalogImport() {
    if (!catalogImportFile.value || !catalogImportPreview.value) {
      messages.error('Сначала проверьте CSV')
      return
    }
    if (catalogImportPreview.value.error_rows > 0) {
      messages.error('CSV с ошибками нельзя применить')
      return
    }
    const confirmed = confirm(
      `Применить ${catalogImportPreview.value.changed_rows} изменений в справочник?`
    )
    if (!confirmed) {
      return
    }

    catalogApplyLoading.value = true
    const formData = new FormData()
    formData.append('file', catalogImportFile.value)
    try {
      const { data } = await apiClient.post('/admin/catalog/import/apply', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      catalogImportPreview.value = data
      clearCatalogMutationCaches()
      await refreshAfterCatalogImportMutation()
      messages.success(`Применено строк: ${data.applied_rows}`)
    } catch (e: any) {
      messages.error(e.response?.data?.detail || 'Не удалось применить CSV')
    } finally {
      catalogApplyLoading.value = false
    }
  }

  async function rollbackCatalogImportBatch(batch: CatalogImportBatch) {
    const confirmed = confirm(`Откатить CSV-импорт #${batch.id}?`)
    if (!confirmed) {
      return
    }
    catalogRollbackLoading.value = batch.id
    try {
      const { data } = await apiClient.post(`/admin/catalog/import/batches/${batch.id}/rollback`)
      clearCatalogMutationCaches()
      await refreshAfterCatalogImportMutation()
      messages.success(`Откатили строк: ${data.rolled_back_rows}`)
    } catch (e: any) {
      messages.error(e.response?.data?.detail || 'Не удалось откатить импорт')
    } finally {
      catalogRollbackLoading.value = null
    }
  }

  return {
    catalogImportPreview,
    catalogImportLoading,
    catalogApplyLoading,
    catalogImportFile,
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
  }
}
