import { describe, expect, it } from 'vitest'
import { DEMO_USER_DISPLAY_NAME, buildUserInitials, normalizeDemoDisplayName } from './userInitials'

describe('user initials', () => {
  it('uses first name and patronymic for a full Russian name', () => {
    expect(buildUserInitials('Иван Петрович Сидоров')).toBe('ИП')
  })

  it('uses abbreviated first name and patronymic from surname-first format', () => {
    expect(buildUserInitials('Сидоров И.П.')).toBe('ИП')
  })

  it('falls back for empty names', () => {
    expect(buildUserInitials('', 'У')).toBe('У')
  })

  it('normalizes stale demo names from old sessions', () => {
    expect(normalizeDemoDisplayName('Старое демо-имя')).toBe(DEMO_USER_DISPLAY_NAME)
    expect(normalizeDemoDisplayName('Dev employee')).toBe(DEMO_USER_DISPLAY_NAME)
  })
})
