/**
 * modules/admin/components/ItemAssignments.jsx
 *
 * Collapsible assignments panel shown on each item card in ItemCatalog.
 * Displays which compartments this item is assigned to (vehicle, jump bag,
 * or station supply room) and allows supervisors to add, edit, or remove
 * assignments.
 *
 * ITM-6: "Where" picker replaced the vehicle-only select. The backend
 * POST /admin/items/{id}/assign accepts either vehicle_id (vehicle) or
 * location_id (jump bag / supply room) — the frontend now exposes all three.
 *
 * UX principles (tired crew / end-of-shift user):
 *   - Panel is collapsed by default — doesn't clutter the catalog list
 *   - Count shown on toggle immediately — no need to expand to see if assigned
 *   - Add assignment is a 3-step inline form: where → compartment → quantities
 *   - Each step narrows — compartment list only shown after location is picked
 *   - Edit and Remove are per-row — no navigation required
 *   - Confirmations are inline — no modals to dismiss
 *
 * Props:
 *   item          — the full item object
 *   stationId     — current station (scopes vehicle list)
 *   vehicles      — all vehicles at the station (passed from ItemCatalog)
 *   locations     — all inventory locations at the station (jump bags + supply room)
 */

import React, { useState, useCallback, useEffect } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import { adminApi } from '../api/adminApi.js'

// ── QtyBadge ─────────────────────────────────────────────────────────────────

function QtyBadge({ min, max }) {
  return (
    <span className="assignment-qty">
      Min&nbsp;<strong>{min}</strong>
      &nbsp;·&nbsp;
      Max&nbsp;<strong>{max}</strong>
    </span>
  )
}

// ── Derive location type from an existing assignment ──────────────────────────

function deriveLocType(assignment, locations) {
  if (assignment.vehicle_id != null) return 'vehicle'
  const loc = (locations ?? []).find(l => l.location_id === assignment.location_id)
  return loc?.location_type === 'JUMP_BAG' ? 'jump_bag' : 'supply_room'
}

// ── EditRow ───────────────────────────────────────────────────────────────────

