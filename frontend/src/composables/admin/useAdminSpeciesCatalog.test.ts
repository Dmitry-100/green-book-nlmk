import { describe, expect, it, vi } from 'vitest'

import { useAdminSpeciesCatalog } from './useAdminSpeciesCatalog'

function makeCatalog() {
  const apiClient = {
    get: vi.fn().mockResolvedValue({ data: { items: [], total: 0 } }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    put: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
  }
  const router = {
    replace: vi.fn(),
  }

  return {
    apiClient,
    router,
    catalog: useAdminSpeciesCatalog({
      route: { query: { tab: 'species' } },
      router,
      refreshCatalogQuality: vi.fn(),
      apiClient,
      getCachedGet: vi.fn().mockResolvedValue({ data: { items: [], total: 0 } }),
      clearCache: vi.fn(),
      messages: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
      },
    }),
  }
}

describe('useAdminSpeciesCatalog', () => {
  it('clears missing-audio quality gap when has-audio filter is enabled', () => {
    const { catalog, router } = makeCatalog()

    catalog.adminSpeciesFilters.quality_gap = 'missing_audio'
    catalog.adminSpeciesFilters.has_audio = true
    catalog.onAdminSpeciesHasAudioChange()

    expect(catalog.adminSpeciesFilters.quality_gap).toBe('')
    expect(catalog.adminSpeciesFilters.has_audio).toBe(true)
    expect(catalog.adminSpeciesPage.value).toBe(1)
    expect(router.replace).toHaveBeenCalledWith({
      query: {
        tab: 'species',
        species_has_audio: 'true',
      },
    })
  })

  it('lets missing-audio quality gap disable has-audio filter', () => {
    const { catalog, router } = makeCatalog()

    catalog.adminSpeciesFilters.has_audio = true
    catalog.applyCatalogQualityGap('missing_audio')

    expect(catalog.adminSpeciesFilters.quality_gap).toBe('missing_audio')
    expect(catalog.adminSpeciesFilters.has_audio).toBe(false)
    expect(router.replace).toHaveBeenCalledWith({
      query: {
        tab: 'species',
        species_quality_gap: 'missing_audio',
      },
    })
  })

  it('resets filters and keeps unrelated URL query values', () => {
    const apiClient = {
      get: vi.fn().mockResolvedValue({ data: { items: [], total: 0 } }),
      post: vi.fn().mockResolvedValue({ data: {} }),
      put: vi.fn().mockResolvedValue({ data: {} }),
      delete: vi.fn().mockResolvedValue({ data: {} }),
    }
    const router = { replace: vi.fn() }
    const catalog = useAdminSpeciesCatalog({
      route: {
        query: {
          tab: 'species',
          species_group: 'birds',
          preserved: 'yes',
        },
      },
      router,
      refreshCatalogQuality: vi.fn(),
      apiClient,
      getCachedGet: vi.fn().mockResolvedValue({ data: { items: [], total: 0 } }),
      clearCache: vi.fn(),
      messages: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
      },
    })

    catalog.adminSpeciesFilters.search = 'синица'
    catalog.adminSpeciesFilters.group = 'birds'
    catalog.adminSpeciesFilters.category = 'synanthropic'
    catalog.adminSpeciesFilters.has_audio = true
    catalog.adminSpeciesFilters.quality_gap = 'missing_photo'
    catalog.adminSpeciesPage.value = 3

    catalog.resetAdminSpeciesFilters()

    expect(catalog.adminSpeciesFilters).toMatchObject({
      search: '',
      group: '',
      category: '',
      has_audio: false,
      quality_gap: '',
    })
    expect(catalog.adminSpeciesPage.value).toBe(1)
    expect(router.replace).toHaveBeenCalledWith({
      query: {
        tab: 'species',
        preserved: 'yes',
      },
    })
  })
})
