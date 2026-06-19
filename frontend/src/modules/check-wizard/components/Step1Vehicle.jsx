/**
 * modules/check-wizard/components/Step1Vehicle.jsx
 * Step 1: Vehicle / portable equipment selection + date + second crew.
 *
 * Session F Block 4 (F-UX7):
 *   LastCheckBanner now appears inline below the selected vehicle card.
 *
 * Bug fix (post-Block-6):
 *   Vehicle card color dots now use vehicleDisplayColor() so each vehicle
 *   shows its own color (vehicle_color → station.primary_color → palette).
 *   Previously all dots showed the station palette color regardless of the
 *   per-vehicle color set in the admin Vehicles screen.
 *
 * Session AD (BUG-AD1, defensive): "active" and "retired_at" are independent
 *   fields. The backend call here passes active=true, and retiring a vehicle
 *   happens to also set active=false, so retired vehicles are excluded today
 *   — but that's a side effect, not a guarantee. Filtering on !v.retired_at
 *   here too means this screen can't surface a retired vehicle for a new
 *   check even if that side effect ever changes.
 *
 * Two groups of selectable cards are shown:
 *
 *   1. Vehicles — loaded from GET /stations/{id}/vehicles
 *      Each vehicle card carries a vehicle_id; the orchestrator resolves
 *      the corresponding location_id (VEHICLE type) from all locations.
 *
 *   2. Portable locations — loaded from GET /stations/{id}/locations
 *      These are JUMP_BAG and EQUIPMENT locations not tied to one vehicle.
 *      Each card carries the location_id directly — no vehicle_id resolution
 *      needed. The label ("Jump Bag (Units 710/712)") is the display name.
 *
 * onSelect is called with:
 *   {
 *     stationId,
 *     vehicleId,      // null for portable locations
 *     locationId,     // set directly for portable; null for vehicles (resolved in orchestrator)
 *     checkDate,
 *     secondCrew,
 *     vehicle,        // Vehicle object for vehicles; null for portable
 *     selectionLabel, // display name for the submitted check
 *   }
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import { checkApi } from '../api/checkApi.js'
import { todayIso, formatCheckDate, clampCheckDate, relativeIso } from '../../../shared/utils/dateHelpers.js'
import { stationColor, vehicleDisplayColor } from '../../../shared/utils/stationColors.js'
import Spinner from '../../../shared/components/Spinner.jsx'
import LastCheckBanner from '../../../shared/components/LastCheckBanner.jsx'

// Internal selection shape:
//   { type: 'vehicle', vehicleId, vehicle }
//   { type: 'location', locationId, label, locationType }
const NO_SELECTION = null

// A vehicle is checkable only if it's active and not permanently retired.
function isCheckableVehicle(v) {
  return v.active !== false && !v.retired_at
}

export default function Step1Vehicle({ draft, preselectedStation, onSelect }) {
  const { getToken } = useAuth()

  const today = todayIso()

  // SR-F4: Supply room checks skip vehicle selection entirely — auto-advance on mount.
  useEffect(() => {
    if (draft?._supplyRoom && draft.location_id) {
      onSelect({
        stationId:      draft.station_id ?? preselectedStation?.station_id,
        vehicleId:      null,
        locationId:     draft.location_id,
        checkDate:      today,
        secondCrew:     '',
        vehicle:        null,
        selectionLabel: 'Station Supply Room',
        locationType:   'STATION_SUPPLY_ROOM',
      })
    }
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  const [selection, setSelection] = useState(() => {
    // Restore from draft if resuming
    if (draft?.vehicle_id) return { type: 'vehicle', vehicleId: draft.vehicle_id, vehicle: null }
    if (draft?.location_id && !draft?.vehicle_id) return {
      type: 'location', locationId: draft.location_id,
      label: draft.selection_label ?? '', locationType: draft.location_type ?? 'JUMP_BAG',
    }
    return NO_SELECTION
  })

  const [checkDate, setCheckDate]   = useState(draft?.check_date ?? today)
  const [secondCrew, setSecondCrew] = useState(draft?.second_crew ?? '')

  // Collapse date/crew by default unless something non-default is already set
  const defaultOpen = (draft?.check_date && draft.check_date !== today) || !!draft?.second_crew
  const [detailsOpen, setDetailsOpen] = useState(!!defaultOpen)

  const station   = preselectedStation ?? null
  const stationId = station?.station_id ?? null

  // Load vehicles at this station
  const {
    data: vehicles,
    isLoading: loadingVehicles,
    error: vehiclesError,
  } = useApi(
    () => stationId ? checkApi.getVehicles(stationId, getToken) : Promise.resolve(null),
    [stationId]
  )

  // Load portable locations (jump bags, equipment) at this station
  const {
    data: portableLocations,
    isLoading: loadingLocations,
  } = useApi(
    () => stationId ? checkApi.getStationLocations(stationId, getToken) : Promise.resolve(null),
    [stationId]
  )

  // Auto-select if exactly one vehicle and no portable locations
  useEffect(() => {
    const activeVehicles = vehicles?.filter(isCheckableVehicle) ?? []
    const portables      = portableLocations ?? []
    if (activeVehicles.length === 1 && portables.length === 0 && !selection) {
      setSelection({ type: 'vehicle', vehicleId: activeVehicles[0].vehicle_id, vehicle: activeVehicles[0] })
    }
  }, [vehicles, portableLocations, selection])

  // Reset selection if station changes
  useEffect(() => {
    setSelection(draft?.vehicle_id
      ? { type: 'vehicle', vehicleId: draft.vehicle_id, vehicle: null }
      : NO_SELECTION
    )
  }, [stationId])

  const handleDateChange = useCallback((e) => {
    setCheckDate(clampCheckDate(e.target.value))
  }, [])

  const canProceed = stationId && selection && checkDate
  const stColors   = station ? stationColor(station.name, 0) : null

  const selectedVehicleId  = selection?.type === 'vehicle'  ? selection.vehicleId  : null
  const selectedLocationId = selection?.type === 'location' ? selection.locationId : null

  function handleProceed() {
    if (!canProceed) return

    if (selection.type === 'vehicle') {
      const v = vehicles?.find(v => v.vehicle_id === selection.vehicleId)
      onSelect({
        stationId,
        vehicleId:      selection.vehicleId,
        locationId:     null,   // orchestrator resolves from all locations
        checkDate,
        secondCrew,
        vehicle:        v ?? null,
        selectionLabel: v ? `Unit ${v.vehicle_number} ${v.vehicle_type}` : '',
      })
    } else {
      // Portable location — location_id is known directly
      onSelect({
        stationId,
        vehicleId:      null,
        locationId:     selection.locationId,
        checkDate,
        secondCrew,
        vehicle:        null,
        selectionLabel: selection.label,
        locationLabel:  selection.label,
        locationType:   selection.locationType,
      })
    }
  }

  // SR-F4: Render nothing while auto-advance fires for supply room checks.
  if (draft?._supplyRoom) return <Spinner label="Preparing supply room check…" />

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

  const isLoading = loadingVehicles || loadingLocations
  const activeVehicles = vehicles?.filter(isCheckableVehicle) ?? []
  const portables      = portableLocations ?? []
  const hasAnyItems    = activeVehicles.length > 0 || portables.length > 0

  const proceedLabel = !selection
    ? 'Select a vehicle or bag to continue'
    : 'Continue to compartments →'

  return (
    <div className="wizard-step">

      {/* Station context band */}
      <div
        className="station-band"
        style={{
          background: station.primary_color ?? stColors?.primary ?? 'var(--color-brand)',
          color: stColors?.text ?? '#ffffff',
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

      {/* Selection group */}
      <div className="form-group">
        <label className="form-label">What are you checking?</label>

        {isLoading ? (
          <Spinner label="Loading…" size="sm" />
        ) : vehiclesError ? (
          <div className="api-error-card">
            <div className="api-error-card__icon">⚠️</div>
            <div className="api-error-card__title">Could not load vehicles</div>
            <div className="api-error-card__message">{vehiclesError.message}</div>
          </div>
        ) : !hasAnyItems ? (
          <p className="form-hint">No active vehicles or equipment at this station.</p>
        ) : (
          <div className="vehicle-cards" role="radiogroup" aria-label="Select what you are checking">

            {/* ── Vehicle cards ─────────────────────────────────────────── */}
            {activeVehicles.map(v => {
              const isSelected   = selection?.type === 'vehicle' && selection.vehicleId === v.vehicle_id
              // Per-vehicle color: vehicle_color → station.primary_color → station palette
              const dotColor     = vehicleDisplayColor(v, station, 0)
              const selectedBg   = isSelected ? `${dotColor}18` : undefined // 18 = ~10% opacity
              return (
                <button
                  key={`vehicle-${v.vehicle_id}`}
                  role="radio"
                  aria-checked={isSelected}
                  className={`vehicle-card ${isSelected ? 'vehicle-card--selected' : ''}`}
                  style={isSelected ? {
                    borderColor: dotColor,
                    background:  selectedBg,
                  } : {}}
                  onClick={() => setSelection({ type: 'vehicle', vehicleId: v.vehicle_id, vehicle: v })}
                  type="button"
                >
                  {/* Color dot — per-vehicle color */}
                  <div
                    className="vehicle-card__color-dot"
                    style={{ background: dotColor }}
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

            {/* ── Portable location cards (Jump Bags, Equipment) ────────── */}
            {portables.map(loc => {
              const isSelected = selection?.type === 'location' && selection.locationId === loc.location_id
              const icon       = loc.location_type === 'JUMP_BAG' ? '🎒' : '🔧'
              // Portables don't have their own color — use station color
              const dotColor   = station.primary_color ?? stColors?.primary ?? 'var(--color-brand)'
              return (
                <button
                  key={`loc-${loc.location_id}`}
                  role="radio"
                  aria-checked={isSelected}
                  className={`vehicle-card vehicle-card--portable ${isSelected ? 'vehicle-card--selected' : ''}`}
                  style={isSelected ? {
                    borderColor: dotColor,
                    background:  `${dotColor}18`,
                  } : {}}
                  onClick={() => setSelection({
                    type:         'location',
                    locationId:   loc.location_id,
                    label:        loc.label,
                    locationType: loc.location_type,
                  })}
                  type="button"
                >
                  <div
                    className="vehicle-card__color-dot vehicle-card__color-dot--muted"
                    style={{ background: dotColor, opacity: 0.5 }}
                    aria-hidden="true"
                  />
                  <div className="vehicle-card__info">
                    <div className="vehicle-card__number">
                      <span aria-hidden="true">{icon} </span>{loc.label}
                    </div>
                    <div className="vehicle-card__type">
                      {loc.location_type === 'JUMP_BAG' ? 'Jump Bag' : 'Equipment'}
                    </div>
                  </div>
                </button>
              )
            })}

          </div>
        )}
      </div>

      {/* ── F-UX7: Last-check banner ──────────────────────────────────────
          Rendered only when a vehicle (not a portable location) is selected.
          Sits between the vehicle list and the date/crew fields so the crew
          sees it before committing to the date.                            */}
      {(selectedVehicleId || selectedLocationId) && (
        <LastCheckBanner
          vehicleId={selectedVehicleId}
          locationId={selectedLocationId}
          todayIso={today}
          getToken={getToken}
        />
      )}

      {/* Collapsible date / crew — collapsed by default for today's date with no second crew */}
      <button
        className="step1-details-toggle"
        type="button"
        aria-expanded={detailsOpen}
        onClick={() => setDetailsOpen(o => !o)}
      >
        <span>
          {checkDate !== today || secondCrew
            ? `${formatCheckDate(checkDate)}${secondCrew ? ` · ${secondCrew}` : ''}`
            : 'Change date or add crew member'}
        </span>
        <span className="step1-details-toggle__chevron" aria-hidden="true">
          {detailsOpen ? '∧' : '∨'}
        </span>
      </button>

      {detailsOpen && (
        <div className="step1-details">
          {/* Check date */}
          <div className="form-group">
            <label className="form-label" htmlFor="check-date">Check date</label>
            <div className="date-field">
              <div
                className="date-field__display"
                style={stColors ? { color: stColors.primary } : {}}
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
        </div>
      )}

      {/* Proceed */}
      <button
        className="btn btn--primary btn--large"
        style={canProceed && stColors ? { background: stColors.primary } : {}}
        onClick={handleProceed}
        disabled={!canProceed}
        type="button"
      >
        {proceedLabel}
      </button>
    </div>
  )
}
