/**
 * modules/check-wizard/components/Step4Reconcile.jsx
 * Step 4 — Reconcile: interactive shopping list of short/missing/low items.
 *
 * SUPPLY/DOCUMENT items show the count +/− controls.
 * MEASUREMENT items show a read-only "reading was X, minimum is Y" row —
 *   they cannot be topped off by the responder; they need physical action
 *   (e.g. refill O2 tank) and then a re-check. So they appear in the
 *   supervisor attention section, not the interactive restock section.
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

  const allShortItems = useMemo(() => collectShortItems(draft?.compartments), [draft])
  const failItems     = useMemo(() => collectFailItems(draft?.compartments),  [draft])

  // Split short items: interactive restock (SUPPLY/DOCUMENT) vs
  // read-only low-reading items (MEASUREMENT) which need physical action
  const restockItems      = allShortItems.filter(i => i.check_type === 'SUPPLY' || i.check_type === 'DOCUMENT')
  const lowReadingItems   = allShortItems.filter(i => i.check_type === 'MEASUREMENT')

  // All interactive restock items must be resolved before continuing
  const allResolved = restockItems.length === 0

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
    const restockLines = restockItems.map(i =>
      `• ${i.item_name} — have ${i.quantity_found}, need ${i.quantity_needed} (${i.compartment_name})`
    )
    const lowLines = lowReadingItems.map(i =>
      `• ${i.item_name} — reading ${i.measurement_value}, min ${i.min_value} (${i.compartment_name}) ⚠ needs attention`
    )
    const failLines = failItems.map(i =>
      `• ${i.item_name} — ${i.check_type === 'FUNCTIONAL' ? 'functional fail' : 'missing'} (${i.compartment_name}) ⚠ supervisor`
    )
    const sections = []
    if (restockLines.length) sections.push(`NEED TO RESTOCK:\n${restockLines.join('\n')}`)
    if (lowLines.length)     sections.push(`LOW READINGS:\n${lowLines.join('\n')}`)
    if (failLines.length)    sections.push(`NEEDS SUPERVISOR:\n${failLines.join('\n')}`)
    return [`🚑 Restock List — ${label}`, date, '', ...sections, '', '— EMS ReadyKit'].join('\n')
  }, [draft, selectionLabel, restockItems, lowReadingItems, failItems])

  const handleShare = useCallback(async () => {
    const text = buildShareText()
    if (navigator.share) {
      try { await navigator.share({ title: 'Restock List', text }); setShareStatus('shared'); setTimeout(() => setShareStatus(null), 2000) }
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

  const hasAnything = allShortItems.length > 0 || failItems.length > 0

  return (
    <div className="wizard-step">

      <div className="reconcile-header">
        <h2 className="wizard-step__title">Step 4 — Restock</h2>
        {hasAnything && (
          <button className="btn btn--secondary reconcile-share-btn" onClick={handleShare}
            type="button" aria-label="Share or copy the restock list">{shareLabel}</button>
        )}
      </div>

      {/* All clear */}
      {allResolved && failItems.length === 0 && lowReadingItems.length === 0 && (
        <div className="reconcile-all-clear">
          <div className="reconcile-all-clear__icon" aria-hidden="true">✓</div>
          <div className="reconcile-all-clear__title">All items resolved</div>
          <div className="reconcile-all-clear__sub">Everything is stocked and accounted for.</div>
        </div>
      )}

      {/* Interactive restock items — SUPPLY/DOCUMENT only */}
      {restockItems.length > 0 && (
        <div className="reconcile-section">
          <h3 className="reconcile-section__title">
            Needs restocking
            <span className="reconcile-section__count">{restockItems.length}</span>
          </h3>
          <p className="reconcile-section__hint">
            Tap "Add N" to top off, or use −/+ if you grabbed a different number.
          </p>
          <div className="reconcile-list">
            {restockItems.map(item => (
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

      {/* Low readings — MEASUREMENT items below minimum */}
      {lowReadingItems.length > 0 && (
        <div className="reconcile-section">
          <h3 className="reconcile-section__title">
            Low readings
            <span className="reconcile-section__count">{lowReadingItems.length}</span>
          </h3>
          <p className="reconcile-section__hint">
            These readings are below minimum. Address the issue, then re-check.
          </p>
          <div className="reconcile-list">
            {lowReadingItems.map(item => (
              <LowReadingRow key={`${item.compartment_id}-${item.item_id}`} item={item} />
            ))}
          </div>
        </div>
      )}

      {/* Partial completion banner */}
      {allResolved && (failItems.length > 0 || lowReadingItems.length > 0) && (
        <div className="reconcile-all-clear reconcile-all-clear--partial">
          <div className="reconcile-all-clear__icon" aria-hidden="true">✓</div>
          <div className="reconcile-all-clear__title">Restock complete</div>
          <div className="reconcile-all-clear__sub">
            The items below need attention and are flagged automatically.
          </div>
        </div>
      )}

      {/* Fail items — need supervisor */}
      {failItems.length > 0 && (
        <div className="reconcile-section reconcile-section--fail">
          <h3 className="reconcile-section__title reconcile-section__title--fail">
            Needs supervisor attention
            <span className="reconcile-section__count reconcile-section__count--fail">{failItems.length}</span>
          </h3>
          <p className="reconcile-section__hint">
            These items cannot be resolved during a daily check. They are flagged automatically.
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
        <button className="btn btn--primary btn--large" onClick={onContinue} type="button">
          {allResolved
            ? 'Continue to Submit →'
            : `Continue with ${restockItems.length} item${restockItems.length !== 1 ? 's' : ''} short →`}
        </button>
      </div>
    </div>
  )
}

// ── ReconcileRow — SUPPLY/DOCUMENT items ─────────────────────────────────────
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

      <div className="supply-input__counter">
        <button className="counter-btn" onClick={() => onDecrement(item)}
          disabled={item.quantity_found <= 0} type="button"
          aria-label={`Decrease count for ${item.item_name}`}>−</button>
        <span className="reconcile-row__count" aria-live="polite">{item.quantity_found}</span>
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
          onClick={() => setShowNote(true)} type="button">+ Add note</button>
      )}
    </div>
  )
}

// ── LowReadingRow — MEASUREMENT items below minimum ───────────────────────────
// These cannot be "topped off" by the responder — they need physical action
// (e.g. refill O2, recharge AED) and then a re-check. Show the actual reading
// and the minimum so the responder knows what they are dealing with.
function LowReadingRow({ item }) {
  return (
    <div className="reconcile-row reconcile-row--short">
      <div className="reconcile-row__info">
        <div className="reconcile-row__name">{item.item_name}</div>
        <div className="reconcile-row__location">{item.compartment_name}</div>
        <div className="reconcile-row__qty">
          Reading <strong>{item.measurement_value}</strong>
          {item.min_value != null && (
            <> · Minimum <strong>{item.min_value}</strong>
              <span className="reconcile-row__shortage"> — below minimum</span>
            </>
          )}
        </div>
      </div>
      <div className="reconcile-row__supervisor-badge">Address &amp; re-check</div>
    </div>
  )
}

// ── FailRow — FUNCTIONAL/MISSING items ───────────────────────────────────────
function FailRow({ item }) {
  const reason = item.check_type === 'FUNCTIONAL'
    ? 'Problem found — needs supervisor'
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
