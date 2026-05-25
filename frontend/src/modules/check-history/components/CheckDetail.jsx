/**
 * components/CheckDetail.jsx
 * Full check detail view — line items, acknowledgement, soft-delete.
 */

import React, { useState } from 'react'
import { canAccess } from '../../../shared/utils/roleGuard.js'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { checkHistoryApi } from '../api/checkHistoryApi.js'
import { formatDateTime } from '../../../shared/utils/dateHelpers.js'

const STATUS_LABEL = {
  PASS:          { label: 'Pass',          className: 'check-status--pass' },
  NEEDS_RESTOCK: { label: 'Needs Restock', className: 'check-status--warn' },
  FAIL:          { label: 'Fail',          className: 'check-status--fail' },
}

const LINE_STATUS_LABEL = {
  OK:       { label: 'OK',       className: 'line-status--ok' },
  SHORT:    { label: 'Short',    className: 'line-status--warn' },
  LOW:      { label: 'Low',      className: 'line-status--warn' },
  MISSING:  { label: 'Missing',  className: 'line-status--fail' },
  EXPIRED:  { label: 'Expired',  className: 'line-status--fail' },
  FAIL:     { label: 'Fail',     className: 'line-status--fail' },
  OVERDUE:  { label: 'Overdue',  className: 'line-status--fail' },
}

