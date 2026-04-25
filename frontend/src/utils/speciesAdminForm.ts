export type AdminSpeciesRow = {
  id: number
  name_ru: string
  name_latin: string
  group: string
  category: string
  conservation_status?: string | null
  is_poisonous: boolean
  season_info?: string | null
  biotopes?: string | null
  description?: string | null
  do_dont_rules?: string | null
  photo_urls?: string[] | null
  audio_url?: string | null
  audio_title?: string | null
  audio_source?: string | null
  audio_license?: string | null
}

export const SPECIES_ADMIN_FORM_TABS = [
  { name: 'main', label: 'Основное' },
  { name: 'content', label: 'Контент' },
  { name: 'media', label: 'Медиа' },
] as const

export type AdminSpeciesListFilters = {
  search: string
  group: string
  category: string
  has_audio: boolean
  quality_gap: AdminSpeciesQualityGap
}

export type AdminSpeciesListPagination = {
  page: number
  pageSize: number
}

export type AdminSpeciesQualityGap =
  | ''
  | 'missing_photo'
  | 'missing_description'
  | 'short_description'
  | 'missing_audio'
export type AdminSpeciesQualityGapCode = Exclude<AdminSpeciesQualityGap, ''>

type AdminSpeciesListQueryValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | Array<string | number | boolean | null | undefined>

export type AdminSpeciesListUrlQuery = Record<string, AdminSpeciesListQueryValue>

export type SpeciesAdminQualityBadge = {
  code: AdminSpeciesQualityGapCode
  label: string
  type: 'warning' | 'info'
}

export type SpeciesContentGapCounts = Partial<
  Record<AdminSpeciesQualityGapCode, number>
>

export type SpeciesAdminQualityGapItem = {
  code: AdminSpeciesQualityGapCode
  label: string
  count: number
  type: 'warning' | 'info'
}

export type AdminSpeciesEditForm = {
  id: number | null
  name_ru: string
  name_latin: string
  group: string
  category: string
  conservation_status: string
  is_poisonous: boolean
  season_info: string
  biotopes: string
  description: string
  do_dont_rules: string
  photo_urls_text: string
  audio_url: string
  audio_title: string
  audio_source: string
  audio_license: string
}

const ADMIN_SPECIES_QUERY_KEYS = new Set([
  'species_search',
  'species_group',
  'species_category',
  'species_has_audio',
  'species_quality_gap',
  'species_page',
])

const ADMIN_SPECIES_GROUPS = new Set([
  'plants',
  'fungi',
  'insects',
  'herpetofauna',
  'birds',
  'mammals',
])

const ADMIN_SPECIES_CATEGORIES = new Set([
  'ruderal',
  'typical',
  'rare',
  'red_book',
  'synanthropic',
])

const ADMIN_SPECIES_QUALITY_GAPS = new Set([
  'missing_photo',
  'missing_description',
  'short_description',
  'missing_audio',
])

const ADMIN_SPECIES_QUALITY_GAP_ITEMS: Array<
  Omit<SpeciesAdminQualityGapItem, 'count'>
> = [
  { code: 'missing_photo', label: 'Без фото', type: 'warning' },
  { code: 'missing_description', label: 'Без описания', type: 'warning' },
  { code: 'short_description', label: 'Короткое описание', type: 'warning' },
  { code: 'missing_audio', label: 'Без аудио', type: 'info' },
]
const SHORT_DESCRIPTION_MIN_CHARS = 120

function text(value: string | null | undefined): string {
  return value || ''
}

function optionalText(value: string): string | null {
  const normalized = value.trim()
  return normalized || null
}

function mediaList(value: string): string[] | null {
  const items = value
    .split(/\n|;/)
    .map((item) => item.trim())
    .filter(Boolean)
  return items.length ? items : null
}

function queryValue(value: AdminSpeciesListQueryValue): string {
  const raw = Array.isArray(value) ? value[0] : value
  if (raw === null || raw === undefined) {
    return ''
  }
  return String(raw).trim()
}

function hasText(value: string | null | undefined): boolean {
  return Boolean(value?.trim())
}

