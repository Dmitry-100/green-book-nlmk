import { describe, expect, it } from 'vitest'
import {
  buildDevAuthEmail,
  isInvalidDevAuthEmail,
  normalizeDevAuthDisplayName,
  normalizeDevAuthEmail,
} from './devAuthIdentity'

describe('dev auth identity', () => {
  it('normalizes tester display names', () => {
    expect(normalizeDevAuthDisplayName('  Иван   Иванович   Иванов  ')).toBe('Иван Иванович Иванов')
  })

  it('uses an explicit email when it is provided', () => {
    expect(buildDevAuthEmail('Иван Иванов', 'employee', ' Ivan.Ivanov@NLMK.com ')).toBe(
      'ivan.ivanov@nlmk.com'
    )
  })

  it('generates stable dev emails without exposing the full name', () => {
    const first = buildDevAuthEmail('Иван Иванов', 'employee')
    const second = buildDevAuthEmail('Иван Иванов', 'employee')
    const otherRole = buildDevAuthEmail('Иван Иванов', 'admin')

    expect(first).toBe(second)
    expect(first).toMatch(/^employee\.[a-z0-9]+@nlmk\.dev$/)
    expect(first).not.toContain('Иван')
    expect(otherRole).not.toBe(first)
  })

  it('validates optional emails', () => {
    expect(normalizeDevAuthEmail('tester@nlmk.com')).toBe('tester@nlmk.com')
    expect(normalizeDevAuthEmail('bad-email')).toBe('')
    expect(isInvalidDevAuthEmail('bad-email')).toBe(true)
    expect(isInvalidDevAuthEmail('')).toBe(false)
  })
})
