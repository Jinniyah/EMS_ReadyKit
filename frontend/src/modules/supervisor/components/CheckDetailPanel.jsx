/**
 * components/CheckDetailPanel.jsx
 * Full check detail for supervisors — F-5F3, F-5F4, F-5F5.
 *
 * "I Fixed This" is independent of acknowledgement.
 * A supervisor can acknowledge with a note AND still come back to fix items.
 * The button stays visible as long as there are unresolved fail items
 * and the check hasn't been marked fixed (localFixed).
 */

import React, { useState } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import Spinner from '../../../shared/components/Spinner.jsx'
import { supervisorApi } from '../api/supervisorApi.js'
import { formatDateTime } from '../../../shared/utils/dateHelpers.js'

const STATUS_META = {
  PASS:          { label: 'Pass',          className: 'sup-status--pass' },
  NEEDS_RESTOCK: { label: 'Needs Restock', className: 'sup-status--warn' },
  FAIL:          { label: 'Fail',          className: 'sup-status--fail' },
}

const LINE_META = {
  OK:      { label: 'OK',      className: 'line--ok' },
  SHORT:   { label: 'Short',   className: 'line--warn' },
  LOW:     { label: 'Low',     className: 'line--warn' },
  MISSING: { label: 'Missing', className: 'line--fail' },
  EXPIRED: { label: 'Expired', className: 'line--fail' },
  FAIL:    { label: 'Fail',    className: 'line--fail' },
  OVERDUE: { label: 'Overdue', className: 'line--fail' },
}

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d + 'T12:00:00').toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

function LineItemMeta({ li }) {
  const type = li.check_type ?? 'SUPPLY'
  const parts = []
  if (type === 'SUPPLY' || type === 'DOCUMENT') {
    parts.push(`${li.quantity_found} / ${li.quantity_needed}`)
    if (li.lot_number)      parts.push(`Lot: ${li.lot_number}`)
    if (li.expiration_date) parts.push(`Exp: ${fmtDate(li.expiration_date)}`)
  } else if (type === 'MEASUREMENT') {
    if (li.measurement_value != null) parts.push(`Reading: ${li.measurement_value}`)
  } else if (type === 'FUNCTIONAL') {
    if (li.functional_pass != null) parts.push(li.functional_pass ? 'Pass ✓' : 'Fail ✗')
  } else if (type === 'DATE_RECORD') {
    if (li.date_value) parts.push(`Last recorded: ${fmtDate(li.date_value)}`)
  }
  if (!parts.length) return null
  return (
    <div className="cdp-line__meta">
      {parts.map((p, i) => <span key={i}>{p}</span>)}
    </div>
  )
}

function AcknowledgeForm({ checkId, existing, onDone, onCancel }) {
  const { getToken } = useAuth()
  const [notes, setNotes]         = useState(existing ?? '')
  const [isSubmitting, setSubmit] = useState(false)
  const [error, setError]         = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (notes.trim().length < 5) { setError('Please provide at least 5 characters.'); return }
    setSubmit(true); setError(null)
    try {
      await supervisorApi.acknowledgeCheck(checkId, notes.trim(), getToken)
      onDone()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmit(false)
    }
  }

  return (
    <form className="cdp-ack-form" onSubmit={handleSubmit} noValidate>
      <h4 className="cdp-ack-form__title">Record Corrective Action</h4>
      <textarea
        className="cdp-ack-form__textarea"
        value={notes}
        onChange={e => setNotes(e.target.value)}
        placeholder="Describe what corrective action was taken or is planned…"
        rows={3}
        maxLength={500}
      />
      {error && <div className="cdp-ack-form__error" role="alert">{error}</div>}
      <button type="submit" className="btn btn--primary btn--full" disabled={isSubmitting}>
        {isSubmitting ? 'Saving…' : 'Save Note'}
      </button>
      {onCancel && (
        <button type="button" className="btn btn--secondary btn--full"
          onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </button>
      )}
    </form>
  )
}