export function buildAdminSpeciesListParams(
  filters: AdminSpeciesListFilters,
  pagination: AdminSpeciesListPagination = { page: 1, pageSize: 200 }
) {
  const page = Math.max(1, Math.floor(pagination.page))
  const pageSize = Math.max(1, Math.floor(pagination.pageSize))
  const skip = (page - 1) * pageSize
  const params: Record<string, string | number | boolean> = {
    ...(skip > 0 ? { skip } : {}),
    limit: pageSize,
    include_total: true,
  }
  const search = filters.search.trim()
  if (search.length >= 2) {
    params.search = search
  }
  if (filters.group) {
    params.group = filters.group
  }
  if (filters.category) {
    params.category = filters.category
  }
  if (filters.has_audio && filters.quality_gap !== 'missing_audio') {
    params.has_audio = true
  }
  if (filters.quality_gap) {
    params.quality_gap = filters.quality_gap
  }
  return params
}

export function buildAdminSpeciesListCacheKey(
  params: Record<string, string | number | boolean>
): string {
  return `species:list:admin:${JSON.stringify(params)}`
}

export function buildAdminSpeciesListUrlQuery(
  currentQuery: AdminSpeciesListUrlQuery,
  filters: AdminSpeciesListFilters,
  pagination: AdminSpeciesListPagination
): Record<string, string> {
  const query: Record<string, string> = {}

  for (const [key, value] of Object.entries(currentQuery)) {
    if (ADMIN_SPECIES_QUERY_KEYS.has(key)) {
      continue
    }
    const normalized = queryValue(value)
    if (normalized) {
      query[key] = normalized
    }
  }

  const search = filters.search.trim()
  if (search) {
    query.species_search = search
  }
  if (filters.group) {
    query.species_group = filters.group
  }
  if (filters.category) {
    query.species_category = filters.category
  }
  if (filters.has_audio && filters.quality_gap !== 'missing_audio') {
    query.species_has_audio = 'true'
  }
  if (filters.quality_gap) {
    query.species_quality_gap = filters.quality_gap
  }
  if (pagination.page > 1) {
    query.species_page = String(Math.floor(pagination.page))
  }

  return query
}

export function parseAdminSpeciesListUrlState(
  query: AdminSpeciesListUrlQuery,
  pageSize: number
): {
  filters: AdminSpeciesListFilters
  pagination: AdminSpeciesListPagination
} {
  const group = queryValue(query.species_group)
  const category = queryValue(query.species_category)
  const qualityGap = queryValue(query.species_quality_gap)
  const page = Number.parseInt(queryValue(query.species_page), 10)
  const normalizedQualityGap = ADMIN_SPECIES_QUALITY_GAPS.has(qualityGap)
    ? (qualityGap as AdminSpeciesQualityGap)
    : ''
  const hasAudio =
    normalizedQualityGap !== 'missing_audio' &&
    ['true', '1', 'yes'].includes(
      queryValue(query.species_has_audio).toLowerCase()
    )

  return {
    filters: {
      search: queryValue(query.species_search),
      group: ADMIN_SPECIES_GROUPS.has(group) ? group : '',
      category: ADMIN_SPECIES_CATEGORIES.has(category) ? category : '',
      has_audio: hasAudio,
      quality_gap: normalizedQualityGap,
    },
    pagination: {
      page: Number.isInteger(page) && page > 0 ? page : 1,
      pageSize: Math.max(1, Math.floor(pageSize)),
    },
  }
}

export function clampAdminSpeciesListPage(
  page: number,
  total: number,
  pageSize: number
): number {
  const safePage = Math.max(1, Math.floor(page))
  const safeTotal = Math.max(0, Math.floor(total))
  const safePageSize = Math.max(1, Math.floor(pageSize))
  const lastPage = Math.max(1, Math.ceil(safeTotal / safePageSize))
  return Math.min(safePage, lastPage)
}

