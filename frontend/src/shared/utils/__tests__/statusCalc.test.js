/**
 * tests/statusCalc.test.js
 * Unit tests for shared/utils/statusCalc.js
 *
 * These are pure function tests — no React, no DOM needed.
 */
import { describe, it, expect } from 'vitest'
import {
  checkStatus,
  lineItemStatus,
  hasFailItem,
  hasWarnItem,
  compartmentStatus,
  checkTypeLabel,
  hapticPattern,
} from '../statusCalc.js'

// ── checkStatus ───────────────────────────────────────────────────────────────
describe('checkStatus', () => {
  it('PASS returns ok severity', () => {
    expect(checkStatus('PASS').severity).toBe('ok')
    expect(checkStatus('PASS').label).toBe('Pass')
  })

  it('NEEDS_RESTOCK returns warn severity', () => {
    expect(checkStatus('NEEDS_RESTOCK').severity).toBe('warn')
    expect(checkStatus('NEEDS_RESTOCK').label).toBe('Restock needed')
  })

  it('FAIL returns fail severity', () => {
    expect(checkStatus('FAIL').severity).toBe('fail')
    expect(checkStatus('FAIL').label).toBe('Problem found')
  })

  it('unknown status returns ok severity with Unknown label', () => {
    const result = checkStatus('BOGUS')
    expect(result.severity).toBe('ok')
    expect(result.label).toBe('Unknown')
  })

  it('every result has label, icon, color, bg, severity', () => {
    for (const s of ['PASS', 'NEEDS_RESTOCK', 'FAIL']) {
      const r = checkStatus(s)
      expect(r).toHaveProperty('label')
      expect(r).toHaveProperty('icon')
      expect(r).toHaveProperty('color')
      expect(r).toHaveProperty('bg')
      expect(r).toHaveProperty('severity')
    }
  })
})

// ── lineItemStatus ────────────────────────────────────────────────────────────
describe('lineItemStatus', () => {
  it('OK returns ok severity', () => {
    expect(lineItemStatus('OK').severity).toBe('ok')
    expect(lineItemStatus('OK').label).toBe('OK')
  })

  it('SHORT returns warn severity', () => {
    expect(lineItemStatus('SHORT').severity).toBe('warn')
  })

  it('LOW returns warn severity', () => {
    expect(lineItemStatus('LOW').severity).toBe('warn')
    expect(lineItemStatus('LOW').label).toBe('Low')
  })

  it('MISSING returns fail severity', () => {
    expect(lineItemStatus('MISSING').severity).toBe('fail')
    expect(lineItemStatus('MISSING').label).toBe('Missing')
  })

  it('EXPIRED returns fail severity', () => {
    expect(lineItemStatus('EXPIRED').severity).toBe('fail')
    expect(lineItemStatus('EXPIRED').label).toBe('Expired')
  })

  it('FAIL returns fail severity', () => {
    expect(lineItemStatus('FAIL').severity).toBe('fail')
    expect(lineItemStatus('FAIL').label).toBe('Problem found')
  })

  it('OVERDUE returns fail severity', () => {
    expect(lineItemStatus('OVERDUE').severity).toBe('fail')
    expect(lineItemStatus('OVERDUE').label).toBe('Overdue')
  })

  it('unknown status returns Not checked', () => {
    expect(lineItemStatus('UNKNOWN').label).toBe('Not checked')
  })
})

// ── hasFailItem / hasWarnItem ─────────────────────────────────────────────────
describe('hasFailItem', () => {
  it('returns true when any item is MISSING', () => {
    expect(hasFailItem([{ status: 'OK' }, { status: 'MISSING' }])).toBe(true)
  })

  it('returns true when any item is EXPIRED', () => {
    expect(hasFailItem([{ status: 'EXPIRED' }])).toBe(true)
  })

  it('returns true when any item is FAIL', () => {
    expect(hasFailItem([{ status: 'FAIL' }])).toBe(true)
  })

  it('returns true when any item is OVERDUE', () => {
    expect(hasFailItem([{ status: 'OVERDUE' }])).toBe(true)
  })

  it('returns false when all items are OK', () => {
    expect(hasFailItem([{ status: 'OK' }, { status: 'OK' }])).toBe(false)
  })

  it('returns false when items are only SHORT or LOW', () => {
    expect(hasFailItem([{ status: 'SHORT' }, { status: 'LOW' }])).toBe(false)
  })
})

