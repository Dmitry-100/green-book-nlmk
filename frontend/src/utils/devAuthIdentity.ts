export type DevAuthRole = 'employee' | 'ecologist' | 'admin'

export const DEV_AUTH_DISPLAY_NAME_STORAGE_KEY = 'green-book-dev-auth-display-name'
export const DEV_AUTH_EMAIL_STORAGE_KEY = 'green-book-dev-auth-email'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function normalizeDevAuthDisplayName(value?: string | null): string {
  return value?.trim().replace(/\s+/g, ' ') || ''
}

export function normalizeDevAuthEmail(value?: string | null): string {
  const normalized = value?.trim().toLowerCase() || ''
  return EMAIL_RE.test(normalized) ? normalized : ''
}

export function isInvalidDevAuthEmail(value?: string | null): boolean {
  const normalized = value?.trim() || ''
  return normalized.length > 0 && !EMAIL_RE.test(normalized)
}

export function buildDevAuthEmail(
  displayName: string,
  role: DevAuthRole,
  explicitEmail?: string | null
): string {
  const normalizedEmail = normalizeDevAuthEmail(explicitEmail)
  if (normalizedEmail) {
    return normalizedEmail
  }

  const normalizedName = normalizeDevAuthDisplayName(displayName)
  const identityHash = hashDevAuthIdentity(`${role}:${normalizedName}`)
  return `${role}.${identityHash}@nlmk.dev`
}

function hashDevAuthIdentity(value: string): string {
  let hash = 2166136261
  for (const char of value) {
    hash ^= char.codePointAt(0) || 0
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0).toString(36)
}
