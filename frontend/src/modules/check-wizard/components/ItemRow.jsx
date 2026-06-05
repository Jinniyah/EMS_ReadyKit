/**
 * modules/check-wizard/components/ItemRow.jsx
 *
 * Simplified data flow — one source of truth:
 *   Every interaction immediately writes to the draft via onUpdate(payload).
 *
 * Card states:
 *   untouched  — draftItem is null, white background
 *   touched    — draftItem exists but count not yet submitted, neutral
 *   confirmed  — draftItem.confirmed = true, background reflects result:
 *                  green  = OK
 *                  yellow = SHORT (count below need) or LOW (measurement below min)
 *                  red    = MISSING / FAIL / EXPIRED
 *
 * MEASUREMENT items persist min_value alongside measurement_value so that
 * deriveDraftItemStatus() in statusCalc.js can correctly return 'LOW' without
 * a separate API call. Without min_value in the draft, the status calc has no
 * threshold to compare against and always returns 'OK'.
 *
 * item_name is persisted so Step 4 Reconcile can display it without
 * needing to re-fetch the item catalog.
 */
import React, { useState, useRef, useCallback } from 'react'
import { checkTypeLabel } from '../../../shared/utils/statusCalc.js'
import { formatShortDate, isExpired, todayIso } from '../../../shared/utils/dateHelpers.js'