function EditRow({ assignment, item, vehicles, locations, onSaved, onCancel }) {
  const { getToken } = useAuth()

  const jumpBags   = (locations ?? []).filter(l => l.location_type === 'JUMP_BAG' && !l.retired_at)
  const supplyRoom = (locations ?? []).find(l => l.location_type === 'STATION_SUPPLY_ROOM' && !l.retired_at)

  const initLocType = deriveLocType(assignment, locations)

  const [locType, setLocType]           = useState(initLocType)
  const [vehicleId, setVehicleId]       = useState(String(assignment.vehicle_id ?? ''))
  const [locationId, setLocationId]     = useState(initLocType !== 'vehicle' ? String(assignment.location_id ?? '') : '')
  const [compartmentId, setCompartmentId] = useState(String(assignment.compartment_id ?? ''))
  const [min, setMin]                   = useState(String(assignment.min_quantity))
  const [max, setMax]                   = useState(String(assignment.max_quantity))
  const [error, setError]               = useState(null)
  const [submitting, setSubmitting]     = useState(false)

  // Auto-select supply room when that type is chosen
  useEffect(() => {
    if (locType === 'supply_room' && supplyRoom) {
      setLocationId(String(supplyRoom.location_id))
    }
  }, [locType, supplyRoom?.location_id])

  const { data: compartments, isLoading: loadingCompartments } = useApi(
    () => {
      if (locType === 'vehicle' && vehicleId) return adminApi.getVehicleCompartments(vehicleId, getToken)
      if (locType !== 'vehicle' && locationId) return adminApi.getLocationCompartments(locationId, getToken)
      return Promise.resolve([])
    },
    [locType, vehicleId, locationId]
  )

  function handleLocTypeChange(e) {
    setLocType(e.target.value)
    setVehicleId('')
    setLocationId('')
    setCompartmentId('')
    setError(null)
  }

  function handleVehicleOrLocationChange(e) {
    if (locType === 'vehicle') setVehicleId(e.target.value)
    else setLocationId(e.target.value)
    setCompartmentId('')
    setError(null)
  }

  async function handleSave(e) {
    e.preventDefault()
    const hasLocation = locType === 'vehicle' ? !!vehicleId : !!locationId
    if (!hasLocation)    { setError('Please select a location.'); return }
    if (!compartmentId)  { setError('Please select a compartment.'); return }
    const minN = parseInt(min, 10)
    const maxN = parseInt(max, 10)
    if (isNaN(minN) || minN < 1)    { setError('Min must be at least 1.'); return }
    if (isNaN(maxN) || maxN < minN) { setError('Max must be ≥ min.'); return }

    setSubmitting(true); setError(null)
    try {
      const vehicleChanged     = locType === 'vehicle' && String(assignment.vehicle_id) !== vehicleId
      const locationChanged    = locType !== 'vehicle' && String(assignment.location_id) !== locationId
      const compartmentChanged = String(assignment.compartment_id) !== compartmentId
      const typeChanged        = deriveLocType(assignment, locations) !== locType

      if (vehicleChanged || locationChanged || compartmentChanged || typeChanged) {
        // Moving to a different location/compartment: deactivate old, create new
        await adminApi.deactivateParLevel(assignment.par_id, getToken)
        const payload = {
          compartment_id: parseInt(compartmentId, 10),
          min_quantity:   minN,
          max_quantity:   maxN,
        }
        if (locType === 'vehicle') payload.vehicle_id  = parseInt(vehicleId,  10)
        else                       payload.location_id = parseInt(locationId, 10)
        await adminApi.assignItem(item.item_id, payload, getToken)
      } else {
        // Same location/compartment — just update quantities
        await adminApi.updateParLevel(assignment.par_id, {
          min_quantity: minN,
          max_quantity: maxN,
        }, getToken)
      }
      onSaved()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const pickerValue     = locType === 'vehicle' ? vehicleId : locationId
  const hasPickerValue  = !!pickerValue

  return (
    <form className="assignment-edit-row" onSubmit={handleSave} noValidate>

      {/* Step 1 — Where (location type) */}
      <div className="assignment-field">
        <label className="assignment-field__label">Where</label>
        <select
          className="assignment-field__select"
          value={locType}
          onChange={handleLocTypeChange}
          disabled={submitting}
        >
          <option value="vehicle">Vehicle</option>
          {jumpBags.length > 0 && <option value="jump_bag">Jump Bag</option>}
          {supplyRoom && <option value="supply_room">Station Supply Room</option>}
        </select>
      </div>

      {/* Step 2 — Pick specific vehicle or jump bag (supply room auto-selects) */}
      {locType === 'vehicle' && (
        <div className="assignment-field">
          <label className="assignment-field__label">Vehicle</label>
          <select
            className="assignment-field__select"
            value={vehicleId}
            onChange={handleVehicleOrLocationChange}
            disabled={submitting}
          >
            <option value="">— Select vehicle —</option>
            {(vehicles ?? []).filter(v => v.active && !v.retired_at).map(v => (
              <option key={v.vehicle_id} value={v.vehicle_id}>
                {v.vehicle_number} ({v.vehicle_type})
              </option>
            ))}
          </select>
        </div>
      )}

      {locType === 'jump_bag' && (
        <div className="assignment-field">
          <label className="assignment-field__label">Jump Bag</label>
          <select
            className="assignment-field__select"
            value={locationId}
            onChange={handleVehicleOrLocationChange}
            disabled={submitting}
          >
            <option value="">— Select jump bag —</option>
            {jumpBags.map(l => (
              <option key={l.location_id} value={l.location_id}>
                {l.label}
              </option>
            ))}
          </select>
        </div>
      )}

      {locType === 'supply_room' && supplyRoom && (
        <p className="assignment-location-label">{supplyRoom.label}</p>
      )}

      {/* Step 3 — Pick compartment */}
      {hasPickerValue && (
        <div className="assignment-field">
          <label className="assignment-field__label">Compartment</label>
          {loadingCompartments ? (
            <p className="assignment-loading">Loading compartments…</p>
          ) : (
            <select
              className="assignment-field__select"
              value={compartmentId}
              onChange={e => setCompartmentId(e.target.value)}
              disabled={submitting}
            >
              <option value="">— Select compartment —</option>
              {(compartments ?? []).map(c => (
                <option key={c.compartment_id} value={c.compartment_id}>
                  {c.name}{c.restriction_note ? ` (${c.restriction_note})` : ''}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {/* Step 4 — Quantities */}
      {hasPickerValue && compartmentId && (
        <div className="assignment-edit-fields">
          <label className="assignment-edit-label">
            Needs at least
            <input
              className="assignment-edit-input"
              type="number" min={1} value={min}
              onChange={e => setMin(e.target.value)}
              disabled={submitting}
            />
          </label>
          <label className="assignment-edit-label">
            Restock to
            <input
              className="assignment-edit-input"
              type="number" min={1} value={max}
              onChange={e => setMax(e.target.value)}
              disabled={submitting}
            />
          </label>
        </div>
      )}

      {error && <p className="assignment-error" role="alert">{error}</p>}

      <div className="assignment-edit-actions">
        <button
          type="submit"
          className="btn btn--primary btn--sm"
          disabled={submitting || !hasPickerValue || !compartmentId}
        >
          {submitting ? 'Saving…' : 'Save'}
        </button>
        <button type="button" className="btn btn--secondary btn--sm"
          onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>
    </form>
  )
}

// ── AddAssignmentForm ─────────────────────────────────────────────────────────

function AddAssignmentForm({ item, vehicles, locations, onAdded, onCancel }) {
  const { getToken } = useAuth()

  const jumpBags   = (locations ?? []).filter(l => l.location_type === 'JUMP_BAG' && !l.retired_at)
  const supplyRoom = (locations ?? []).find(l => l.location_type === 'STATION_SUPPLY_ROOM' && !l.retired_at)

  const [locType, setLocType]             = useState('vehicle')
  const [vehicleId, setVehicleId]         = useState('')
  const [locationId, setLocationId]       = useState('')
  const [compartmentId, setCompartmentId] = useState('')
  const [min, setMin]                     = useState('1')
  const [max, setMax]                     = useState('4')
  const [error, setError]                 = useState(null)
  const [submitting, setSubmitting]       = useState(false)

  // Auto-select supply room when that type is chosen
  useEffect(() => {
    if (locType === 'supply_room' && supplyRoom) {
      setLocationId(String(supplyRoom.location_id))
    }
  }, [locType, supplyRoom?.location_id])

  const { data: compartments, isLoading: loadingCompartments } = useApi(
    () => {
      if (locType === 'vehicle' && vehicleId) return adminApi.getVehicleCompartments(vehicleId, getToken)
      if (locType !== 'vehicle' && locationId) return adminApi.getLocationCompartments(locationId, getToken)
      return Promise.resolve([])
    },
    [locType, vehicleId, locationId]
  )

  function handleLocTypeChange(e) {
    setLocType(e.target.value)
    setVehicleId('')
    setLocationId('')
    setCompartmentId('')
    setError(null)
  }

  function handleVehicleOrLocationChange(e) {
    if (locType === 'vehicle') setVehicleId(e.target.value)
    else setLocationId(e.target.value)
    setCompartmentId('')
    setError(null)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const hasLocation = locType === 'vehicle' ? !!vehicleId : !!locationId
    if (!hasLocation)   { setError('Please select a location.'); return }
    if (!compartmentId) { setError('Please select a compartment.'); return }
    const minN = parseInt(min, 10)
    const maxN = parseInt(max, 10)
    if (isNaN(minN) || minN < 1)    { setError('Min must be at least 1.'); return }
    if (isNaN(maxN) || maxN < minN) { setError('Max must be ≥ min.'); return }

    setSubmitting(true); setError(null)
    try {
      const payload = {
        compartment_id: parseInt(compartmentId, 10),
        min_quantity:   minN,
        max_quantity:   maxN,
      }
      if (locType === 'vehicle') payload.vehicle_id  = parseInt(vehicleId,  10)
      else                       payload.location_id = parseInt(locationId, 10)
      await adminApi.assignItem(item.item_id, payload, getToken)
      onAdded()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const pickerValue    = locType === 'vehicle' ? vehicleId : locationId
  const hasPickerValue = !!pickerValue

  return (
    <form className="add-assignment-form" onSubmit={handleSubmit} noValidate>
      <p className="add-assignment-form__title">Add assignment</p>

      {/* Step 1 — Where (location type) */}
      <div className="assignment-field">
        <label className="assignment-field__label">Where</label>
        <select
          className="assignment-field__select"
          value={locType}
          onChange={handleLocTypeChange}
          disabled={submitting}
        >
          <option value="vehicle">Vehicle</option>
          {jumpBags.length > 0 && <option value="jump_bag">Jump Bag</option>}
          {supplyRoom && <option value="supply_room">Station Supply Room</option>}
        </select>
      </div>

      {/* Step 2 — Pick specific vehicle or jump bag */}
      {locType === 'vehicle' && (
        <div className="assignment-field">
          <label className="assignment-field__label">Vehicle</label>
          <select
            className="assignment-field__select"
            value={vehicleId}
            onChange={handleVehicleOrLocationChange}
            disabled={submitting}
          >
            <option value="">— Select vehicle —</option>
            {(vehicles ?? []).filter(v => v.active && !v.retired_at).map(v => (
              <option key={v.vehicle_id} value={v.vehicle_id}>
                {v.vehicle_number} ({v.vehicle_type})
              </option>
            ))}
          </select>
        </div>
      )}

      {locType === 'jump_bag' && (
        <div className="assignment-field">
          <label className="assignment-field__label">Jump Bag</label>
          <select
            className="assignment-field__select"
            value={locationId}
            onChange={handleVehicleOrLocationChange}
            disabled={submitting}
          >
            <option value="">— Select jump bag —</option>
            {jumpBags.map(l => (
              <option key={l.location_id} value={l.location_id}>
                {l.label}
              </option>
            ))}
          </select>
        </div>
      )}

      {locType === 'supply_room' && supplyRoom && (
        <p className="assignment-location-label">{supplyRoom.label}</p>
      )}

      {/* Step 3 — Pick compartment */}
      {hasPickerValue && (
        <div className="assignment-field">
          <label className="assignment-field__label">Compartment</label>
          {loadingCompartments ? (
            <p className="assignment-loading">Loading compartments…</p>
          ) : (
            <select
              className="assignment-field__select"
              value={compartmentId}
              onChange={e => setCompartmentId(e.target.value)}
              disabled={submitting}
            >
              <option value="">— Select compartment —</option>
              {(compartments ?? []).map(c => (
                <option key={c.compartment_id} value={c.compartment_id}>
                  {c.name}{c.restriction_note ? ` (${c.restriction_note})` : ''}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {/* Step 4 — Quantities */}
      {hasPickerValue && compartmentId && (
        <div className="assignment-qty-row">
          <label className="assignment-edit-label">
            Needs at least
            <input
              className="assignment-edit-input"
              type="number" min={1} value={min}
              onChange={e => setMin(e.target.value)}
              disabled={submitting}
            />
          </label>
          <label className="assignment-edit-label">
            Restock to
            <input
              className="assignment-edit-input"
              type="number" min={1} value={max}
              onChange={e => setMax(e.target.value)}
              disabled={submitting}
            />
          </label>
        </div>
      )}

      {error && <p className="assignment-error" role="alert">{error}</p>}

      <div className="assignment-edit-actions">
        <button
          type="submit"
          className="btn btn--primary btn--sm"
          disabled={submitting || !hasPickerValue || !compartmentId}
        >
          {submitting ? 'Saving…' : 'Assign'}
        </button>
        <button type="button" className="btn btn--secondary btn--sm"
          onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>
    </form>
  )
}

// ── ItemAssignments ───────────────────────────────────────────────────────────

export default function ItemAssignments({ item, stationId, vehicles, locations, initialCount = null }) {
  const { getToken } = useAuth()
  const [expanded, setExpanded]           = useState(false)
  const [editingParId, setEditingParId]   = useState(null)
  const [showAddForm, setShowAddForm]     = useState(false)
  const [assignmentsKey, setKey]          = useState(0)
  const [removingParId, setRemovingParId] = useState(null)

  // ── Full assignment list (lazy — only fetched when expanded) ─────────────
  const { data: assignments, isLoading, error } = useApi(
    () => expanded ? adminApi.getItemAssignments(item.item_id, getToken) : Promise.resolve(null),
    [expanded, assignmentsKey, item.item_id]
  )

  const refresh = useCallback(() => {
    setKey(k => k + 1)
    setEditingParId(null)
    setShowAddForm(false)
    setRemovingParId(null)
  }, [])

  async function handleRemove(parId) {
    setRemovingParId(parId)
    try {
      await adminApi.deactivateParLevel(parId, getToken)
      refresh()
    } catch (err) {
      setRemovingParId(null)
      alert(err.message)
    }
  }

  // ── Toggle label ──────────────────────────────────────────────────────────
  const liveCount = assignments?.length ?? null
  const count     = liveCount ?? initialCount

  function toggleLabel() {
    if (expanded) {
      if (count === null) return 'Assignments'
      if (count === 0)    return 'No compartments assigned'
      return `Hide assignments (${count})`
    }
    if (count === null) return 'View assignments'
    if (count === 0)    return 'No compartments assigned'
    return `Assigned to ${count} compartment${count !== 1 ? 's' : ''}`
  }

  return (
    <div className="item-assignments">
      <button
        type="button"
        className="item-assignments__toggle"
        onClick={() => setExpanded(v => !v)}
        aria-expanded={expanded}
        aria-label={`${item.name}: ${toggleLabel()}`}
      >
        <span>📍 {toggleLabel()}</span>
        <span aria-hidden="true">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="item-assignments__panel">
          {isLoading && <p className="assignment-loading">Loading…</p>}
          {error    && <p className="assignment-error" role="alert">Could not load assignments.</p>}

          {!isLoading && !error && (
            <>
              {(assignments ?? []).length === 0 ? (
                <p className="assignment-empty">Not assigned to any compartments yet.</p>
              ) : (
                <ul className="assignment-list">
                  {assignments.map(a => (
                    <li key={a.par_id} className="assignment-row">
                      {editingParId === a.par_id ? (
                        <EditRow
                          assignment={a}
                          item={item}
                          vehicles={vehicles}
                          locations={locations}
                          onSaved={refresh}
                          onCancel={() => setEditingParId(null)}
                        />
                      ) : (
                        <>
                          <div className="assignment-row__info">
                            <span className="assignment-row__vehicle">
                              {a.vehicle_number ?? a.location_label ?? 'Unknown'}
                            </span>
                            <span className="assignment-row__sep">›</span>
                            <span className="assignment-row__compartment">
                              {a.compartment_name ?? 'Unknown compartment'}
                            </span>
                            <QtyBadge min={a.min_quantity} max={a.max_quantity} />
                          </div>
                          <div className="assignment-row__actions">
                            <button
                              type="button"
                              className="btn btn--secondary btn--sm"
                              onClick={() => { setEditingParId(a.par_id); setShowAddForm(false) }}
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              className="assignment-remove-btn"
                              onClick={() => handleRemove(a.par_id)}
                              disabled={removingParId === a.par_id}
                              aria-label={`Remove ${item.name} from ${a.compartment_name}`}
                            >
                              {removingParId === a.par_id ? '…' : '✕'}
                            </button>
                          </div>
                        </>
                      )}
                    </li>
                  ))}
                </ul>
              )}

              {showAddForm ? (
                <AddAssignmentForm
                  item={item}
                  vehicles={vehicles}
                  locations={locations}
                  onAdded={refresh}
                  onCancel={() => setShowAddForm(false)}
                />
              ) : (
                <button
                  type="button"
                  className="btn btn--secondary btn--sm item-assignments__add-btn"
                  onClick={() => { setShowAddForm(true); setEditingParId(null) }}
                >
                  + Add assignment
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
