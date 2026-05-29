/**
 * components/RepairRequestList.jsx
 * Displays repair requests for a vehicle with status badges and
 * a two-modal workflow:
 *   - InProgressModal  — any role, optional note, advances OPEN → IN_PROGRESS
 *   - ResolutionModal  — Supervisor+ only, required notes, closes IN_PROGRESS → RESOLVED
 *
 * B-R1 fix: "Mark In Progress" now opens InProgressModal, not ResolutionModal.
 * B-R2 fix: ResolutionModal is only reachable when repair.status === 'IN_PROGRESS'.
 * F-R1: InProgressModal note field is optional — no minimum length gate.
 */

import React, { useState } from 'react'

const STATUS_META = {
  OPEN:        { label: 'Open',        className: 'badge--open',        icon: '🔴' },
  IN_PROGRESS: { label: 'In Progress', className: 'badge--in-progress', icon: '🟡' },
  RESOLVED:    { label: 'Resolved',    className: 'badge--resolved',    icon: '🟢' },
}

const SEVERITY_META = {
  ROUTINE: { label: 'Routine', className: 'badge--routine' },
  URGENT:  { label: 'Urgent',  className: 'badge--urgent'  },
}

const STATUS_FILTERS = ['ALL', 'OPEN', 'IN_PROGRESS', 'RESOLVED']

