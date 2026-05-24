/**
 * components/ComplianceSummary.jsx
 * Filter tiles — shown below the alert banners as a drill-down tool.
 * Urgency colors only apply when count > 0.
 */

import React from 'react'

const TILES = [
  { key: 'all',       label: 'All',         icon: '📋', className: 'tile--all' },
  { key: 'fail',      label: 'Failed',      icon: '✗',  className: 'tile--fail' },
  { key: 'restock',   label: 'Restock',     icon: '⚠',  className: 'tile--warn' },
  { key: 'unchecked', label: 'Not Checked', icon: '○',  className: 'tile--unchecked' },
  { key: 'pass',      label: 'Passed',      icon: '✓',  className: 'tile--pass' },
]

export default function ComplianceSummary({ summary, activeFilter, onFilterChange }) {
  const counts = {
    all:       summary.total,
    fail:      summary.fail,
    restock:   summary.restock,
    unchecked: summary.unchecked,
    pass:      summary.pass,
  }

  return (
    <div className="compliance-summary" role="group" aria-label="Filter by status">
      {TILES.map(tile => {
        const count   = counts[tile.key]
        const isEmpty = count === 0 && tile.key !== 'all'
        return (
          <button
            key={tile.key}
            className={`compliance-tile ${tile.className} ${isEmpty ? 'compliance-tile--empty' : ''} ${activeFilter === tile.key ? 'compliance-tile--active' : ''}`}
            onClick={() => onFilterChange(tile.key)}
            type="button"
            aria-pressed={activeFilter === tile.key}
          >
            <span className="compliance-tile__icon" aria-hidden="true">{tile.icon}</span>
            <span className="compliance-tile__count">{count}</span>
            <span className="compliance-tile__label">{tile.label}</span>
          </button>
        )
      })}
    </div>
  )
}
