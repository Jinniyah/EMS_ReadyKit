/**
 * shared/utils/statusCalc.js
 * Maps API status strings to UI presentation values.
 *
 * The API returns status strings for two levels:
 *
 *   Check-level (DailyInventoryCheck.status):
 *     PASS | NEEDS_RESTOCK | FAIL
 *
 *   Line-item-level (CheckLineItem.status):
 *     OK | SHORT | MISSING | EXPIRED | LOW | FAIL | OVERDUE
 *
 * This module maps each value to:
 *   label    — plain English label shown to users (never raw API string)
 *   color    — CSS custom property name (--color-status-*)
 *   bg       — background CSS custom property for item rows
 *   icon     — emoji icon (always shown with label — never icon alone)
 *   severity — 'ok' | 'warn' | 'fail' for programmatic use
 *
 * Design decisions (from ADR-005 and phase5_frontend_pwa.md):
 *   - Status is always communicated with both color AND text (never color alone)
 *   - Row backgrounds use 200-stop fills for outdoor sunlight readability
 *   - Validate button uses 600-stop for maximum contrast with white icon
 *
 * Usage:
 *   import { checkStatus, lineItemStatus } from '../utils/statusCalc.js'
 *
 *   const { label, icon, color, severity } = checkStatus('NEEDS_RESTOCK')
 *   const { label, bg } = lineItemStatus('EXPIRED')
 */

// ── Check-level status ────────────────────────────────────────────────────────

const CHECK_STATUS_MAP = {
  PASS: {
    label:    'Pass',
    icon:     '✓',
    color:    'var(--color-status-pass)',
    bg:       'var(--color-status-pass-bg)',
    severity: 'ok',
  },
  NEEDS_RESTOCK: {
    label:    'Needs Restock',
    icon:     '↓',
    color:    'var(--color-status-warn)',
    bg:       'var(--color-status-warn-bg)',
    severity: 'warn',
  },
  FAIL: {
    label:    'Fail',
    icon:     '✗',
    color:    'var(--color-status-fail)',
    bg:       'var(--color-status-fail-bg)',
    severity: 'fail',
  },
}

const CHECK_STATUS_UNKNOWN = {
  label:    'Unknown',
  icon:     '?',
  color:    'var(--color-text-muted)',
  bg:       'var(--color-surface)',
  severity: 'ok',
}

/**
 * Returns display values for a check-level status string.
 * @param {string} status — API check status value
 * @returns {{ label, icon, color, bg, severity }}
 */
export function checkStatus(status) {
  return CHECK_STATUS_MAP[status] ?? CHECK_STATUS_UNKNOWN
}

// ── Line-item-level status ────────────────────────────────────────────────────

const LINE_ITEM_STATUS_MAP = {
  OK: {
    label:    'OK',
    icon:     '✓',
    color:    'var(--color-status-pass)',
    bg:       'var(--color-status-pass-bg)',
    severity: 'ok',
  },
  SHORT: {
    label:    'Short',
    icon:     '↓',
    color:    'var(--color-status-warn)',
    bg:       'var(--color-status-warn-bg)',
    severity: 'warn',
  },
  LOW: {
    label:    'Low',
    icon:     '↓',
    color:    'var(--color-status-warn)',
    bg:       'var(--color-status-warn-bg)',
    severity: 'warn',
  },
  MISSING: {
    label:    'Missing',
    icon:     '✗',
    color:    'var(--color-status-fail)',
    bg:       'var(--color-status-fail-bg)',
    severity: 'fail',
  },
  EXPIRED: {
    label:    'Expired',
    icon:     '⚠',
    color:    'var(--color-status-fail)',
    bg:       'var(--color-status-fail-bg)',
    severity: 'fail',
  },
  FAIL: {
    label:    'Failed',
    icon:     '✗',
    color:    'var(--color-status-fail)',
    bg:       'var(--color-status-fail-bg)',
    severity: 'fail',
  },
  OVERDUE: {
    label:    'Overdue',
    icon:     '⚠',
    color:    'var(--color-status-fail)',
    bg:       'var(--color-status-fail-bg)',
    severity: 'fail',
  },
}

const LINE_ITEM_UNKNOWN = {
  label:    'Not checked',
  icon:     '○',
  color:    'var(--color-text-muted)',
  bg:       'var(--color-surface)',
  severity: 'ok',
}

/**
 * Returns display values for a line-item-level status string.
 * @param {string} status — API line item status value
 * @returns {{ label, icon, color, bg, severity }}
 */
export function lineItemStatus(status) {
  return LINE_ITEM_STATUS_MAP[status] ?? LINE_ITEM_UNKNOWN
}

// ── Severity helpers ──────────────────────────────────────────────────────────

/**
 * Returns true if any line item in the array has fail-tier severity.
 * Used to determine whether a compartment blocks submission.
 * @param {Array<{status: string}>} lineItems
 */
export function hasFailItem(lineItems) {
  return lineItems.some(li => lineItemStatus(li.status).severity === 'fail')
}

/**
 * Returns true if any line item has warn-tier severity (but no fail).
 * @param {Array<{status: string}>} lineItems
 */
export function hasWarnItem(lineItems) {
  return !hasFailItem(lineItems) &&
    lineItems.some(li => lineItemStatus(li.status).severity === 'warn')
}

/**
 * Derives an overall compartment badge from its line items.
 * Mirrors the server-side _compute_check_status logic so the UI
 * can show a compartment status before the check is submitted.
 * @param {Array<{status: string}>} lineItems
 * @returns {{ label, icon, color, bg, severity }}
 */
export function compartmentStatus(lineItems) {
  if (!lineItems || lineItems.length === 0) return lineItemStatus('OK')
  if (hasFailItem(lineItems)) return checkStatus('FAIL')
  if (hasWarnItem(lineItems)) return checkStatus('NEEDS_RESTOCK')
  return checkStatus('PASS')
}

/**
 * Returns the check_type display label for an item.
 * @param {string} checkType — API check_type value
 * @returns {string}
 */
export function checkTypeLabel(checkType) {
  const MAP = {
    SUPPLY:      '',               // default — no badge needed
    MEASUREMENT: 'Reading',
    FUNCTIONAL:  'Pass/Fail',
    DATE_RECORD: 'Date',
    DOCUMENT:    'Document',
  }
  return MAP[checkType] ?? checkType
}

/**
 * Returns haptic vibration pattern for a given line item status.
 * Returns null if no vibration is appropriate.
 * From phase5_frontend_pwa.md §5b: short pulse on validate OK,
 * double pulse on FAIL detection.
 * @param {string} status
 * @returns {number[] | null}
 */
export function hapticPattern(status) {
  const s = lineItemStatus(status)
  if (s.severity === 'fail') return [80, 40, 80]
  if (s.severity === 'ok')   return [40]
  return null
}
