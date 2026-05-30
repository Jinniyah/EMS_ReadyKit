/**
 * modules/admin/components/VehiclesScreen.jsx
 *
 * Full-screen vehicle and compartment management (ADMIN-UX1-F4 through F7).
 * Replaces the seed script — supervisors can add vehicles and compartments
 * directly from this screen.
 *
 * UX principles (tired crew / 68yo iPhone user):
 *   - Large tap targets throughout (60px min)
 *   - One action at a time — add form replaces the button, not a modal
 *   - Vehicle cards are expandable — scan first, detail on demand
 *   - All inline — zero navigation required
 */

import React, { useState } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import Spinner from '../../../shared/components/Spinner.jsx'
import ErrorBoundary from '../../../shared/components/ErrorBoundary.jsx'
import { adminApi } from '../api/adminApi.js'
import { vehicleApi } from '../../vehicles/api/vehicleApi.js'

const VEHICLE_TYPES = ['ALS', 'BLS', 'QRV']

// ── AddVehicleForm ────────────────────────────────────────────────────────────

function AddVehicleForm({ stationId, onSaved, onCancel }) {
  const { getToken } = useAuth()
  const [vehicleNumber, setVehicleNumber] = useState('')
  const [vehicleType, setVehicleType]     = useState('ALS')
  const [error, setError]                 = useState(null)
  const [saving, setSaving]               = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!vehicleNumber.trim()) { setError('Vehicle number is required.'); return }
    setSaving(true); setError(null)
    try {
      await adminApi.createVehicle({
        station_id:     stationId,
        vehicle_number: vehicleNumber.trim().toUpperCase(),
        vehicle_type:   vehicleType,
        active:         true,
      }, getToken)
      onSaved()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="vehicle-form" onSubmit={handleSubmit} noValidate>
      <h3 className="vehicle-form__title">Add Vehicle</h3>
      <div className="vehicle-form__row">
        <div className="vehicle-form__field">
          <label className="vehicle-form__label">
            Vehicle number <span aria-hidden="true">*</span>
          </label>
          <input
            className="vehicle-form__input"
            value={vehicleNumber}
            onChange={e => setVehicleNumber(e.target.value)}
            placeholder="e.g. AMB-712"
            maxLength={30}
            autoFocus
            disabled={saving}
          />
        </div>
        <div className="vehicle-form__field">
          <label className="vehicle-form__label">Type</label>
          <select
            className="vehicle-form__select"
            value={vehicleType}
            onChange={e => setVehicleType(e.target.value)}
            disabled={saving}
          >
            {VEHICLE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      </div>
      {error && <p className="vehicle-form__error" role="alert">{error}</p>}
      <div className="vehicle-form__actions">
        <button type="submit" className="btn btn--primary btn--full" disabled={saving}>
          {saving ? 'Adding…' : 'Add Vehicle'}
        </button>
        <button type="button" className="btn btn--secondary btn--full"
          onClick={onCancel} disabled={saving}>
          Cancel
        </button>
      </div>
    </form>
  )
}

// ── CompartmentForm ───────────────────────────────────────────────────────────

