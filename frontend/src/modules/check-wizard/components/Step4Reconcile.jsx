/**
 * modules/check-wizard/components/Step4Reconcile.jsx
 * Step 4 — Reconcile: interactive shopping list of short/missing items.
 *
 * Shown only when the draft contains warn-severity (SHORT) items after all
 * compartments are completed. Fail-severity items (broken AED, functional
 * fail) are shown read-only — they need supervisor attention and do not
 * block submission.
 *
 * Responder workflow:
 *   1. See the list — know exactly what to grab from the supply room
 *   2. Walk to supply room with device (or share list to partner's phone)
 *   3. Pull items; tap + on each row as they load the ambulance
 *   4. Each row turns green and disappears from the short list when resolved
 *   5. Once the short list is empty, "Continue to Submit →" becomes available
 *      (fail items never block — they are flagged for supervisor)
 *
 * Count updates write directly back to the draft (same path as ItemRow's
 * edit pencil) — so the final submission reflects the updated quantities.
 *
 * Share button fires navigator.share() with a plain-text snapshot of the
 * current list — for texting to a partner. Falls back to clipboard copy
 * on browsers without share support.
 */
import React, { useState, useCallback, useMemo } from 'react'
import { collectShortItems, collectFailItems, deriveDraftItemStatus, lineItemStatus } from '../../../shared/utils/statusCalc.js'

