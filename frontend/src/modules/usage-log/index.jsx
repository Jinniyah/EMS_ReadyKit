/**
 * modules/usage-log/index.jsx
 * After-Call Reset -- "Log Items Used" flow.
 *
 * Steps:
 *   1. Unit picker -- vehicles AND portable locations (jump bags).
 *      Auto-skipped when station has exactly one active unit total.
 *   2. Item picker (frequent items first, search, +/- per item)
 *   3. Confirmation screen after submit
 *
 * Target: <=3 taps for single-unit stations with 1-3 items.
 *
 * USAGE-B1/B2: Submits vehicle_id OR location_id (never both, never neither
 * when a unit is selected) so the backend can subtract usage from the correct
 * unit's last-readings pre-fill, flagging shortages on the next check.
 */
import React, { useEffect, useState, useMemo } from 'react'
import { useAuth } from '../../shared/hooks/useAuth.jsx'
import { vehicleApi } from '../vehicles/api/vehicleApi.js'
import { checkApi } from '../check-wizard/api/checkApi.js'
import { supplyApi } from '../supply-room/api/supplyApi.js'
import { usageApi } from './api/usageApi.js'
import Spinner from '../../shared/components/Spinner.jsx'
import UsageItemPicker from './components/UsageItemPicker.jsx'
import './usage-log.css'

/**
 * Build a unified unit list from vehicles + portable locations.
 * Each entry has: { id, kind: 'vehicle'|'location', label, icon }
 */
function buildUnits(vehicles, locations) {
  const vehicleUnits = vehicles
    .filter(v => v.active === true && !v.retired_at)
    .map(v => ({
      id:    v.vehicle_id,
      kind:  'vehicle',
      label: v.vehicle_number || `Vehicle ${v.vehicle_id}`,
      icon:  '🚑',
    }))

  const locationUnits = locations
    .filter(loc => !loc.retired_at)
    .map(loc => ({
      id:    loc.location_id,
      kind:  'location',
      label: loc.label || loc.location_type,
      icon:  '🎒',
    }))

  return [...vehicleUnits, ...locationUnits]
}

