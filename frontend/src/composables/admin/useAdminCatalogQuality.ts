import { computed, ref } from 'vue'
import api, { getCached } from '../../api/client'
import {
  buildSpeciesAdminQualityGapExportFilename,
  buildSpeciesAdminQualityGapItems,
  type AdminSpeciesQualityGap,
  type SpeciesContentGapCounts,
} from '../../utils/speciesAdminForm'
import { defaultAdminMessages, type AdminMessages } from './adminMessages'

type CatalogQualityItem = {
  id: number
  name_ru: string
  name_latin: string
  group: string
}

export type CatalogQuality = {
  generated_at: string
  species_total: number
  latin_name_exact_species: number
  latin_name_needs_review: number
  latin_name_suspicious_chars: number
  latin_name_needs_review_by_group: Record<string, number>
  latin_name_needs_review_examples: CatalogQualityItem[]
  content_gap_counts: SpeciesContentGapCounts
}

type ApiClient = {
  get: (url: string, config?: Record<string, unknown>) => Promise<any>
}

type CatalogQualityMessages = Pick<AdminMessages, 'success' | 'error' | 'warning'>

type UseAdminCatalogQualityOptions = {
  apiClient?: ApiClient
  getCachedGet?: typeof getCached
  messages?: CatalogQualityMessages
  downloadBlob?: (data: Blob, filename: string) => unknown
}

function browserDownloadBlob(data: Blob, filename: string) {
  const url = URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function useAdminCatalogQuality(options: UseAdminCatalogQualityOptions = {}) {
  const apiClient = options.apiClient || api
  const cachedGet = options.getCachedGet || getCached
  const messages = options.messages || defaultAdminMessages
  const downloadBlob = options.downloadBlob || browserDownloadBlob

  const catalogQuality = ref<CatalogQuality | null>(null)
  const catalogQualityLoading = ref(false)
  const catalogExportLoading = ref(false)

  const catalogQualityCandidates = computed(
    () => catalogQuality.value?.latin_name_needs_review_examples || []
  )
  const catalogQualityGroups = computed(() => Object.entries(
    catalogQuality.value?.latin_name_needs_review_by_group || {}
  ).map(([group, total]) => ({ group, total })))
  const catalogQualityGapItems = computed(() =>
    buildSpeciesAdminQualityGapItems(catalogQuality.value?.content_gap_counts)
  )

  async function loadCatalogQuality(force = false) {
    catalogQualityLoading.value = true
    const params = { limit: 200 }
    try {
      const response = force
        ? await apiClient.get('/admin/catalog/quality', { params })
        : await cachedGet(
            '/admin/catalog/quality',
            { params },
            30 * 1000,
            'admin:catalog:quality:200'
          )
      catalogQuality.value = response.data
    } catch (e: any) {
      messages.error(e.response?.data?.detail || 'Не удалось загрузить проверку каталога')
    } finally {
      catalogQualityLoading.value = false
    }
  }

  async function downloadCatalogExport(needsReview = true) {
    return downloadCatalogExportFile({ needsReview })
  }

  async function downloadCatalogQualityGapExport(qualityGap: AdminSpeciesQualityGap) {
    if (!qualityGap) {
      messages.warning('Выберите очередь')
      return
    }
    return downloadCatalogExportFile({ needsReview: false, qualityGap })
  }

  async function downloadCatalogExportFile({
    needsReview,
    qualityGap = '',
  }: {
    needsReview: boolean
    qualityGap?: AdminSpeciesQualityGap
  }) {
    catalogExportLoading.value = true
    try {
      const params: Record<string, string | boolean> = { needs_review: needsReview }
      if (qualityGap) {
        params.quality_gap = qualityGap
      }
      const response = await apiClient.get('/admin/catalog/export', {
        params,
        responseType: 'blob',
      })
      downloadBlob(
        response.data,
        qualityGap
          ? buildSpeciesAdminQualityGapExportFilename(qualityGap)
          : needsReview ? 'species-catalog-needs-review.csv' : 'species-catalog.csv'
      )
    } catch (e: any) {
      messages.error(e.response?.data?.detail || 'Не удалось скачать каталог')
    } finally {
      catalogExportLoading.value = false
    }
  }

  return {
    catalogQuality,
    catalogQualityLoading,
    catalogExportLoading,
    catalogQualityCandidates,
    catalogQualityGroups,
    catalogQualityGapItems,
    loadCatalogQuality,
    downloadCatalogExport,
    downloadCatalogQualityGapExport,
    downloadCatalogExportFile,
  }
}