function formatDate(isoString) {
  if (!isoString) return '—'
  return new Date(isoString).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

/**
 * InProgressModal — lightweight, note optional.
 * Shown when a user clicks "Mark In Progress" on an OPEN repair request.
 * Available to all roles.
 */
function InProgressModal({ repair, onConfirm, onCancel, isSubmitting }) {
  const [note, setNote] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    onConfirm({
      status: 'IN_PROGRESS',
      resolution_notes: note.trim() || undefined,
    })
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="in-progress-modal-title">
      <div className="modal">
        <h3 id="in-progress-modal-title" className="modal__title">Mark In Progress</h3>
        <p className="modal__body">{repair.description}</p>
        <form onSubmit={handleSubmit} noValidate>
          <div className="modal__field">
            <label className="modal__label" htmlFor="in-progress-note">
              Add a note <span className="modal__optional">(optional)</span>
            </label>
            <textarea
              id="in-progress-note"
              className="modal__textarea"
              value={note}
              onChange={e => setNote(e.target.value)}
              placeholder="e.g. Scheduled for shop visit Thursday…"
              rows={3}
              maxLength={500}
            />
          </div>
          <div className="modal__actions">
            <button type="button" className="btn btn--secondary" onClick={onCancel} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn--primary" disabled={isSubmitting}>
              {isSubmitting ? 'Saving…' : 'Confirm'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/**
 * ResolutionModal — resolution notes required.
 * Shown when a Supervisor clicks "Mark Resolved" on an IN_PROGRESS repair request.
 */
function ResolutionModal({ repair, onConfirm, onCancel, isSubmitting }) {
  const [notes, setNotes] = useState('')
  const [error, setError] = useState(null)

  function handleSubmit(e) {
    e.preventDefault()
    if (notes.trim().length < 5) {
      setError('Please describe what was done to resolve this issue (at least 5 characters).')
      return
    }
    onConfirm({
      status: 'RESOLVED',
      resolution_notes: notes.trim(),
    })
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="resolution-modal-title">
      <div className="modal">
        <h3 id="resolution-modal-title" className="modal__title">Resolve Repair Request</h3>
        <p className="modal__body">{repair.description}</p>
        <form onSubmit={handleSubmit} noValidate>
          <div className="modal__field">
            <label className="modal__label" htmlFor="resolution-notes">
              Resolution Notes <span aria-hidden="true">*</span>
            </label>
            <textarea
              id="resolution-notes"
              className="modal__textarea"
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Describe what was done to resolve this issue…"
              rows={3}
              maxLength={500}
              required
            />
            {error && <div className="modal__error" role="alert">{error}</div>}
          </div>
          <div className="modal__actions">
            <button type="button" className="btn btn--secondary" onClick={onCancel} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn--primary" disabled={isSubmitting}>
              {isSubmitting ? 'Saving…' : 'Mark Resolved'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function RepairRequestList({ requests, canManage, canResolve, onUpdate, isUpdating }) {
  const [statusFilter, setStatusFilter]   = useState('ALL')
  const [inProgressRepair, setInProgressRepair] = useState(null)
  const [resolvingRepair, setResolvingRepair]   = useState(null)

  const filtered = (requests ?? []).filter(r =>
    statusFilter === 'ALL' || r.status === statusFilter
  )

  function handleInProgressConfirm(payload) {
    onUpdate(inProgressRepair, payload, () => setInProgressRepair(null))
  }

  function handleResolveConfirm(payload) {
    onUpdate(resolvingRepair, payload, () => setResolvingRepair(null))
  }

  if (!requests || requests.length === 0) {
    return (
      <div className="repair-list__empty">
        <span aria-hidden="true">✓</span>
        <p>No repair requests on file for this vehicle.</p>
      </div>
    )
  }

  return (
    <div className="repair-list">
      {/* Filter tabs */}
      <div className="repair-list__filters" role="tablist" aria-label="Filter repair requests">
        {STATUS_FILTERS.map(f => (
          <button
            key={f}
            role="tab"
            aria-selected={statusFilter === f}
            className={`repair-filter-tab ${statusFilter === f ? 'repair-filter-tab--active' : ''}`}
            onClick={() => setStatusFilter(f)}
            type="button"
          >
            {f === 'ALL' ? `All (${requests.length})` : f.replace('_', ' ')}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="repair-list__empty">
          No {statusFilter.replace('_', ' ').toLowerCase()} requests.
        </div>
      ) : (
        <ul className="repair-list__items" aria-label="Repair requests">
          {filtered.map(repair => {
            const statusMeta   = STATUS_META[repair.status]     ?? STATUS_META.OPEN
            const severityMeta = SEVERITY_META[repair.severity] ?? SEVERITY_META.ROUTINE
            return (
              <li key={repair.repair_id} className={`repair-item ${repair.severity === 'URGENT' ? 'repair-item--urgent' : ''}`}>
                <div className="repair-item__header">
                  <div className="repair-item__badges">
                    <span className={`badge ${statusMeta.className}`}>
                      {statusMeta.icon} {statusMeta.label}
                    </span>
                    <span className={`badge ${severityMeta.className}`}>
                      {severityMeta.label}
                    </span>
                  </div>
                  <span className="repair-item__date">{formatDate(repair.reported_at)}</span>
                </div>

                <p className="repair-item__description">{repair.description}</p>

                <div className="repair-item__meta">
                  <span>Reported by {repair.reported_by}</span>
                  {repair.resolved_at && (
                    <span> · Resolved {formatDate(repair.resolved_at)} by {repair.resolved_by}</span>
                  )}
                </div>

                {repair.resolution_notes && (
                  <div className="repair-item__resolution">
                    <strong>Resolution:</strong> {repair.resolution_notes}
                  </div>
                )}

                {/* Action buttons — role-gated per transition */}
                {repair.status === 'OPEN' && canManage && (
                  <div className="repair-item__actions">
                    <button
                      className="btn btn--sm btn--ghost"
                      onClick={() => setInProgressRepair(repair)}
                      type="button"
                    >
                      Mark In Progress
                    </button>
                  </div>
                )}

                {repair.status === 'IN_PROGRESS' && canResolve && (
                  <div className="repair-item__actions">
                    <button
                      className="btn btn--sm btn--ghost"
                      onClick={() => setResolvingRepair(repair)}
                      type="button"
                    >
                      Mark Resolved
                    </button>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}

      {inProgressRepair && (
        <InProgressModal
          repair={inProgressRepair}
          onConfirm={handleInProgressConfirm}
          onCancel={() => setInProgressRepair(null)}
          isSubmitting={isUpdating}
        />
      )}

      {resolvingRepair && (
        <ResolutionModal
          repair={resolvingRepair}
          onConfirm={handleResolveConfirm}
          onCancel={() => setResolvingRepair(null)}
          isSubmitting={isUpdating}
        />
      )}
    </div>
  )
}
