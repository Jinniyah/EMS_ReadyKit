/**
 * settings/components/RetiredListSection.jsx
 * RET-F5: Collapsed list of all retired vehicles, locations, and stations.
 * Admin only.
 */
import React, { useState } from 'react'
import { useApi } from '../../../shared/hooks/useApi.js'
import { retirementApi } from '../api/retirementApi.js'
import Spinner from '../../../shared/components/Spinner.jsx'

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

function RetiredTypeList({ station, type, label, getToken }) {
  const [key] = useState(0)
  const { data, isLoading, error } = useApi(
    () => retirementApi.getRetired(type, station.station_id, getToken),
    [station.station_id, key]
  )

  if (isLoading) return <Spinner label={`Loading retired ${label.toLowerCase()}…`} />
  if (error) return <p className="settings-section__empty">Could not load retired {label.toLowerCase()}.</p>
  if (!data || data.length === 0) return <p className="settings-section__empty">No retired {label.toLowerCase()}.</p>

  return (
    <div className="settings-retired-list">
      {data.map(item => (
        <div key={`${item.type}-${item.id}`} className="settings-retired-item">
          <span className="settings-retired-item__name">{item.name}</span>
          <span className="settings-retired-item__meta">
            Retired {formatDate(item.retired_at)}
            {item.retired_by ? ` by ${item.retired_by}` : ''}
            {item.retirement_reason ? ` — ${item.retirement_reason}` : ''}
          </span>
        </div>
      ))}
    </div>
  )
}

export default function RetiredListSection({ station, getToken }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="settings-section">
      <button
        className="settings-section__heading"
        style={{ display: 'flex', justifyContent: 'space-between', width: '100%', background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left', padding: 'var(--space-sm) var(--space-md)' }}
        onClick={() => setOpen(o => !o)}
        type="button"
        aria-expanded={open}
      >
        <span>Retired Items</span>
        <span>{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <>
          <div style={{ padding: 'var(--space-sm) var(--space-md) 0', fontWeight: 700, fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
            Vehicles
          </div>
          <RetiredTypeList station={station} type="vehicles" label="Vehicles" getToken={getToken} />

          <div style={{ padding: 'var(--space-sm) var(--space-md) 0', fontWeight: 700, fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', borderTop: '1px solid var(--color-border)' }}>
            Portable Locations
          </div>
          <RetiredTypeList station={station} type="locations" label="Locations" getToken={getToken} />

          <div style={{ padding: 'var(--space-sm) var(--space-md) 0', fontWeight: 700, fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', borderTop: '1px solid var(--color-border)' }}>
            Stations
          </div>
          <RetiredTypeList station={station} type="stations" label="Stations" getToken={getToken} />
        </>
      )}
    </div>
  )
}
