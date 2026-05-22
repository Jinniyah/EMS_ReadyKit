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

export function checkStatus(status) {
  return CHECK_STATUS_MAP[status] ?? CHECK_STATUS_UNKNOWN
}

// ── Line-item-level status ────────────────────────────────────────────────────

const LINE_ITEM_STATUS_MAP = {
  OK:      { label: 'OK',       icon: '✓', color: 'var(--color-status-pass)', bg: 'var(--color-status-pass-bg)', severity: 'ok'   },
  SHORT:   { label: 'Short',    icon: '↓', color: 'var(--color-status-warn)', bg: 'var(--color-status-warn-bg)', severity: 'warn' },
  LOW:     { label: 'Low',      icon: '↓', color: 'var(--color-status-warn)', bg: 'var(--color-status-warn-bg)', severity: 'warn' },
  MISSING: { label: 'Missing',  icon: '✗', color: 'var(--color-status-fail)', bg: 'var(--color-status-fail-bg)', severity: 'fail' },
  EXPIRED: { label: 'Expired',  icon: '⚠', color: 'var(--color-status-fail)', bg: 'var(--color-status-fail-bg)', severity: 'fail' },
  FAIL:    { label: 'Failed',   icon: '✗', color: 'var(--color-status-fail)', bg: 'var(--color-status-fail-bg)', severity: 'fail' },
  OVERDUE: { label: 'Overdue',  icon: '⚠', color: 'var(--color-status-fail)', bg: 'var(--color-status-fail-bg)', severity: 'fail' },
}

const LINE_ITEM_UNKNOWN = {
  label: 'Not checked', icon: '○', color: 'var(--color-text-muted)', bg: 'var(--color-surface)', severity: 'ok',
}

export function lineItemStatus(status) {
  return LINE_ITEM_STATUS_MAP[status] ?? LINE_ITEM_UNKNOWN
}

// ── Draft item status derivation ──────────────────────────────────────────────

/**
 * Derives the status string from a raw draft line item object.
 *
 * Draft items saved by ItemRow to localStorage do NOT have a `status` field —
 * that only exists on API response objects after submission. This function
 * mirrors server-side _compute_line_item_status so the frontend can derive
 * meaningful status from raw draft fields alone.
 */
export function deriveDraftItemStatus(draftItem) {
  if (!draftItem) return null

  const checkType = draftItem.check_type ?? 'SUPPLY'

  if (checkType === 'FUNCTIONAL') {
    if (draftItem.functional_pass === true)  return 'OK'
    if (draftItem.functional_pass === false) return 'FAIL'
    return null
  }
  if (checkType === 'MEASUREMENT') {
    return draftItem.measurement_value != null ? 'OK' : null
  }
  if (checkType === 'DATE_RECORD') {
    return draftItem.date_value ? 'OK' : null
  }

  // SUPPLY and DOCUMENT — count-based
  const found  = draftItem.quantity_found  ?? 0
  const needed = draftItem.quantity_needed ?? 0
  if (found === 0)    return 'MISSING'
  if (found < needed) return 'SHORT'
  return 'OK'
}

// ── Severity helpers ──────────────────────────────────────────────────────────

export function hasFailItem(lineItems) {
  return lineItems.some(li => {
    const s = li.status ?? deriveDraftItemStatus(li)
    return s ? lineItemStatus(s).severity === 'fail' : false
  })
}

export function hasWarnItem(lineItems) {
  return !hasFailItem(lineItems) &&
    lineItems.some(li => {
      const s = li.status ?? deriveDraftItemStatus(li)
      return s ? lineItemStatus(s).severity === 'warn' : false
    })
}

/**
 * Returns true if the draft has any warn-severity (SHORT) items across
 * all compartments. Used to decide "Reconcile →" vs "Review and Submit →"
 * on Step 2, and to collect the interactive shopping list on Step 4.
 * @param {object} draftCompartments — draft.compartments object
 */
export function draftHasShortItems(draftCompartments) {
  for (const cd of Object.values(draftCompartments ?? {})) {
    for (const li of cd.line_items ?? []) {
      const s = li.status ?? deriveDraftItemStatus(li)
      if (s && lineItemStatus(s).severity === 'warn') return true
    }
  }
  return false
}

/**
 * Returns true if the draft has ANY items needing attention on Step 4 —
 * either warn-severity (SHORT → interactive restock) or fail-severity
 * (FUNCTIONAL FAIL, MISSING → read-only supervisor section).
 *
 * This drives the Step 2 → Step 4 routing decision. If either tier has
 * items, show Reconcile so the responder sees the full picture before
 * submitting. Replacing draftHasShortItems() for routing purposes.
 *
 * @param {object} draftCompartments — draft.compartments object
 */
