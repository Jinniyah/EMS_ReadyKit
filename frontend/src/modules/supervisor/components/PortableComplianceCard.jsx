/**
 * components/PortableComplianceCard.jsx
 *
 * Compliance card for portable locations (Jump Bags, Equipment) —
 * parallel to VehicleComplianceCard but for non-vehicle checkable items.
 *
 * Shows today's check status, resolution state, and a tap-to-review affordance.
 * Styled with the same vc-card CSS classes so it blends seamlessly with the
 * vehicle card list.
 */

import React from 'react'

const STATUS_META = {
  PASS:          { label: 'Pass',         icon: '✓', className: 'status--pass' },
  NEEDS_RESTOCK: { label: 'Needs Restock',icon: '⚠', className: 'status--warn' },
  FAIL:          { label: 'FAIL',         icon: '✗', className: 'status--fail' },
}

const LOCATION_ICON = {
  JUMP_BAG:  '🎒',
  EQUIPMENT: '🔧',
}

function formatTime(isoString) {
  if (!isoString) return ''
  return new Date(isoString).toLocaleTimeString(undefined, {
    hour: 'numeric', minute: '2-digit',
  })
}

function getResolutionState(check) {
  if (!check.reviewed_at) return 'unresolved'
  if (check.corrective_action?.startsWith('Items fixed by supervisor:')) return 'fixed'
  return 'noted'
}

function ResolutionTag({ resolution, status }) {
  if (status === 'PASS') return null
  if (resolution === 'fixed') return <span className="resolution-tag resolution-tag--fixed">✓ Fixed</span>
  if (resolution === 'noted') return <span className="resolution-tag resolution-tag--noted">✎ Noted</span>
  return <span className="resolution-tag resolution-tag--unresolved">✗ Not Fixed</span>
}

export default function PortableComplianceCard({ location, checks, onSelectCheck }) {
  const latestCheck = checks?.[0] ?? null
  const statusMeta  = latestCheck ? (STATUS_META[latestCheck.status] ?? STATUS_META.PASS) : null

  const latestResolution  = latestCheck ? getResolutionState(latestCheck) : null
  const latestNeedsAction = latestCheck &&
    latestCheck.status !== 'PASS' &&
    latestResolution === 'unresolved'

  const cardClass = !latestCheck
    ? 'vc-card--unchecked'
    : latestCheck.status === 'FAIL'          ? 'vc-card--fail'
    : latestCheck.status === 'NEEDS_RESTOCK' ? 'vc-card--needs-restock'
    : 'vc-card--pass'

  const icon = LOCATION_ICON[location.location_type] ?? '📦'
  const typeLabel = location.location_type === 'JUMP_BAG' ? 'Jump Bag' : 'Equipment'

  return (
    <div className={`vc-card ${cardClass}`}>

      {/* Location identity */}
      <div className="vc-card__identity">
        <span className="vc-card__icon" aria-hidden="true">{icon}</span>
        <div style={{ flex: 1 }}>
          <div className="vc-card__number">{location.label}</div>
          <div className="vc-card__type">{typeLabel}</div>
        </div>
        {latestNeedsAction && (
          <span className="vc-card__needs-ack">⚠ Needs Action</span>
        )}
      </div>

      {/* Latest check status */}
      {latestCheck ? (
        <button
          className="vc-card__check-btn"
          onClick={() => onSelectCheck(latestCheck)}
          type="button"
          aria-label={`View check for ${location.label} — ${statusMeta.label}`}
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
          <span className="vc-card__unchecked-hint">Must be checked before going out</span>
        </div>
      )}
    </div>
  )
}