export default function ItemRow({
  item,
  parLevel,
  lot,
  draftItem,
  onUpdate,
  onTouched,
}) {
  const checkType      = item.check_type ?? 'SUPPLY'
  const quantityNeeded = parLevel?.min_quantity ?? 0
  const minValue       = parLevel?.min_value ?? item.measurement_minimum ?? null
  const touchedRef     = useRef(false)

  const isFailing = checkType === 'FUNCTIONAL' &&
    draftItem?.functional_pass === false &&
    !draftItem?.confirmed
  const [showNotes, setShowNotes] = useState(!!(draftItem?.notes) || isFailing)
  const notesRef = useRef(null)

  const touch = useCallback(() => {
    if (!touchedRef.current) {
      touchedRef.current = true
      onTouched?.(item.item_id)
    }
  }, [item.item_id, onTouched])

  const persist = useCallback((fields) => {
    touch()
    onUpdate({
      item_id:           item.item_id,
      // item_name persisted so Step 4 Reconcile can display it
      item_name:         item.name ?? '',
      check_type:        checkType,
      quantity_needed:   quantityNeeded,
      // min_value persisted so deriveDraftItemStatus can detect LOW readings
      min_value:         minValue,
      quantity_found:    draftItem?.quantity_found    ?? 0,
      measurement_value: draftItem?.measurement_value ?? null,
      functional_pass:   draftItem?.functional_pass   ?? null,
      date_value:        draftItem?.date_value         ?? null,
      notes:             draftItem?.notes              ?? null,
      confirmed:         draftItem?.confirmed          ?? false,
      ...fields,
    })
  }, [touch, onUpdate, item.item_id, item.name, checkType, quantityNeeded, minValue, draftItem])

  const currentQty = draftItem?.quantity_found ?? 0

  const handleIncrement  = useCallback(() => {
    const newQty = currentQty + 1
    const atPar  = quantityNeeded > 0 && newQty === quantityNeeded
    persist({ quantity_found: newQty, confirmed: atPar })
    if (atPar && navigator.vibrate) navigator.vibrate([40])
  }, [persist, currentQty, quantityNeeded])
  const handleDecrement  = useCallback(() => {
    const newQty = Math.max(0, currentQty - 1)
    const atPar  = quantityNeeded > 0 && newQty === quantityNeeded
    persist({ quantity_found: newQty, confirmed: atPar })
    if (atPar && navigator.vibrate) navigator.vibrate([40])
  }, [persist, currentQty, quantityNeeded])
  const handleSetQty     = useCallback((val) => {
    const n = parseInt(val, 10)
    if (!isNaN(n) && n >= 0) {
      const atPar = quantityNeeded > 0 && n === quantityNeeded
      persist({ quantity_found: n, confirmed: atPar })
      if (atPar && navigator.vibrate) navigator.vibrate([40])
    }
  }, [persist, quantityNeeded])
  const handleAllPresent = useCallback(() => { persist({ quantity_found: quantityNeeded, confirmed: true }); if (navigator.vibrate) navigator.vibrate([40]) }, [persist, quantityNeeded])
  const handleSubmitCount = useCallback(() => {
    persist({ confirmed: true })
    if (navigator.vibrate) {
      const val = draftItem?.measurement_value
      const isLow = checkType === 'MEASUREMENT' && val != null && minValue != null && val < minValue
      navigator.vibrate(isLow ? [80, 40, 80] : (draftItem?.quantity_found ?? 0) === 0 ? [80, 40, 80] : [40])
    }
  }, [persist, draftItem, checkType, minValue])

  const handleMeasurement = useCallback((val) => {
    persist({ measurement_value: parseFloat(val) || null, confirmed: false })
  }, [persist])

  const handleFunctional = useCallback((val) => {
    if (val === true) {
      persist({ functional_pass: true, confirmed: true })
      if (navigator.vibrate) navigator.vibrate([40])
    } else {
      persist({ functional_pass: false, confirmed: false })
      setShowNotes(true)
      setTimeout(() => notesRef.current?.focus(), 50)
      if (navigator.vibrate) navigator.vibrate([80, 40, 80])
    }
  }, [persist])

  const handleDateChange = useCallback((val) => persist({ date_value: val || null, confirmed: false }), [persist])
  const handleDateBlur   = useCallback((val) => { if (val) persist({ date_value: val, confirmed: true }) }, [persist])
  const handleDateToday  = useCallback(() => { persist({ date_value: todayIso(), confirmed: true }); if (navigator.vibrate) navigator.vibrate([40]) }, [persist])
  const handleNotes      = useCallback((val) => persist({ notes: val.trim() || null }), [persist])
  const handleEdit       = useCallback(() => { persist({ confirmed: false }); if (draftItem?.notes || draftItem?.functional_pass === false) setShowNotes(true) }, [persist, draftItem])

  const [showKeypad, setShowKeypad] = useState(false)
  const [keypadValue, setKeypadValue] = useState('0')
  const openKeypad   = useCallback(() => { touch(); setKeypadValue(String(currentQty)); setShowKeypad(true) }, [touch, currentQty])
  const commitKeypad = useCallback(() => { handleSetQty(keypadValue); setShowKeypad(false) }, [handleSetQty, keypadValue])

  const hasDraft         = draftItem !== null
  const confirmed        = draftItem?.confirmed ?? false
  const isCountType      = checkType === 'SUPPLY' || checkType === 'DOCUMENT'
  const isZeroCount      = isCountType && (draftItem?.quantity_found ?? 0) === 0
  const isShortCount     = isCountType && quantityNeeded > 0 && (draftItem?.quantity_found ?? 0) > 0 && (draftItem?.quantity_found ?? 0) < quantityNeeded
  const isFunctionalFail = hasDraft && checkType === 'FUNCTIONAL' && draftItem?.functional_pass === false

  // MEASUREMENT: yellow when reading is below minimum threshold
  const isMeasurementLow = checkType === 'MEASUREMENT' &&
    hasDraft &&
    draftItem?.measurement_value != null &&
    minValue != null &&
    draftItem.measurement_value < minValue

  const rowBg = !hasDraft
    ? 'var(--color-surface)'
    : isFunctionalFail || isZeroCount
      ? 'var(--color-status-fail-bg)'
      : isShortCount || isMeasurementLow
        ? 'var(--color-status-warn-bg)'
        : 'var(--color-status-pass-bg)'

  const countLabel = (() => {
    if (checkType === 'MEASUREMENT') return `${draftItem?.measurement_value ?? '—'} ${item.unit_of_measure ?? ''}`
    if (checkType === 'FUNCTIONAL')  return draftItem?.functional_pass === true ? 'Pass' : draftItem?.functional_pass === false ? 'Fail' : '—'
    if (checkType === 'DATE_RECORD') return draftItem?.date_value ? formatShortDate(draftItem.date_value) : '—'
    return `${draftItem?.quantity_found ?? 0} / ${quantityNeeded}`
  })()

  const isFailPending    = checkType === 'FUNCTIONAL' && draftItem?.functional_pass === false && !confirmed
  const isAtPar          = isCountType && quantityNeeded > 0 && currentQty === quantityNeeded
  const showSubmitButton = (isCountType && hasDraft && !isAtPar) || checkType === 'MEASUREMENT' || isFailPending

  // ── Confirmed (locked) display ────────────────────────────────────────────
  if (confirmed) {
    return (
      <div className="item-row item-row--confirmed" style={{ '--row-bg': rowBg }}
        aria-label={`${item.name}: ${countLabel}`}>
        <div className="item-row__submitted-inner">
          <div className="item-row__submitted-left">
            <div className="item-row__name item-row__name--submitted">
              {item.name}
              {item.controlled_substance && <span className="item-row__cs-badge" aria-label="Controlled substance">🔒</span>}
            </div>
            <div className="item-row__submitted-count">
              {countLabel}
              {isZeroCount      && <span className="item-row__zero-warning"> ⚠ check count</span>}
              {isShortCount     && <span className="item-row__short-warning"> ↓ short</span>}
              {isMeasurementLow && <span className="item-row__short-warning"> ↓ low — below {minValue} {item.unit_of_measure ?? ''}</span>}
              {isFunctionalFail && <span className="item-row__fail-tag"> ✗ Failed</span>}
            </div>
            {draftItem?.notes && <div className="item-row__submitted-note">📝 {draftItem.notes}</div>}
          </div>
          <button className="item-row__edit-btn" onClick={handleEdit} type="button"
            aria-label={`Edit ${item.name}`} title="Edit">✏</button>
        </div>
      </div>
    )
  }

  // ── Edit display ──────────────────────────────────────────────────────────
  return (
    <div className="item-row item-row--pending" style={{ '--row-bg': rowBg }}>
      <div className="item-row__header">
        <div className="item-row__name">
          {item.name}
          {item.controlled_substance && <span className="item-row__cs-badge" aria-label="Controlled substance">🔒 CS</span>}
          {checkType !== 'SUPPLY' && <span className="item-row__type-badge">{checkTypeLabel(checkType)}</span>}
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

      <div className="item-row__input">
        {(checkType === 'SUPPLY' || checkType === 'DOCUMENT') && (
          <div className="supply-input__counter">
            <button className="counter-btn" onClick={handleDecrement} disabled={currentQty <= 0} type="button" aria-label="Decrease quantity">−</button>
            <button className="counter-value" onClick={openKeypad} type="button" aria-label={`Quantity: ${currentQty}. Tap to type.`}>{currentQty}</button>
            <button className="counter-btn" onClick={handleIncrement} type="button" aria-label="Increase quantity">+</button>
            {quantityNeeded > 0 && (
              <button className="btn btn--all-present" onClick={handleAllPresent} type="button"
                aria-label={`All ${quantityNeeded} present`}>All {quantityNeeded} present</button>
            )}
          </div>
        )}

        {checkType === 'MEASUREMENT' && (
          <MeasurementInput
            value={draftItem?.measurement_value ?? ''}
            onChange={handleMeasurement}
            unit={item.unit_of_measure}
            minimum={minValue}
            isLow={isMeasurementLow}
          />
        )}

        {checkType === 'FUNCTIONAL' && (
          <FunctionalInput value={draftItem?.functional_pass ?? null} onChange={handleFunctional} />
        )}

        {checkType === 'DATE_RECORD' && (
          <DateRecordInput
            value={draftItem?.date_value ?? ''}
            onChange={handleDateChange}
            onBlur={handleDateBlur}
            onToday={handleDateToday}
          />
        )}
      </div>

      {showNotes && (
        <div className="item-row__notes">
          {isFailPending && <p className="item-row__notes-prompt">Document the reason for failure (optional)</p>}
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

      <div className="item-row__actions">
        {!showNotes ? (
          <button className="btn-text" type="button"
            onClick={() => { setShowNotes(true); setTimeout(() => notesRef.current?.focus(), 50) }}
            aria-label={`Add note for ${item.name}`}>+ Note</button>
        ) : <div />}
        {showSubmitButton && (
          <button className="btn btn--submit-count" onClick={handleSubmitCount} type="button"
            aria-label={isFailPending ? `Confirm fail for ${item.name}` : `Submit count for ${item.name}`}>
            {isFailPending ? 'Confirm fail' : 'Submit count'}
          </button>
        )}
      </div>

      {showKeypad && (
        <div className="keypad-overlay" role="dialog" aria-label="Enter quantity">
          <div className="keypad">
            <div className="keypad__context">Need: {quantityNeeded}</div>
            <input className="keypad__display" type="number" inputMode="numeric"
              value={keypadValue} onChange={e => setKeypadValue(e.target.value)}
              autoFocus min={0} aria-label="Quantity" />
            <div className="keypad__buttons">
              {['1','2','3','4','5','6','7','8','9','','0','⌫'].map((k, i) => (
                <button key={i} className={`keypad__key ${!k ? 'keypad__key--empty' : ''}`}
                  onClick={() => {
                    if (!k) return
                    if (k === '⌫') setKeypadValue(v => v.slice(0, -1) || '0')
                    else setKeypadValue(v => v === '0' ? k : v + k)
                  }}
                  type="button" aria-label={k === '⌫' ? 'Backspace' : k || undefined}>{k}</button>
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

function MeasurementInput({ value, onChange, unit, minimum, isLow }) {
  return (
    <div className="measurement-input">
      <label className="measurement-input__label">
        Reading ({unit})
        {minimum != null && (
          <span className={`measurement-input__min ${isLow ? 'measurement-input__min--low' : ''}`}>
            {' '}— min {minimum}{isLow ? ' ⚠ below minimum' : ''}
          </span>
        )}
      </label>
      <input
        type="number" inputMode="decimal"
        className={`form-input measurement-input__field ${isLow ? 'measurement-input__field--low' : ''}`}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={`Enter ${unit}…`}
        step="any" min={0}
        aria-label={`${unit} reading`}
        aria-invalid={isLow}
      />
    </div>
  )
}

function FunctionalInput({ value, onChange }) {
  return (
    <div className="functional-input" role="radiogroup" aria-label="Pass or fail">
      <button role="radio" aria-checked={value === true}
        className={`functional-btn functional-btn--pass ${value === true ? 'functional-btn--active' : ''}`}
        onClick={() => onChange(true)} type="button">✓ Pass</button>
      <button role="radio" aria-checked={value === false}
        className={`functional-btn functional-btn--fail ${value === false ? 'functional-btn--active' : ''}`}
        onClick={() => onChange(false)} type="button">✗ Fail</button>
    </div>
  )
}

function DateRecordInput({ value, onChange, onBlur, onToday }) {
  return (
    <div className="date-record-input">
      <div className="date-record-input__row">
        <div className="date-record-input__picker">
          <label className="measurement-input__label">Date recorded</label>
          <input type="date" className="form-input"
            value={value}
            onChange={e => onChange(e.target.value)}
            onBlur={e => onBlur(e.target.value)}
            max={new Date().toISOString().slice(0, 10)}
            aria-label="Date recorded" />
        </div>
        <button className="btn btn--today" onClick={onToday} type="button"
          aria-label="Set date to today and confirm">Today</button>
      </div>
    </div>
  )
}
