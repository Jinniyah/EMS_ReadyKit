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
// Edits quantities + optional priority check toggle and question (RX-F12).

function EditCompartmentParRow({ assignment, onSaved, onCancel }) {
  const { getToken } = useAuth()
  const [min, setMin]                     = useState(String(assignment.min_quantity))
  const [max, setMax]                     = useState(String(assignment.max_quantity))
  const [isPriority, setIsPriority]       = useState(assignment.priority_check ?? false)
  const [question, setQuestion]           = useState(assignment.priority_question ?? '')
  const [error, setError]                 = useState(null)
  const [submitting, setSub]              = useState(false)

  async function handleSave(e) {
    e.preventDefault()
    const minN = parseInt(min, 10)
    const maxN = parseInt(max, 10)
    if (isNaN(minN) || minN < 1)    { setError('Min must be at least 1.'); return }
    if (isNaN(maxN) || maxN < minN) { setError('Max must be ≥ min.'); return }
    setSub(true); setError(null)
    try {
      await adminApi.updateParLevel(assignment.par_id, {
        min_quantity:      minN,
        max_quantity:      maxN,
        priority_check:    isPriority,
        priority_question: isPriority ? (question.trim() || null) : null,
      }, getToken)
      onSaved(assignment.par_id)
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

      <label className="assignment-edit-priority-row">
        <input
          type="checkbox"
          checked={isPriority}
          onChange={e => setIsPriority(e.target.checked)}
          disabled={submitting}
        />
        <span>Show as priority item at start of check</span>
      </label>

      {isPriority && (
        <label className="assignment-edit-label assignment-edit-label--full">
          Custom check question (optional, max 150 chars)
          <input
            className="assignment-edit-input assignment-edit-input--wide"
            type="text"
            maxLength={150}
            value={question}
            onChange={e => setQuestion(e.target.value)}
            placeholder={`e.g. "AED shows READY?"`}
            disabled={submitting}
          />
        </label>
      )}

      {error && <p className="assignment-error assignment-error--prominent" role="alert">{error}</p>}
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

function AddItemToCompartmentForm({ compartmentId, vehicleId, locationId, stationId, onAdded, onCancel }) {
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
        ...(vehicleId   != null ? { vehicle_id:  vehicleId  } : {}),
        ...(locationId  != null ? { location_id: locationId } : {}),
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
          stationId={stationId}
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

// ── ConfirmRemoveRow ──────────────────────────────────────────────────────────
// Inline confirmation shown when the ✕ remove button is clicked.

function ConfirmRemoveRow({ itemName, onConfirm, onCancel }) {
  const [reason, setReason] = useState('')
  const [submitting, setSub] = useState(false)

  async function handleConfirm() {
    setSub(true)
    await onConfirm(reason.trim() || null)
  }

  return (
    <div className="assignment-confirm-remove">
      <p className="assignment-confirm-remove__label">
        Remove <strong>{itemName}</strong> from this compartment?
      </p>
      <label className="assignment-edit-label assignment-edit-label--full">
        Reason (optional)
        <input
          className="assignment-edit-input assignment-edit-input--wide"
          type="text"
          maxLength={200}
          value={reason}
          onChange={e => setReason(e.target.value)}
          placeholder="e.g. No longer stocked on this unit"
          disabled={submitting}
          autoFocus
        />
      </label>
      <div className="assignment-edit-actions">
        <button
          type="button"
          className="btn btn--danger btn--sm"
          onClick={handleConfirm}
          disabled={submitting}
        >
          {submitting ? 'Removing…' : 'Remove'}
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
    </div>
  )
}

// ── CompartmentParLevels ──────────────────────────────────────────────────────

export default function CompartmentParLevels({ compartmentId, vehicleId, locationId, stationId }) {
  const { getToken }                          = useAuth()
  const [expanded, setExpanded]               = useState(false)
  const [listKey, setListKey]                 = useState(0)
  const [editingParId, setEditingParId]       = useState(null)
  const [showAddForm, setShowAddForm]         = useState(false)
  const [confirmRemoveId, setConfirmRemoveId] = useState(null)
  const [removeError, setRemoveError]         = useState(null)
  const [savedParId, setSavedParId]           = useState(null)

  const { data: assignments, isLoading, error } = useApi(
    () => expanded
      ? adminApi.getCompartmentAssignments(compartmentId, getToken)
      : Promise.resolve(null),
    [expanded, listKey, compartmentId]
  )

  const refresh = useCallback((savedId = null) => {
    setListKey(k => k + 1)
    setEditingParId(null)
    setShowAddForm(false)
    setConfirmRemoveId(null)
    setRemoveError(null)
    if (savedId != null) {
      setSavedParId(savedId)
      setTimeout(() => setSavedParId(null), 2500)
    }
  }, [])

  async function handleRemoveConfirmed(parId, reason) {
    try {
      await adminApi.deactivateParLevelFull(parId, reason, getToken)
      refresh()
    } catch (err) {
      setConfirmRemoveId(null)
      setRemoveError(err.message)
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
          {removeError && <p className="assignment-error" role="alert">{removeError}</p>}

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
                      ) : confirmRemoveId === a.par_id ? (
                        <ConfirmRemoveRow
                          itemName={a.item_name ?? `Item #${a.item_id}`}
                          onConfirm={reason => handleRemoveConfirmed(a.par_id, reason)}
                          onCancel={() => { setConfirmRemoveId(null); setRemoveError(null) }}
                        />
                      ) : (
                        <>
                          <div className="assignment-row__info">
                            <span className="assignment-row__compartment">
                              {a.item_name ?? `Item #${a.item_id}`}
                              {a.priority_check && (
                                <span className="assignment-priority-badge" title={a.priority_question || 'Priority item'}>
                                  {' '}★
                                </span>
                              )}
                            </span>
                            <QtyBadge min={a.min_quantity} max={a.max_quantity} />
                          </div>
                          {savedParId === a.par_id && (
                            <p className="assignment-saved-flash" role="status">
                              ✓ Saved
                            </p>
                          )}
                          <div className="assignment-row__actions">
                            <button
                              type="button"
                              className="btn btn--secondary btn--sm"
                              onClick={() => { setEditingParId(a.par_id); setShowAddForm(false); setConfirmRemoveId(null) }}
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              className="assignment-remove-btn"
                              onClick={() => { setConfirmRemoveId(a.par_id); setEditingParId(null); setShowAddForm(false) }}
                              aria-label={`Remove ${a.item_name ?? 'item'} from compartment`}
                            >
                              ✕
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
                  locationId={locationId}
                  stationId={stationId}
                  onAdded={refresh}
                  onCancel={() => setShowAddForm(false)}
                />
              ) : (
                <button
                  type="button"
                  className="btn btn--secondary btn--sm item-assignments__add-btn"
                  onClick={() => { setShowAddForm(true); setEditingParId(null); setConfirmRemoveId(null) }}
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
