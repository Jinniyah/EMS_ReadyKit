/**
 * components/RepairRequestList.jsx
 * Displays repair requests for a vehicle with status badges and
 * a resolve/advance workflow for Supervisors.
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

function ResolutionModal({ repair, onConfirm, onCancel, isSubmitting }) {
  const [notes, setNotes]   = useState('')
  const [error, setError]   = useState(null)
  const isResolving = repair.status === 'OPEN' || repair.status === 'IN_PROGRESS'

  function handleSubmit(e) {
    e.preventDefault()
    if (isResolving && notes.trim().length < 5) {
      setError('Please provide resolution notes (at least 5 characters).')
      return
    }
    onConfirm({
      status: isResolving ? 'RESOLVED' : 'IN_PROGRESS',
      resolution_notes: isResolving ? notes.trim() : undefined,
    })
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="resolution-modal-title">
      <div className="modal">
        <h3 id="resolution-modal-title" className="modal__title">
          {isResolving ? 'Resolve Repair Request' : 'Mark In Progress'}
        </h3>
        <p className="modal__body">
          {repair.description}
        </p>
        <form onSubmit={handleSubmit} noValidate>
          {isResolving && (
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
          )}
          <div className="modal__actions">
            <button type="button" className="btn btn--ghost" onClick={onCancel} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn--primary" disabled={isSubmitting}>
              {isSubmitting ? 'Saving…' : isResolving ? 'Mark Resolved' : 'Mark In Progress'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function RepairRequestList({ requests, canManage, onUpdate, isUpdating }) {
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [managingRepair, setManagingRepair] = useState(null)

  const filtered = (requests ?? []).filter(r =>
    statusFilter === 'ALL' || r.status === statusFilter
  )

  function handleUpdateConfirm(payload) {
    onUpdate(managingRepair, payload, () => setManagingRepair(null))
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
            const statusMeta   = STATUS_META[repair.status]   ?? STATUS_META.OPEN
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
                  <span className="repair-item__date">
                    {formatDate(repair.reported_at)}
                  </span>
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

                {canManage && repair.status !== 'RESOLVED' && (
                  <div className="repair-item__actions">
                    <button
                      className="btn btn--sm btn--ghost"
                      onClick={() => setManagingRepair(repair)}
                      type="button"
                    >
                      {repair.status === 'OPEN' ? 'Mark In Progress' : 'Mark Resolved'}
                    </button>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}

      {managingRepair && (
        <ResolutionModal
          repair={managingRepair}
          onConfirm={handleUpdateConfirm}
          onCancel={() => setManagingRepair(null)}
          isSubmitting={isUpdating}
        />
      )}
    </div>
  )
}
