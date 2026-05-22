/**
 * shared/utils/dateHelpers.js
 * Date formatting and ISO string helpers.
 *
 * All dates in the API are ISO 8601 strings (YYYY-MM-DD or full datetime).
 * These helpers format them for human display without importing a date library.
 */

const DATE_FORMATTER = new Intl.DateTimeFormat('en-US', {
  weekday: 'long',
  year:    'numeric',
  month:   'long',
  day:     'numeric',
})

const SHORT_DATE_FORMATTER = new Intl.DateTimeFormat('en-US', {
  year:  'numeric',
  month: 'short',
  day:   'numeric',
})

const TIME_FORMATTER = new Intl.DateTimeFormat('en-US', {
  hour:   'numeric',
  minute: '2-digit',
  hour12: true,
})

const SHORT_DATETIME_FORMATTER = new Intl.DateTimeFormat('en-US', {
  month:  'short',
  day:    'numeric',
  hour:   'numeric',
  minute: '2-digit',
  hour12: true,
})

/**
 * "Tuesday, May 13, 2026" — used on Step 1 check date display.
 * @param {string} isoDate — YYYY-MM-DD
 */
export function formatCheckDate(isoDate) {
  if (!isoDate) return ''
  const [y, m, d] = isoDate.split('-').map(Number)
  return DATE_FORMATTER.format(new Date(y, m - 1, d))
}

/**
 * "May 13, 2026" — used for expiry dates and lot dates.
 * @param {string} isoDate — YYYY-MM-DD
 */
export function formatShortDate(isoDate) {
  if (!isoDate) return ''
  const [y, m, d] = isoDate.split('-').map(Number)
  return SHORT_DATE_FORMATTER.format(new Date(y, m - 1, d))
}

/**
 * "May 22 at 2:32 PM" — used in the multi-draft picker to distinguish
 * multiple in-progress checks for the same vehicle on the same day.
 * @param {string | Date} datetime
 */
export function formatShortDatetime(datetime) {
  if (!datetime) return ''
  return SHORT_DATETIME_FORMATTER.format(new Date(datetime))
}

/**
 * "05:58 AM" — used on submitted confirmation screen.
 * @param {string | Date} datetime
 */
export function formatTime(datetime) {
  if (!datetime) return ''
  return TIME_FORMATTER.format(new Date(datetime))
}

/**
 * "Saved today at 05:48 AM" — used on draft resume banner.
 * @param {Date | string} savedAt
 */
export function formatSavedAt(savedAt) {
  if (!savedAt) return ''
  const d = typeof savedAt === 'string' ? new Date(savedAt) : savedAt
  const now = new Date()
  const isToday =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth()   === now.getMonth() &&
    d.getDate()    === now.getDate()
  const timeStr = TIME_FORMATTER.format(d)
  return isToday ? `Saved today at ${timeStr}` : `Saved ${SHORT_DATE_FORMATTER.format(d)} at ${timeStr}`
}

/**
 * Returns today's date as a YYYY-MM-DD string in local time.
 */
export function todayIso() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/**
 * Returns YYYY-MM-DD for a date that is `offsetDays` away from today.
 * @param {number} offsetDays
 */
export function relativeIso(offsetDays) {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/**
 * Returns number of days between two YYYY-MM-DD strings.
 * Positive if dateB is after dateA.
 */
export function daysBetween(dateA, dateB) {
  const [ay, am, ad] = dateA.split('-').map(Number)
  const [by, bm, bd] = dateB.split('-').map(Number)
  const a = new Date(ay, am - 1, ad)
  const b = new Date(by, bm - 1, bd)
  return Math.round((b - a) / (1000 * 60 * 60 * 24))
}

/**
 * Returns true if isoDate is in the past (before today).
 * @param {string} isoDate — YYYY-MM-DD
 */
export function isExpired(isoDate) {
  if (!isoDate) return false
  return daysBetween(isoDate, todayIso()) > 0
}

/**
 * Clamps a YYYY-MM-DD string to the allowed check date range.
 * @param {string} isoDate
 * @param {number} maxDaysBack
 */
export function clampCheckDate(isoDate, maxDaysBack = 7) {
  const today    = todayIso()
  const earliest = relativeIso(-maxDaysBack)
  if (isoDate > today)    return today
  if (isoDate < earliest) return earliest
  return isoDate
}
