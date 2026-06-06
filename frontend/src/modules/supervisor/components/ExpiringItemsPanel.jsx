/**
 * modules/supervisor/components/ExpiringItemsPanel.jsx
 * SUP-F3: Expandable panel listing stock lots expiring within N days.
 * Shown as an inline accordion on the compliance dashboard.
 */
import React, { useState } from 'react'

function formatDate(isoDate) {
  if (!isoDate) return '—'
  return new Date(isoDate + 'T12:00:00').toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

export default function ExpiringItemsPanel({ groups, totalCount, urgentCount }) {
  const [open, setOpen] = useState(false)

  if (!groups?.length) return null

  const isUrgent = urgentCount > 0
  const alertClass = isUrgent ? 'sup-alert sup-alert--expiry-urgent' : 'sup-alert sup-alert--expiry-warn'

  return (
    <div className="sup-expiry-panel">
      <button
        className={alertClass}
        onClick={() => setOpen(v => !v)}
        type="button"
        aria-expanded={open}
      >
        <span>
          {isUrgent ? '⚠ ' : '○ '}
          {urgentCount > 0
            ? `${urgentCount} item${urgentCount !== 1 ? 's' : ''} expiring within 7 days`
            : `${totalCount} item${totalCount !== 1 ? 's' : ''} expiring within 30 days`}
        </span>
        <span className="sup-expiry-panel__chevron" aria-hidden="true">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="sup-expiry-panel__body" role="region" aria-label="Expiring items">
          {groups.map(group => (
            <div key={group.location_id} className="sup-expiry-group">
              <div className="sup-expiry-group__name">
                {group.vehicle_number ? `Unit ${group.vehicle_number}` : group.location_label}
              </div>
              {group.lots.map(lot => {
                const urgent = lot.days_until_expiry <= 7
                return (
                  <div
                    key={lot.lot_id}
                    className={`sup-expiry-row ${urgent ? 'sup-expiry-row--urgent' : ''}`}
                  >
                    <div className="sup-expiry-row__name">{lot.item_name}</div>
                    <div className="sup-expiry-row__detail">
                      {lot.lot_number && <span>Lot {lot.lot_number} · </span>}
                      <span>Exp {formatDate(lot.expiration_date)}</span>
                      <span className={`sup-expiry-row__days ${urgent ? 'sup-expiry-row__days--urgent' : ''}`}>
                        {' '}({lot.days_until_expiry === 0 ? 'today' : `${lot.days_until_expiry} day${lot.days_until_expiry !== 1 ? 's' : ''}`})
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
