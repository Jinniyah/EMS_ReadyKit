/**
 * modules/supervisor/index.jsx
 * Supervisor Dashboard — F-5F1, F-5F3, F-5F4, F-5F5
 * Session F Block 3: Compliance Calendar (F-5F2) added.
 */

import React, { useState } from 'react'
import { useAuth } from '../../shared/hooks/useAuth.jsx'
import Spinner from '../../shared/components/Spinner.jsx'
import ErrorBoundary from '../../shared/components/ErrorBoundary.jsx'
import ComplianceSummary from './components/ComplianceSummary.jsx'
import VehicleComplianceCard from './components/VehicleComplianceCard.jsx'
import CheckDetailPanel from './components/CheckDetailPanel.jsx'
import ComplianceCalendar from './components/ComplianceCalendar.jsx'
import PortableComplianceCard from './components/PortableComplianceCard.jsx'
import ExpiringItemsPanel from './components/ExpiringItemsPanel.jsx'
import SupplyLowStockPanel from './components/SupplyLowStockPanel.jsx'
import { supervisorApi } from './api/supervisorApi.js'
import { useApi } from '../../shared/hooks/useApi.js'
import './supervisor.css'

const SORT_WEIGHT = { FAIL: 0, UNCHECKED: 1, NEEDS_RESTOCK: 2, PASS: 3, INACTIVE: 4 }

function vehicleWeight(vehicle, checks) {
  if (!vehicle.active) return SORT_WEIGHT.INACTIVE
  if (!checks?.length) return SORT_WEIGHT.UNCHECKED
  return SORT_WEIGHT[checks[0].status] ?? SORT_WEIGHT.PASS
}

