/**
 * modules/supervisor/index.jsx
 * Supervisor Dashboard — F-5F1, F-5F3, F-5F4, F-5F5
 */

import React, { useState } from 'react'
import { useAuth } from '../../shared/hooks/useAuth.jsx'
import Spinner from '../../shared/components/Spinner.jsx'
import ErrorBoundary from '../../shared/components/ErrorBoundary.jsx'
import ComplianceSummary from './components/ComplianceSummary.jsx'
import VehicleComplianceCard from './components/VehicleComplianceCard.jsx'
import CheckDetailPanel from './components/CheckDetailPanel.jsx'
import { supervisorApi } from './api/supervisorApi.js'
import { useApi } from '../../shared/hooks/useApi.js'
import './supervisor.css'

const SORT_WEIGHT = { FAIL: 0, UNCHECKED: 1, NEEDS_RESTOCK: 2, PASS: 3, INACTIVE: 4 }

function vehicleWeight(vehicle, checks) {
  if (!vehicle.active) return SORT_WEIGHT.INACTIVE
  if (!checks?.length) return SORT_WEIGHT.UNCHECKED
  return SORT_WEIGHT[checks[0].status] ?? SORT_WEIGHT.PASS
}

export default function SupervisorDashboard({ station, onBack }) {
  const { getToken } = useAuth()
  const [activeFilter, setActiveFilter]   = useState('all')
  const [selectedCheck, setSelectedCheck] = useState(null) // { check, vehicleId, vehicleNumber }

  const { data, isLoading, error, refetch } = useApi(
    () => supervisorApi.getTodayCompliance(station.station_id, getToken),
    [station.station_id]
  )

  if (selectedCheck) {
    return (
      <ErrorBoundary moduleName="Check Detail">
        <CheckDetailPanel
          checkSummary={selectedCheck.check}
          vehicleId={selectedCheck.vehicleId}
          vehicleNumber={selectedCheck.vehicleNumber}
          onBack={() => setSelectedCheck(null)}
        />
      </ErrorBoundary>
    )
  }

  const vehicles  = data?.vehicles ?? []
  const byVehicle = data?.checksByVehicle ?? {}
  const summary   = data?.summary ?? { total: 0, pass: 0, fail: 0, restock: 0, unchecked: 0 }

  const filteredVehicles = vehicles.filter(v => {
    if (activeFilter === 'all') return true
    if (!v.active) return false
    const checks = byVehicle[v.vehicle_id] ?? []
    const latest = checks[0]
    if (activeFilter === 'unchecked') return checks.length === 0
    if (activeFilter === 'pass')      return latest?.status === 'PASS'
    if (activeFilter === 'fail')      return latest?.status === 'FAIL'
    if (activeFilter === 'restock')   return latest?.status === 'NEEDS_RESTOCK'
    return true
  })

  const sortedVehicles = [...filteredVehicles].sort((a, b) =>
    vehicleWeight(a, byVehicle[a.vehicle_id]) -
    vehicleWeight(b, byVehicle[b.vehicle_id])
  )

  const allClear = summary.fail === 0 && summary.unchecked === 0 && summary.total > 0

  const dateLabel = new Date().toLocaleDateString(undefined, {
    weekday: 'long', month: 'long', day: 'numeric',
  })

  return (
    <div className="sup-dashboard">

      <div className="sup-dashboard__header">
        <button className="btn-text sup-dashboard__back" onClick={onBack} type="button">
          ← Back
        </button>
        <div className="sup-dashboard__title-block">
          <h1 className="sup-dashboard__title">Compliance Dashboard</h1>
          <p className="sup-dashboard__subtitle">{station.name} · {dateLabel}</p>
        </div>
        <button
          className="btn btn--secondary btn--sm"
          onClick={refetch}
          type="button"
          aria-label="Refresh"
        >
          ↻
        </button>
      </div>

      {isLoading ? (
        <Spinner label="Loading compliance data…" />
      ) : error ? (
        <div className="sup-dashboard__error" role="alert">
          <p>⚠ Could not load compliance data.</p>
          <button className="btn btn--secondary" onClick={refetch} type="button">Try again</button>
        </div>
      ) : (
        <>
          <ErrorBoundary moduleName="Compliance Summary">
            <ComplianceSummary
              summary={summary}
              activeFilter={activeFilter}
              onFilterChange={setActiveFilter}
            />
          </ErrorBoundary>

          <div className="sup-dashboard__alerts">
            {summary.fail > 0 && (
              <div className="sup-alert sup-alert--fail" role="alert">
                ✗ {summary.fail} vehicle{summary.fail !== 1 ? 's' : ''} failed today's check
                — tap to review and fix
              </div>
            )}
            {summary.unchecked > 0 && (
              <div className="sup-alert sup-alert--unchecked" role="alert">
                ○ {summary.unchecked} vehicle{summary.unchecked !== 1 ? 's' : ''} not yet checked today
                — must be checked before going out
              </div>
            )}
            {allClear && (
              <div className="sup-alert sup-alert--all-clear">
                ✓ All vehicles checked — no issues today
              </div>
            )}
          </div>

          {sortedVehicles.length === 0 ? (
            <div className="sup-dashboard__empty">No vehicles match this filter.</div>
          ) : (
            <ul className="sup-dashboard__vehicle-list" aria-label="Vehicles">
              {sortedVehicles.map(vehicle => (
                <li key={vehicle.vehicle_id}>
                  <ErrorBoundary moduleName={`Vehicle ${vehicle.vehicle_number}`}>
                    <VehicleComplianceCard
                      vehicle={vehicle}
                      checks={byVehicle[vehicle.vehicle_id] ?? []}
                      onSelectCheck={check => setSelectedCheck({
                        check,
                        vehicleId: vehicle.vehicle_id,
                        vehicleNumber: vehicle.vehicle_number,
                      })}
                    />
                  </ErrorBoundary>
                </li>
              ))}
            </ul>
          )}

          <div className="sup-dashboard__placeholder">
            <span aria-hidden="true">📅</span>
            <p>Compliance Calendar — coming once the date-range endpoint (B-E3) is built</p>
          </div>
        </>
      )}
    </div>
  )
}
