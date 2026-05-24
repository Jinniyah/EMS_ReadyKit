/**
 * components/VehicleComplianceCard.jsx
 *
 * Visual hierarchy for check status in the "Earlier today" list:
 *   UNRESOLVED FAIL = red background, bold "✗ Not Fixed" tag — can't miss it
 *   RESOLVED (fixed by supervisor) = green "✓ Fixed" tag
 *   ACKNOWLEDGED (note only) = muted "Noted" tag
 *   PASS = no tag needed
 */

import React from 'react'

const STATUS_META = {
  PASS:          { label: 'Pass',         icon: '✓', className: 'status--pass' },
  NEEDS_RESTOCK: { label: 'Needs Restock',icon: '⚠', className: 'status--warn' },
  FAIL:          { label: 'FAIL',         icon: '✗', className: 'status--fail' },
}

function formatTime(isoString) {
  if (!isoString) return ''
  return new Date(isoString).toLocaleTimeString(undefined, {
    hour: 'numeric', minute: '2-digit',
  })
}

/**
 * Determine the resolution state of a check.
 * 'fixed'    — supervisor used "I Fixed This" (corrective_action starts with "Items fixed by supervisor:")
 * 'noted'    — supervisor added a note only
 * 'unresolved' — not yet acknowledged
 */
function getResolutionState(check) {
  if (!check.reviewed_at) return 'unresolved'
  if (check.corrective_action?.startsWith('Items fixed by supervisor:')) return 'fixed'
  return 'noted'
}

export default function VehicleComplianceCard({ vehicle, checks, onSelectCheck }) {
  const latestCheck = checks?.[0] ?? null
  const statusMeta  = latestCheck ? (STATUS_META[latestCheck.status] ?? STATUS_META.PASS) : null

  const latestResolution  = latestCheck ? getResolutionState(latestCheck) : null
  const latestNeedsAction = latestCheck &&
    latestCheck.status !== 'PASS' &&
    latestResolution === 'unresolved'

  // Older checks that are FAIL/RESTOCK and still unresolved
  const unresolvedOlderChecks = checks.slice(1).filter(
    c => c.status !== 'PASS' && getResolutionState(c) === 'unresolved'
  )

  const cardClass = !vehicle.active          ? 'vc-card--inactive'
    : !latestCheck                           ? 'vc-card--unchecked'
    : latestCheck.status === 'FAIL'          ? 'vc-card--fail'
    : latestCheck.status === 'NEEDS_RESTOCK' ? 'vc-card--needs-restock'
    : unresolvedOlderChecks.length > 0       ? 'vc-card--has-unresolved'
    : 'vc-card--pass'

  return (
    <div className={`vc-card ${cardClass}`}>

      {/* Vehicle identity */}
      <div className="vc-card__identity">
        <span className="vc-card__icon" aria-hidden="true">
          {!vehicle.active ? '🚫' : '🚑'}
        </span>
        <div style={{ flex: 1 }}>
          <div className="vc-card__number">{vehicle.vehicle_number}</div>
          <div className="vc-card__type">{vehicle.vehicle_type}</div>
        </div>
        {latestNeedsAction && (
          <span className="vc-card__needs-ack">⚠ Needs Action</span>
        )}
      </div>

      {/* Latest check status */}
      {!vehicle.active ? (
        <div className="vc-card__status">
          <span className="vc-badge vc-badge--inactive">Out of Service</span>
          {vehicle.inactive_reason && (
            <span className="vc-card__inactive-reason">{vehicle.inactive_reason}</span>
          )}
        </div>
      ) : latestCheck ? (
        <button
          className="vc-card__check-btn"
          onClick={() => onSelectCheck(latestCheck)}
          type="button"
          aria-label={`View check for ${vehicle.vehicle_number} — ${statusMeta.label}`}
        >
          <span className={`vc-badge ${statusMeta.className}`}>
            {statusMeta.icon} {statusMeta.label}
          </span>
          <span className="vc-card__time">{formatTime(latestCheck.timestamp)}</span>
          <ResolutionTag resolution={latestResolution} status={latestCheck.status} />
          <span className={`vc-card__view-label ${latestNeedsAction ? '' : 'vc-card__view-label--muted'}`}>
            {latestNeedsAction ? 'Tap to fix →' : 'Tap to view →'}
          </span>
        </button>
      ) : (
        <div className="vc-card__unchecked-action">
          <span className="vc-card__unchecked-msg">○ Check not completed today</span>
          <span className="vc-card__unchecked-hint">Vehicle must be checked before going out</span>
        </div>
      )}

      {/* Unresolved older checks warning strip */}
      {unresolvedOlderChecks.length > 0 && (
        <div className="vc-card__unresolved-strip">
          <span className="vc-card__unresolved-icon">⚠</span>
          <span className="vc-card__unresolved-msg">
            {unresolvedOlderChecks.length} earlier{' '}
            {unresolvedOlderChecks.length === 1 ? 'check has' : 'checks have'} unresolved issues
          </span>
        </div>
      )}

      {/* Earlier checks today */}
      {checks.length > 1 && (
        <div className="vc-card__multi">
          <div className="vc-card__multi-label">Earlier today</div>
          {checks.slice(1).map(c => {
            const m          = STATUS_META[c.status] ?? STATUS_META.PASS
            const resolution = getResolutionState(c)
            return (
              <button
                key={c.check_id}
                className={`vc-card__multi-item ${resolution === 'unresolved' && c.status !== 'PASS' ? 'vc-card__multi-item--unresolved' : ''}`}
                onClick={() => onSelectCheck(c)}
                type="button"
              >
                <span className={`vc-badge vc-badge--sm ${m.className}`}>
                  {m.icon} {m.label}
                </span>
                <span className="vc-card__time">{formatTime(c.timestamp)}</span>
                <ResolutionTag resolution={resolution} status={c.status} />
                <span className="vc-card__chevron" aria-hidden="true">›</span>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

/**
 * ResolutionTag — shows the action state of a non-PASS check.
 * Fixed (green) / Noted (muted) / Not Fixed (red, bold) / nothing for PASS
 */
function ResolutionTag({ resolution, status }) {
  if (status === 'PASS') return null

  if (resolution === 'fixed') {
    return <span className="resolution-tag resolution-tag--fixed">✓ Fixed</span>
  }
  if (resolution === 'noted') {
    return <span className="resolution-tag resolution-tag--noted">✎ Noted</span>
  }
  // Unresolved FAIL/RESTOCK — make it impossible to miss
  return <span className="resolution-tag resolution-tag--unresolved">✗ Not Fixed</span>
}
