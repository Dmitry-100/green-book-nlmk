import { describe, expect, it } from 'vitest'
import { DEMO_USER_DISPLAY_NAME, buildUserInitials, normalizeDemoDisplayName } from './userInitials'

describe('user initials', () => {
  it('uses first name and patronymic for a full Russian name', () => {
    expect(buildUserInitials('Дмитрий Максимович Сотников')).toBe('ДМ')
  })

  it('uses abbreviated first name and patronymic from surname-first format', () => {
    expect(buildUserInitials('Сотников Д.М.')).toBe('ДМ')
  })

  it('falls back for empty names', () => {
    expect(buildUserInitials('', 'У')).toBe('У')
  })

  it('normalizes stale demo names from old sessions', () => {
    expect(normalizeDemoDisplayName('Сотников Д.С.')).toBe(DEMO_USER_DISPLAY_NAME)
    expect(normalizeDemoDisplayName('Dev employee')).toBe(DEMO_USER_DISPLAY_NAME)
  })
})
