/**
 * tests/dateHelpers.test.js
 * Unit tests for shared/utils/dateHelpers.js
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  formatCheckDate,
  formatShortDate,
  todayIso,
  relativeIso,
  daysBetween,
  isExpired,
  clampCheckDate,
} from '../dateHelpers.js'

describe('formatCheckDate', () => {
  it('formats a YYYY-MM-DD string as a long weekday date', () => {
    const result = formatCheckDate('2026-05-13')
    expect(result).toContain('2026')
    expect(result).toContain('13')
    // Day of week for 2026-05-13 is Wednesday
    expect(result).toContain('Wednesday')
  })

  it('returns empty string for falsy input', () => {
    expect(formatCheckDate('')).toBe('')
    expect(formatCheckDate(null)).toBe('')
  })
})

describe('formatShortDate', () => {
  it('formats a date without weekday', () => {
    const result = formatShortDate('2026-05-13')
    expect(result).toContain('2026')
    expect(result).not.toContain('Wednesday')
  })

  it('returns empty string for empty input', () => {
    expect(formatShortDate('')).toBe('')
  })
})

describe('todayIso', () => {
  it('returns a YYYY-MM-DD string', () => {
    const result = todayIso()
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})

describe('relativeIso', () => {
  it('offset 0 returns today', () => {
    expect(relativeIso(0)).toBe(todayIso())
  })

  it('offset -1 returns yesterday', () => {
    const yesterday = relativeIso(-1)
    const today = todayIso()
    expect(yesterday < today).toBe(true)
  })

  it('returns YYYY-MM-DD format', () => {
    expect(relativeIso(-7)).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})

describe('daysBetween', () => {
  it('same date → 0', () => {
    expect(daysBetween('2026-05-01', '2026-05-01')).toBe(0)
  })

  it('one day apart → 1', () => {
    expect(daysBetween('2026-05-01', '2026-05-02')).toBe(1)
  })

  it('negative when B is before A', () => {
    expect(daysBetween('2026-05-10', '2026-05-01')).toBe(-9)
  })

  it('month boundary', () => {
    expect(daysBetween('2026-01-31', '2026-02-01')).toBe(1)
  })
})

describe('isExpired', () => {
  it('past date is expired', () => {
    expect(isExpired('2020-01-01')).toBe(true)
  })

  it('future date is not expired', () => {
    expect(isExpired('2099-12-31')).toBe(false)
  })

  it('empty string is not expired', () => {
    expect(isExpired('')).toBe(false)
  })
})

describe('clampCheckDate', () => {
  it('today is valid', () => {
    const today = todayIso()
    expect(clampCheckDate(today)).toBe(today)
  })

  it('future date is clamped to today', () => {
    const future = relativeIso(3)
    expect(clampCheckDate(future)).toBe(todayIso())
  })

  it('date 7 days ago is valid with default limit', () => {
    const sevenDaysAgo = relativeIso(-7)
    expect(clampCheckDate(sevenDaysAgo)).toBe(sevenDaysAgo)
  })

  it('date 8 days ago is clamped to 7 days ago', () => {
    const eightDaysAgo = relativeIso(-8)
    const sevenDaysAgo = relativeIso(-7)
    expect(clampCheckDate(eightDaysAgo)).toBe(sevenDaysAgo)
  })

  it('respects custom maxDaysBack', () => {
    const threeDaysAgo = relativeIso(-3)
    expect(clampCheckDate(threeDaysAgo, 2)).toBe(relativeIso(-2))
  })
})