export default function Step4Reconcile({
  draft,
  selectionLabel,
  onUpdateItem,   // (compartmentId, payload) => void — same as Step 3
  onContinue,     // () => void — proceed to Step 5 Submit
  onBack,         // () => void — back to Step 2 Compartments
}) {
  const [shareStatus, setShareStatus] = useState(null) // null | 'copied' | 'shared'

  // Recompute short/fail lists reactively from draft on every render.
  // Since draft updates flow through from onUpdateItem → saveDraft → prop,
  // items disappear from the list as the responder restocks.
  const shortItems = useMemo(
    () => collectShortItems(draft?.compartments),
    [draft]
  )
  const failItems = useMemo(
    () => collectFailItems(draft?.compartments),
    [draft]
  )

  const allResolved = shortItems.length === 0

  // ── Inline count update ───────────────────────────────────────────────────
  // Finds the line item in the draft and applies the delta, then calls
  // onUpdateItem which writes it back through useDraft → localStorage.
  // Mirrors the exact same update path as the edit pencil in ItemRow.
  const handleIncrement = useCallback((item) => {
    const compKey = String(item.compartment_id)
    const cd      = draft?.compartments?.[compKey]
    const li      = cd?.line_items?.find(l => l.item_id === item.item_id)
    if (!li) return
    onUpdateItem(item.compartment_id, {
      ...li,
      quantity_found: (li.quantity_found ?? 0) + 1,
      confirmed:      true,
    })
    if (navigator.vibrate) navigator.vibrate([30])
  }, [draft, onUpdateItem])

  const handleDecrement = useCallback((item) => {
    const compKey = String(item.compartment_id)
    const cd      = draft?.compartments?.[compKey]
    const li      = cd?.line_items?.find(l => l.item_id === item.item_id)
    if (!li) return
    onUpdateItem(item.compartment_id, {
      ...li,
      quantity_found: Math.max(0, (li.quantity_found ?? 0) - 1),
      confirmed:      true,
    })
  }, [draft, onUpdateItem])

  const handleNoteChange = useCallback((item, value) => {
    const compKey = String(item.compartment_id)
    const cd      = draft?.compartments?.[compKey]
    const li      = cd?.line_items?.find(l => l.item_id === item.item_id)
    if (!li) return
    onUpdateItem(item.compartment_id, {
      ...li,
      notes:     value.trim() || null,
      confirmed: li.confirmed ?? true,
    })
  }, [draft, onUpdateItem])

  // ── Share / copy ──────────────────────────────────────────────────────────
  const buildShareText = useCallback(() => {
    const date  = draft?.check_date ?? new Date().toISOString().slice(0, 10)
    const label = selectionLabel || 'Check'

    const shortLines = shortItems.map(
      i => `• ${i.item_name} — have ${i.quantity_found}, need ${i.quantity_needed} (${i.compartment_name})`
    )
    const failLines = failItems.map(
      i => `• ${i.item_name} — ${i.check_type === 'FUNCTIONAL' ? 'functional fail' : 'missing'} (${i.compartment_name}) ⚠ supervisor`
    )

    const sections = []
    if (shortLines.length) sections.push(`NEED TO RESTOCK:\n${shortLines.join('\n')}`)
    if (failLines.length)  sections.push(`NEEDS SUPERVISOR:\n${failLines.join('\n')}`)

    return [
      `🚑 Reconcile List — ${label}`,
      date,
      '',
      ...sections,
      '',
      '— EMS ReadyKit',
    ].join('\n')
  }, [draft, selectionLabel, shortItems, failItems])

  const handleShare = useCallback(async () => {
    const text = buildShareText()
    if (navigator.share) {
      try {
        await navigator.share({ title: 'Reconcile List', text })
        setShareStatus('shared')
        setTimeout(() => setShareStatus(null), 2000)
      } catch {
        // User cancelled share — no feedback needed
      }
    } else {
      // Fallback: copy to clipboard
      try {
        await navigator.clipboard.writeText(text)
        setShareStatus('copied')
        setTimeout(() => setShareStatus(null), 2000)
      } catch {
        setShareStatus(null)
      }
    }
  }, [buildShareText])

  const shareLabel = shareStatus === 'shared' ? '✓ Shared!'
    : shareStatus === 'copied'  ? '✓ Copied!'
    : navigator.share           ? '📤 Share list'
    : '📋 Copy list'

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="wizard-step">

      {/* Header */}
      <div className="reconcile-header">
        <h2 className="wizard-step__title">Step 4 — Reconcile</h2>
        {(shortItems.length > 0 || failItems.length > 0) && (
          <button
            className="btn btn--secondary reconcile-share-btn"
            onClick={handleShare}
            type="button"
            aria-label="Share or copy the reconcile list"
          >
            {shareLabel}
          </button>
        )}
      </div>

      {/* All clear */}
      {allResolved && failItems.length === 0 && (
        <div className="reconcile-all-clear">
          <div className="reconcile-all-clear__icon" aria-hidden="true">✓</div>
          <div className="reconcile-all-clear__title">All items resolved</div>
          <div className="reconcile-all-clear__sub">Everything is stocked and accounted for.</div>
        </div>
      )}

      {/* Short items — interactive */}
      {shortItems.length > 0 && (
        <div className="reconcile-section">
          <h3 className="reconcile-section__title">
            Needs restocking
            <span className="reconcile-section__count">{shortItems.length}</span>
          </h3>
          <p className="reconcile-section__hint">
            Tap + as you load each item onto the vehicle. Items drop off the list when the count is met.
          </p>
          <div className="reconcile-list">
            {shortItems.map(item => (
              <ReconcileRow
                key={`${item.compartment_id}-${item.item_id}`}
                item={item}
                onIncrement={handleIncrement}
                onDecrement={handleDecrement}
                onNoteChange={handleNoteChange}
              />
            ))}
          </div>
        </div>
      )}

      {/* All short items resolved but fail items remain */}
      {allResolved && failItems.length > 0 && (
        <div className="reconcile-all-clear reconcile-all-clear--partial">
          <div className="reconcile-all-clear__icon" aria-hidden="true">✓</div>
          <div className="reconcile-all-clear__title">Restock complete</div>
          <div className="reconcile-all-clear__sub">
            The items below need supervisor attention and are logged automatically.
          </div>
        </div>
      )}

      {/* Fail items — read only */}
      {failItems.length > 0 && (
        <div className="reconcile-section reconcile-section--fail">
          <h3 className="reconcile-section__title reconcile-section__title--fail">
            Needs supervisor attention
            <span className="reconcile-section__count reconcile-section__count--fail">
              {failItems.length}
            </span>
          </h3>
          <p className="reconcile-section__hint">
            These items cannot be resolved during a daily check. They are flagged automatically and do not block submission.
          </p>
          <div className="reconcile-list">
            {failItems.map(item => (
              <FailRow key={`${item.compartment_id}-${item.item_id}`} item={item} />
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="reconcile-actions">
        <button className="btn btn--secondary" onClick={onBack} type="button">
          ← Back
        </button>
        <button
          className="btn btn--primary btn--large"
          onClick={onContinue}
          disabled={!allResolved}
          type="button"
        >
          {allResolved ? 'Continue to Submit →' : `${shortItems.length} item${shortItems.length !== 1 ? 's' : ''} remaining`}
        </button>
      </div>
    </div>
  )
}

// ── ReconcileRow — interactive short item ─────────────────────────────────────
function ReconcileRow({ item, onIncrement, onDecrement, onNoteChange }) {
  const [showNote, setShowNote] = useState(!!item.notes)

  const needed   = item.quantity_needed
  const found    = item.quantity_found
  const shortage = needed - found

  return (
    <div className="reconcile-row reconcile-row--short">
      <div className="reconcile-row__info">
        <div className="reconcile-row__name">{item.item_name}</div>
        <div className="reconcile-row__location">{item.compartment_name}</div>
        <div className="reconcile-row__qty">
          Have <strong>{found}</strong> · Need <strong>{needed}</strong>
          <span className="reconcile-row__shortage"> — grab {shortage} more</span>
        </div>
      </div>

      <div className="reconcile-row__controls">
        <button
          className="counter-btn"
          onClick={() => onDecrement(item)}
          disabled={found <= 0}
          type="button"
          aria-label={`Decrease count for ${item.item_name}`}
        >−</button>
        <span className="reconcile-row__count" aria-live="polite">{found}</span>
        <button
          className="counter-btn"
          onClick={() => onIncrement(item)}
          type="button"
          aria-label={`Increase count for ${item.item_name}`}
        >+</button>
      </div>

      {showNote ? (
        <textarea
          className="form-textarea reconcile-row__note"
          defaultValue={item.notes}
          onBlur={e => onNoteChange(item, e.target.value)}
          placeholder='e.g. "Building is also short of this item"'
          maxLength={150}
          rows={2}
          aria-label={`Note for ${item.item_name}`}
        />
      ) : (
        <button
          className="btn-text reconcile-row__add-note"
          onClick={() => setShowNote(true)}
          type="button"
        >
          + Add note
        </button>
      )}
    </div>
  )
}

// ── FailRow — read-only fail item ─────────────────────────────────────────────
function FailRow({ item }) {
  const reason = item.check_type === 'FUNCTIONAL'
    ? 'Functional check failed'
    : item.quantity_found === 0
      ? 'Count is zero — verify with supervisor'
      : 'Requires supervisor review'

  return (
    <div className="reconcile-row reconcile-row--fail">
      <div className="reconcile-row__info">
        <div className="reconcile-row__name">{item.item_name}</div>
        <div className="reconcile-row__location">{item.compartment_name}</div>
        <div className="reconcile-row__fail-reason">⚠ {reason}</div>
      </div>
      <div className="reconcile-row__supervisor-badge">Supervisor</div>
    </div>
  )
}
