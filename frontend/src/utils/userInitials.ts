const ABBREVIATED_NAME_RE = /(?:^|\s)([A-Za-zА-ЯЁ])\.\s*([A-Za-zА-ЯЁ])\./u
const STALE_DEMO_DISPLAY_NAMES = new Set([
  'Сотников Д.С.',
  'Dev employee',
  'Dev ecologist',
  'Dev admin',
])

export const DEMO_USER_DISPLAY_NAME = 'Дмитрий Максимович Сотников'

function firstLetter(value: string): string {
  return value.match(/[A-Za-zА-Яа-яЁё]/u)?.[0] || ''
}

export function buildUserInitials(displayName?: string | null, fallback = '?'): string {
  const normalized = displayName?.trim().replace(/\s+/g, ' ')
  if (!normalized) {
    return fallback
  }

  const abbreviatedName = normalized.match(ABBREVIATED_NAME_RE)
  if (abbreviatedName) {
    return `${abbreviatedName[1]}${abbreviatedName[2]}`.toLocaleUpperCase('ru-RU')
  }

  const initials = normalized
    .split(' ')
    .map(firstLetter)
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toLocaleUpperCase('ru-RU')

  return initials || fallback
}

export function normalizeDemoDisplayName(displayName?: string | null): string {
  const normalized = displayName?.trim()
  if (!normalized || STALE_DEMO_DISPLAY_NAMES.has(normalized)) {
    return DEMO_USER_DISPLAY_NAME
  }

  return normalized
}