function CompartmentForm({ locationId, compartment, onSaved, onCancel }) {
  const { getToken } = useAuth()
  const isEdit = !!compartment

  const [form, setForm] = useState({
    name:                compartment?.name                ?? '',
    location_descriptor: compartment?.location_descriptor ?? '',
    sort_order:          String(compartment?.sort_order ?? 0),
    restriction_note:    compartment?.restriction_note    ?? '',
    active:              compartment?.active              ?? true,
  })
  const [error, setError]   = useState(null)
  const [saving, setSaving] = useState(false)

  function set(field, value) { setForm(f => ({ ...f, [field]: value })) }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.name.trim()) { setError('Compartment name is required.'); return }
    setSaving(true); setError(null)
    try {
      const payload = {
        location_id:         locationId,
        name:                form.name.trim(),
        location_descriptor: form.location_descriptor.trim() || null,
        sort_order: (() => { const n = parseInt(form.sort_order, 10); return isNaN(n) ? 0 : n })(),
        restriction_note:    form.restriction_note.trim() || null,
        als_only:            false,
        active:              form.active,
      }
      if (isEdit) {
        await adminApi.updateCompartment(compartment.compartment_id, payload, getToken)
      } else {
        await adminApi.createCompartment(locationId, payload, getToken)
      }
      onSaved()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="compartment-form" onSubmit={handleSubmit} noValidate>
      <h4 className="compartment-form__title">
        {isEdit ? 'Edit Compartment' : 'Add Compartment'}
      </h4>
      <div className="vehicle-form__field">
        <label className="vehicle-form__label">
          Name <span aria-hidden="true">*</span>
        </label>
        <input
          className="vehicle-form__input"
          value={form.name}
          onChange={e => set('name', e.target.value)}
          placeholder="e.g. PC 1 (Airway)"
          maxLength={100}
          autoFocus
          disabled={saving}
        />
      </div>
      <div className="vehicle-form__field">
        <label className="vehicle-form__label">
          Location <span className="vehicle-form__hint-inline">(optional — helps crew find it)</span>
        </label>
        <input
          className="vehicle-form__input"
          value={form.location_descriptor}
          onChange={e => set('location_descriptor', e.target.value)}
          placeholder="e.g. Interior, left side front"
          maxLength={150}
          disabled={saving}
        />
      </div>
      <div className="vehicle-form__row">
        <div className="vehicle-form__field">
          <label className="vehicle-form__label">Sort order</label>
          <input
            className="vehicle-form__input"
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            value={form.sort_order}
            onChange={e => {
              const val = e.target.value.replace(/[^0-9]/g, '')
              set('sort_order', val)
            }}
            disabled={saving}
          />
        </div>
        <div className="vehicle-form__field">
          <label className="vehicle-form__label">
            Access restriction <span className="vehicle-form__hint-inline">(optional)</span>
          </label>
          <input
            className="vehicle-form__input"
            value={form.restriction_note}
            onChange={e => set('restriction_note', e.target.value)}
            placeholder="e.g. ALS crews only"
            maxLength={100}
            disabled={saving}
          />
        </div>
      </div>
      {isEdit && (
        <label className="vehicle-form__toggle-label">
          <input
            type="checkbox"
            checked={form.active}
            onChange={e => set('active', e.target.checked)}
            className="vehicle-form__checkbox"
            disabled={saving}
          />
          <span>Active</span>
        </label>
      )}
      {error && <p className="vehicle-form__error" role="alert">{error}</p>}
      <div className="vehicle-form__actions">
        <button type="submit" className="btn btn--primary btn--full" disabled={saving}>
          {saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Add Compartment'}
        </button>
        <button type="button" className="btn btn--secondary btn--full"
          onClick={onCancel} disabled={saving}>
          Cancel
        </button>
      </div>
    </form>
  )
}

// ── VehicleAdminCard ──────────────────────────────────────────────────────────