describe('hasWarnItem', () => {
  it('returns true when there is a SHORT and no FAIL', () => {
    expect(hasWarnItem([{ status: 'SHORT' }])).toBe(true)
  })

  it('returns true when there is a LOW and no FAIL', () => {
    expect(hasWarnItem([{ status: 'LOW' }])).toBe(true)
  })

  it('returns false when there is a FAIL (fail takes priority)', () => {
    expect(hasWarnItem([{ status: 'SHORT' }, { status: 'MISSING' }])).toBe(false)
  })

  it('returns false when all items are OK', () => {
    expect(hasWarnItem([{ status: 'OK' }])).toBe(false)
  })
})

// ── compartmentStatus ─────────────────────────────────────────────────────────
describe('compartmentStatus', () => {
  it('empty line items → PASS', () => {
    expect(compartmentStatus([]).severity).toBe('ok')
  })

  it('all OK → PASS', () => {
    expect(compartmentStatus([{ status: 'OK' }, { status: 'OK' }]).severity).toBe('ok')
  })

  it('any MISSING → FAIL', () => {
    expect(compartmentStatus([{ status: 'OK' }, { status: 'MISSING' }]).severity).toBe('fail')
  })

  it('any SHORT (no FAIL) → NEEDS_RESTOCK (warn)', () => {
    expect(compartmentStatus([{ status: 'OK' }, { status: 'SHORT' }]).severity).toBe('warn')
  })

  it('FAIL beats SHORT', () => {
    expect(compartmentStatus([{ status: 'SHORT' }, { status: 'EXPIRED' }]).severity).toBe('fail')
  })
})

// ── checkTypeLabel ────────────────────────────────────────────────────────────
describe('checkTypeLabel', () => {
  it('SUPPLY returns empty string', () => {
    expect(checkTypeLabel('SUPPLY')).toBe('')
  })

  it('MEASUREMENT returns Reading', () => {
    expect(checkTypeLabel('MEASUREMENT')).toBe('Reading')
  })

  it('FUNCTIONAL returns Pass/Fail', () => {
    expect(checkTypeLabel('FUNCTIONAL')).toBe('Pass/Fail')
  })

  it('DATE_RECORD returns Date', () => {
    expect(checkTypeLabel('DATE_RECORD')).toBe('Date')
  })

  it('DOCUMENT returns Document', () => {
    expect(checkTypeLabel('DOCUMENT')).toBe('Document')
  })

  it('unknown returns the raw value', () => {
    expect(checkTypeLabel('CUSTOM')).toBe('CUSTOM')
  })
})

// ── hapticPattern ─────────────────────────────────────────────────────────────
describe('hapticPattern', () => {
  it('OK → short pulse [40]', () => {
    expect(hapticPattern('OK')).toEqual([40])
  })

  it('FAIL → double pulse', () => {
    expect(hapticPattern('FAIL')).toEqual([80, 40, 80])
  })

  it('MISSING → double pulse', () => {
    expect(hapticPattern('MISSING')).toEqual([80, 40, 80])
  })

  it('EXPIRED → double pulse', () => {
    expect(hapticPattern('EXPIRED')).toEqual([80, 40, 80])
  })

  it('SHORT → null (no vibration for warn)', () => {
    expect(hapticPattern('SHORT')).toBeNull()
  })

  it('LOW → null', () => {
    expect(hapticPattern('LOW')).toBeNull()
  })
})