export default function UsageLogScreen({ station, onBack }) {
  const { getToken } = useAuth()

  const [step, setStep]                     = useState('loading')
  const [units, setUnits]                   = useState([])          // unified vehicle+location list
  const [selectedUnit, setSelectedUnit]     = useState(null)        // { id, kind, label, icon }
  const [catalogItems, setCatalogItems]     = useState([])
  const [frequentItems, setFrequentItems]   = useState([])
  const [quantities, setQuantities]         = useState({})
  const [loadError, setLoadError]           = useState(null)
  const [submitError, setSubmitError]       = useState(null)
  const [submittedCount, setSubmittedCount] = useState(0)

  useEffect(() => {
    if (!station?.station_id) return
    Promise.all([
      vehicleApi.getActiveStationVehicles(station.station_id, getToken),
      checkApi.getStationLocations(station.station_id, getToken).catch(() => []),
      supplyApi.getCatalog(station.station_id, getToken),
      usageApi.getFrequentItems(station.station_id, getToken),
    ])
      .then(([vList, locList, catalog, frequent]) => {
        const allUnits = buildUnits(vList, locList)
        setUnits(allUnits)

        setCatalogItems(
          catalog
            .filter(i => i.check_type === 'SUPPLY' || !i.check_type)
            .sort((a, b) => a.item_name.localeCompare(b.item_name))
        )
        setFrequentItems(frequent)

        if (allUnits.length === 1) {
          // Single unit -- skip the picker entirely
          setSelectedUnit(allUnits[0])
          setStep('items')
        } else {
          // Multiple units (or none) -- show the picker
          setStep('unit')
        }
      })
      .catch(e => {
        setLoadError(e.message || 'Could not load items.')
        setStep('error')
      })
  }, [station, getToken])

  function handleUnitSelect(unit) {
    setSelectedUnit(unit)
    setStep('items')
  }

  function handleQuantityChange(itemId, qty) {
    setQuantities(prev => ({ ...prev, [itemId]: qty }))
  }

  const selectedItems = useMemo(
    () => Object.entries(quantities)
      .filter(([, qty]) => qty > 0)
      .map(([itemId, qty]) => ({ item_id: parseInt(itemId, 10), quantity_used: qty })),
    [quantities]
  )

  async function handleDone() {
    if (selectedItems.length === 0) { onBack(); return }
    setStep('submitting')
    setSubmitError(null)
    try {
      const payload = {
        station_id:  station.station_id,
        vehicle_id:  selectedUnit?.kind === 'vehicle'  ? selectedUnit.id : null,
        location_id: selectedUnit?.kind === 'location' ? selectedUnit.id : null,
        timestamp:   new Date().toISOString(),
        items:       selectedItems,
      }
      await usageApi.logUsage(payload, getToken)
      setSubmittedCount(selectedItems.length)
      setStep('done')
    } catch (e) {
      setSubmitError(e.response?.data?.detail || e.message || 'Something went wrong. Please try again.')
      setStep('items')
    }
  }

  const totalUnits = selectedItems.reduce((s, i) => s + i.quantity_used, 0)

  return (
    <div className="ul-screen">

      {/* Header */}
      <div className="ul-header">
        <button
          className="ul-back-btn"
          onClick={onBack}
          type="button"
          aria-label="Back to Home"
        >
          ← Home
        </button>
        <div className="ul-header__text">
          <h1 className="ul-header__title">Log Items Used</h1>
          {station && <p className="ul-header__station">{station.name}</p>}
        </div>
      </div>

      {/* Loading */}
      {step === 'loading' && <Spinner label="Loading items…" />}

      {/* Error */}
      {step === 'error' && (
        <div className="ul-error" role="alert">
          <p>{loadError}</p>
          <button className="btn btn--secondary" onClick={onBack} type="button">
            Go back
          </button>
        </div>
      )}

      {/* Step 1: Unit picker (vehicles + portable locations) */}
      {step === 'unit' && (
        <div className="ul-body">
          <p className="ul-prompt">Which unit was on the call?</p>
          <div className="ul-vehicle-list">
            {units.map(unit => (
              <button
                key={`${unit.kind}-${unit.id}`}
                className="ul-vehicle-btn"
                onClick={() => handleUnitSelect(unit)}
                type="button"
              >
                <span className="ul-vehicle-btn__icon" aria-hidden="true">{unit.icon}</span>
                <span className="ul-vehicle-btn__name">{unit.label}</span>
                <span className="ul-vehicle-btn__arrow" aria-hidden="true">›</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Step 2: Item picker */}
      {step === 'items' && (
        <div className="ul-body ul-body--items">
          {selectedUnit && (
            <div className="ul-vehicle-badge">
              {selectedUnit.icon} {selectedUnit.label}
              <button
                className="ul-vehicle-badge__change"
                onClick={() => units.length > 1 ? setStep('unit') : null}
                type="button"
                style={{ display: units.length > 1 ? undefined : 'none' }}
              >
                Change
              </button>
            </div>
          )}

          {submitError && (
            <div className="ul-submit-error" role="alert">{submitError}</div>
          )}

          <UsageItemPicker
            catalogItems={catalogItems}
            frequentItems={frequentItems}
            quantities={quantities}
            onQuantityChange={handleQuantityChange}
          />

          <div className="ul-footer">
            <button
              className="btn btn--primary btn--large ul-done-btn"
              onClick={handleDone}
              type="button"
              disabled={selectedItems.length === 0}
            >
              {selectedItems.length === 0
                ? 'Select items above'
                : `Done — ${totalUnits} unit${totalUnits !== 1 ? 's' : ''} logged`}
            </button>
            {selectedItems.length === 0 && (
              <button
                className="btn btn--ghost ul-skip-btn"
                onClick={onBack}
                type="button"
              >
                Nothing used
              </button>
            )}
          </div>
        </div>
      )}

      {/* Submitting */}
      {step === 'submitting' && <Spinner label="Saving…" />}

      {/* Done */}
      {step === 'done' && (
        <div className="ul-body ul-done">
          <div className="ul-done__icon" aria-hidden="true">✓</div>
          <h2 className="ul-done__heading">Logged!</h2>
          <p className="ul-done__detail">
            {submittedCount} item{submittedCount !== 1 ? 's' : ''} recorded.
            {selectedUnit ? ` ${selectedUnit.label} quantities updated.` : ''}
          </p>
          <button
            className="btn btn--primary btn--large"
            onClick={onBack}
            type="button"
          >
            Back to Home
          </button>
        </div>
      )}

    </div>
  )
}
