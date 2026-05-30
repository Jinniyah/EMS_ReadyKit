/**
 * modules/admin/components/ItemAssignments.jsx
 *
 * Collapsible assignments panel shown on each item card in ItemCatalog.
 * Displays which vehicle compartments this item is assigned to and
 * allows supervisors to add, edit, or remove assignments.
 *
 * UX principles (tired crew / end-of-shift user):
 *   - Panel is collapsed by default — doesn't clutter the catalog list
 *   - One tap to expand and see all assignments
 *   - Add assignment is a 3-step inline form: vehicle → compartment → quantities
 *   - Each step narrows — compartment list only shows after vehicle is picked
 *   - Edit and Remove are per-row — no navigation required
 *   - Confirmations are inline — no modals to dismiss
 *
 * Props:
 *   item          — the full item object
 *   stationId     — current station (scopes vehicle list)
 *   vehicles      — all vehicles at the station (passed from ItemCatalog)
 */

import React, { useState, useCallback } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import { adminApi } from '../api/adminApi.js'

function QtyBadge({ min, max }) {
  return (
    <span className="assignment-qty">
      Min&nbsp;<strong>{min}</strong>
      &nbsp;·&nbsp;
      Max&nbsp;<strong>{max}</strong>
    </span>
  )
}

function EditRow({ assignment, item, vehicles, onSaved, onCancel }) {
  const { getToken } = useAuth()

  const [vehicleId, setVehicleId]         = useState(String(assignment.vehicle_id ?? ''))
  const [compartmentId, setCompartmentId] = useState(String(assignment.compartment_id ?? ''))
  const [min, setMin]                     = useState(String(assignment.min_quantity))
  const [max, setMax]                     = useState(String(assignment.max_quantity))
  const [error, setError]                 = useState(null)
  const [submitting, setSubmitting]       = useState(false)

  const { data: compartments, isLoading: loadingCompartments } = useApi(
    () => vehicleId ? adminApi.getVehicleCompartments(vehicleId, getToken) : Promise.resolve([]),
    [vehicleId]
  )

  function handleVehicleChange(e) {
    setVehicleId(e.target.value)
    setCompartmentId('')
    setError(null)
  }

  async function handleSave(e) {
    e.preventDefault()
    if (!vehicleId)     { setError('Please select a vehicle.'); return }
    if (!compartmentId) { setError('Please select a compartment.'); return }
    const minN = parseInt(min, 10)
    const maxN = parseInt(max, 10)
    if (isNaN(minN) || minN < 1)    { setError('Min must be at least 1.'); return }
    if (isNaN(maxN) || maxN < minN) { setError('Max must be ≥ min.'); return }

    setSubmitting(true); setError(null)
    try {
      const vehicleChanged     = String(assignment.vehicle_id)     !== vehicleId
      const compartmentChanged = String(assignment.compartment_id) !== compartmentId

      if (vehicleChanged || compartmentChanged) {
        // Move to a different compartment: remove old, create new
        await adminApi.removeParLevel(assignment.par_id, getToken)
        await adminApi.assignItem(item.item_id, {
          vehicle_id:     parseInt(vehicleId, 10),
          compartment_id: parseInt(compartmentId, 10),
          min_quantity:   minN,
          max_quantity:   maxN,
        }, getToken)
      } else {
        // Same compartment — just update quantities
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

  return (
    <form className="assignment-edit-row" onSubmit={handleSave} noValidate>

      {/* Vehicle picker */}
      <div className="assignment-field">
        <label className="assignment-field__label">Vehicle</label>
        <select
          className="assignment-field__select"
          value={vehicleId}
          onChange={handleVehicleChange}
          disabled={submitting}
        >
          <option value="">— Select vehicle —</option>
          {(vehicles ?? []).filter(v => v.active).map(v => (
            <option key={v.vehicle_id} value={v.vehicle_id}>
              {v.vehicle_number} ({v.vehicle_type})
            </option>
          ))}
        </select>
      </div>

      {/* Compartment picker */}
      {vehicleId && (
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

      {/* Quantities */}
      {vehicleId && compartmentId && (
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
          disabled={submitting || !vehicleId || !compartmentId}
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

function AddAssignmentForm({ item, vehicles, onAdded, onCancel }) {
  const { getToken } = useAuth()
  const [vehicleId, setVehicleId]       = useState('')
  const [compartmentId, setCompartmentId] = useState('')
  const [min, setMin]                   = useState('1')
  const [max, setMax]                   = useState('4')
  const [error, setError]               = useState(null)
  const [submitting, setSubmitting]     = useState(false)

  const {
    data: compartments,
    isLoading: loadingCompartments,
  } = useApi(
    () => vehicleId ? adminApi.getVehicleCompartments(vehicleId, getToken) : Promise.resolve([]),
    [vehicleId]
  )

  // Reset compartment when vehicle changes
  function handleVehicleChange(e) {
    setVehicleId(e.target.value)
    setCompartmentId('')
    setError(null)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!vehicleId)     { setError('Please select a vehicle.'); return }
    if (!compartmentId) { setError('Please select a compartment.'); return }
    const minN = parseInt(min, 10)
    const maxN = parseInt(max, 10)
    if (isNaN(minN) || minN < 1)   { setError('Min must be at least 1.'); return }
    if (isNaN(maxN) || maxN < minN) { setError('Max must be ≥ min.'); return }

    setSubmitting(true); setError(null)
    try {
      await adminApi.assignItem(item.item_id, {
        vehicle_id:     parseInt(vehicleId, 10),
        compartment_id: parseInt(compartmentId, 10),
        min_quantity:   minN,
        max_quantity:   maxN,
      }, getToken)
      onAdded()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="add-assignment-form" onSubmit={handleSubmit} noValidate>
      <p className="add-assignment-form__title">Assign to vehicle compartment</p>

      {/* Step 1 — Pick vehicle */}
      <div className="assignment-field">
        <label className="assignment-field__label">Vehicle</label>
        <select
          className="assignment-field__select"
          value={vehicleId}
          onChange={handleVehicleChange}
          disabled={submitting}
        >
          <option value="">— Select vehicle —</option>
          {(vehicles ?? []).filter(v => v.active).map(v => (
            <option key={v.vehicle_id} value={v.vehicle_id}>
              {v.vehicle_number} ({v.vehicle_type})
            </option>
          ))}
        </select>
      </div>

      {/* Step 2 — Pick compartment (only shown after vehicle selected) */}
      {vehicleId && (
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

      {/* Step 3 — Quantities (only shown after compartment selected) */}
      {vehicleId && compartmentId && (
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
          disabled={submitting || !vehicleId || !compartmentId}
        >
          {submitting ? 'Saving…' : 'Assign'}
        </button>
        <button
          type="button"
          className="btn btn--secondary btn--sm"
          onClick={onCancel}
          disabled={submitting}
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

export default function ItemAssignments({ item, stationId, vehicles }) {
  const { getToken } = useAuth()
  const [expanded, setExpanded]         = useState(false)
  const [editingParId, setEditingParId] = useState(null)
  const [showAddForm, setShowAddForm]   = useState(false)
  const [assignmentsKey, setKey]        = useState(0)
  const [removingParId, setRemovingParId] = useState(null)

  const {
    data: assignments,
    isLoading,
    error,
  } = useApi(
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
      await adminApi.removeParLevel(parId, getToken)
      refresh()
    } catch (err) {
      setRemovingParId(null)
      alert(err.message)
    }
  }

  const knownCount  = assignments?.length ?? null  // null = not yet fetched
  const hasAny       = knownCount !== null && knownCount > 0
  const confirmedNone = knownCount === 0

  return (
    <div className="item-assignments">
      <button
        type="button"
        className="item-assignments__toggle"
        onClick={() => setExpanded(v => !v)}
        aria-expanded={expanded}
      >
        <span>
          📍 {expanded
            ? hasAny
              ? `Hide assignments (${knownCount})`
              : 'No compartments assigned'
            : hasAny
              ? `Assigned to ${knownCount} compartment${knownCount !== 1 ? 's' : ''}`
              : confirmedNone
                ? 'No compartments assigned'
                : 'View assignments'}
        </span>
        <span aria-hidden="true">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="item-assignments__panel">
          {isLoading && <p className="assignment-loading">Loading…</p>}
          {error    && <p className="assignment-error">Could not load assignments.</p>}

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
                          onSaved={refresh}
                          onCancel={() => setEditingParId(null)}
                        />
                      ) : (
                        <>
                          <div className="assignment-row__info">
                            <span className="assignment-row__vehicle">
                              {a.vehicle_number}
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
                              onClick={() => setEditingParId(a.par_id)}
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
                  onAdded={refresh}
                  onCancel={() => setShowAddForm(false)}
                />
              ) : (
                <button
                  type="button"
                  className="btn btn--secondary btn--sm item-assignments__add-btn"
                  onClick={() => setShowAddForm(true)}
                >
                  + Assign to vehicle
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