export default function SupervisorDashboard({ station, onBack, onNavigateToVehicles, onNavigateToSupplyRoom }) {
  const { getToken } = useAuth()
  const [activeFilter, setActiveFilter]   = useState('all')
  const [selectedCheck, setSelectedCheck] = useState(null) // { check, vehicleId, vehicleNumber }

  const { data, isLoading, error, refetch } = useApi(
    () => supervisorApi.getTodayCompliance(station.station_id, getToken),
    [station.station_id]
  )

  const { data: expiringGroups } = useApi(
    () => supervisorApi.getExpiringSoon(station.station_id, getToken),
    [station.station_id]
  )

  const { data: supplyAlerts } = useApi(
    () => supervisorApi.getSupplyAlerts(station.station_id, getToken),
    [station.station_id]
  )

  const { data: damagedItems } = useApi(
    () => supervisorApi.getDamagedItems(station.station_id, getToken),
    [station.station_id]
  )

  // If a check detail is requested (either from today's cards or from the calendar),
  // push to CheckDetailPanel
  if (selectedCheck) {
    return (
      <ErrorBoundary moduleName="Check Detail">
        <CheckDetailPanel
          checkSummary={selectedCheck.check ?? { check_id: selectedCheck.checkId }}
          vehicleId={selectedCheck.vehicleId}
          vehicleNumber={selectedCheck.vehicleNumber ?? ''}
          onBack={() => setSelectedCheck(null)}
          onNavigateToVehicles={onNavigateToVehicles}
        />
      </ErrorBoundary>
    )
  }

  const vehicles        = data?.vehicles          ?? []
  const byVehicle       = data?.checksByVehicle   ?? {}
  const portables       = data?.portables         ?? []
  const byLocation      = data?.checksByLocation  ?? {}
  const openRepairCount = data?.openRepairCount   ?? 0
  const repairStateByVehicle = data?.repairStateByVehicle ?? {}
  const summary         = data?.summary ?? { total: 0, pass: 0, fail: 0, restock: 0, unchecked: 0 }

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

  const expiryGroups  = expiringGroups ?? []
  const expiryTotal   = expiryGroups.reduce((n, g) => n + g.lots.length, 0)
  const expiryUrgent  = expiryGroups.reduce((n, g) => n + g.lots.filter(l => l.days_until_expiry <= 7).length, 0)

  const supplyLow = supplyAlerts ?? []
  const damaged   = damagedItems ?? []

  const allClear = summary.unresolvedFail === 0 && summary.unchecked === 0 && summary.total > 0 && expiryUrgent === 0 && supplyLow.length === 0 && damaged.length === 0

  const dateLabel = new Date().toLocaleDateString(undefined, {
    weekday: 'long', month: 'long', day: 'numeric',
  })

  // Handler for calendar cell taps: receive a checkId, open the detail panel.
  // We don't know vehicleNumber at this point — CheckDetailPanel will load it.
  function handleCalendarCheckClick(checkId) {
    setSelectedCheck({ checkId, check: null, vehicleId: null, vehicleNumber: null })
  }

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
            {summary.unresolvedFail > 0 && (
              <div className="sup-alert sup-alert--fail" role="alert">
                ✗ {summary.unresolvedFail} {summary.unresolvedFail !== 1 ? 'items' : 'item'} failed today's check
                — tap to review and fix
              </div>
            )}
            {summary.unchecked > 0 && (
              <div className="sup-alert sup-alert--unchecked" role="alert">
                ○ {summary.unchecked} {summary.unchecked !== 1 ? 'items' : 'item'} not yet checked today
                — must be checked before going out
              </div>
            )}
            {openRepairCount > 0 && (
              <button
                className="sup-alert sup-alert--repair"
                role="alert"
                type="button"
                onClick={onNavigateToVehicles}
              >
                🔧 {openRepairCount} problem{openRepairCount !== 1 ? 's' : ''} reported
                — tap to review
              </button>
            )}
            {expiryTotal > 0 && (
              <ExpiringItemsPanel
                groups={expiryGroups}
                totalCount={expiryTotal}
                urgentCount={expiryUrgent}
              />
            )}
            <SupplyLowStockPanel alerts={supplyLow} onGoToSupplyRoom={onNavigateToSupplyRoom} />
            {damaged.length > 0 && (
              <details className="sup-alert sup-alert--damaged">
                <summary>
                  ⚠ {damaged.length} damaged item{damaged.length !== 1 ? 's' : ''} on equipment — tap to see
                </summary>
                <ul className="sup-alert__damaged-list">
                  {damaged.map((d, i) => (
                    <li key={i}>
                      <strong>{d.item_name}</strong>
                      <span className="sup-alert__damaged-location">
                        {d.vehicle_number ?? d.location_label} · {d.compartment_name}
                      </span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
            {allClear && openRepairCount === 0 && expiryTotal === 0 && (
              <div className="sup-alert sup-alert--all-clear">
                ✓ All vehicles and equipment checked — no issues today
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
                      repairState={repairStateByVehicle[vehicle.vehicle_id] ?? null}
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

          {/* ── Portable locations (jump bags, equipment) ────────────── */}
          {portables.length > 0 && (
            <>
              <h3 style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '1rem 0 0.5rem' }}>
                Portable Equipment
              </h3>
              <ul className="sup-dashboard__vehicle-list" aria-label="Portable equipment">
                {portables.map(loc => (
                  <li key={loc.location_id}>
                    <ErrorBoundary moduleName={`Location ${loc.label}`}>
                      <PortableComplianceCard
                        location={loc}
                        checks={byLocation[loc.location_id] ?? []}
                        onSelectCheck={check => setSelectedCheck({
                          check,
                          vehicleId:     null,
                          vehicleNumber: loc.label,
                        })}
                      />
                    </ErrorBoundary>
                  </li>
                ))}
              </ul>
            </>
          )}

          {/* ── Compliance Calendar (F-5F2) ───────────────────────────── */}
          <ErrorBoundary moduleName="Compliance Calendar">
            <ComplianceCalendar
              station={station}
              vehicles={vehicles}
              portables={portables}
              onViewCheck={handleCalendarCheckClick}
            />
          </ErrorBoundary>
        </>
      )}
    </div>
  )
}
