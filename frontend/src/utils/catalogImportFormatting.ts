const CATALOG_FIELD_LABELS: Record<string, string> = {
  name_ru: 'Название',
  name_latin: 'Латинское название',
  group: 'Группа',
  category: 'Категория',
  conservation_status: 'Охранный статус',
  season_info: 'Сезонность',
  biotopes: 'Местообитания',
  description: 'Описание',
  do_dont_rules: 'Памятка',
  is_poisonous: 'Ядовитость',
  photo_urls: 'Фото',
  audio_url: 'Аудио',
  audio_title: 'Название аудио',
  audio_source: 'Источник аудио',
  audio_license: 'Лицензия аудио',
}

function fieldLabel(field: string): string {
  return CATALOG_FIELD_LABELS[field] || field
}

function valueLabel(value: unknown): string {
  if (Array.isArray(value)) {
    return value.length ? value.join('; ') : 'пусто'
  }
  if (value === null || value === undefined || value === '') {
    return 'пусто'
  }
  if (typeof value === 'boolean') {
    return value ? 'да' : 'нет'
  }
  return String(value)
}

export function formatCatalogImportFields(fields: string[]): string {
  return fields.map(fieldLabel).join(', ')
}

export function formatCatalogImportDelta(values: Record<string, unknown>): string {
  const entries = Object.entries(values)
  if (!entries.length) {
    return '—'
  }
  return entries
    .map(([key, value]) => `${fieldLabel(key)}: ${valueLabel(value)}`)
    .join(' | ')
}
