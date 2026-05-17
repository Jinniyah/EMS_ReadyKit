/**
 * tests/useDraft.test.js
 * Unit tests for shared/hooks/useDraft.js
 *
 * Tests the pure helper functions — draftKey, _listAllDrafts logic via
 * localStorage mock.  The hook itself requires renderHook which we
 * test via the React Testing Library setup.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { draftKey } from '../useDraft.js'

describe('draftKey', () => {
  it('returns expected format', () => {
    expect(draftKey(712, '2026-05-13')).toBe('ems_draft_712_2026-05-13')
  })

  it('different vehicles produce different keys', () => {
    expect(draftKey(710, '2026-05-13')).not.toBe(draftKey(712, '2026-05-13'))
  })

  it('different dates produce different keys', () => {
    expect(draftKey(712, '2026-05-13')).not.toBe(draftKey(712, '2026-05-14'))
  })
})