function IFixedThisForm({ checkId, vehicleId, failItems, onDone, onCancel }) {
  const { getToken } = useAuth()
  const [notes, setNotes]         = useState('')
  const [isSubmitting, setSubmit] = useState(false)
  const [error, setError]         = useState(null)

  const failSummary = failItems.map(li => li.item_name ?? `Item #${li.item_id}`).join(', ')

  async function handleSubmit(e) {
    e.preventDefault()
    if (notes.trim().length < 5) { setError('Please describe what you did (at least 5 characters).'); return }
    setSubmit(true); setError(null)
    try {
      await supervisorApi.resolveFailedItems(checkId, vehicleId, notes.trim(), getToken)
      onDone()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmit(false)
    }
  }

  return (
    <form className="cdp-fix-form" onSubmit={handleSubmit} noValidate>
      <h4 className="cdp-fix-form__title">✓ I Fixed This</h4>
      <p className="cdp-fix-form__body">
        Describe what you did to resolve the failed items. This will be recorded
        as a resolved repair request and the check will be acknowledged.
        <br />
        <strong>The original FAIL record is preserved for compliance.</strong>
        {' '}The next check starts fresh.
      </p>
      {failSummary && (
        <div className="cdp-fix-form__items">
          <span className="cdp-fix-form__items-label">Failed items:</span>
          <span>{failSummary}</span>
        </div>
      )}
      <textarea
        className="cdp-fix-form__textarea"
        value={notes}
        onChange={e => setNotes(e.target.value)}
        placeholder="e.g. Replaced AED battery, restocked oxygen, swapped broken BP cuff with spare…"
        rows={3}
        maxLength={500}
        autoFocus
      />
      {error && <div className="cdp-fix-form__error" role="alert">{error}</div>}
      <button type="submit" className="btn btn--primary btn--full" disabled={isSubmitting}>
        {isSubmitting ? 'Saving…' : '✓ Confirm Fix & Close'}
      </button>
      <button type="button" className="btn btn--secondary btn--full"
        onClick={onCancel} disabled={isSubmitting}>
        Cancel
      </button>
    </form>
  )
}