function VehicleAdminCard({ vehicle, onVehicleUpdated }) {
  const { getToken } = useAuth()
  const [expanded, setExpanded]           = useState(false)
  const [showAddComp, setShowAddComp]     = useState(false)
  const [editingComp, setEditingComp]     = useState(null)
  const [compsKey, setCompsKey]           = useState(0)
  const [toggling, setToggling]           = useState(false)
  const [showOosForm, setShowOosForm]     = useState(false)
  const [oosReason, setOosReason]         = useState('')
  const [oosError, setOosError]           = useState(null)
  const [showRtsForm, setShowRtsForm]     = useState(false)
  const [rtsComment, setRtsComment]       = useState('')

  // Fetch compartments via admin route (already filtered to vehicle)
  const { data: compartments, isLoading } = useApi(
    () => expanded
      ? adminApi.getVehicleCompartments(vehicle.vehicle_id, getToken)
      : Promise.resolve(null),
    [expanded, compsKey, vehicle.vehicle_id]
  )

  // Fetch this vehicle's inventory location_id (needed for compartment creation)
  const { data: locations } = useApi(
    () => expanded
      ? adminApi.getVehicleLocation(vehicle.station_id, getToken)
      : Promise.resolve(null),
    [expanded, vehicle.station_id]
  )
  const locationId = locations?.find(l => l.vehicle_id === vehicle.vehicle_id)?.location_id ?? null

  function refreshComps() {
    setCompsKey(k => k + 1)
    setShowAddComp(false)
    setEditingComp(null)
  }

  async function handleMarkOutOfService(e) {
    e.preventDefault()
    if (!oosReason.trim()) { setOosError('A reason is required.'); return }
    setToggling(true); setOosError(null)
    try {
      await adminApi.updateVehicle(vehicle.vehicle_id, {
        active:          false,
        inactive_reason: oosReason.trim(),
      }, getToken)
      setShowOosForm(false)
      setOosReason('')
      onVehicleUpdated()
    } catch (err) {
      setOosError(err.message)
    } finally {
      setToggling(false)
    }
  }

  async function handleReturnToService(e) {
    e.preventDefault()
    setToggling(true)
    try {
      await adminApi.updateVehicle(vehicle.vehicle_id, {
        active:          true,
        inactive_reason: rtsComment.trim() || null,
      }, getToken)
      setShowRtsForm(false)
      setRtsComment('')
      onVehicleUpdated()
    } catch (err) {
      alert(err.message)
    } finally {
      setToggling(false)
    }
  }

  return (
    <div className={`admin-vehicle-card ${!vehicle.active ? 'admin-vehicle-card--inactive' : ''}`}>

      <button
        className="admin-vehicle-card__header"
        onClick={() => setExpanded(v => !v)}
        type="button"
        aria-expanded={expanded}
      >
        <div className="admin-vehicle-card__info">
          <span className="admin-vehicle-card__number">{vehicle.vehicle_number}</span>
          <span className="admin-vehicle-card__type">{vehicle.vehicle_type}</span>
          {!vehicle.active && (
            <span className="admin-vehicle-card__inactive-badge">Out of service</span>
          )}
        </div>
        <span aria-hidden="true">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="admin-vehicle-card__body">

          {/* Vehicle service toggle */}
          <div className="admin-vehicle-card__actions">
            {vehicle.active ? (
              showOosForm ? (
                <form
                  className="oos-form"
                  onSubmit={handleMarkOutOfService}
                  noValidate
                >
                  <label className="oos-form__label">
                    Reason for taking out of service <span aria-hidden="true">*</span>
                  </label>
                  <input
                    className="oos-form__input"
                    value={oosReason}
                    onChange={e => { setOosReason(e.target.value); setOosError(null) }}
                    placeholder="e.g. Scheduled maintenance, mechanical failure…"
                    maxLength={200}
                    autoFocus
                    disabled={toggling}
                  />
                  {oosError && (
                    <p className="vehicle-form__error" role="alert">{oosError}</p>
                  )}
                  <div className="oos-form__actions">
                    <button
                      type="submit"
                      className="btn btn--primary btn--sm"
                      disabled={toggling}
                    >
                      {toggling ? 'Saving…' : 'Confirm'}
                    </button>
                    <button
                      type="button"
                      className="btn btn--secondary btn--sm"
                      onClick={() => { setShowOosForm(false); setOosReason(''); setOosError(null) }}
                      disabled={toggling}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  onClick={() => setShowOosForm(true)}
                >
                  Mark Out of Service
                </button>
              )
            ) : (
              <>
                {vehicle.inactive_reason && (
                  <p className="oos-reason">
                    <strong>Reason:</strong> {vehicle.inactive_reason}
                  </p>
                )}
                {showRtsForm ? (
                  <form className="oos-form" onSubmit={handleReturnToService} noValidate>
                    <label className="oos-form__label">
                      Return to service note
                      <span className="oos-form__optional"> (optional)</span>
                    </label>
                    <input
                      className="oos-form__input"
                      value={rtsComment}
                      onChange={e => setRtsComment(e.target.value)}
                      placeholder="e.g. Maintenance complete, ready for service…"
                      maxLength={200}
                      autoFocus
                      disabled={toggling}
                    />
                    <div className="oos-form__actions">
                      <button
                        type="submit"
                        className="btn btn--primary btn--sm"
                        disabled={toggling}
                      >
                        {toggling ? 'Saving…' : 'Confirm'}
                      </button>
                      <button
                        type="button"
                        className="btn btn--secondary btn--sm"
                        onClick={() => { setShowRtsForm(false); setRtsComment('') }}
                        disabled={toggling}
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                ) : (
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    onClick={() => setShowRtsForm(true)}
                  >
                    Return to Service
                  </button>
                )}
              </>
            )}
          </div>

          {/* Compartments */}
          <div className="admin-vehicle-card__section">
            <div className="admin-vehicle-card__section-header">
              <h4 className="admin-vehicle-card__section-title">
                Compartments
                {compartments && (
                  <span className="admin-vehicle-card__comp-count">
                    {' '}({compartments.filter(c => c.active).length} active)
                  </span>
                )}
              </h4>
              {!showAddComp && !editingComp && locationId && (
                <button
                  type="button"
                  className="btn btn--primary btn--sm"
                  onClick={() => setShowAddComp(true)}
                >
                  + Add
                </button>
              )}
            </div>

            {isLoading && <Spinner label="Loading compartments…" size="sm" />}

            {showAddComp && locationId && (
              <ErrorBoundary moduleName="Add Compartment">
                <CompartmentForm
                  locationId={locationId}
                  compartment={null}
                  onSaved={refreshComps}
                  onCancel={() => setShowAddComp(false)}
                />
              </ErrorBoundary>
            )}

            {!isLoading && !showAddComp && (
              <ul className="admin-compartment-list">
                {(compartments ?? []).length === 0 ? (
                  <li className="admin-compartment-empty">
                    No compartments yet — tap "+ Add" to create the first one.
                  </li>
                ) : (
                  compartments.map(comp => (
                    <li
                      key={comp.compartment_id}
                      className={`admin-compartment-row ${!comp.active ? 'admin-compartment-row--inactive' : ''}`}
                    >
                      {editingComp?.compartment_id === comp.compartment_id ? (
                        <ErrorBoundary moduleName="Edit Compartment">
                          <CompartmentForm
                            locationId={locationId}
                            compartment={comp}
                            onSaved={refreshComps}
                            onCancel={() => setEditingComp(null)}
                          />
                        </ErrorBoundary>
                      ) : (
                        <>
                          <div className="admin-compartment-row__info">
                            <span className="admin-compartment-row__name">{comp.name}</span>
                            {comp.location_descriptor && (
                              <span className="admin-compartment-row__descriptor">
                                {comp.location_descriptor}
                              </span>
                            )}
                            {comp.restriction_note && (
                              <span className="admin-compartment-row__restriction">
                                🔒 {comp.restriction_note}
                              </span>
                            )}
                            {!comp.active && (
                              <span className="admin-compartment-row__inactive">Inactive</span>
                            )}
                          </div>
                          <button
                            type="button"
                            className="btn btn--secondary btn--sm"
                            onClick={() => { setEditingComp(comp); setShowAddComp(false) }}
                          >
                            Edit
                          </button>
                        </>
                      )}
                    </li>
                  ))
                )}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── VehiclesScreen ────────────────────────────────────────────────────────────

export default function VehiclesScreen({ station, onBack }) {
  const { getToken } = useAuth()
  const [showAddVehicle, setShowAddVehicle] = useState(false)
  const [vehiclesKey, setVehiclesKey]       = useState(0)
  const [showInactive, setShowInactive]     = useState(false)

  const { data: vehicles, isLoading, error } = useApi(
    () => vehicleApi.getStationVehicles(station.station_id, getToken),
    [vehiclesKey, station.station_id]
  )

  const displayed = (vehicles ?? []).filter(v => showInactive || v.active)

  function refresh() {
    setVehiclesKey(k => k + 1)
    setShowAddVehicle(false)
  }

  return (
    <div className="admin-subscreen">
      <div className="admin-subscreen__header">
        <button className="admin-screen__back" onClick={onBack} type="button">
          ← Back
        </button>
        <div>
          <h2 className="admin-subscreen__title">Vehicles</h2>
          <p className="admin-subscreen__station">{station.name}</p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="admin-subscreen__toolbar">
        {!showAddVehicle && (
          <button
            type="button"
            className="btn btn--primary btn--full"
            onClick={() => setShowAddVehicle(true)}
          >
            + Add Vehicle
          </button>
        )}
        <label className="vehicle-inactive-toggle">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={e => setShowInactive(e.target.checked)}
          />
          Show out-of-service vehicles
        </label>
      </div>

      {/* Add vehicle form */}
      {showAddVehicle && (
        <ErrorBoundary moduleName="Add Vehicle">
          <AddVehicleForm
            stationId={station.station_id}
            onSaved={refresh}
            onCancel={() => setShowAddVehicle(false)}
          />
        </ErrorBoundary>
      )}

      {/* Vehicle list */}
      {isLoading ? (
        <Spinner label="Loading vehicles…" />
      ) : error ? (
        <div className="admin-screen__error" role="alert">⚠ {error.message}</div>
      ) : displayed.length === 0 ? (
        <div className="admin-vehicles__empty">
          {showInactive
            ? 'No vehicles at this station yet.'
            : 'No active vehicles. Tap "+ Add Vehicle" to add one.'}
        </div>
      ) : (
        <div className="admin-vehicles-list">
          {displayed.map(v => (
            <ErrorBoundary key={v.vehicle_id} moduleName={`Vehicle ${v.vehicle_number}`}>
              <VehicleAdminCard vehicle={v} onVehicleUpdated={refresh} />
            </ErrorBoundary>
          ))}
        </div>
      )}
    </div>
  )
}
