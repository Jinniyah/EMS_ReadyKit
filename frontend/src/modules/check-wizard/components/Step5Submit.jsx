/**
 * modules/check-wizard/components/Step5Submit.jsx
 * Step 5 — Submit.
 *
 * PASS check: status badge + single "Submit — Unit NNN" button. No compartment
 * list, no repair toggle, no notes field, no confirmation modal. Fast path for
 * the common case — a clean truck at end of shift.
 *
 * NEEDS_RESTOCK / FAIL: full review — compartment list, repair toggle (pre-selected
 * on FAIL), notes field, confirmation modal.
 */
import React, { useState, useMemo } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import {
  compartmentStatus,
  deriveDraftItemStatus,
  lineItemStatus,
  collectFailItems,
  buildAutoRepairNotes,
} from '../../../shared/utils/statusCalc.js'
import { formatCheckDate } from '../../../shared/utils/dateHelpers.js'
import StatusBadge from '../../../shared/components/StatusBadge.jsx'
import Modal from '../../../shared/components/Modal.jsx'

export default function Step5Submit({
  draft,
  checkDate,
  vehicle,
  selectionLabel,
  compartments,
  onSubmit,
  onBack,
  isSubmitting,
  submitError,
}) {
  const { user } = useAuth()

  const failItems    = useMemo(() => collectFailItems(draft?.compartments), [draft])
  const hasFailItems = failItems.length > 0
  const autoRepairNotes = useMemo(
    () => buildAutoRepairNotes(draft?.compartments),
    [draft]
  )

  const [overallNotes, setOverallNotes] = useState(draft?.overall_notes ?? '')
  const [repairNeeded, setRepairNeeded] = useState(hasFailItems)
  const [repairNotes, setRepairNotes]   = useState(
    hasFailItems ? autoRepairNotes : (draft?.repair_notes ?? '')
  )
  const [showConfirm, setShowConfirm] = useState(false)

  const allLineItems = Object.values(draft?.compartments ?? {}).flatMap(
    c => c.line_items ?? []
  )
  const overallStatusKey = (() => {
    const hasFail = allLineItems.some(li => {
      const s = li.status ?? deriveDraftItemStatus(li)
      return s ? lineItemStatus(s).severity === 'fail' : false
    })
    const hasWarn = !hasFail && allLineItems.some(li => {
      const s = li.status ?? deriveDraftItemStatus(li)
      return s ? lineItemStatus(s).severity === 'warn' : false
    })
    return hasFail ? 'FAIL' : hasWarn ? 'NEEDS_RESTOCK' : 'PASS'
  })()

  const isPass = overallStatusKey === 'PASS'
  const displayDate  = checkDate ?? draft?.check_date
  const checkSubject = vehicle
    ? `Unit ${vehicle.vehicle_number}`
    : selectionLabel || 'This check'

  function handleSubmit() {
    onSubmit({ overallNotes, repairNeeded, repairNotes })
  }

  function handleConfirmSubmit() {
    setShowConfirm(false)
    onSubmit({ overallNotes, repairNeeded, repairNotes })
  }

  return (
    <div className="wizard-step">
      <h2 className="wizard-step__title">Step 5 — Submit</h2>

      {/* Identity */}
      <div className="review-identity" role="note">
        <span className="review-identity__label">Submitting as:</span>
        <span className="review-identity__name">{user?.name}</span>
        <span className="review-identity__role">{user?.role}</span>
      </div>
      {draft?.second_crew && (
        <div className="review-identity">
          <span className="review-identity__label">Second crew:</span>
          <span className="review-identity__name">{draft.second_crew}</span>
        </div>
      )}

      {/* Summary */}
      <div className="review-summary">
        <div className="review-summary__row">
          <span>Check subject</span>
          <strong>{checkSubject}</strong>
        </div>
        <div className="review-summary__row">
          <span>Check date</span>
          <strong>{formatCheckDate(displayDate)}</strong>
        </div>
        <div className="review-summary__row">
          <span>Overall status</span>
          <StatusBadge status={overallStatusKey} />
        </div>
      </div>

      {/* ── PASS fast path — no extra sections ───────────────────────── */}
      {isPass && (
        <>
          {submitError && (
            <div className="form-error" role="alert">{submitError}</div>
          )}
          <div className="step4-actions">
            <button className="btn btn--secondary" onClick={onBack} type="button">
              ← Back
            </button>
            <button
              className="btn btn--primary btn--large"
              onClick={handleSubmit}
              disabled={isSubmitting}
              type="button"
            >
              {isSubmitting ? 'Submitting…' : `Submit — ${checkSubject}`}
            </button>
          </div>
        </>
      )}

      {/* ── FAIL / NEEDS_RESTOCK — full review ───────────────────────── */}
      {!isPass && (
        <>
          {/* Compartment list */}
          <div className="review-compartments">
            <h3 className="review-section-title">Compartments</h3>
            {compartments?.map(comp => {
              const cd        = draft?.compartments?.[String(comp.compartment_id)]
              const lineItems = cd?.line_items ?? []
              const status    = compartmentStatus(lineItems)
              const statusKey = status.severity === 'fail'  ? 'FAIL'
                : status.severity === 'warn' ? 'NEEDS_RESTOCK'
                : 'PASS'
              return (
                <div key={comp.compartment_id} className="review-compartment-row">
                  <span className="review-compartment-row__name">{comp.name}</span>
                  <StatusBadge status={statusKey} size="sm" />
                </div>
              )
            })}
          </div>

          {/* Repair flag */}
          <div className="form-group">
            <label className="form-label">
              Repair or maintenance needed?
              {hasFailItems && (
                <span className="form-label__optional"> — pre-filled from failed items</span>
              )}
            </label>
            <div className="toggle-group" role="radiogroup">
              <button
                role="radio"
                aria-checked={!repairNeeded}
                className={`toggle-btn ${!repairNeeded ? 'toggle-btn--active' : ''}`}
                onClick={() => setRepairNeeded(false)}
                type="button"
              >
                No issues
              </button>
              <button
                role="radio"
                aria-checked={repairNeeded}
                className={`toggle-btn toggle-btn--warn ${repairNeeded ? 'toggle-btn--active' : ''}`}
                onClick={() => setRepairNeeded(true)}
                type="button"
              >
                ⚠ Repair needed
              </button>
            </div>
            {repairNeeded && (
              <textarea
                className="form-textarea"
                value={repairNotes}
                onChange={e => setRepairNotes(e.target.value)}
                placeholder="Describe the repair needed…"
                rows={4}
                aria-label="Repair description"
              />
            )}
          </div>

          {/* Overall notes */}
          <div className="form-group">
            <label className="form-label" htmlFor="overall-notes">
              Overall notes <span className="form-label__optional">(optional)</span>
            </label>
            <textarea
              id="overall-notes"
              className="form-textarea"
              value={overallNotes}
              onChange={e => setOverallNotes(e.target.value)}
              placeholder="Any notes about this check…"
              rows={3}
              maxLength={500}
            />
          </div>

          {submitError && (
            <div className="form-error" role="alert">{submitError}</div>
          )}

          <div className="step4-actions">
            <button className="btn btn--secondary" onClick={onBack} type="button">
              ← Back
            </button>
            <button
              className="btn btn--primary btn--large"
              onClick={() => setShowConfirm(true)}
              disabled={isSubmitting}
              type="button"
            >
              {isSubmitting ? 'Submitting…' : 'Submit check'}
            </button>
          </div>

          <Modal
            open={showConfirm}
            title="Submit this check?"
            confirmLabel="Yes, submit"
            cancelLabel="Go back"
            onConfirm={handleConfirmSubmit}
            onCancel={() => setShowConfirm(false)}
          >
            <p>
              You are submitting the daily check for{' '}
              <strong>{checkSubject}</strong> on{' '}
              <strong>{formatCheckDate(displayDate)}</strong>.
            </p>
            <p style={{ marginTop: '8px' }}>
              Submitted as: <strong>{user?.name}</strong>
              {draft?.second_crew && <> and <strong>{draft.second_crew}</strong></>}.
            </p>
            {hasFailItems && (
              <p style={{ marginTop: '8px', color: 'var(--color-status-fail)', fontWeight: 600 }}>
                ⚠ {failItems.length} item{failItems.length !== 1 ? 's' : ''} flagged for supervisor attention.
              </p>
            )}
            <p style={{ marginTop: '8px', color: 'var(--color-text-muted)', fontSize: '15px' }}>
              This action cannot be undone.
            </p>
          </Modal>
        </>
      )}
    </div>
  )
}
