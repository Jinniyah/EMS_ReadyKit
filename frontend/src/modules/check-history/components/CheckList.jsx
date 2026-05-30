/**
 * components/CheckList.jsx
 * Reusable check list — used by both My Checks (Responder) and
 * the Supervisor history view. Tapping a row opens CheckDetail.
 */

import React from 'react'

const STATUS_META = {
  PASS:          { label: 'Pass',          icon: '✓', className: 'check-status--pass' },
  NEEDS_RESTOCK: { label: 'Needs Restock', icon: '⚠', className: 'check-status--warn' },
  FAIL:          { label: 'Fail',          icon: '✗', className: 'check-status--fail' },
}

function formatTime(isoString) {
  if (!isoString) return ''
  // Ensure the string is treated as UTC. The backend always emits 'Z'-suffixed
  // strings, but guard against naive strings from old records or caching.
  const normalized = isoString.endsWith('Z') || isoString.includes('+') ? isoString : isoString + 'Z'
  return new Date(normalized).toLocaleTimeString(undefined, {
    hour: 'numeric', minute: '2-digit',
  })
}

function groupByDate(checks) {
  const groups = {}
  for (const check of checks) {
    const date = check.check_date
    if (!groups[date]) groups[date] = []
    groups[date].push(check)
  }
  // Return sorted most-recent-first
  return Object.entries(groups).sort((a, b) => b[0].localeCompare(a[0]))
}

function formatDateHeading(dateStr) {
  const d = new Date(dateStr + 'T12:00:00')
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(today.getDate() - 1)

  if (d.toDateString() === today.toDateString()) return 'Today'
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday'
  return d.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })
}

export default function CheckList({ checks, onSelectCheck, showPerformedBy = false }) {
  if (!checks || checks.length === 0) {
    return (
      <div className="check-list__empty">
        <span aria-hidden="true">📋</span>
        <p>No checks found.</p>
      </div>
    )
  }

  const groups = groupByDate(checks)

  return (
    <div className="check-list">
      {groups.map(([date, dateChecks]) => (
        <div key={date} className="check-list__group">
          <h3 className="check-list__date-heading">{formatDateHeading(date)}</h3>
          <ul className="check-list__items">
            {dateChecks.map(check => {
              const meta = STATUS_META[check.status] ?? STATUS_META.PASS
              return (
                <li key={check.check_id}>
                  <button
                    className="check-list__row"
                    onClick={() => onSelectCheck(check)}
                    type="button"
                  >
                    <div className="check-list__row-left">
                      <span className={`check-status check-status--sm ${meta.className}`}>
                        {meta.icon}
                      </span>
                      <div className="check-list__row-info">
                        <span className="check-list__row-title">
                          {showPerformedBy ? check.performed_by : formatTime(check.timestamp)}
                        </span>
                        <span className="check-list__row-sub">
                          {showPerformedBy
                            ? formatTime(check.timestamp)
                            : `${check.line_items?.length ?? 0} items`}
                        </span>
                      </div>
                    </div>
                    <div className="check-list__row-right">
                      <span className={`check-status check-status--label ${meta.className}`}>
                        {meta.label}
                      </span>
                      <span className="check-list__chevron" aria-hidden="true">›</span>
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </div>
  )
}
