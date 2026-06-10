/**
 * modules/usage-log/index.jsx
 * After-Call Reset — "Log Items Used" flow.
 *
 * Steps:
 *   1. Vehicle picker (auto-skipped when station has exactly one active vehicle)
 *   2. Item picker (frequent items first, search, +/- per item)
 *   3. Confirmation screen after submit
 *
 * Target: ≤3 taps for single-vehicle stations with 1–3 items.
 */
import React, { useEffect, useState, useMemo } from 'react'
import { useAuth } from '../../shared/hooks/useAuth.jsx'
import { vehicleApi } from '../vehicles/api/vehicleApi.js'
import { supplyApi } from '../supply-room/api/supplyApi.js'
import { usageApi } from './api/usageApi.js'
import Spinner from '../../shared/components/Spinner.jsx'
import UsageItemPicker from './components/UsageItemPicker.jsx'
import './usage-log.css'

export default function UsageLogScreen({ station, onBack }) {
  const { getToken } = useAuth()

  const [step, setStep]                   = useState('loading')  // loading | vehicle | items | submitting | done | error
  const [vehicles, setVehicles]           = useState([])
  const [selectedVehicle, setSelectedVehicle] = useState(null)
  const [catalogItems, setCatalogItems]   = useState([])
  const [frequentItems, setFrequentItems] = useState([])
  const [quantities, setQuantities]       = useState({})
  const [loadError, setLoadError]         = useState(null)
  const [submitError, setSubmitError]     = useState(null)
  const [submittedCount, setSubmittedCount] = useState(0)

  useEffect(() => {
    if (!station?.station_id) return
    Promise.all([
      vehicleApi.getStationVehicles(station.station_id, getToken),
      supplyApi.getCatalog(station.station_id, getToken),
      usageApi.getFrequentItems(station.station_id, getToken),
    ])
      .then(([vList, catalog, frequent]) => {
        const active = vList.filter(v => v.status === 'ACTIVE')
        setVehicles(active)
        // Supply catalog includes all items; keep only SUPPLY type with station_supply
        // The getCatalog endpoint (SR-B1) already filters to station_supply=true.
        setCatalogItems(
          catalog
            .filter(i => i.check_type === 'SUPPLY' || !i.check_type)
            .sort((a, b) => a.item_name.localeCompare(b.item_name))
        )
        setFrequentItems(frequent)

        if (active.length === 1) {
          setSelectedVehicle(active[0])
          setStep('items')
        } else if (active.length === 0) {
          setSelectedVehicle(null)
          setStep('items')
        } else {
          setStep('vehicle')
        }
      })
      .catch(e => {
        setLoadError(e.message || 'Could not load items.')
        setStep('error')
      })
  }, [station, getToken])

  function handleVehicleSelect(vehicle) {
    setSelectedVehicle(vehicle)
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
      await usageApi.logUsage(
        {
          station_id: station.station_id,
          vehicle_id: selectedVehicle?.vehicle_id ?? null,
          timestamp:  new Date().toISOString(),
          items:      selectedItems,
        },
        getToken
      )
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

      {/* Step 1: Vehicle picker */}
      {step === 'vehicle' && (
        <div className="ul-body">
          <p className="ul-prompt">Which vehicle was on the call?</p>
          <div className="ul-vehicle-list">
            {vehicles.map(v => (
              <button
                key={v.vehicle_id}
                className="ul-vehicle-btn"
                onClick={() => handleVehicleSelect(v)}
                type="button"
              >
                <span className="ul-vehicle-btn__icon" aria-hidden="true">🚑</span>
                <span className="ul-vehicle-btn__name">{v.vehicle_number || `Vehicle ${v.vehicle_id}`}</span>
                <span className="ul-vehicle-btn__arrow" aria-hidden="true">›</span>
              </button>
            ))}
            <button
              className="ul-vehicle-btn ul-vehicle-btn--skip"
              onClick={() => handleVehicleSelect(null)}
              type="button"
            >
              <span className="ul-vehicle-btn__name ul-vehicle-btn__name--muted">Not vehicle-specific</span>
              <span className="ul-vehicle-btn__arrow" aria-hidden="true">›</span>
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Item picker */}
      {step === 'items' && (
        <div className="ul-body ul-body--items">
          {selectedVehicle && (
            <div className="ul-vehicle-badge">
              🚑 {selectedVehicle.vehicle_number || `Vehicle ${selectedVehicle.vehicle_id}`}
              <button
                className="ul-vehicle-badge__change"
                onClick={() => vehicles.length > 1 ? setStep('vehicle') : null}
                type="button"
                style={{ display: vehicles.length > 1 ? undefined : 'none' }}
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
            Supply room counts updated.
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
