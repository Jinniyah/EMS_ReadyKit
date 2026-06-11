/**
 * settings/components/VehicleManagementSection.jsx
 * S-F7: Vehicle management in Settings — list vehicles + retire action (RET-F1).
 * Also lists portable locations (jump bags) with retire action (RET-F2).
 * Admin only.
 */
import React, { useState } from 'react'
import { useApi } from '../../../shared/hooks/useApi.js'
import { retirementApi } from '../api/retirementApi.js'
import Spinner from '../../../shared/components/Spinner.jsx'

function RetireConfirmSheet({ name, onConfirm, onCancel, saving, error }) {
  const [reason, setReason] = useState('')
  return (
    <div className="ems-confirm-overlay" role="dialog" aria-modal="true">
      <div className="ems-confirm-sheet">
        <p className="ems-confirm-sheet__title">Retire {name}?</p>
        <p className="ems-confirm-sheet__desc">
          This permanently marks the item as retired. It will be hidden from active lists.
          This action cannot be undone.
        </p>
        <textarea
          placeholder="Reason for retirement (required)"
          value={reason}
          onChange={e => setReason(e.target.value)}
          maxLength={500}
        />
        {error && <p className="ems-confirm-sheet__error">{error}</p>}
        <div className="ems-confirm-sheet__actions">
          <button className="ems-confirm-sheet__cancel" onClick={onCancel} type="button">
            Cancel
          </button>
          <button
            className="ems-confirm-sheet__confirm"
            onClick={() => onConfirm(reason)}
            disabled={!reason.trim() || saving}
            type="button"
          >
            {saving ? 'Retiring…' : 'Retire'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function VehicleManagementSection({ station, getToken, onRefresh }) {
  const [vehicleKey, setVehicleKey] = useState(0)
  const [locationKey, setLocationKey] = useState(0)
  const [retireTarget, setRetireTarget] = useState(null)
  const [retiring, setRetiring] = useState(false)
  const [retireError, setRetireError] = useState(null)

  const { data: vehicles, isLoading: vLoad, error: vErr } = useApi(
    () => retirementApi.getStationVehicles(station.station_id, getToken),
    [station.station_id, vehicleKey]
  )

  const { data: locations, isLoading: lLoad, error: lErr } = useApi(
    () => retirementApi.getStationLocations(station.station_id, getToken),
    [station.station_id, locationKey]
  )

  const activeVehicles  = (vehicles  ?? []).filter(v => !v.retired_at)
  const activeLocations = (locations ?? []).filter(l => !l.retired_at)

  async function handleRetire(reason) {
    if (!reason.trim()) return
    setRetiring(true)
    setRetireError(null)
    try {
      if (retireTarget.kind === 'vehicle') {
        await retirementApi.retireVehicle(retireTarget.id, reason, getToken)
        setVehicleKey(k => k + 1)
      } else {
        await retirementApi.retireLocation(retireTarget.id, reason, getToken)
        setLocationKey(k => k + 1)
      }
      setRetireTarget(null)
      if (onRefresh) onRefresh()
    } catch (e) {
      setRetireError(e.message)
    } finally {
      setRetiring(false)
    }
  }

  return (
    <>
      {retireTarget && (
        <RetireConfirmSheet
          name={retireTarget.name}
          onConfirm={handleRetire}
          onCancel={() => { setRetireTarget(null); setRetireError(null) }}
          saving={retiring}
          error={retireError}
        />
      )}

      <div className="settings-section">
        <h2 className="settings-section__heading">Vehicles</h2>

        {vLoad ? (
          <Spinner label="Loading vehicles…" />
        ) : vErr ? (
          <p className="settings-section__empty">Could not load vehicles.</p>
        ) : activeVehicles.length === 0 ? (
          <p className="settings-section__empty">No active vehicles.</p>
        ) : (
          activeVehicles.map(v => (
            <div key={v.vehicle_id} className="settings-row">
              <div className="settings-row__content">
                <div className="settings-row__label">{v.vehicle_number}</div>
                <div className="settings-row__description">{v.vehicle_type}{!v.active ? ' — Out of Service' : ''}</div>
              </div>
              <div className="settings-row__control">
                <button
                  className="settings-retire-btn"
                  onClick={() => setRetireTarget({ kind: 'vehicle', id: v.vehicle_id, name: v.vehicle_number })}
                  type="button"
                >
                  Retire
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {(lLoad || (activeLocations && activeLocations.length > 0)) && (
        <div className="settings-section">
          <h2 className="settings-section__heading">Portable Locations</h2>

          {lLoad ? (
            <Spinner label="Loading locations…" />
          ) : lErr ? (
            <p className="settings-section__empty">Could not load locations.</p>
          ) : activeLocations.length === 0 ? (
            <p className="settings-section__empty">No active portable locations.</p>
          ) : (
            activeLocations.map(loc => (
              <div key={loc.location_id} className="settings-row">
                <div className="settings-row__content">
                  <div className="settings-row__label">{loc.label}</div>
                  <div className="settings-row__description">{loc.location_type}</div>
                </div>
                <div className="settings-row__control">
                  <button
                    className="settings-retire-btn"
                    onClick={() => setRetireTarget({ kind: 'location', id: loc.location_id, name: loc.label })}
                    type="button"
                  >
                    Retire
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </>
  )
}
