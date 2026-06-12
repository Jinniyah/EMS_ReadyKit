/**
 * modules/supervisor/components/SupplyLowStockPanel.jsx
 * SR-F5: Expandable panel listing supply room items below par.
 * Red if any are completely out; amber if just below par.
 */
import React, { useState } from 'react'

export default function SupplyLowStockPanel({ alerts, onGoToSupplyRoom }) {
  const [open, setOpen] = useState(false)

  if (!alerts?.length) return null

  const hasOut    = alerts.some(a => a.on_hand === 0)
  const alertClass = hasOut
    ? 'sup-alert sup-alert--supply-out'
    : 'sup-alert sup-alert--supply-low'
  const icon      = hasOut ? '✗ ' : '⚠ '
  const outCount  = alerts.filter(a => a.on_hand === 0).length
  const summary   = hasOut
    ? `${outCount} supply item${outCount !== 1 ? 's' : ''} completely out`
    : `${alerts.length} supply item${alerts.length !== 1 ? 's' : ''} below minimum`

  return (
    <div className="sup-supply-panel">
      <button
        className={alertClass}
        onClick={() => setOpen(v => !v)}
        type="button"
        aria-expanded={open}
      >
        <span>{icon}{summary} — tap to review</span>
        <span className="sup-supply-panel__chevron" aria-hidden="true">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="sup-supply-panel__body" role="region" aria-label="Low supply items">
          {alerts.map(a => {
            const isOut = a.on_hand === 0
            return (
              <div
                key={a.item_name}
                className={`sup-supply-row ${isOut ? 'sup-supply-row--out' : ''}`}
              >
                <span className="sup-supply-row__name">{a.item_name}</span>
                <span className={`sup-supply-row__count ${isOut ? 'sup-supply-row__count--out' : ''}`}>
                  {a.on_hand} / {a.par_min} {a.unit}
                </span>
              </div>
            )
          })}
          {onGoToSupplyRoom && (
            <button
              className="sup-supply-panel__go-btn btn btn--primary"
              onClick={onGoToSupplyRoom}
              type="button"
            >
              → Go to Station Supplies
            </button>
          )}
        </div>
      )}
    </div>
  )
}
