import { reactive, ref } from 'vue'
import api, { clearCachedGets, getCached } from '../../api/client'
import {
  SPECIES_ADMIN_FORM_TABS,
  buildAdminSpeciesListCacheKey,
  buildAdminSpeciesListParams,
  buildAdminSpeciesListUrlQuery,
  buildEmptySpeciesForm,
  buildSpeciesEditForm,
  buildSpeciesUpdatePayload,
  clampAdminSpeciesListPage,
  parseAdminSpeciesListUrlState,
  type AdminSpeciesEditForm,
  type AdminSpeciesListFilters,
  type AdminSpeciesListUrlQuery,
  type AdminSpeciesQualityGap,
  type AdminSpeciesRow,
} from '../../utils/speciesAdminForm'
import { defaultAdminMessages, type AdminMessages } from './adminMessages'

type ApiClient = {
  get: (url: string, config?: Record<string, unknown>) => Promise<any>
  post: (url: string, data?: unknown, config?: Record<string, unknown>) => Promise<any>
  put: (url: string, data?: unknown, config?: Record<string, unknown>) => Promise<any>
  delete: (url: string, config?: Record<string, unknown>) => Promise<any>
}

type RouterLike = {
  replace: (location: { query: Record<string, string> }) => unknown
}

type RouteLike = {
  query: AdminSpeciesListUrlQuery
}

type SpeciesCatalogMessages = Pick<AdminMessages, 'success' | 'error' | 'warning'>

type UseAdminSpeciesCatalogOptions = {
  route: RouteLike
  router: RouterLike
  refreshCatalogQuality: (force?: boolean) => Promise<unknown> | unknown
  apiClient?: ApiClient
  getCachedGet?: typeof getCached
  clearCache?: typeof clearCachedGets
  messages?: SpeciesCatalogMessages
}

