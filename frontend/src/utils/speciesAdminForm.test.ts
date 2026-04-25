import { describe, expect, it } from 'vitest'
import {
  SPECIES_ADMIN_FORM_TABS,
  buildAdminSpeciesListCacheKey,
  buildAdminSpeciesListParams,
  buildAdminSpeciesListUrlQuery,
  buildSpeciesAdminQualityBadges,
  buildSpeciesAdminQualityGapExportFilename,
  buildSpeciesAdminQualityGapItems,
  clampAdminSpeciesListPage,
  buildSpeciesFormPreview,
  buildEmptySpeciesForm,
  parseAdminSpeciesListUrlState,
  buildSpeciesEditForm,
  buildSpeciesUpdatePayload,
} from './speciesAdminForm'

describe('species admin form', () => {
  it('defines stable form tabs for add and edit dialogs', () => {
    expect(SPECIES_ADMIN_FORM_TABS).toEqual([
      { name: 'main', label: 'Основное' },
      { name: 'content', label: 'Контент' },
      { name: 'media', label: 'Медиа' },
    ])
  })

  it('builds admin species list params from filters', () => {
    expect(
      buildAdminSpeciesListParams({
        search: '  синица ',
        group: 'birds',
        category: 'synanthropic',
        has_audio: true,
        quality_gap: '',
      })
    ).toEqual({
      limit: 200,
      include_total: true,
      search: 'синица',
      group: 'birds',
      category: 'synanthropic',
      has_audio: true,
    })
  })

  it('omits short search and empty admin species list filters', () => {
    const params = buildAdminSpeciesListParams({
      search: ' с ',
      group: '',
      category: '',
      has_audio: false,
      quality_gap: '',
    })

    expect(params).toEqual({ limit: 200, include_total: true })
    expect(buildAdminSpeciesListCacheKey(params)).toBe(
      'species:list:admin:{"limit":200,"include_total":true}'
    )
  })

  it('builds paginated admin species list params and cache keys', () => {
    const params = buildAdminSpeciesListParams(
      {
        search: 'липа',
        group: 'plants',
        category: '',
        has_audio: false,
        quality_gap: 'missing_photo',
      },
      {
        page: 3,
        pageSize: 50,
      }
    )

    expect(params).toEqual({
      skip: 100,
      limit: 50,
      include_total: true,
      search: 'липа',
      group: 'plants',
      quality_gap: 'missing_photo',
    })
    expect(buildAdminSpeciesListCacheKey(params)).toBe(
      'species:list:admin:{"skip":100,"limit":50,"include_total":true,"search":"липа","group":"plants","quality_gap":"missing_photo"}'
    )
  })

  it('lets quality gap for missing audio win over has-audio filter', () => {
    expect(
      buildAdminSpeciesListParams({
        search: '',
        group: '',
        category: '',
        has_audio: true,
        quality_gap: 'missing_audio',
      })
    ).toEqual({
      limit: 200,
      include_total: true,
      quality_gap: 'missing_audio',
    })
  })

  it('builds clean URL query for admin species list state', () => {
    expect(
      buildAdminSpeciesListUrlQuery(
        { tab: 'species', species_search: 'old', species_page: '4' },
        {
          search: ' липа ',
          group: 'plants',
          category: '',
          has_audio: true,
          quality_gap: 'missing_description',
        },
        {
          page: 3,
          pageSize: 50,
        }
      )
    ).toEqual({
      tab: 'species',
      species_search: 'липа',
      species_group: 'plants',
      species_quality_gap: 'missing_description',
      species_has_audio: 'true',
      species_page: '3',
    })
  })

  it('parses admin species list state from URL query', () => {
    expect(
      parseAdminSpeciesListUrlState(
        {
          species_search: [' синица '],
          species_group: 'birds',
          species_category: 'rare',
          species_quality_gap: 'missing_photo',
          species_has_audio: 'true',
          species_page: '4',
        },
        50
      )
    ).toEqual({
      filters: {
        search: 'синица',
        group: 'birds',
        category: 'rare',
        has_audio: true,
        quality_gap: 'missing_photo',
      },
      pagination: {
        page: 4,
        pageSize: 50,
      },
    })
  })

  it('drops invalid admin species URL query values', () => {
    expect(
      parseAdminSpeciesListUrlState(
        {
          species_group: 'unknown',
          species_category: 'strange',
          species_quality_gap: 'unknown',
          species_has_audio: 'false',
          species_page: '-2',
        },
        50
      )
    ).toEqual({
      filters: {
        search: '',
        group: '',
        category: '',
        has_audio: false,
        quality_gap: '',
      },
      pagination: {
        page: 1,
        pageSize: 50,
      },
    })
  })

  it('clamps admin species page after total changes', () => {
    expect(clampAdminSpeciesListPage(5, 200, 50)).toBe(4)
    expect(clampAdminSpeciesListPage(3, 101, 50)).toBe(3)
    expect(clampAdminSpeciesListPage(5, 0, 50)).toBe(1)
    expect(clampAdminSpeciesListPage(-4, 120, 50)).toBe(1)
  })

  it('builds quality badges for incomplete admin species rows', () => {
    expect(
      buildSpeciesAdminQualityBadges({
        id: 12,
        name_ru: 'Пустая карточка',
        name_latin: 'Carduus',
        group: 'plants',
        category: 'typical',
        is_poisonous: false,
        photo_urls: [],
        description: ' ',
        audio_url: null,
      })
    ).toEqual([
      { code: 'missing_photo', label: 'нет фото', type: 'warning' },
      { code: 'missing_description', label: 'нет описания', type: 'warning' },
      { code: 'missing_audio', label: 'нет аудио', type: 'info' },
    ])
  })

  it('does not show quality badges for complete admin species rows', () => {
    expect(
      buildSpeciesAdminQualityBadges({
        id: 13,
        name_ru: 'Большая синица',
        name_latin: 'Parus major',
        group: 'birds',
        category: 'typical',
        is_poisonous: false,
        photo_urls: ['https://example.com/parus.jpg'],
        description:
          'Подробное описание вида для редакционной карточки, которое заметно длиннее минимального порога и помогает пользователю понять признаки, местообитания и сезонность.',
        audio_url: '/api/media/species-audio/parus-major.ogg',
      })
    ).toEqual([])
  })

  it('shows a warning for short descriptions', () => {
    expect(
      buildSpeciesAdminQualityBadges({
        id: 14,
        name_ru: 'Краткая карточка',
        name_latin: 'Vulpes vulpes',
        group: 'mammals',
        category: 'typical',
        is_poisonous: false,
        photo_urls: ['https://example.com/vulpes.jpg'],
        description: 'Очень коротко.',
        audio_url: '/api/media/species-audio/vulpes.ogg',
      })
    ).toEqual([
      {
        code: 'short_description',
        label: 'короткое описание',
        type: 'warning',
      },
    ])
  })

  it('builds quality gap filter counters in a stable order', () => {
    expect(
      buildSpeciesAdminQualityGapItems({
        missing_audio: 7,
        missing_photo: 2,
        short_description: 4,
      })
    ).toEqual([
      { code: 'missing_photo', label: 'Без фото', count: 2, type: 'warning' },
      {
        code: 'missing_description',
        label: 'Без описания',
        count: 0,
        type: 'warning',
      },
      {
        code: 'short_description',
        label: 'Короткое описание',
        count: 4,
        type: 'warning',
      },
      { code: 'missing_audio', label: 'Без аудио', count: 7, type: 'info' },
    ])
  })

  it('builds quality gap CSV export filenames', () => {
    expect(buildSpeciesAdminQualityGapExportFilename('missing_photo')).toBe(
      'species-catalog-missing-photo.csv'
    )
    expect(buildSpeciesAdminQualityGapExportFilename('missing_description')).toBe(
      'species-catalog-missing-description.csv'
    )
    expect(buildSpeciesAdminQualityGapExportFilename('missing_audio')).toBe(
      'species-catalog-missing-audio.csv'
    )
    expect(buildSpeciesAdminQualityGapExportFilename('short_description')).toBe(
      'species-catalog-short-description.csv'
    )
  })

  it('builds a full empty form for creating a species', () => {
    expect(buildEmptySpeciesForm()).toEqual({
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
    })
  })

  it('builds an editable form from a species row', () => {
    expect(
      buildSpeciesEditForm({
        id: 7,
        name_ru: 'Большая синица',
        name_latin: 'Parus major',
        group: 'birds',
        category: 'synanthropic',
        conservation_status: null,
        is_poisonous: false,
        season_info: 'апрель-июнь',
        biotopes: 'Парки',
        description: null,
        do_dont_rules: 'Не тревожить гнездо',
        photo_urls: ['https://example.com/a.jpg', 'https://example.com/b.jpg'],
        audio_url: '/api/media/species-audio/parus-major.ogg',
        audio_title: 'Голос',
        audio_source: null,
        audio_license: 'CC BY',
      })
    ).toEqual({
      id: 7,
      name_ru: 'Большая синица',
      name_latin: 'Parus major',
      group: 'birds',
      category: 'synanthropic',
      conservation_status: '',
      is_poisonous: false,
      season_info: 'апрель-июнь',
      biotopes: 'Парки',
      description: '',
      do_dont_rules: 'Не тревожить гнездо',
      photo_urls_text: 'https://example.com/a.jpg\nhttps://example.com/b.jpg',
      audio_url: '/api/media/species-audio/parus-major.ogg',
      audio_title: 'Голос',
      audio_source: '',
      audio_license: 'CC BY',
    })
  })

  it('normalizes optional text and media list for update payload', () => {
    expect(
      buildSpeciesUpdatePayload({
        id: 7,
        name_ru: '  Большая синица  ',
        name_latin: ' Parus major ',
        group: 'birds',
        category: 'synanthropic',
        conservation_status: ' ',
        is_poisonous: false,
        season_info: ' апрель-июнь ',
        biotopes: ' Парки ',
        description: '',
        do_dont_rules: ' Не тревожить гнездо ',
        photo_urls_text: ' https://example.com/a.jpg\n\nhttps://example.com/b.jpg ',
        audio_url: ' /api/media/species-audio/parus-major.ogg ',
        audio_title: ' ',
        audio_source: ' Wikimedia ',
        audio_license: ' CC BY ',
      })
    ).toEqual({
      name_ru: 'Большая синица',
      name_latin: 'Parus major',
      group: 'birds',
      category: 'synanthropic',
      conservation_status: null,
      is_poisonous: false,
      season_info: 'апрель-июнь',
      biotopes: 'Парки',
      description: null,
      do_dont_rules: 'Не тревожить гнездо',
      photo_urls: ['https://example.com/a.jpg', 'https://example.com/b.jpg'],
      audio_url: '/api/media/species-audio/parus-major.ogg',
      audio_title: null,
      audio_source: 'Wikimedia',
      audio_license: 'CC BY',
    })
  })

  it('builds preview data from the current form values', () => {
    expect(
      buildSpeciesFormPreview({
        id: null,
        name_ru: ' Большая синица ',
        name_latin: ' Parus major ',
        group: 'birds',
        category: 'synanthropic',
        conservation_status: 'Обычный вид',
        is_poisonous: false,
        season_info: ' апрель-июнь ',
        biotopes: ' Парки ',
        description: ' Обычная птица промплощадки. ',
        do_dont_rules: ' Не тревожить гнездо ',
        photo_urls_text: ' https://example.com/parus.jpg\nhttps://example.com/second.jpg ',
        audio_url: ' /api/media/species-audio/parus-major.ogg ',
        audio_title: ' Голос большой синицы ',
        audio_source: '',
        audio_license: '',
      })
    ).toEqual({
      name_ru: 'Большая синица',
      name_latin: 'Parus major',
      group: 'birds',
      category: 'synanthropic',
      conservation_status: 'Обычный вид',
      is_poisonous: false,
      season_info: 'апрель-июнь',
      biotopes: 'Парки',
      description: 'Обычная птица промплощадки.',
      do_dont_rules: 'Не тревожить гнездо',
      photo_url: 'https://example.com/parus.jpg',
      has_audio: true,
      audio_title: 'Голос большой синицы',
    })
  })

  it('clears photo urls when textarea is empty', () => {
    const payload = buildSpeciesUpdatePayload({
      ...buildSpeciesEditForm({
        id: 1,
        name_ru: 'Полынь',
        name_latin: 'Artemisia vulgaris',
        group: 'plants',
        category: 'ruderal',
        is_poisonous: false,
      }),
      photo_urls_text: '   ',
    })

    expect(payload.photo_urls).toBeNull()
  })
})
