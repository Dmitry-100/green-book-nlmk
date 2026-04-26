import { describe, expect, it, vi } from 'vitest'

import { useAdminCatalogImport, type CatalogImportBatch } from './useAdminCatalogImport'

function makeCatalogImport() {
  const apiClient = {
    get: vi.fn().mockResolvedValue({ data: { items: [], total: 0 } }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  }
  const cachedGet = vi.fn().mockResolvedValue({ data: { items: [], total: 0 } })
  const clearCache = vi.fn()
  const messages = {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  }
  const refreshSpecies = vi.fn().mockResolvedValue(undefined)
  const refreshCatalogQuality = vi.fn().mockResolvedValue(undefined)

  const catalogImport = useAdminCatalogImport({
    refreshSpecies,
    refreshCatalogQuality,
    apiClient,
    getCachedGet: cachedGet,
    clearCache,
    messages,
    confirm: vi.fn().mockReturnValue(false),
  })

  return {
    apiClient,
    cachedGet,
    clearCache,
    messages,
    refreshSpecies,
    refreshCatalogQuality,
    catalogImport,
  }
}

describe('useAdminCatalogImport', () => {
  it('resets batch paging and detail when status filter changes', async () => {
    const { catalogImport, apiClient, clearCache } = makeCatalogImport()

    catalogImport.catalogBatchPage.value = 3
    catalogImport.catalogBatchStatusFilter.value = 'rolled_back'
    catalogImport.catalogBatchDetails.value = {
      id: 17,
      filename: 'catalog.csv',
      status: 'applied',
      actor_user_id: 1,
      rolled_back_by_user_id: null,
      total_rows: 10,
      changed_rows: 2,
      unchanged_rows: 8,
      error_rows: 0,
      applied_rows: 2,
      created_at: '2026-04-26T00:00:00Z',
      rolled_back_at: null,
      changes: [],
    }

    await catalogImport.onCatalogBatchStatusChange()

    expect(catalogImport.catalogBatchPage.value).toBe(1)
    expect(catalogImport.catalogBatchDetails.value).toBeNull()
    expect(clearCache).toHaveBeenCalledWith('admin:catalog:import:batches:')
    expect(apiClient.get).toHaveBeenCalledWith('/admin/catalog/import/batches', {
      params: {
        skip: 0,
        limit: 5,
        status: 'rolled_back',
      },
    })
  })

  it('does not apply import until CSV preview exists', async () => {
    const { catalogImport, apiClient, messages } = makeCatalogImport()

    await catalogImport.applyCatalogImport()

    expect(messages.error).toHaveBeenCalledWith('Сначала проверьте CSV')
    expect(apiClient.post).not.toHaveBeenCalled()
  })

  it('does not rollback a batch when confirmation is declined', async () => {
    const { catalogImport, apiClient } = makeCatalogImport()
    const batch: CatalogImportBatch = {
      id: 42,
      filename: 'catalog.csv',
      status: 'applied',
      actor_user_id: 1,
      rolled_back_by_user_id: null,
      total_rows: 10,
      changed_rows: 2,
      unchanged_rows: 8,
      error_rows: 0,
      applied_rows: 2,
      created_at: '2026-04-26T00:00:00Z',
      rolled_back_at: null,
    }

    await catalogImport.rollbackCatalogImportBatch(batch)

    expect(apiClient.post).not.toHaveBeenCalled()
    expect(catalogImport.catalogRollbackLoading.value).toBeNull()
  })
})
