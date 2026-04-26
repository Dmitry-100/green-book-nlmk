import { describe, expect, it } from 'vitest'

import {
  fromDatetimeLocalInputValue,
  toDatetimeLocalInputValue,
} from './datetimeLocal'

describe('datetimeLocal', () => {
  it('formats a Date for datetime-local inputs without seconds', () => {
    const value = new Date(2026, 3, 26, 9, 5, 42)

    expect(toDatetimeLocalInputValue(value)).toBe('2026-04-26T09:05')
  })

  it('parses datetime-local input values into local Date objects', () => {
    const value = fromDatetimeLocalInputValue('2026-04-26T09:05')

    expect(value).toBeInstanceOf(Date)
    expect(value?.getFullYear()).toBe(2026)
    expect(value?.getMonth()).toBe(3)
    expect(value?.getDate()).toBe(26)
    expect(value?.getHours()).toBe(9)
    expect(value?.getMinutes()).toBe(5)
  })

  it('returns null for empty or invalid input values', () => {
    expect(fromDatetimeLocalInputValue('')).toBeNull()
    expect(fromDatetimeLocalInputValue('not-a-date')).toBeNull()
  })
})
