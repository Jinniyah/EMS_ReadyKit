/**
 * modules/check-wizard/components/Step1Vehicle.jsx
 * Step 1: Vehicle selection + date + second crew.
 *
 * Station is pre-selected from the home screen — this step only shows
 * the vehicles at that station. The station context band is shown at top
 * as a visual reminder of which station we're working at.
 *
 * If no station was pre-selected (edge case), falls back to showing
 * the full station picker inline.
 */
import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import { checkApi } from '../api/checkApi.js'
import { todayIso, formatCheckDate, clampCheckDate, relativeIso } from '../../../shared/utils/dateHelpers.js'
import { stationColor } from '../../../shared/utils/stationColors.js'
import Spinner from '../../../shared/components/Spinner.jsx'

export default function Step1Vehicle({ draft, preselectedStation, onSelect }) {
  const { getToken } = useAuth()

  const [vehicleId, setVehicleId]   = useState(draft?.vehicle_id ?? null)
  const [checkDate, setCheckDate]   = useState(draft?.check_date ?? todayIso())
  const [secondCrew, setSecondCrew] = useState(draft?.second_crew ?? '')

  // Use preselected station from home screen
  const station = preselectedStation ?? null
  const stationId = station?.station_id ?? null

  // Load vehicles for this station
  const {
    data: vehicles,
    isLoading: loadingVehicles,
    error: vehiclesError,
  } = useApi(
    () => stationId ? checkApi.getVehicles(stationId, getToken) : Promise.resolve(null),
    [stationId]
  )

  // Auto-select vehicle if only one active vehicle exists
  useEffect(() => {
    const active = vehicles?.filter(v => v.active !== false) ?? []
    if (active.length === 1 && vehicleId === null) {
      setVehicleId(active[0].vehicle_id)
    }
  }, [vehicles, vehicleId])

  // Reset vehicle selection if station somehow changes
  useEffect(() => {
    setVehicleId(draft?.vehicle_id ?? null)
  }, [stationId])

  const handleDateChange = useCallback((e) => {
    setCheckDate(clampCheckDate(e.target.value))
  }, [])

  const canProceed = stationId && vehicleId && checkDate

  // Station color
  const colors = station ? stationColor(station.name, 0) : null

  function handleProceed() {
    if (!canProceed) return
    const selectedVehicle = vehicles?.find(v => v.vehicle_id === vehicleId)
    onSelect({
      stationId,
      vehicleId,
      checkDate,
      secondCrew,
      vehicle: selectedVehicle,
    })
  }

  if (!station) {
    return (
      <div className="wizard-step">
        <div className="api-error-card">
          <div className="api-error-card__icon">📍</div>
          <div className="api-error-card__title">No station selected</div>
          <div className="api-error-card__message">
            Go back to the home screen and select your station first.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="wizard-step">

      {/* Station context — visual reminder throughout the check */}
      <div
        className="station-band"
        style={{
          background: colors?.primary ?? 'var(--color-brand)',
          color: colors?.text ?? '#ffffff',
        }}
        aria-label={`Checking at: ${station.name}`}
      >
        <div className="station-band__info">
          <span className="station-band__icon" aria-hidden="true">📍</span>
          <div>
            <div className="station-band__name">{station.name}</div>
            {station.region && (
              <div className="station-band__region">{station.region}</div>
            )}
          </div>
        </div>
      </div>

      {/* Vehicle selection */}
      <div className="form-group">
        <label className="form-label">Select vehicle</label>
        {loadingVehicles ? (
          <Spinner label="Loading vehicles…" size="sm" />
        ) : vehiclesError ? (
          <div className="api-error-card">
            <div className="api-error-card__icon">⚠️</div>
            <div className="api-error-card__title">Could not load vehicles</div>
            <div className="api-error-card__message">{vehiclesError.message}</div>
          </div>
        ) : (
          <div className="vehicle-cards" role="radiogroup" aria-label="Select your vehicle">
            {vehicles?.filter(v => v.active !== false).map(v => {
              const isSelected = vehicleId === v.vehicle_id
              return (
                <button
                  key={v.vehicle_id}
                  role="radio"
                  aria-checked={isSelected}
                  className={`vehicle-card ${isSelected ? 'vehicle-card--selected' : ''}`}
                  style={isSelected && colors ? {
                    borderColor: colors.primary,
                    background: colors.light,
                  } : {}}
                  onClick={() => setVehicleId(v.vehicle_id)}
                  type="button"
                >
                  <div
                    className="vehicle-card__color-dot"
                    style={{ background: colors?.primary ?? 'var(--color-brand)' }}
                    aria-hidden="true"
                  />
                  <div className="vehicle-card__info">
                    <div className="vehicle-card__number">Unit {v.vehicle_number}</div>
                    <div className="vehicle-card__type">{v.vehicle_type}</div>
                  </div>
                  {v.requires_controlled_substance_check && (
                    <div
                      className="vehicle-card__cs-badge"
                      aria-label="ALS — controlled substances required"
                    >
                      ALS
                    </div>
                  )}
                </button>
              )
            })}
            {vehicles?.filter(v => v.active !== false).length === 0 && (
              <p className="form-hint">No active vehicles at this station.</p>
            )}
          </div>
        )}
      </div>

      {/* Check date */}
      <div className="form-group">
        <label className="form-label" htmlFor="check-date">Check date</label>
        <div className="date-field">
          <div
            className="date-field__display"
            style={colors ? { color: colors.primary } : {}}
          >
            {formatCheckDate(checkDate)}
          </div>
          <input
            id="check-date"
            type="date"
            className="form-input date-field__input"
            value={checkDate}
            min={relativeIso(-7)}
            max={todayIso()}
            onChange={handleDateChange}
            aria-label="Change check date"
          />
        </div>
        <p className="form-hint">Defaults to today. Can be changed up to 7 days back.</p>
      </div>

      {/* Second crew */}
      <div className="form-group">
        <label className="form-label" htmlFor="second-crew">
          Second crew member{' '}
          <span className="form-label__optional">(optional)</span>
        </label>
        <input
          id="second-crew"
          type="text"
          className="form-input"
          value={secondCrew}
          onChange={e => setSecondCrew(e.target.value)}
          placeholder="Enter name…"
          autoComplete="off"
        />
        <p className="form-hint">
          Required for controlled substance checks on ALS vehicles.
        </p>
      </div>

      {/* Proceed */}
      <button
        className="btn btn--primary btn--large"
        style={canProceed && colors ? { background: colors.primary } : {}}
        onClick={handleProceed}
        disabled={!canProceed}
        type="button"
      >
        {!vehicleId
          ? 'Select a vehicle to continue'
          : 'Continue to compartments →'}
      </button>
    </div>
  )
}
