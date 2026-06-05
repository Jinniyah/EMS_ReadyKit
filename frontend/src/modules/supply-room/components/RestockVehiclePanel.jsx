/**
 * supply-room/components/RestockVehiclePanel.jsx
 * SUPPLY-F2 — Restock vehicle flow.
 *
 * Steps:
 *  1. SELECT_VEHICLE — pick which unit to restock
 *  2. REVIEW_ITEMS   — stepper for each item below par
 *  3. DONE           — summary
 *
 * Bug fix: vehicle.location_id does not exist on VehicleRead. The vehicle's
 * inventory location_id is resolved by loading all station locations and
 * matching on vehicle_id (same pattern as the check wizard).
 */
import React, { useState, useEffect } from 'react'
import { vehicleApi } from '../../vehicles/api/vehicleApi.js'
import { supplyApi } from '../api/supplyApi.js'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'

export default function RestockVehiclePanel({ station, supplyRoomLocationId, onDone }) {
  const { getToken } = useAuth()

  const [step, setStep]                     = useState('SELECT_VEHICLE')
  const [vehicles, setVehicles]             = useState([])
  const [locations, setLocations]           = useState([])
  const [selectedVehicle, setSelectedVehicle] = useState(null)
  const [vehicleSummary, setVehicleSummary] = useState([])
  const [supplySummary, setSupplySummary]   = useState([])
  const [qtys, setQtys]                     = useState({})
  const [showAtPar, setShowAtPar]           = useState(false)
  const [submitting, setSubmitting]         = useState(false)
  const [result, setResult]                 = useState(null)
  const [error, setError]                   = useState(null)

  // Load vehicles + all station locations together so we can resolve location_id.
  useEffect(() => {
    if (!station?.station_id) return
    Promise.all([
      vehicleApi.getActiveStationVehicles(station.station_id, getToken),
      supplyApi.getStationLocations(station.station_id, getToken),
    ])
      .then(([vs, locs]) => { setVehicles(vs); setLocations(locs) })
      .catch(() => setError('Could not load vehicles for this station.'))
  }, [station, getToken])

  async function handleSelectVehicle(vehicle) {
    setError(null)

    // Resolve the vehicle's VEHICLE-type inventory location.
    const vehicleLoc = locations.find(
      l => l.vehicle_id === vehicle.vehicle_id && l.location_type === 'VEHICLE'
    )
    if (!vehicleLoc) {
      setError(`No inventory location found for Unit ${vehicle.vehicle_number}. Has it been set up in admin?`)
      return
    }

    const enriched = { ...vehicle, location_id: vehicleLoc.location_id }
    setSelectedVehicle(enriched)

    try {
      const [vSummary, sSummary] = await Promise.all([
        supplyApi.getStockSummary(vehicleLoc.location_id, getToken),
        supplyApi.getStockSummary(supplyRoomLocationId, getToken),
      ])
      setVehicleSummary(vSummary)
      setSupplySummary(sSummary)
      setShowAtPar(false)

      // Pre-fill to fill up to par_max (capped by supply room availability)
      const initial = {}
      for (const item of vSummary) {
        if (item.par_min != null && item.total_quantity < item.par_min) {
          const available = sSummary.find(s => s.item_id === item.item_id)?.total_quantity ?? 0
          const needed    = (item.par_max ?? item.par_min) - item.total_quantity
          initial[item.item_id] = Math.min(needed, available)
        }
      }
      setQtys(initial)
      setStep('REVIEW_ITEMS')
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleTransfer() {
    const items = Object.entries(qtys).filter(([, q]) => q > 0)
    if (!items.length) {
      setError('Enter a quantity for at least one item.')
      return
    }
    setSubmitting(true)
    setError(null)
    const transferred = []
    const errors      = []
    for (const [itemId, qty] of items) {
      try {
        await supplyApi.transfer({
          from_location_id: supplyRoomLocationId,
          to_location_id:   selectedVehicle.location_id,
          item_id:          parseInt(itemId, 10),
          quantity:         qty,
        }, getToken)
        transferred.push(itemId)
      } catch (e) {
        errors.push({ itemId, message: e.message })
      }
    }
    setSubmitting(false)
    setResult({ transferred, errors })
    setStep('DONE')
  }

  // ── Step 1: Select vehicle ────────────────────────────────────────────────

  if (step === 'SELECT_VEHICLE') {
    const dotColor = (v) =>
      v.vehicle_color ?? station?.primary_color ?? 'var(--color-text-muted)'

    return (
      <div className="sr-panel">
        <h2 className="sr-panel__heading">Select Vehicle to Restock</h2>
        {error && <div className="sr-error"><strong>{error}</strong></div>}

        {vehicles.length === 0 ? (
          <p className="sr-empty">No active vehicles at this station.</p>
        ) : (
          <div className="sr-vehicle-list">
            {vehicles.map(v => (
              <button
                key={v.vehicle_id}
                className="sr-vehicle-card"
                onClick={() => handleSelectVehicle(v)}
                type="button"
              >
                <div
                  className="sr-vehicle-card__dot"
                  style={{ background: dotColor(v) }}
                  aria-hidden="true"
                />
                <div className="sr-vehicle-card__info">
                  <span className="sr-vehicle-card__number">Unit {v.vehicle_number}</span>
                  <span className="sr-vehicle-card__type">{v.vehicle_type}</span>
                </div>
                <span className="sr-vehicle-card__arrow" aria-hidden="true">›</span>
              </button>
            ))}
          </div>
        )}
      </div>
    )
  }

  // ── Step 2: Review items below par ────────────────────────────────────────

  if (step === 'REVIEW_ITEMS') {
    const restockItems = vehicleSummary.filter(
      item => item.par_min != null && item.total_quantity < item.par_min
    )
    const atParItems = vehicleSummary.filter(
      item => item.par_min != null && item.total_quantity >= item.par_min
    )

    return (
      <div className="sr-panel">
        <button
          className="sr-back-btn"
          onClick={() => setStep('SELECT_VEHICLE')}
          type="button"
        >
          ← Back
        </button>

        <div>
          <h2 className="sr-panel__heading">Unit {selectedVehicle.vehicle_number}</h2>
          <p className="sr-panel__subtext">
            Adjust quantities to move from the supply room to this unit.
          </p>
        </div>

        {error && <div className="sr-error"><strong>{error}</strong></div>}

        {restockItems.length === 0 ? (
          <div className="sr-all-good">
            <span className="sr-all-good__icon">✓</span>
            <span>All items are at or above par level.</span>
          </div>
        ) : (
          <>
            <div className="sr-transfer-list">
              {restockItems.map(item => {
                const supplyItem = supplySummary.find(s => s.item_id === item.item_id)
                const available  = supplyItem?.total_quantity ?? 0
                const qty        = qtys[item.item_id] ?? 0

                const onTruckClass = item.total_quantity === 0
                  ? 'sr-stat__value sr-stat__value--low'
                  : 'sr-stat__value sr-stat__value--warn'
                const supplyClass = available === 0
                  ? 'sr-stat__value sr-stat__value--low'
                  : 'sr-stat__value sr-stat__value--ok'

                return (
                  <div key={item.item_id} className="sr-transfer-row">
                    <div className="sr-transfer-row__name">{item.item_name}</div>

                    <div className="sr-transfer-row__stats">
                      <div className="sr-stat">
                        <span className="sr-stat__label">On Truck</span>
                        <span className={onTruckClass}>{item.total_quantity}</span>
                      </div>
                      <div className="sr-stat">
                        <span className="sr-stat__label">Par</span>
                        <span className="sr-stat__value">
                          {item.par_min}–{item.par_max ?? item.par_min}
                        </span>
                      </div>
                      <div className="sr-stat">
                        <span className="sr-stat__label">Supply Room</span>
                        <span className={supplyClass}>{available}</span>
                      </div>
                    </div>

                    <div className="sr-qty-row">
                      <button
                        className="sr-qty-btn"
                        onClick={() => setQtys(q => ({
                          ...q,
                          [item.item_id]: Math.max(0, (q[item.item_id] ?? 0) - 1),
                        }))}
                        disabled={qty === 0}
                        type="button"
                        aria-label={`Decrease quantity for ${item.item_name}`}
                      >−</button>
                      <span className="sr-qty-display" aria-live="polite">{qty}</span>
                      <button
                        className="sr-qty-btn"
                        onClick={() => setQtys(q => ({
                          ...q,
                          [item.item_id]: Math.min(available, (q[item.item_id] ?? 0) + 1),
                        }))}
                        disabled={qty >= available}
                        type="button"
                        aria-label={`Increase quantity for ${item.item_name}`}
                      >+</button>
                    </div>
                  </div>
                )
              })}
            </div>

            <button
              className="btn btn--primary btn--full"
              onClick={handleTransfer}
              disabled={submitting}
              type="button"
            >
              {submitting ? 'Transferring…' : 'Transfer to Vehicle'}
            </button>
          </>
        )}

        {atParItems.length > 0 && (
          <div>
            <button
              className="sr-at-par-toggle"
              onClick={() => setShowAtPar(v => !v)}
              type="button"
            >
              {showAtPar ? '▲' : '▼'} {atParItems.length} item{atParItems.length !== 1 ? 's' : ''} already at par
            </button>
            {showAtPar && (
              <div className="sr-at-par-list">
                {atParItems.map(item => (
                  <div key={item.item_id} className="sr-at-par-row">
                    <span className="sr-at-par-row__name">{item.item_name}</span>
                    <span className="sr-at-par-row__count">
                      {item.total_quantity} / {item.par_min} min ✓
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  // ── Step 3: Done ─────────────────────────────────────────────────────────

  if (step === 'DONE') {
    const count = result?.transferred?.length ?? 0
    return (
      <div className="sr-panel">
        <div className="sr-success-box">
          <span className="sr-success-box__icon">✓</span>
          <h2 className="sr-success-box__heading">Transfer Complete</h2>
          <p className="sr-success-box__detail">
            {count} item type{count !== 1 ? 's' : ''} moved to Unit {selectedVehicle?.vehicle_number}
          </p>
        </div>

        {result?.errors?.length > 0 && (
          <div className="sr-transfer-errors">
            <p className="sr-transfer-errors__title">Some items could not be transferred:</p>
            {result.errors.map((e, i) => (
              <div key={i} className="sr-transfer-error-item">{e.message}</div>
            ))}
          </div>
        )}

        <button className="btn btn--primary btn--full" onClick={onDone} type="button">
          Done
        </button>
        <button
          className="btn btn--secondary btn--full"
          onClick={() => { setStep('SELECT_VEHICLE'); setResult(null) }}
          type="button"
        >
          Restock Another Vehicle
        </button>
      </div>
    )
  }

  return null
}