export default function CheckDetailPanel({ checkSummary, vehicleId, vehicleNumber, onBack }) {
  const { getToken } = useAuth()
  const [activePanel, setActivePanel] = useState(null) // 'acknowledge' | 'fix' | null
  const [localFixed, setLocalFixed]   = useState(false)

  const { data: check, isLoading, error, refetch } = useApi(
    () => supervisorApi.getCheckDetail(checkSummary.check_id, getToken),
    [checkSummary.check_id]
  )

  const statusMeta     = STATUS_META[check?.status] ?? STATUS_META.PASS
  const isAcknowledged = !!check?.reviewed_at

  const failItems = (check?.line_items ?? []).filter(li =>
    ['FAIL', 'MISSING', 'EXPIRED', 'OVERDUE', 'SHORT', 'LOW'].includes(li.status)
  )

  // "I Fixed This" is available as long as:
  // - there are fail items
  // - the supervisor hasn't already fixed it this session
  // It is INDEPENDENT of acknowledgement — a supervisor can add a note
  // and still come back to close the fix later.
  const canFix = failItems.length > 0 && !localFixed

  function handleFixDone() {
    setLocalFixed(true)
    setActivePanel(null)
    refetch()
  }

  function handleAckDone() {
    setActivePanel(null)
    refetch()
  }

  return (
    <div className="cdp">

      <div className="cdp__header">
        <button className="btn-text cdp__back" onClick={onBack} type="button">
          ← Back
        </button>
        <div style={{ flex: 1 }}>
          <h2 className="cdp__title">Check Detail</h2>
          <p className="cdp__subtitle">{vehicleNumber ?? ''} · {checkSummary.check_date}</p>
        </div>
        <button
          className="btn btn--secondary btn--sm cdp__print no-print"
          onClick={() => window.print()}
          type="button"
          aria-label="Print this check record"
        >
          🖨 Print
        </button>
      </div>

      {isLoading ? <Spinner label="Loading check…" /> : error ? (
        <div className="cdp__error" role="alert">
          Could not load check detail.{' '}
          <button className="btn-text" onClick={refetch}>Retry</button>
        </div>
      ) : (
        <>
          {/* Summary */}
          <div className="cdp__summary print-section">
            <div className="cdp__summary-row">
              <span className="cdp__label">Status</span>
              <span className={`sup-status ${statusMeta.className}`}>{statusMeta.label}</span>
            </div>
            <div className="cdp__summary-row">
              <span className="cdp__label">Vehicle</span>
              <span>{vehicleNumber ?? `#${check.vehicle_id}`}</span>
            </div>
            <div className="cdp__summary-row">
              <span className="cdp__label">Performed by</span>
              <span>{check.performed_by}</span>
            </div>
            <div className="cdp__summary-row">
              <span className="cdp__label">Submitted</span>
              <span>{formatDateTime(check.timestamp)}</span>
            </div>
            {check.notes && (
              <div className="cdp__summary-row">
                <span className="cdp__label">Notes</span>
                <span>{check.notes}</span>
              </div>
            )}
          </div>

          {/* Fixed confirmation */}
          {localFixed && (
            <div className="cdp__resolved-banner" role="status">
              ✓ Fixed and recorded — the next check starts fresh
            </div>
          )}

          {/* Existing acknowledgement */}
          {isAcknowledged && activePanel !== 'acknowledge' && (
            <div className="cdp__ack print-section">
              <div className="cdp__ack-header">
                <span className="cdp__ack-icon">✓</span>
                <div>
                  <div className="cdp__ack-title">Acknowledged</div>
                  <div className="cdp__ack-meta">
                    {check.reviewed_by} · {formatDateTime(check.reviewed_at)}
                  </div>
                </div>
              </div>
              {check.corrective_action && (
                <p className="cdp__ack-notes">{check.corrective_action}</p>
              )}
              <button className="btn btn--secondary btn--sm no-print"
                onClick={() => setActivePanel('acknowledge')} type="button">
                Update Note
              </button>
            </div>
          )}

          {/* Failed items callout */}
          {failItems.length > 0 && activePanel === null && (
            <div className="cdp__fail-callout print-section">
              <h3 className="cdp__fail-title">
                ⚠ {failItems.length} item{failItems.length !== 1 ? 's' : ''} need attention
              </h3>
              <ul className="cdp__fail-list">
                {failItems.map((li, i) => {
                  const lm = LINE_META[li.status] ?? LINE_META.FAIL
                  return (
                    <li key={i} className="cdp__fail-item">
                      <span className={`line-badge ${lm.className}`}>{lm.label}</span>
                      <span>{li.item_name ?? `Item #${li.item_id}`}</span>
                    </li>
                  )
                })}
              </ul>

              {/* Action buttons — always visible while fail items exist */}
              {canFix && (
                <div className="cdp__fail-actions no-print">
                  <button
                    className="btn btn--primary btn--full"
                    onClick={() => setActivePanel('fix')}
                    type="button"
                  >
                    ✓ I Fixed This — Record Resolution
                  </button>
                  {!isAcknowledged && (
                    <button
                      className="btn btn--secondary btn--full"
                      onClick={() => setActivePanel('acknowledge')}
                      type="button"
                    >
                      Add Note Only (not yet fixed)
                    </button>
                  )}
                </div>
              )}

              {/* Already fixed confirmation inline */}
              {localFixed && (
                <div className="cdp__fail-resolved">
                  ✓ Resolution recorded
                </div>
              )}
            </div>
          )}

          {/* Acknowledge button for checks that need a note but no fail items */}
          {!isAcknowledged && failItems.length === 0 &&
           check.status !== 'PASS' && activePanel === null && (
            <button className="btn btn--primary btn--full no-print"
              onClick={() => setActivePanel('acknowledge')} type="button">
              ✓ Acknowledge &amp; Record Corrective Action
            </button>
          )}

          {/* Inline panels */}
          {activePanel === 'fix' && (
            <IFixedThisForm
              checkId={check.check_id}
              vehicleId={vehicleId ?? check.vehicle_id}
              failItems={failItems}
              onDone={handleFixDone}
              onCancel={() => setActivePanel(null)}
            />
          )}

          {activePanel === 'acknowledge' && (
            <AcknowledgeForm
              checkId={check.check_id}
              existing={check.corrective_action}
              onDone={handleAckDone}
              onCancel={() => setActivePanel(null)}
            />
          )}

          {/* All line items */}
          {check.line_items?.length > 0 && (
            <div className="cdp__section print-section">
              <h3 className="cdp__section-title">All Items ({check.line_items.length})</h3>
              <ul className="cdp__items">
                {check.line_items.map((li, i) => {
                  const lm = LINE_META[li.status] ?? LINE_META.OK
                  return (
                    <li key={i} className={`cdp-line ${li.status !== 'OK' ? 'cdp-line--attention' : ''}`}>
                      <div className="cdp-line__top">
                        <span className="cdp-line__name">
                          {li.item_name ?? `Item #${li.item_id}`}
                        </span>
                        <span className={`line-badge ${lm.className}`}>{lm.label}</span>
                      </div>
                      <LineItemMeta li={li} />
                      {li.notes && <p className="cdp-line__notes">{li.notes}</p>}
                    </li>
                  )
                })}
              </ul>
            </div>
          )}

          {/* Print footer */}
          <div className="cdp__print-footer print-only">
            <p>EMS ReadyKit — Official Vehicle Inspection Record</p>
            <p>Check ID: {check.check_id} · Generated: {new Date().toLocaleString()}</p>
            <div className="cdp__sig-block">
              <div className="cdp__sig-line">
                <span>Responder Signature</span>
                <span>________________________________</span>
              </div>
              <div className="cdp__sig-line">
                <span>Supervisor Signature</span>
                <span>________________________________</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