export function draftNeedsReconcile(draftCompartments) {
  for (const cd of Object.values(draftCompartments ?? {})) {
    for (const li of cd.line_items ?? []) {
      const s = li.status ?? deriveDraftItemStatus(li)
      if (!s) continue
      const sev = lineItemStatus(s).severity
      if (sev === 'warn' || sev === 'fail') return true
    }
  }
  return false
}

export function compartmentStatus(lineItems) {
  if (!lineItems || lineItems.length === 0) return lineItemStatus('OK')
  if (hasFailItem(lineItems)) return checkStatus('FAIL')
  if (hasWarnItem(lineItems)) return checkStatus('NEEDS_RESTOCK')
  return checkStatus('PASS')
}

// ── Reconcile list helpers ────────────────────────────────────────────────────

/**
 * Collects all warn-severity (SHORT) line items across the entire draft.
 * Used by Step 4 Reconcile for the interactive restock list.
 * @param {object} draftCompartments — draft.compartments object
 * @returns {Array<object>}
 */
export function collectShortItems(draftCompartments) {
  const result = []
  for (const cd of Object.values(draftCompartments ?? {})) {
    for (const li of cd.line_items ?? []) {
      const status = li.status ?? deriveDraftItemStatus(li)
      if (!status) continue
      if (lineItemStatus(status).severity === 'warn') {
        result.push({
          item_id:          li.item_id,
          item_name:        li.item_name ?? li.name ?? '',
          check_type:       li.check_type ?? 'SUPPLY',
          quantity_found:   li.quantity_found  ?? 0,
          quantity_needed:  li.quantity_needed ?? 0,
          compartment_id:   li.compartment_id  ?? cd.compartment_id,
          compartment_name: cd.name ?? '',
          notes:            li.notes ?? '',
        })
      }
    }
  }
  return result
}

/**
 * Collects all fail-severity line items across the entire draft.
 * Shown read-only in Reconcile ("needs supervisor attention").
 * Also used by Step 5 to auto-populate the repair notes field.
 * @param {object} draftCompartments — draft.compartments object
 * @returns {Array<object>}
 */
export function collectFailItems(draftCompartments) {
  const result = []
  for (const cd of Object.values(draftCompartments ?? {})) {
    for (const li of cd.line_items ?? []) {
      const status = li.status ?? deriveDraftItemStatus(li)
      if (!status) continue
      if (lineItemStatus(status).severity === 'fail') {
        result.push({
          item_id:          li.item_id,
          item_name:        li.item_name ?? li.name ?? '',
          check_type:       li.check_type ?? 'SUPPLY',
          quantity_found:   li.quantity_found  ?? 0,
          quantity_needed:  li.quantity_needed ?? 0,
          functional_pass:  li.functional_pass ?? null,
          compartment_id:   li.compartment_id  ?? cd.compartment_id,
          compartment_name: cd.name ?? '',
          notes:            li.notes ?? '',
        })
      }
    }
  }
  return result
}

/**
 * Builds a human-readable repair notes string from fail-severity draft items.
 * Used to auto-populate the repair notes field on Step 5.
 *
 * Example output:
 *   "Compartment 2 — Reconcile Trigger:\n
 *    • [TEST] Broken Equipment — Functional check failed\n"
 *
 * @param {object} draftCompartments — draft.compartments object
 * @returns {string} — empty string if no fail items
 */
export function buildAutoRepairNotes(draftCompartments) {
  const failItems = collectFailItems(draftCompartments)
  if (!failItems.length) return ''

  // Group by compartment name for readability
  const byCompartment = {}
  for (const item of failItems) {
    const key = item.compartment_name || 'Unknown compartment'
    if (!byCompartment[key]) byCompartment[key] = []

    const reason = item.check_type === 'FUNCTIONAL'
      ? 'Functional check failed'
      : item.quantity_found === 0
        ? 'Count is zero'
        : 'Check failed'

    byCompartment[key].push(`• ${item.item_name} — ${reason}`)
  }

  return Object.entries(byCompartment)
    .map(([comp, lines]) => `${comp}:\n${lines.join('\n')}`)
    .join('\n\n')
}

// ── Misc helpers ──────────────────────────────────────────────────────────────

export function checkTypeLabel(checkType) {
  const MAP = {
    SUPPLY:      '',
    MEASUREMENT: 'Reading',
    FUNCTIONAL:  'Pass/Fail',
    DATE_RECORD: 'Date',
    DOCUMENT:    'Document',
  }
  return MAP[checkType] ?? checkType
}

export function hapticPattern(status) {
  const s = lineItemStatus(status)
  if (s.severity === 'fail') return [80, 40, 80]
  if (s.severity === 'ok')   return [40]
  return null
}