export function buildSpeciesAdminQualityBadges(
  row: AdminSpeciesRow
): SpeciesAdminQualityBadge[] {
  const badges: SpeciesAdminQualityBadge[] = []
  const description = row.description?.trim() ?? ''
  if (!row.photo_urls?.some(hasText)) {
    badges.push({ code: 'missing_photo', label: 'нет фото', type: 'warning' })
  }
  if (!description) {
    badges.push({
      code: 'missing_description',
      label: 'нет описания',
      type: 'warning',
    })
  } else if (description.length < SHORT_DESCRIPTION_MIN_CHARS) {
    badges.push({
      code: 'short_description',
      label: 'короткое описание',
      type: 'warning',
    })
  }
  if (!hasText(row.audio_url)) {
    badges.push({ code: 'missing_audio', label: 'нет аудио', type: 'info' })
  }
  return badges
}

export function buildSpeciesAdminQualityGapItems(
  counts: SpeciesContentGapCounts | null | undefined
): SpeciesAdminQualityGapItem[] {
  return ADMIN_SPECIES_QUALITY_GAP_ITEMS.map((item) => ({
    ...item,
    count: Math.max(0, Math.floor(counts?.[item.code] ?? 0)),
  }))
}

export function buildSpeciesAdminQualityGapExportFilename(
  qualityGap: AdminSpeciesQualityGapCode
): string {
  return `species-catalog-${qualityGap.replace(/_/g, '-')}.csv`
}

export function buildSpeciesEditForm(row: AdminSpeciesRow): AdminSpeciesEditForm {
  return {
    id: row.id,
    name_ru: row.name_ru,
    name_latin: row.name_latin,
    group: row.group,
    category: row.category,
    conservation_status: text(row.conservation_status),
    is_poisonous: row.is_poisonous,
    season_info: text(row.season_info),
    biotopes: text(row.biotopes),
    description: text(row.description),
    do_dont_rules: text(row.do_dont_rules),
    photo_urls_text: (row.photo_urls || []).join('\n'),
    audio_url: text(row.audio_url),
    audio_title: text(row.audio_title),
    audio_source: text(row.audio_source),
    audio_license: text(row.audio_license),
  }
}

export function buildEmptySpeciesForm(): AdminSpeciesEditForm {
  return {
    id: null,
    name_ru: '',
    name_latin: '',
    group: 'plants',
    category: 'typical',
    conservation_status: '',
    is_poisonous: false,
    season_info: '',
    biotopes: '',
    description: '',
    do_dont_rules: '',
    photo_urls_text: '',
    audio_url: '',
    audio_title: '',
    audio_source: '',
    audio_license: '',
  }
}

export function buildSpeciesUpdatePayload(form: AdminSpeciesEditForm) {
  return {
    name_ru: form.name_ru.trim(),
    name_latin: form.name_latin.trim(),
    group: form.group,
    category: form.category,
    conservation_status: optionalText(form.conservation_status),
    is_poisonous: form.is_poisonous,
    season_info: optionalText(form.season_info),
    biotopes: optionalText(form.biotopes),
    description: optionalText(form.description),
    do_dont_rules: optionalText(form.do_dont_rules),
    photo_urls: mediaList(form.photo_urls_text),
    audio_url: optionalText(form.audio_url),
    audio_title: optionalText(form.audio_title),
    audio_source: optionalText(form.audio_source),
    audio_license: optionalText(form.audio_license),
  }
}

export function buildSpeciesFormPreview(form: AdminSpeciesEditForm) {
  const photoUrls = mediaList(form.photo_urls_text)

  return {
    name_ru: form.name_ru.trim(),
    name_latin: form.name_latin.trim(),
    group: form.group,
    category: form.category,
    conservation_status: optionalText(form.conservation_status),
    is_poisonous: form.is_poisonous,
    season_info: optionalText(form.season_info),
    biotopes: optionalText(form.biotopes),
    description: optionalText(form.description),
    do_dont_rules: optionalText(form.do_dont_rules),
    photo_url: photoUrls?.[0] || null,
    has_audio: Boolean(optionalText(form.audio_url)),
    audio_title: optionalText(form.audio_title),
  }
}
