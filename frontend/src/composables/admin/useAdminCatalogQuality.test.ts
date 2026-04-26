import { describe, expect, it, vi } from 'vitest'

import { useAdminCatalogQuality } from './useAdminCatalogQuality'

function makeCatalogQuality() {
  const apiClient = {
    get: vi.fn().mockResolvedValue({ data: { content_gap_counts: {} } }),
  }
  const cachedGet = vi.fn().mockResolvedValue({ data: { content_gap_counts: {} } })
  const messages = {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  }
  const downloadBlob = vi.fn()

  return {
    apiClient,
    cachedGet,
    messages,
    downloadBlob,
    catalogQuality: useAdminCatalogQuality({
      apiClient,
      getCachedGet: cachedGet,
      messages,
      downloadBlob,
    }),
  }
}

describe('useAdminCatalogQuality', () => {
  it('loads catalog quality through cached request by default', async () => {
    const { catalogQuality, cachedGet } = makeCatalogQuality()

    await catalogQuality.loadCatalogQuality()

    expect(cachedGet).toHaveBeenCalledWith(
      '/admin/catalog/quality',
      { params: { limit: 200 } },
      30 * 1000,
      'admin:catalog:quality:200'
    )
    expect(catalogQuality.catalogQuality.value).toEqual({ content_gap_counts: {} })
  })

  it('warns and skips gap export when quality gap is empty', async () => {
    const { catalogQuality, apiClient, messages } = makeCatalogQuality()

    await catalogQuality.downloadCatalogQualityGapExport('')

    expect(messages.warning).toHaveBeenCalledWith('Выберите очередь')
    expect(apiClient.get).not.toHaveBeenCalled()
  })

  it('downloads selected gap export with gap filename', async () => {
    const blob = new Blob(['id,name_ru'])
    const { catalogQuality, apiClient, downloadBlob } = makeCatalogQuality()
    apiClient.get.mockResolvedValue({ data: blob })

    await catalogQuality.downloadCatalogQualityGapExport('missing_audio')

    expect(apiClient.get).toHaveBeenCalledWith('/admin/catalog/export', {
      params: {
        needs_review: false,
        quality_gap: 'missing_audio',
      },
      responseType: 'blob',
    })
    expect(downloadBlob).toHaveBeenCalledWith(blob, 'species-catalog-missing-audio.csv')
  })
})
