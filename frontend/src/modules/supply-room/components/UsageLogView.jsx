/**
 * UsageLogView.jsx
 * Station Supplies → Usage Log history.
 * Shows usage events logged via After-Call Reset, most recent first.
 */
import React from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import { usageApi } from '../../usage-log/api/usageApi.js'
import Spinner from '../../../shared/components/Spinner.jsx'
import '../../usage-log/usage-log.css'

function formatDate(isoString) {
  if (!isoString) return ''
  const d = new Date(isoString)
  return d.toLocaleDateString('en-US', {
    month: 'short', day: 'numeric',
  }) + ' · ' + d.toLocaleTimeString('en-US', {
    hour: 'numeric', minute: '2-digit',
  })
}

export default function UsageLogView({ stationId }) {
  const { getToken } = useAuth()

  const { data: events, isLoading, error, refetch } = useApi(
    () => usageApi.getHistory(stationId, getToken),
    [stationId]
  )

  if (isLoading) return <Spinner label="Loading usage log…" />

  if (error) {
    return (
      <div className="sr-error" role="alert">
        <strong>Could not load usage log</strong>
        <p style={{ margin: '4px 0 0' }}>{error.message}</p>
        <button className="btn btn--secondary" onClick={refetch} type="button" style={{ marginTop: '8px' }}>
          Try again
        </button>
      </div>
    )
  }

  if (!events?.length) {
    return (
      <div className="ulh">
        <p className="ulh__empty">
          No usage has been logged yet.{'\n'}
          Use "Log Items Used" from the home screen after a call.
        </p>
      </div>
    )
  }

  return (
    <div className="ulh">
      {events.map(evt => (
        <div key={evt.event_id} className="ulh__row">
          <div className="ulh__row-header">
            <div>
              <div className="ulh__date">{formatDate(evt.timestamp)}</div>
              <div className="ulh__by">{evt.performed_by}</div>
            </div>
            {evt.vehicle_number && (
              <div className="ulh__vehicle">{evt.vehicle_number}</div>
            )}
          </div>
          <div className="ulh__items">
            {evt.items.map((item, i) => (
              <span key={item.item_id}>
                {item.item_name} ×{item.quantity_used}
                {i < evt.items.length - 1 ? ', ' : ''}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
