/**
 * modules/admin/components/CompartmentParLevels.jsx
 *
 * Vehicle-centric par level management embedded inside each compartment row
 * in VehiclesScreen. Complements the item-centric view in ItemAssignments —
 * same API calls, same UX patterns, different navigation starting point.
 *
 * Reuses: adminApi.assignItem / updateParLevel / deactivateParLevel,
 *         ItemSearchCombobox, and the CSS classes from ItemAssignments.
 */

import React, { useState, useCallback } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import { adminApi } from '../api/adminApi.js'
import ItemSearchCombobox from '../../../shared/components/ItemSearchCombobox.jsx'

// ── QtyBadge ──────────────────────────────────────────────────────────────────

function QtyBadge({ min, max }) {
  return (
    <span className="assignment-qty">
      Min&nbsp;<strong>{min}</strong>
      &nbsp;·&nbsp;
      Max&nbsp;<strong>{max}</strong>
    </span>
  )
}

// ── EditCompartmentParRow ─────────────────────────────────────────────────────
// Simpler than ItemAssignments/EditRow — vehicle and compartment are already
// known from context, so this only edits the quantities.

function EditCompartmentParRow({ assignment, onSaved, onCancel }) {
  const { getToken } = useAuth()
  const [min, setMin]           = useState(String(assignment.min_quantity))
  const [max, setMax]           = useState(String(assignment.max_quantity))
  const [error, setError]       = useState(null)
  const [submitting, setSub]    = useState(false)

  async function handleSave(e) {
    e.preventDefault()
    const minN = parseInt(min, 10)
    const maxN = parseInt(max, 10)
    if (isNaN(minN) || minN < 1)    { setError('Min must be at least 1.'); return }
    if (isNaN(maxN) || maxN < minN) { setError('Max must be ≥ min.'); return }
    setSub(true); setError(null)
    try {
      await adminApi.updateParLevel(assignment.par_id, {
        min_quantity: minN,
        max_quantity: maxN,
      }, getToken)
      onSaved()
    } catch (err) {
      setError(err.message)
    } finally {
      setSub(false)
    }
  }

  return (
    <form className="assignment-edit-row" onSubmit={handleSave} noValidate>
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
      {error && <p className="assignment-error" role="alert">{error}</p>}
      <div className="assignment-edit-actions">
        <button type="submit" className="btn btn--primary btn--sm" disabled={submitting}>
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

// ── AddItemToCompartmentForm ──────────────────────────────────────────────────
// Compartment and vehicle are already known — user just picks the item and
// sets quantities. Quantities appear only after an item is selected.

function AddItemToCompartmentForm({ compartmentId, vehicleId, onAdded, onCancel }) {
  const { getToken }                      = useAuth()
  const [selectedItem, setSelectedItem]   = useState(null)
  const [min, setMin]                     = useState('1')
  const [max, setMax]                     = useState('4')
  const [error, setError]                 = useState(null)
  const [submitting, setSub]              = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!selectedItem) { setError('Please select an item.'); return }
    const minN = parseInt(min, 10)
    const maxN = parseInt(max, 10)
    if (isNaN(minN) || minN < 1)    { setError('Min must be at least 1.'); return }
    if (isNaN(maxN) || maxN < minN) { setError('Max must be ≥ min.'); return }
    setSub(true); setError(null)
    try {
      await adminApi.assignItem(selectedItem.item_id, {
        vehicle_id:     vehicleId,
        compartment_id: compartmentId,
        min_quantity:   minN,
        max_quantity:   maxN,
      }, getToken)
      onAdded()
    } catch (err) {
      setError(err.message)
    } finally {
      setSub(false)
    }
  }

  return (
    <form className="add-assignment-form" onSubmit={handleSubmit} noValidate>
      <p className="add-assignment-form__title">Add item to compartment</p>
      <div className="assignment-field">
        <label className="assignment-field__label">Item</label>
        <ItemSearchCombobox
          onSelect={item => { setSelectedItem(item); setError(null) }}
          placeholder="Type to search items…"
          disabled={submitting}
          autoFocus
        />
      </div>
      {selectedItem && (
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
          disabled={submitting || !selectedItem}
        >
          {submitting ? 'Adding…' : 'Add Item'}
        </button>
        <button type="button" className="btn btn--secondary btn--sm"
          onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>
    </form>
  )
}

// ── CompartmentParLevels ──────────────────────────────────────────────────────

export default function CompartmentParLevels({ compartmentId, vehicleId }) {
  const { getToken }                      = useAuth()
  const [expanded, setExpanded]           = useState(false)
  const [listKey, setListKey]             = useState(0)
  const [editingParId, setEditingParId]   = useState(null)
  const [showAddForm, setShowAddForm]     = useState(false)
  const [removingParId, setRemovingParId] = useState(null)

  const { data: assignments, isLoading, error } = useApi(
    () => expanded
      ? adminApi.getCompartmentAssignments(compartmentId, getToken)
      : Promise.resolve(null),
    [expanded, listKey, compartmentId]
  )

  const refresh = useCallback(() => {
    setListKey(k => k + 1)
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

  const count = assignments?.length ?? null

  function toggleLabel() {
    if (count === null) return 'Par levels'
    if (count === 0)    return 'No items assigned'
    return `Par levels (${count})`
  }

  return (
    <div className="compartment-par-levels">
      <button
        type="button"
        className="item-assignments__toggle"
        onClick={() => setExpanded(v => !v)}
        aria-expanded={expanded}
      >
        <span>📍 {toggleLabel()}</span>
        <span aria-hidden="true">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="item-assignments__panel">
          {isLoading && <p className="assignment-loading">Loading…</p>}
          {error && <p className="assignment-error" role="alert">Could not load assignments.</p>}

          {!isLoading && !error && (
            <>
              {(assignments ?? []).length === 0 ? (
                <p className="assignment-empty">No items assigned to this compartment yet.</p>
              ) : (
                <ul className="assignment-list">
                  {assignments.map(a => (
                    <li key={a.par_id} className="assignment-row">
                      {editingParId === a.par_id ? (
                        <EditCompartmentParRow
                          assignment={a}
                          onSaved={refresh}
                          onCancel={() => setEditingParId(null)}
                        />
                      ) : (
                        <>
                          <div className="assignment-row__info">
                            <span className="assignment-row__compartment">
                              {a.item_name ?? `Item #${a.item_id}`}
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
                              aria-label={`Remove ${a.item_name ?? 'item'} from compartment`}
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
                <AddItemToCompartmentForm
                  compartmentId={compartmentId}
                  vehicleId={vehicleId}
                  onAdded={refresh}
                  onCancel={() => setShowAddForm(false)}
                />
              ) : (
                <button
                  type="button"
                  className="btn btn--secondary btn--sm item-assignments__add-btn"
                  onClick={() => { setShowAddForm(true); setEditingParId(null) }}
                >
                  + Add Item
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