export function useAdminSpeciesCatalog(options: UseAdminSpeciesCatalogOptions) {
  const apiClient = options.apiClient || api
  const cachedGet = options.getCachedGet || getCached
  const clearCache = options.clearCache || clearCachedGets
  const messages = options.messages || defaultAdminMessages

  const speciesList = ref<AdminSpeciesRow[]>([])
  const adminSpeciesTotal = ref(0)
  const adminSpeciesPage = ref(1)
  const adminSpeciesPageSize = 50
  const adminSpeciesFilters = reactive<AdminSpeciesListFilters>({
    search: '',
    group: '',
    category: '',
    has_audio: false,
    quality_gap: '',
  })
  const showAddSpecies = ref(false)
  const showEditSpecies = ref(false)
  const editSpeciesSaving = ref(false)
  const editSpeciesForm = ref<AdminSpeciesEditForm | null>(null)
  const addSpeciesFormTab = ref(SPECIES_ADMIN_FORM_TABS[0].name)
  const editSpeciesFormTab = ref(SPECIES_ADMIN_FORM_TABS[0].name)
  const newSpecies = reactive<AdminSpeciesEditForm>(buildEmptySpeciesForm())
  let adminSpeciesSearchTimer: ReturnType<typeof setTimeout>

  function adminSpeciesPagination() {
    return {
      page: adminSpeciesPage.value,
      pageSize: adminSpeciesPageSize,
    }
  }

  function adminSpeciesUrlStateSignature(
    filters: AdminSpeciesListFilters,
    pagination: { page: number; pageSize: number }
  ) {
    return JSON.stringify({ filters, pagination })
  }

  function applyAdminSpeciesStateFromUrl(): boolean {
    const { filters, pagination } = parseAdminSpeciesListUrlState(
      options.route.query,
      adminSpeciesPageSize
    )
    const currentSignature = adminSpeciesUrlStateSignature(
      { ...adminSpeciesFilters },
      adminSpeciesPagination()
    )
    const nextSignature = adminSpeciesUrlStateSignature(filters, pagination)
    if (currentSignature === nextSignature) {
      return false
    }

    Object.assign(adminSpeciesFilters, filters)
    adminSpeciesPage.value = pagination.page
    return true
  }

  function syncAdminSpeciesUrl() {
    options.router.replace({
      query: buildAdminSpeciesListUrlQuery(
        options.route.query,
        adminSpeciesFilters,
        adminSpeciesPagination()
      ),
    })
  }

  async function fetchSpecies(force = false): Promise<void> {
    const params = buildAdminSpeciesListParams(adminSpeciesFilters, {
      page: adminSpeciesPage.value,
      pageSize: adminSpeciesPageSize,
    })
    const response = force
      ? await apiClient.get('/species', { params })
      : await cachedGet(
          '/species',
          { params },
          5 * 60 * 1000,
          buildAdminSpeciesListCacheKey(params)
        )
    const data = response.data
    const total = data.total ?? data.items?.length ?? 0
    const safePage = clampAdminSpeciesListPage(
      adminSpeciesPage.value,
      total,
      adminSpeciesPageSize
    )
    if (safePage !== adminSpeciesPage.value) {
      adminSpeciesPage.value = safePage
      syncAdminSpeciesUrl()
      await fetchSpecies(true)
      return
    }

    speciesList.value = data.items || []
    adminSpeciesTotal.value = total
  }

  function applyAdminSpeciesFilters() {
    adminSpeciesPage.value = 1
    clearCache('species:list:admin:')
    syncAdminSpeciesUrl()
    void fetchSpecies(true)
  }

  function onAdminSpeciesHasAudioChange() {
    if (adminSpeciesFilters.has_audio && adminSpeciesFilters.quality_gap === 'missing_audio') {
      adminSpeciesFilters.quality_gap = ''
    }
    applyAdminSpeciesFilters()
  }

  function onAdminSpeciesQualityGapChange() {
    if (adminSpeciesFilters.quality_gap === 'missing_audio') {
      adminSpeciesFilters.has_audio = false
    }
    applyAdminSpeciesFilters()
  }

  function applyCatalogQualityGap(gap: AdminSpeciesQualityGap) {
    adminSpeciesFilters.quality_gap =
      adminSpeciesFilters.quality_gap === gap ? '' : gap
    if (adminSpeciesFilters.quality_gap === 'missing_audio') {
      adminSpeciesFilters.has_audio = false
    }
    applyAdminSpeciesFilters()
  }

  function applyCatalogQualityGapFromPanel(gap: string) {
    applyCatalogQualityGap(gap as AdminSpeciesQualityGap)
  }

  function debouncedFetchSpecies() {
    clearTimeout(adminSpeciesSearchTimer)
    adminSpeciesSearchTimer = setTimeout(applyAdminSpeciesFilters, 300)
  }

  function resetAdminSpeciesFilters() {
    adminSpeciesFilters.search = ''
    adminSpeciesFilters.group = ''
    adminSpeciesFilters.category = ''
    adminSpeciesFilters.has_audio = false
    adminSpeciesFilters.quality_gap = ''
    applyAdminSpeciesFilters()
  }

  function onAdminSpeciesPageChange(page: number) {
    adminSpeciesPage.value = page
    syncAdminSpeciesUrl()
    void fetchSpecies()
  }

  function clearCatalogMutationCaches() {
    clearCache('species:list:')
    clearCache('admin:audit:')
    clearCache('admin:ops:')
    clearCache('admin:catalog:')
  }

  async function refreshCatalogAfterMutation() {
    await Promise.all([
      fetchSpecies(true),
      Promise.resolve(options.refreshCatalogQuality(true)),
    ])
  }

  async function addSpecies() {
    try {
      await apiClient.post('/species', buildSpeciesUpdatePayload(newSpecies))
      showAddSpecies.value = false
      Object.assign(newSpecies, buildEmptySpeciesForm())
      addSpeciesFormTab.value = SPECIES_ADMIN_FORM_TABS[0].name
      messages.success('Вид добавлен')
      clearCatalogMutationCaches()
      await refreshCatalogAfterMutation()
    } catch (e: any) {
      messages.error(e.response?.data?.detail || 'Ошибка')
    }
  }

  function openAddSpecies() {
    Object.assign(newSpecies, buildEmptySpeciesForm())
    addSpeciesFormTab.value = SPECIES_ADMIN_FORM_TABS[0].name
    showAddSpecies.value = true
  }

  function openEditSpecies(row: AdminSpeciesRow) {
    editSpeciesForm.value = buildSpeciesEditForm(row)
    editSpeciesFormTab.value = SPECIES_ADMIN_FORM_TABS[0].name
    showEditSpecies.value = true
  }

  async function saveSpeciesEdit() {
    if (!editSpeciesForm.value) {
      return
    }
    editSpeciesSaving.value = true
    try {
      await apiClient.put(
        `/species/${editSpeciesForm.value.id}`,
        buildSpeciesUpdatePayload(editSpeciesForm.value)
      )
      showEditSpecies.value = false
      editSpeciesForm.value = null
      messages.success('Вид обновлён')
      clearCatalogMutationCaches()
      await refreshCatalogAfterMutation()
    } catch (e: any) {
      messages.error(e.response?.data?.detail || 'Не удалось обновить вид')
    } finally {
      editSpeciesSaving.value = false
    }
  }

  async function deleteSpecies(id: number) {
    try {
      await apiClient.delete(`/species/${id}`)
      messages.success('Вид удалён')
      clearCatalogMutationCaches()
      await refreshCatalogAfterMutation()
    } catch (e: any) {
      messages.error(e.response?.data?.detail || 'Ошибка')
    }
  }

  return {
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
    applyCatalogQualityGap,
    applyCatalogQualityGapFromPanel,
    debouncedFetchSpecies,
    resetAdminSpeciesFilters,
    onAdminSpeciesPageChange,
    addSpecies,
    openAddSpecies,
    openEditSpecies,
    saveSpeciesEdit,
    deleteSpecies,
  }
}
