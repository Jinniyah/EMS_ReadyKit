/**
 * modules/vehicles/index.jsx
 * Vehicle & Equipment Status screen.
 *
 * VE-F1: renamed from "Vehicle Status" to "Vehicle & Equipment Status"
 * F-5E1: Repair request form with severity selector and URGENT banner
 * F-5E2: Mark vehicle inactive toggle (Supervisor+)
 * F-5E3: Repair request status tracking display
 *
 * Session AD (BUG-AD1): Retired vehicles must never appear here. "active"
 * and "retired_at" are independent fields — retiring a vehicle sets
 * active=false as a side effect, but that's not the same thing as a
 * temporary out-of-service vehicle. This screen excludes anything with
 * retired_at set so it can't be reported on or returned to service from
 * here.
 */

import React, { useState } from 'react'
import { useAuth } from '../../shared/hooks/useAuth.jsx'
import { useApi } from '../../shared/hooks/useApi.js'
import Spinner from '../../shared/components/Spinner.jsx'
import ErrorBoundary from '../../shared/components/ErrorBoundary.jsx'
import VehicleCard from './components/VehicleCard.jsx'
import { vehicleApi } from './api/vehicleApi.js'
import './vehicles.css'

export default function VehicleStatusScreen({ station, onBack }) {
  const { getToken } = useAuth()

  const {
    data: vehicles,
    isLoading,
    error,
    refetch,
  } = useApi(
    () => vehicleApi.getStationVehicles(station.station_id, getToken),
    [station.station_id]
  )

  // Patch updated vehicles into local state for instant UI feedback
  // without requiring a full refetch on every toggle.
  const [localOverrides, setLocalOverrides] = useState({})

  function handleVehicleUpdated(updated) {
    setLocalOverrides(prev => ({ ...prev, [updated.vehicle_id]: updated }))
  }

  const displayVehicles = (vehicles ?? [])
    .map(v => localOverrides[v.vehicle_id] ?? v)
    .filter(v => !v.retired_at)

  const activeCount   = displayVehicles.filter(v => v.active).length
  const inactiveCount = displayVehicles.filter(v => !v.active).length

  return (
    <div className="ve-screen">
      <div className="ve-screen__header">
        <button
          className="btn-text ve-screen__back"
          onClick={onBack}
          type="button"
          aria-label="Back to home"
        >
          ← Back
        </button>
        <div className="ve-screen__title-block">
          <h1 className="ve-screen__title">Vehicle &amp; Equipment Status</h1>
          <p className="ve-screen__subtitle">{station.name}</p>
        </div>
      </div>

      {displayVehicles.length > 0 && (
        <div className="ve-screen__summary">
          <span className="ve-summary__item ve-summary__item--active">
            {activeCount} in service
          </span>
          {inactiveCount > 0 && (
            <span className="ve-summary__item ve-summary__item--inactive">
              {inactiveCount} out of service
            </span>
          )}
        </div>
      )}

      {isLoading ? (
        <Spinner label="Loading vehicles…" />
      ) : error ? (
        <div className="ve-screen__error" role="alert">
          <div className="error-card">
            <span className="error-card__icon" aria-hidden="true">⚠️</span>
            <p className="error-card__title">Could not load vehicles</p>
            <p className="error-card__detail">{error.message}</p>
            <button className="btn btn--ghost" onClick={refetch} type="button">
              Try again
            </button>
          </div>
        </div>
      ) : displayVehicles.length === 0 ? (
        <div className="ve-screen__empty">
          No vehicles found at this station.
        </div>
      ) : (
        <ul className="ve-screen__vehicle-list" aria-label="Vehicles">
          {displayVehicles.map(vehicle => (
            <li key={vehicle.vehicle_id}>
              <ErrorBoundary moduleName={`Vehicle ${vehicle.vehicle_number}`}>
                <VehicleCard
                  vehicle={vehicle}
                  onVehicleUpdated={handleVehicleUpdated}
                />
              </ErrorBoundary>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
