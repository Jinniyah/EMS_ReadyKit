/**
 * modules/check-wizard/components/DraftBanner.jsx
 * Resume/discard banner shown when an in-progress draft exists.
 * Shown on the home screen and at the top of the wizard if a draft
 * for a different vehicle/date exists.
 */
import React, { useState } from 'react'
import { formatSavedAt, formatCheckDate } from '../../../shared/utils/dateHelpers.js'
import Modal from '../../../shared/components/Modal.jsx'

export default function DraftBanner({ draft, onResume, onDiscard }) {
  const [showConfirm, setShowConfirm] = useState(false)

  if (!draft) return null

  return (
    <div className="draft-banner" role="note" aria-label="In-progress check draft">
      <div className="draft-banner__icon" aria-hidden="true">📋</div>
      <div className="draft-banner__info">
        <div className="draft-banner__title">
          Check in progress — Vehicle #{draft.vehicle_id}
        </div>
        <div className="draft-banner__date">
          {formatCheckDate(draft.check_date)}
        </div>
        <div className="draft-banner__saved">
          {formatSavedAt(draft.saved_at)}
        </div>
      </div>
      <div className="draft-banner__actions">
        <button
          className="btn btn--primary"
          onClick={onResume}
          type="button"
        >
          Resume
        </button>
        <button
          className="btn-text btn-text--danger"
          onClick={() => setShowConfirm(true)}
          type="button"
        >
          Discard
        </button>
      </div>

      <Modal
        open={showConfirm}
        title="Discard this draft?"
        confirmLabel="Yes, discard"
        cancelLabel="Keep draft"
        onConfirm={() => { setShowConfirm(false); onDiscard() }}
        onCancel={() => setShowConfirm(false)}
        danger
      >
        <p>
          All progress on the check for{' '}
          <strong>Vehicle #{draft.vehicle_id}</strong> on{' '}
          <strong>{formatCheckDate(draft.check_date)}</strong> will be lost.
        </p>
      </Modal>
    </div>
  )
}
