/**
 * modules/check-wizard/components/DraftBanner.jsx
 * Resume/discard banner for in-progress draft groups.
 *
 * A "group" is all drafts for the same vehicle/location on any date.
 * When there is only one draft in the group, Resume opens it directly.
 * When there are multiple (post-call restock, shift-start/end), a picker
 * modal shows each draft with its timestamp so the responder can choose.
 *
 * Uses selection_label instead of vehicle_id so jump bag drafts display
 * their label ("Unit 712 Jump Bag") rather than null.
 */
import React, { useState } from 'react'
import { formatSavedAt, formatCheckDate, formatShortDatetime } from '../../../shared/utils/dateHelpers.js'
import Modal from '../../../shared/components/Modal.jsx'

export default function DraftBanner({ group, onResume, onDiscard }) {
  const [showConfirm,  setShowConfirm]  = useState(false)
  const [showPicker,   setShowPicker]   = useState(false)

  if (!group || group.count === 0) return null

  const { selectionLabel, checkDate, count, drafts } = group

  // Single draft — resume immediately; no picker needed
  function handleResume() {
    if (count === 1) {
      onResume(drafts[0].key, drafts[0].draft)
    } else {
      setShowPicker(true)
    }
  }

  // Discard ALL drafts in this group
  function handleDiscardAll() {
    setShowConfirm(false)
    drafts.forEach(d => onDiscard(d.key))
  }

  const mostRecentSavedAt = drafts[0]?.draft.saved_at

  return (
    <div className="draft-banner" role="note" aria-label="In-progress check draft">
      <div className="draft-banner__icon" aria-hidden="true">📋</div>
      <div className="draft-banner__info">
        <div className="draft-banner__title">
          {count > 1
            ? `${count} checks in progress — ${selectionLabel}`
            : `Check in progress — ${selectionLabel}`}
        </div>
        <div className="draft-banner__date">
          {formatCheckDate(checkDate)}
        </div>
        <div className="draft-banner__saved">
          {formatSavedAt(mostRecentSavedAt)}
        </div>
      </div>
      <div className="draft-banner__actions">
        <button
          className="btn btn--primary"
          onClick={handleResume}
          type="button"
        >
          {count > 1 ? `Resume (${count})` : 'Resume'}
        </button>
        <button
          className="btn-text btn-text--danger"
          onClick={() => setShowConfirm(true)}
          type="button"
        >
          Discard
        </button>
      </div>

      {/* ── Discard confirmation ──────────────────────────────────────── */}
      <Modal
        open={showConfirm}
        title={count > 1 ? `Discard all ${count} drafts?` : 'Discard this draft?'}
        confirmLabel="Yes, discard"
        cancelLabel="Keep draft"
        onConfirm={handleDiscardAll}
        onCancel={() => setShowConfirm(false)}
        danger
      >
        <p>
          {count > 1
            ? `All ${count} in-progress checks for `
            : `The in-progress check for `}
          <strong>{selectionLabel}</strong>
          {checkDate && <> on <strong>{formatCheckDate(checkDate)}</strong></>} will be lost.
        </p>
      </Modal>

      {/* ── Multi-draft picker ────────────────────────────────────────── */}
      {showPicker && (
        <div className="draft-picker-overlay" role="dialog" aria-label="Choose which check to resume">
          <div className="draft-picker">
            <div className="draft-picker__header">
              <h2 className="draft-picker__title">Which check do you want to resume?</h2>
              <button
                className="btn-text"
                onClick={() => setShowPicker(false)}
                type="button"
                aria-label="Close picker"
              >
                Cancel
              </button>
            </div>
            <div className="draft-picker__list">
              {drafts.map(({ key, draft, savedAt }) => (
                <button
                  key={key}
                  className="draft-picker__item"
                  onClick={() => { setShowPicker(false); onResume(key, draft) }}
                  type="button"
                >
                  <div className="draft-picker__item-label">
                    {draft.notes
                      ? <strong>{draft.notes.split('\n')[0]}</strong>
                      : <span className="draft-picker__item-time">
                          Started {draft.started_at
                            ? formatShortDatetime(draft.started_at)
                            : formatSavedAt(draft.saved_at)}
                        </span>
                    }
                  </div>
                  <div className="draft-picker__item-meta">
                    {formatSavedAt(draft.saved_at)}
                    {' · '}
                    {Object.values(draft.compartments ?? {}).filter(c => c.status === 'complete').length}
                    {' / '}
                    {Object.values(draft.compartments ?? {}).length}
                    {' compartments done'}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
