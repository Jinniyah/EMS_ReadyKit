/**
 * shared/utils/lastCheckBanner.js
 *
 * Pure helpers for the F-UX7 last-check banner.
 * No React — importable anywhere.
 *
 * Banner states
 * ─────────────
 *   green  — checked today AND status is PASS
 *   amber  — checked today but FAIL/NEEDS_RESTOCK, OR 1–7 days ago
 *   red    — never checked, or last check was more than 7 days ago
 *   null   — still loading (caller renders a skeleton)
 *
 * These mirror EMS operational expectations:
 *   - Same-day PASS → crew is good to go, low visual noise
 *   - Same-day FAIL → needs attention before departure, amber (not red —
 *     the vehicle was at least checked; supervisor already knows)
 *   - 1–7 days → crew should be aware the check is getting stale
 *   - >7 days / never → urgent, something is wrong
 */

/** @typedef {'green'|'amber'|'red'} BannerColor */

/**
 * Compute banner color from the most-recent check record.
 *
 * @param {object|null} lastCheck  — most recent DailyInventoryCheckRead, or null
 * @param {string}      todayIso  — "YYYY-MM-DD" (local date)
 * @returns {BannerColor}
 */
export function bannerColor(lastCheck, todayIso) {
  if (!lastCheck) return 'red'

  const daysDiff = daysBetween(lastCheck.check_date, todayIso)

  if (daysDiff === 0) {
    // Checked today
    return lastCheck.status === 'PASS' ? 'green' : 'amber'
  }
  if (daysDiff <= 7) return 'amber'
  return 'red'
}

/**
 * Human-readable summary line for the banner body.
 *
 * @param {object|null} lastCheck
 * @param {string}      todayIso
 * @param {string}      performedBy  — from lastCheck.performed_by, passed separately so
 *                                     callers can keep the function pure
 * @returns {string}
 */
export function bannerSummary(lastCheck, todayIso) {
  if (!lastCheck) return 'No check on record for this vehicle.'

  const days = daysBetween(lastCheck.check_date, todayIso)
  const who  = lastCheck.performed_by ? ` by ${lastCheck.performed_by}` : ''

  if (days === 0) {
    const statusLabel = statusText(lastCheck.status)
    return `Checked today${who} — ${statusLabel}`
  }
  if (days === 1) return `Last checked yesterday${who}`
  return `Last checked ${days} days ago${who}`
}

/** Severity label shown in the banner badge. */
export function bannerLabel(lastCheck, todayIso) {
  if (!lastCheck) return 'Never checked'
  const days = daysBetween(lastCheck.check_date, todayIso)
  if (days === 0) return statusText(lastCheck.status)
  if (days === 1) return '1 day ago'
  return `${days} days ago`
}

// ── Internal helpers ──────────────────────────────────────────────────────────

/** Number of calendar days between two YYYY-MM-DD strings. Always >= 0. */
function daysBetween(isoA, isoB) {
  const msPerDay = 86400000
  const a = Date.parse(isoA)
  const b = Date.parse(isoB)
  return Math.max(0, Math.round(Math.abs(b - a) / msPerDay))
}

function statusText(status) {
  switch (status) {
    case 'PASS':          return 'All clear'
    case 'FAIL':          return 'Failed — issues outstanding'
    case 'NEEDS_RESTOCK': return 'Needs restock'
    default:              return status ?? 'Unknown'
  }
}
