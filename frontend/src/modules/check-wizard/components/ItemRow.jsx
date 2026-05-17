/**
 * modules/check-wizard/components/ItemRow.jsx
 *
 * Simplified data flow — one source of truth:
 *   Every interaction (+ / − / All present / Submit count) immediately
 *   writes to the draft via onUpdate(payload). There is no separate
 *   "local state vs draft" split. When you re-enter a compartment, every
 *   row reads its current value directly from draftItem.
 *
 * Card states:
 *   untouched  — draftItem is null, white background
 *   touched    — draftItem exists, quantity_found > 0, green background
 *   zero       — draftItem exists, quantity_found = 0, yellow background
 *   confirmed  — draftItem.confirmed = true, green/yellow + locked display
 *
 * "Submit count" / "All present" set confirmed=true → shows locked display
 *   with ✏ edit button.
 * Clicking ✏ sets confirmed=false → back to edit mode with current values.
 * "Save compartment" works regardless of confirmed state — whatever is in
 *   the draft at that moment is saved.
 */
import React, { useState, useRef, useCallback } from 'react'
import { lineItemStatus, checkTypeLabel } from '../../../shared/utils/statusCalc.js'
import { formatShortDate, isExpired } from '../../../shared/utils/dateHelpers.js'

export default function ItemRow({
  item,
  parLevel,
  lot,
  draftItem,    // current saved state from draft (null if untouched)
  onUpdate,     // (payload) => void — called on every change, immediately persists
  onTouched,    // (itemId) => void — called on first interaction
}) {
  const checkType      = item.check_type ?? 'SUPPLY'
  const quantityNeeded = parLevel?.min_quantity ?? 0
  const touchedRef     = useRef(false)
  const [showNotes, setShowNotes] = useState(!!(draftItem?.notes))
  const notesRef = useRef(null)

  const touch = useCallback(() => {
    if (!touchedRef.current) {
      touchedRef.current = true
      onTouched?.(item.item_id)
    }
  }, [item.item_id, onTouched])

  // ── Core update function — writes everything to draft immediately ──────────
  const persist = useCallback((fields) => {
    touch()
    onUpdate({
      item_id:           item.item_id,
      quantity_needed:   quantityNeeded,
      quantity_found:    draftItem?.quantity_found    ?? 0,
      measurement_value: draftItem?.measurement_value ?? null,
      functional_pass:   draftItem?.functional_pass   ?? null,
      date_value:        draftItem?.date_value         ?? null,
      notes:             draftItem?.notes              ?? null,
      confirmed:         draftItem?.confirmed          ?? false,
      ...fields,
    })
  }, [touch, onUpdate, item.item_id, quantityNeeded, draftItem])

  // ── Quantity helpers ──────────────────────────────────────────────────────
  const currentQty = draftItem?.quantity_found ?? 0

  const handleIncrement = useCallback(() => {
    persist({ quantity_found: currentQty + 1, confirmed: false })
  }, [persist, currentQty])

  const handleDecrement = useCallback(() => {
    persist({ quantity_found: Math.max(0, currentQty - 1), confirmed: false })
  }, [persist, currentQty])

  const handleSetQty = useCallback((val) => {
    const n = parseInt(val, 10)
    if (!isNaN(n) && n >= 0) {
      persist({ quantity_found: n, confirmed: false })
    }
  }, [persist])

  // ── All present — sets quantity to needed AND confirms ────────────────────
  const handleAllPresent = useCallback(() => {
    persist({
      quantity_found: quantityNeeded,
      confirmed:      true,
    })
    if (navigator.vibrate) navigator.vibrate([40])
  }, [persist, quantityNeeded])

  // ── Submit count — confirms current values ────────────────────────────────
  const handleSubmitCount = useCallback(() => {
    persist({ confirmed: true })
    if (navigator.vibrate) {
      const qty = draftItem?.quantity_found ?? 0
      navigator.vibrate(qty === 0 ? [80, 40, 80] : [40])
    }
  }, [persist, draftItem])

  // ── Measurement / functional / date ───────────────────────────────────────
  const handleMeasurement = useCallback((val) => {
    persist({ measurement_value: parseFloat(val) || null, confirmed: false })
  }, [persist])

  const handleFunctional = useCallback((val) => {
    persist({ functional_pass: val, confirmed: false })
  }, [persist])

  const handleDate = useCallback((val) => {
    persist({ date_value: val || null, confirmed: false })
  }, [persist])

  const handleNotes = useCallback((val) => {
    persist({ notes: val.trim() || null })
  }, [persist])

  // ── Edit (pencil) — just un-confirms, keeps all values ───────────────────
  const handleEdit = useCallback(() => {
    persist({ confirmed: false })
  }, [persist])

  // ── Keypad ────────────────────────────────────────────────────────────────
  const [showKeypad, setShowKeypad] = useState(false)
  const [keypadValue, setKeypadValue] = useState('0')

  const openKeypad = useCallback(() => {
    touch()
    setKeypadValue(String(currentQty))
    setShowKeypad(true)
  }, [touch, currentQty])

  const commitKeypad = useCallback(() => {
    handleSetQty(keypadValue)
    setShowKeypad(false)
  }, [handleSetQty, keypadValue])

  // ── Derived display values ────────────────────────────────────────────────
  const hasDraft    = draftItem !== null
  const confirmed   = draftItem?.confirmed ?? false
  const isZeroTouch = hasDraft && (checkType === 'SUPPLY' || checkType === 'DOCUMENT') &&
                      (draftItem?.quantity_found ?? 0) === 0

  // Row background:
  //   no draft    → white (untouched)
  //   zero count  → yellow (may be a mistake)
  //   otherwise   → green
  const rowBg = !hasDraft
    ? 'var(--color-surface)'
    : isZeroTouch
      ? 'var(--color-status-warn-bg)'
      : 'var(--color-status-pass-bg)'

  const countLabel = (() => {
    if (checkType === 'MEASUREMENT') return `${draftItem?.measurement_value ?? '—'} ${item.unit_of_measure}`
    if (checkType === 'FUNCTIONAL')  return draftItem?.functional_pass === true ? 'Pass' : draftItem?.functional_pass === false ? 'Fail' : '—'
    if (checkType === 'DATE_RECORD') return draftItem?.date_value ?? '—'
    return `${draftItem?.quantity_found ?? 0} counted`
  })()

  // ── Confirmed (locked) display ────────────────────────────────────────────
  if (confirmed) {
    return (
      <div
        className="item-row item-row--confirmed"
        style={{ '--row-bg': rowBg }}
        aria-label={`${item.name}: ${countLabel}`}
      >
        <div className="item-row__submitted-inner">
          <div className="item-row__submitted-left">
            <div className="item-row__name item-row__name--submitted">
              {item.name}
              {item.controlled_substance && (
                <span className="item-row__cs-badge" aria-label="Controlled substance">🔒</span>
              )}
            </div>
            <div className="item-row__submitted-count">
              {countLabel}
              {isZeroTouch && (
                <span className="item-row__zero-warning"> ⚠ check count</span>
              )}
              {draftItem?.notes && (
                <div className="item-row__submitted-note">📝 {draftItem.notes}</div>
              )}
            </div>
          </div>
          <button
            className="item-row__edit-btn"
            onClick={handleEdit}
            type="button"
            aria-label={`Edit count for ${item.name}`}
            title="Edit count"
          >✏</button>
        </div>
      </div>
    )
  }

  // ── Edit display ──────────────────────────────────────────────────────────
  return (
    <div
      className="item-row item-row--pending"
      style={{ '--row-bg': rowBg }}
    >
      <div className="item-row__header">
        <div className="item-row__name">
          {item.name}
          {item.controlled_substance && (
            <span className="item-row__cs-badge" aria-label="Controlled substance">🔒 CS</span>
          )}
          {checkType !== 'SUPPLY' && (
            <span className="item-row__type-badge">{checkTypeLabel(checkType)}</span>
          )}
        </div>
      </div>

      {lot && (
        <div className={`item-row__lot ${isExpired(lot.expiration_date) ? 'item-row__lot--expired' : ''}`}>
          Lot {lot.lot_number ?? '—'}
          {lot.expiration_date && (
            <> · Exp {formatShortDate(lot.expiration_date)}
              {isExpired(lot.expiration_date) && <span className="item-row__expired-tag"> EXPIRED</span>}
            </>
          )}
        </div>
      )}

      {(checkType === 'SUPPLY' || checkType === 'DOCUMENT') && (
        <div className="item-row__need">Need: <strong>{quantityNeeded}</strong></div>
      )}

      {/* Input controls */}
      <div className="item-row__input">
        {(checkType === 'SUPPLY' || checkType === 'DOCUMENT') && (
          <div className="supply-input__counter">
            <button
              className="counter-btn"
              onClick={handleDecrement}
              disabled={currentQty <= 0}
              type="button"
              aria-label="Decrease quantity"
            >−</button>

            <button
              className="counter-value"
              onClick={openKeypad}
              type="button"
              aria-label={`Quantity: ${currentQty}. Tap to type.`}
            >{currentQty}</button>

            <button
              className="counter-btn"
              onClick={handleIncrement}
              type="button"
              aria-label="Increase quantity"
            >+</button>

            {quantityNeeded > 0 && (
              <button
                className="btn btn--all-present"
                onClick={handleAllPresent}
                type="button"
                aria-label={`All ${quantityNeeded} present`}
              >
                All {quantityNeeded} present
              </button>
            )}
          </div>
        )}

        {checkType === 'MEASUREMENT' && (
          <MeasurementInput
            value={draftItem?.measurement_value ?? ''}
            onChange={handleMeasurement}
            unit={item.unit_of_measure}
            minimum={item.measurement_minimum}
          />
        )}

        {checkType === 'FUNCTIONAL' && (
          <FunctionalInput
            value={draftItem?.functional_pass ?? null}
            onChange={handleFunctional}
          />
        )}

        {checkType === 'DATE_RECORD' && (
          <DateRecordInput
            value={draftItem?.date_value ?? ''}
            onChange={handleDate}
          />
        )}
      </div>

      {/* Notes */}
      {showNotes && (
        <div className="item-row__notes">
          <textarea
            ref={notesRef}
            className="form-textarea"
            defaultValue={draftItem?.notes ?? ''}
            onBlur={e => handleNotes(e.target.value)}
            placeholder="Add a note… (max 150 characters)"
            maxLength={150}
            rows={2}
            aria-label={`Note for ${item.name}`}
          />
        </div>
      )}

      {/* Action bar */}
      <div className="item-row__actions">
        {!showNotes ? (
          <button
            className="btn-text"
            onClick={() => { setShowNotes(true); setTimeout(() => notesRef.current?.focus(), 50) }}
            type="button"
            aria-label={`Add note for ${item.name}`}
          >+ Note</button>
        ) : <div />}

        <button
          className="btn btn--submit-count"
          onClick={handleSubmitCount}
          type="button"
          aria-label={`Submit count for ${item.name}`}
        >Submit count</button>
      </div>

      {/* Keypad overlay */}
      {showKeypad && (
        <div className="keypad-overlay" role="dialog" aria-label="Enter quantity">
          <div className="keypad">
            <div className="keypad__context">Need: {quantityNeeded}</div>
            <input
              className="keypad__display"
              type="number"
              inputMode="numeric"
              value={keypadValue}
              onChange={e => setKeypadValue(e.target.value)}
              autoFocus
              min={0}
              aria-label="Quantity"
            />
            <div className="keypad__buttons">
              {['1','2','3','4','5','6','7','8','9','','0','⌫'].map((k, i) => (
                <button
                  key={i}
                  className={`keypad__key ${!k ? 'keypad__key--empty' : ''}`}
                  onClick={() => {
                    if (!k) return
                    if (k === '⌫') setKeypadValue(v => v.slice(0, -1) || '0')
                    else setKeypadValue(v => v === '0' ? k : v + k)
                  }}
                  type="button"
                  aria-label={k === '⌫' ? 'Backspace' : k || undefined}
                >{k}</button>
              ))}
            </div>
            <div className="keypad__actions">
              <button className="btn btn--secondary" onClick={() => setShowKeypad(false)} type="button">Cancel</button>
              <button className="btn btn--primary" onClick={commitKeypad} type="button">Confirm</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function MeasurementInput({ value, onChange, unit, minimum }) {
  return (
    <div className="measurement-input">
      <label className="measurement-input__label">
        Reading ({unit})
        {minimum != null && <span className="measurement-input__min"> — min {minimum}</span>}
      </label>
      <input
        type="number" inputMode="decimal"
        className="form-input measurement-input__field"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={`Enter ${unit}…`}
        step="any" min={0}
        aria-label={`${unit} reading`}
      />
    </div>
  )
}

function FunctionalInput({ value, onChange }) {
  return (
    <div className="functional-input" role="radiogroup" aria-label="Pass or fail">
      <button
        role="radio" aria-checked={value === true}
        className={`functional-btn functional-btn--pass ${value === true ? 'functional-btn--active' : ''}`}
        onClick={() => onChange(true)} type="button"
      >✓ Pass</button>
      <button
        role="radio" aria-checked={value === false}
        className={`functional-btn functional-btn--fail ${value === false ? 'functional-btn--active' : ''}`}
        onClick={() => onChange(false)} type="button"
      >✗ Fail</button>
    </div>
  )
}

function DateRecordInput({ value, onChange }) {
  return (
    <div className="date-record-input">
      <label className="measurement-input__label">Date recorded</label>
      <input
        type="date" className="form-input"
        value={value}
        onChange={e => onChange(e.target.value)}
        max={new Date().toISOString().slice(0, 10)}
        aria-label="Date recorded"
      />
    </div>
  )
}