function formatDate(isoString) {
  if (!isoString) return '—'
  return new Date(isoString).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

/**
 * Render the meaningful value(s) for a line item based on its check_type.
 * Avoids showing "0 / 1" for MEASUREMENT/FUNCTIONAL items where that number is meaningless.
 */
function LineItemMeta({ li }) {
  const type = li.check_type ?? 'SUPPLY'
  const parts = []

  if (type === 'SUPPLY' || type === 'DOCUMENT') {
    parts.push(`${li.quantity_found} / ${li.quantity_needed}`)
    if (li.lot_number)      parts.push(`Lot: ${li.lot_number}`)
    if (li.expiration_date) parts.push(`Exp: ${formatDate(li.expiration_date)}`)
  } else if (type === 'MEASUREMENT') {
    if (li.measurement_value != null) parts.push(`Reading: ${li.measurement_value}`)
  } else if (type === 'FUNCTIONAL') {
    if (li.functional_pass != null) parts.push(li.functional_pass ? 'Pass ✓' : 'Fail ✗')
  } else if (type === 'DATE_RECORD') {
    if (li.date_value) parts.push(`Last recorded: ${formatDate(li.date_value)}`)
  }

  if (parts.length === 0) return null

  return (
    <div className="check-line-item__meta">
      {parts.map((p, i) => <span key={i}>{p}</span>)}
    </div>
  )
}

function AcknowledgePanel({ checkId, existing, onDone }) {
  const { getToken } = useAuth()
  const [notes, setNotes]             = useState(existing ?? '')
  const [isSubmitting, setSubmitting] = useState(false)
  const [error, setError]             = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (notes.trim().length < 5) { setError('Please provide at least 5 characters.'); return }
    setSubmitting(true); setError(null)
    try {
      await checkHistoryApi.acknowledgeCheck(checkId, notes.trim(), getToken)
      onDone()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="acknowledge-panel" onSubmit={handleSubmit} noValidate>
      <h4 className="acknowledge-panel__title">
        {existing ? 'Update Corrective Action' : 'Acknowledge & Record Corrective Action'}
      </h4>
      <textarea
        className="acknowledge-panel__textarea"
        value={notes}
        onChange={e => setNotes(e.target.value)}
        placeholder="Describe what corrective action was taken…"
        rows={3}
        maxLength={500}
      />
      {error && <div className="acknowledge-panel__error" role="alert">{error}</div>}
      <button type="submit" className="btn btn--primary btn--full" disabled={isSubmitting}>
        {isSubmitting ? 'Saving…' : 'Save Acknowledgement'}
      </button>
    </form>
  )
}

function SoftDeletePanel({ checkId, onDone, onCancel }) {
  const { getToken } = useAuth()
  const [reason, setReason]           = useState('')
  const [isSubmitting, setSubmitting] = useState(false)
  const [error, setError]             = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (reason.trim().length < 5) { setError('Please provide at least 5 characters.'); return }
    setSubmitting(true); setError(null)
    try {
      await checkHistoryApi.softDeleteCheck(checkId, reason.trim(), getToken)
      onDone()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="delete-panel" onSubmit={handleSubmit} noValidate>
      <div className="delete-panel__warning" role="alert">
        <strong>⚠ This check will be hidden immediately.</strong> It will be permanently
        deleted after 90 days. A mandatory reason is required.
      </div>
      <textarea
        className="delete-panel__textarea"
        value={reason}
        onChange={e => setReason(e.target.value)}
        placeholder="Why is this check being deleted? e.g. Duplicate submission, wrong vehicle…"
        rows={3}
        maxLength={300}
      />
      {error && <div className="delete-panel__error" role="alert">{error}</div>}
      <div className="delete-panel__actions">
        <button type="submit" className="btn btn--danger btn--full" disabled={isSubmitting}>
          {isSubmitting ? 'Deleting…' : 'Delete This Check'}
        </button>
        <button type="button" className="btn btn--secondary btn--full"
          onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </button>
      </div>
    </form>
  )
}

export default function CheckDetail({ check, onBack, onDeleted }) {
  const { user } = useAuth()
  const isSupervisor = canAccess(user, 'supervisor')

  const [activePanel, setActivePanel] = useState(null)
  const [localCheck, setLocalCheck]   = useState(check)

  const statusMeta = STATUS_LABEL[localCheck.status] ?? STATUS_LABEL.PASS

  function handleAcknowledgeDone() {
    setLocalCheck(prev => ({
      ...prev,
      corrective_action: 'Updated — please refresh to see the latest note.',
      reviewed_at: new Date().toISOString(),
    }))
    setActivePanel(null)
  }

  return (
    <div className="check-detail">

      <div className="check-detail__header">
        <button className="btn-text check-detail__back" onClick={onBack} type="button">
          ← Back
        </button>
        <div>
          <h2 className="check-detail__title">Check Detail</h2>
          <p className="check-detail__subtitle">{localCheck.check_date}</p>
        </div>
      </div>

      <div className="check-detail__summary">
        <div className="check-detail__summary-row">
          <span className="check-detail__label">Status</span>
          <span className={`check-status check-status--label ${statusMeta.className}`}>
            {statusMeta.label}
          </span>
        </div>
        <div className="check-detail__summary-row">
          <span className="check-detail__label">Performed by</span>
          <span>{localCheck.performed_by}</span>
        </div>
        <div className="check-detail__summary-row">
          <span className="check-detail__label">Time</span>
          <span>{formatDateTime(localCheck.timestamp)}</span>
        </div>
        {localCheck.notes && (
          <div className="check-detail__summary-row">
            <span className="check-detail__label">Notes</span>
            <span>{localCheck.notes}</span>
          </div>
        )}
      </div>

      {/* Acknowledgement */}
      {localCheck.reviewed_at && activePanel !== 'acknowledge' && (
        <div className="check-detail__ack">
          <div className="check-detail__ack-header">
            <span className="check-detail__ack-icon">✓</span>
            <div>
              <div className="check-detail__ack-title">Acknowledged</div>
              <div className="check-detail__ack-meta">
                {localCheck.reviewed_by} · {formatDateTime(localCheck.reviewed_at)}
              </div>
            </div>
          </div>
          {localCheck.corrective_action && (
            <p className="check-detail__ack-notes">{localCheck.corrective_action}</p>
          )}
          {isSupervisor && (
            <button className="btn btn--secondary btn--sm"
              onClick={() => setActivePanel('acknowledge')} type="button">
              Update Note
            </button>
          )}
        </div>
      )}

      {/* Line items */}
      {localCheck.line_items?.length > 0 && (
        <div className="check-detail__section">
          <h3 className="check-detail__section-title">
            Items ({localCheck.line_items.length})
          </h3>
          <ul className="check-detail__items">
            {localCheck.line_items.map((li, i) => {
              const lsMeta = LINE_STATUS_LABEL[li.status] ?? LINE_STATUS_LABEL.OK
              return (
                <li key={i} className="check-line-item">
                  <div className="check-line-item__top">
                    <span className="check-line-item__name">
                      {li.item_name ?? `Item #${li.item_id}`}
                    </span>
                    <span className={`line-status ${lsMeta.className}`}>{lsMeta.label}</span>
                  </div>
                  <LineItemMeta li={li} />
                  {li.notes && <p className="check-line-item__notes">{li.notes}</p>}
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {/* Supervisor actions */}
      {isSupervisor && activePanel === null && (
        <div className="check-detail__actions">
          {!localCheck.reviewed_at && (
            <button className="btn btn--primary btn--full"
              onClick={() => setActivePanel('acknowledge')} type="button">
              ✓ Acknowledge &amp; Add Corrective Action
            </button>
          )}
          <button className="btn btn--secondary btn--full"
            onClick={() => setActivePanel('delete')} type="button">
            Delete This Check
          </button>
        </div>
      )}

      {activePanel === 'acknowledge' && (
        <AcknowledgePanel
          checkId={localCheck.check_id}
          existing={localCheck.corrective_action}
          onDone={handleAcknowledgeDone}
        />
      )}

      {activePanel === 'delete' && (
        <SoftDeletePanel
          checkId={localCheck.check_id}
          onDone={onDeleted}
          onCancel={() => setActivePanel(null)}
        />
      )}
    </div>
  )
}
