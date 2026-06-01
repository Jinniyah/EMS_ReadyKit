/**
 * shared/components/LastCheckBanner.jsx  (F-UX7)
 *
 * Inline banner shown on a selected vehicle card in Step 1 of the check wizard.
 * Communicates the last check's recency and status at a glance before the
 * crew commits to starting a check.
 *
 * Props
 * ─────
 * vehicleId  {number|null}   Vehicle to look up. Null = render nothing.
 * todayIso   {string}        "YYYY-MM-DD" local today — passed in so callers
 *                            control the date rather than the component.
 * getToken   {function}      Auth token getter.
 *
 * States
 * ──────
 * Loading   → skeleton shimmer (one line, same height as the banner)
 * green     → "All clear" (checked today, PASS) — low noise, subtle green tint
 * amber     → "Needs attention" (today with issues, or 1–7 days ago) — amber
 * red       → "Not checked recently" (>7 days or never) — strong red, impossible to miss
 *
 * UX rationale (tired crew / 68yo iPhone user):
 * - Banner is 100% passive — no buttons, no actions required
 * - Color carries the full signal; text adds detail for those who look
 * - One tap target: the vehicle card itself, not this banner
 * - Font is large enough to read in a dark ambulance bay
 */

import React from 'react'
import { useApi } from '../hooks/useApi.js'
import { checkApi } from '../../modules/check-wizard/api/checkApi.js'
import { bannerColor, bannerSummary, bannerLabel } from '../utils/lastCheckBanner.js'
import './LastCheckBanner.css'

export default function LastCheckBanner({ vehicleId, locationId, todayIso, getToken }) {
  const { data: checks, isLoading } = useApi(
    () => {
      if (vehicleId)  return checkApi.getVehicleChecks(vehicleId, getToken)
      if (locationId) return checkApi.getLocationChecks(locationId, getToken)
      return Promise.resolve(null)
    },
    [vehicleId, locationId]
  )

  if (!vehicleId && !locationId) return null

  if (isLoading) {
    return <div className="lcb lcb--loading" aria-busy="true" aria-label="Loading last check…" />
  }

  // Most recent non-deleted check (API returns newest-first)
  const lastCheck = checks?.find(c => !c.deleted_at) ?? null
  const color     = bannerColor(lastCheck, todayIso)
  const summary   = bannerSummary(lastCheck, todayIso)
  const label     = bannerLabel(lastCheck, todayIso)

  const icons = { green: '✓', amber: '!', red: '⚠' }
  const ariaLabel = `Last check: ${summary}`

  return (
    <div
      className={`lcb lcb--${color}`}
      role="status"
      aria-label={ariaLabel}
      aria-live="polite"
    >
      <span className="lcb__icon" aria-hidden="true">{icons[color]}</span>
      <div className="lcb__body">
        <span className="lcb__label">{label}</span>
        <span className="lcb__summary">{summary}</span>
      </div>
    </div>
  )
}
