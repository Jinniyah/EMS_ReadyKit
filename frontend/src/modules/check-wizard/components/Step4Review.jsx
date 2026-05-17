/**
 * modules/check-wizard/components/Step4Review.jsx
 * Step 4: Review all compartments, add overall notes, repair flag, submit.
 *
 * Uses String(compartment_id) for all draft lookups — JSON round-trip
 * through localStorage converts numeric object keys to strings.
 */
import React, { useState } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { compartmentStatus } from '../../../shared/utils/statusCalc.js'
import { formatCheckDate } from '../../../shared/utils/dateHelpers.js'
import StatusBadge from '../../../shared/components/StatusBadge.jsx'
import Modal from '../../../shared/components/Modal.jsx'

export default function Step4Review({
  draft,
  vehicle,
  compartments,
  onSubmit,
  onBack,
  isSubmitting,
  submitError,
}) {
  const { user } = useAuth()
  const [overallNotes, setOverallNotes] = useState(draft?.overall_notes ?? '')
  const [repairNeeded, setRepairNeeded] = useState(draft?.repair_needed ?? false)
  const [repairNotes, setRepairNotes]   = useState(draft?.repair_notes  ?? '')
  const [showConfirm, setShowConfirm]   = useState(false)

  // Collect all line items across compartments for overall status preview
  const allLineItems = Object.values(draft?.compartments ?? {}).flatMap(
    c => c.line_items ?? []
  )
  const overallStatusKey = (() => {
    const hasFail = allLineItems.some(li =>
      ['MISSING', 'EXPIRED', 'FAIL', 'OVERDUE'].includes(li.status))
    const hasWarn = !hasFail && allLineItems.some(li =>
      ['SHORT', 'LOW'].includes(li.status))
    return hasFail ? 'FAIL' : hasWarn ? 'NEEDS_RESTOCK' : 'PASS'
  })()

  function handleConfirmSubmit() {
    setShowConfirm(false)
    onSubmit({ overallNotes, repairNeeded, repairNotes })
  }

  return (
    <div className="wizard-step">
      <h2 className="wizard-step__title">Step 4 — Review and submit</h2>

      {/* Identity confirmation */}
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

      {/* Check summary */}
      <div className="review-summary">
        <div className="review-summary__row">
          <span>Vehicle</span>
          <strong>Unit {vehicle?.vehicle_number ?? draft?.vehicle_id}</strong>
        </div>
        <div className="review-summary__row">
          <span>Check date</span>
          <strong>{formatCheckDate(draft?.check_date)}</strong>
        </div>
        <div className="review-summary__row">
          <span>Overall status</span>
          <StatusBadge status={overallStatusKey} />
        </div>
      </div>

      {/* Compartment summary — use String key for draft lookup */}
      <div className="review-compartments">
        <h3 className="review-section-title">Compartments</h3>
        {compartments?.map(comp => {
          const cd        = draft?.compartments?.[String(comp.compartment_id)]
          const lineItems = cd?.line_items ?? []
          const status    = compartmentStatus(lineItems)
          const statusKey = status.severity === 'fail' ? 'FAIL'
            : status.severity === 'warn' ? 'NEEDS_RESTOCK' : 'PASS'
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
        <label className="form-label">Repair or maintenance needed?</label>
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
            rows={3}
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
        <div className="form-error" role="alert">
          {submitError}
        </div>
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
          <strong>Unit {vehicle?.vehicle_number}</strong> on{' '}
          <strong>{formatCheckDate(draft?.check_date)}</strong>.
        </p>
        <p style={{ marginTop: '8px' }}>
          Submitted as: <strong>{user?.name}</strong>
          {draft?.second_crew && <> and <strong>{draft.second_crew}</strong></>}.
        </p>
        <p style={{ marginTop: '8px', color: 'var(--color-text-muted)', fontSize: '15px' }}>
          This action cannot be undone.
        </p>
      </Modal>
    </div>
  )
}
