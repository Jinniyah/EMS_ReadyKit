/**
 * modules/check-wizard/components/SubmittedScreen.jsx
 * Confirmation screen after a successful check submission.
 */
import React from 'react'
import { formatCheckDate, formatTime } from '../../../shared/utils/dateHelpers.js'

export default function SubmittedScreen({
  checkId, draft, vehicle, submittedAt, onStartNew, onGoHome,
}) {
  return (
    <div className="submitted-screen">
      <div className="submitted-screen__checkmark" aria-label="Check submitted successfully">
        ✓
      </div>

      <h1 className="submitted-screen__title">
        Unit {vehicle?.vehicle_number ?? draft?.vehicle_id} is ready
      </h1>

      <p className="submitted-screen__cleared">
        Truck is cleared for service
      </p>

      <div className="submitted-screen__ref" aria-label={`Check reference number ${checkId}`}>
        <div className="submitted-screen__ref-label">Check reference</div>
        <div className="submitted-screen__ref-id">#{checkId}</div>
      </div>

      <div className="submitted-screen__meta">
        <div>{formatCheckDate(draft?.check_date)}</div>
        <div>
          Submitted {formatTime(submittedAt)}
          {draft?.second_crew && <> · {draft.second_crew}</>}
        </div>
      </div>

      <div className="submitted-screen__actions">
        <button
          className="btn btn--primary"
          onClick={onGoHome}
          type="button"
        >
          ← Back to home
        </button>
        <button
          className="btn btn--secondary"
          onClick={onStartNew}
          type="button"
        >
          Start another check
        </button>
      </div>
    </div>
  )
}
