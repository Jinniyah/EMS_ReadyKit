/**
 * modules/check-wizard/components/Step4Reconcile.jsx
 * Step 4 — Reconcile: interactive shopping list of short/missing items.
 *
 * Controls row mirrors Step 3 Items exactly:
 *   [ − ]  [ count ]  [ + ]  [ Add N ]
 *
 * "Add N" sits to the right of + — same position as "All N present" on
 * Step 3 — so the interface is immediately familiar. One tap tops off the
 * count to par and the row disappears. The −/+ are still there for when the
 * responder grabbed a different number than the full shortage.
 */
import React, { useState, useCallback, useMemo } from 'react'
import { collectShortItems, collectFailItems } from '../../../shared/utils/statusCalc.js'

export default function Step4Reconcile({
  draft,
  selectionLabel,
  onUpdateItem,
  onContinue,
  onBack,
}) {
  const [shareStatus, setShareStatus] = useState(null)

  const shortItems  = useMemo(() => collectShortItems(draft?.compartments), [draft])
  const failItems   = useMemo(() => collectFailItems(draft?.compartments),  [draft])
  const allResolved = shortItems.length === 0

  const _getLineItem = useCallback((item) => {
    const cd = draft?.compartments?.[String(item.compartment_id)]
    return cd?.line_items?.find(l => l.item_id === item.item_id) ?? null
  }, [draft])

  const handleIncrement = useCallback((item) => {
    const li = _getLineItem(item)
    if (!li) return
    onUpdateItem(item.compartment_id, { ...li, quantity_found: (li.quantity_found ?? 0) + 1, confirmed: true })
    if (navigator.vibrate) navigator.vibrate([30])
  }, [_getLineItem, onUpdateItem])

  const handleDecrement = useCallback((item) => {
    const li = _getLineItem(item)
    if (!li) return
    onUpdateItem(item.compartment_id, { ...li, quantity_found: Math.max(0, (li.quantity_found ?? 0) - 1), confirmed: true })
  }, [_getLineItem, onUpdateItem])

  const handleTopOff = useCallback((item) => {
    const li = _getLineItem(item)
    if (!li) return
    onUpdateItem(item.compartment_id, { ...li, quantity_found: item.quantity_needed, confirmed: true })
    if (navigator.vibrate) navigator.vibrate([40])
  }, [_getLineItem, onUpdateItem])

  const handleNoteChange = useCallback((item, value) => {
    const li = _getLineItem(item)
    if (!li) return
    onUpdateItem(item.compartment_id, { ...li, notes: value.trim() || null, confirmed: li.confirmed ?? true })
  }, [_getLineItem, onUpdateItem])

  const buildShareText = useCallback(() => {
    const date  = draft?.check_date ?? new Date().toISOString().slice(0, 10)
    const label = selectionLabel || 'Check'
    const shortLines = shortItems.map(i =>
      `• ${i.item_name} — have ${i.quantity_found}, need ${i.quantity_needed} (${i.compartment_name})`
    )
    const failLines = failItems.map(i =>
      `• ${i.item_name} — ${i.check_type === 'FUNCTIONAL' ? 'functional fail' : 'missing'} (${i.compartment_name}) ⚠ supervisor`
    )
    const sections = []
    if (shortLines.length) sections.push(`NEED TO RESTOCK:\n${shortLines.join('\n')}`)
    if (failLines.length)  sections.push(`NEEDS SUPERVISOR:\n${failLines.join('\n')}`)
    return [`🚑 Reconcile List — ${label}`, date, '', ...sections, '', '— EMS ReadyKit'].join('\n')
  }, [draft, selectionLabel, shortItems, failItems])

  const handleShare = useCallback(async () => {
    const text = buildShareText()
    if (navigator.share) {
      try { await navigator.share({ title: 'Reconcile List', text }); setShareStatus('shared'); setTimeout(() => setShareStatus(null), 2000) }
      catch { /* user cancelled */ }
    } else {
      try { await navigator.clipboard.writeText(text); setShareStatus('copied'); setTimeout(() => setShareStatus(null), 2000) }
      catch { setShareStatus(null) }
    }
  }, [buildShareText])

  const shareLabel = shareStatus === 'shared' ? '✓ Shared!'
    : shareStatus === 'copied'  ? '✓ Copied!'
    : navigator.share           ? '📤 Share list'
    : '📋 Copy list'

  return (
    <div className="wizard-step">

      <div className="reconcile-header">
        <h2 className="wizard-step__title">Step 4 — Reconcile</h2>
        {(shortItems.length > 0 || failItems.length > 0) && (
          <button className="btn btn--secondary reconcile-share-btn" onClick={handleShare}
            type="button" aria-label="Share or copy the reconcile list">{shareLabel}</button>
        )}
      </div>

      {allResolved && failItems.length === 0 && (
        <div className="reconcile-all-clear">
          <div className="reconcile-all-clear__icon" aria-hidden="true">✓</div>
          <div className="reconcile-all-clear__title">All items resolved</div>
          <div className="reconcile-all-clear__sub">Everything is stocked and accounted for.</div>
        </div>
      )}

      {shortItems.length > 0 && (
        <div className="reconcile-section">
          <h3 className="reconcile-section__title">
            Needs restocking
            <span className="reconcile-section__count">{shortItems.length}</span>
          </h3>
          <p className="reconcile-section__hint">
            Tap "Add N" to top off, or use −/+ if you grabbed a different number.
          </p>
          <div className="reconcile-list">
            {shortItems.map(item => (
              <ReconcileRow
                key={`${item.compartment_id}-${item.item_id}`}
                item={item}
                onIncrement={handleIncrement}
                onDecrement={handleDecrement}
                onTopOff={handleTopOff}
                onNoteChange={handleNoteChange}
              />
            ))}
          </div>
        </div>
      )}

      {allResolved && failItems.length > 0 && (
        <div className="reconcile-all-clear reconcile-all-clear--partial">
          <div className="reconcile-all-clear__icon" aria-hidden="true">✓</div>
          <div className="reconcile-all-clear__title">Restock complete</div>
          <div className="reconcile-all-clear__sub">
            The items below need supervisor attention and are logged automatically.
          </div>
        </div>
      )}

      {failItems.length > 0 && (
        <div className="reconcile-section reconcile-section--fail">
          <h3 className="reconcile-section__title reconcile-section__title--fail">
            Needs supervisor attention
            <span className="reconcile-section__count reconcile-section__count--fail">{failItems.length}</span>
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

      <div className="reconcile-actions">
        <button className="btn btn--secondary" onClick={onBack} type="button">← Back</button>
        <button className="btn btn--primary btn--large" onClick={onContinue} disabled={!allResolved} type="button">
          {allResolved ? 'Continue to Submit →' : `${shortItems.length} item${shortItems.length !== 1 ? 's' : ''} remaining`}
        </button>
      </div>
    </div>
  )
}

// ── ReconcileRow ──────────────────────────────────────────────────────────────
// Controls row: [ − ] [ count ] [ + ] [ Add N ]
// Matches the Step 3 supply counter layout exactly — same classes, same order,
// so the interface feels identical and requires no relearning.
function ReconcileRow({ item, onIncrement, onDecrement, onTopOff, onNoteChange }) {
  const [showNote, setShowNote] = useState(!!item.notes)
  const shortage = item.quantity_needed - item.quantity_found

  return (
    <div className="reconcile-row reconcile-row--short">
      <div className="reconcile-row__info">
        <div className="reconcile-row__name">{item.item_name}</div>
        <div className="reconcile-row__location">{item.compartment_name}</div>
        <div className="reconcile-row__qty">
          Have <strong>{item.quantity_found}</strong> · Need <strong>{item.quantity_needed}</strong>
          <span className="reconcile-row__shortage"> — grab {shortage} more</span>
        </div>
      </div>

      {/* Single control row: − count + [Add N]  ← matches Step 3 exactly */}
      <div className="supply-input__counter">
        <button className="counter-btn" onClick={() => onDecrement(item)}
          disabled={item.quantity_found <= 0} type="button"
          aria-label={`Decrease count for ${item.item_name}`}>−</button>

        <span className="reconcile-row__count" aria-live="polite">
          {item.quantity_found}
        </span>

        <button className="counter-btn" onClick={() => onIncrement(item)}
          type="button" aria-label={`Increase count for ${item.item_name}`}>+</button>

        <button className="btn btn--all-present" onClick={() => onTopOff(item)}
          type="button" aria-label={`Add ${shortage} ${item.item_name} to meet par`}>
          Add {shortage}
        </button>
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
        <button className="btn-text reconcile-row__add-note"
          onClick={() => setShowNote(true)} type="button">
          + Add note
        </button>
      )}
    </div>
  )
}

// ── FailRow ───────────────────────────────────────────────────────────────────
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
