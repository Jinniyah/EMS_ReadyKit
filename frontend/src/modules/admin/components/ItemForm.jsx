/**
 * modules/admin/components/ItemForm.jsx
 *
 * Add or edit an item in the catalog.
 *
 * UX principles (tired crew / end-of-shift user):
 *   - Required fields first, optional fields below a clear divider
 *   - Conditional fields appear only when relevant (check type drives visibility)
 *   - One large primary action button, one plain cancel link — no ambiguity
 *   - Errors shown inline next to the field that caused them, not in a toast
 *   - AI fields are in a clearly-labeled collapsed section — advanced, not in the way
 *
 * Props:
 *   item        — existing item object (edit mode) or null (create mode)
 *   onSaved(item) — called after successful save
 *   onCancel    — called when the user cancels
 */

import React, { useState } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { canAccess } from '../../../shared/utils/roleGuard.js'
import { adminApi } from '../api/adminApi.js'

const CATEGORIES  = ['Medication', 'Consumable', 'Equipment', 'Document']
const CHECK_TYPES = [
  { value: 'SUPPLY',      label: 'Supply Count',       hint: 'Counted or presence-verified item' },
  { value: 'MEASUREMENT', label: 'Measurement',         hint: 'Numeric reading — O2 PSI, temperature' },
  { value: 'FUNCTIONAL',  label: 'Functional Check',   hint: 'Pass / Fail — battery OK, runs & starts' },
  { value: 'DATE_RECORD', label: 'Date Record',         hint: 'Date recorded — AED last charge date' },
  { value: 'DOCUMENT',    label: 'Document Present',   hint: 'Presence-only paperwork check' },
]

function Field({ label, required, hint, error, children }) {
  return (
    <div className="item-form__field">
      <label className="item-form__label">
        {label}{required && <span className="item-form__required" aria-hidden="true"> *</span>}
      </label>
      {hint && <p className="item-form__hint">{hint}</p>}
      {children}
      {error && <p className="item-form__field-error" role="alert">{error}</p>}
    </div>
  )
}

export default function ItemForm({ item, onSaved, onCancel }) {
  const { user, getToken } = useAuth()
  const isAdmin    = canAccess(user, 'administrator')
  const isEditMode = !!item

  const [form, setForm] = useState({
    name:                item?.name                ?? '',
    category:            item?.category            ?? 'Consumable',
    check_type:          item?.check_type          ?? 'SUPPLY',
    unit_of_measure:     item?.unit_of_measure     ?? 'each',
    controlled_substance:item?.controlled_substance ?? false,
    measurement_minimum: item?.measurement_minimum  ?? '',
    measurement_maximum: item?.measurement_maximum  ?? '',
    recurrence_days:     item?.recurrence_days      ?? '',
    active:              item?.active               ?? true,
    // AI fields
    alternate_names:     item?.alternate_names      ?? '',
    ai_tags:             item?.ai_tags              ?? '',
    barcode:             item?.barcode              ?? '',
    reference_image_url: item?.reference_image_url  ?? '',
  })

  const [errors, setErrors]           = useState({})
  const [globalError, setGlobalError] = useState(null)
  const [isSubmitting, setSubmitting] = useState(false)
  const [showAI, setShowAI]           = useState(
    !!(item?.alternate_names || item?.ai_tags || item?.barcode || item?.reference_image_url)
  )

  function set(field, value) {
    setForm(f => ({ ...f, [field]: value }))
    if (errors[field]) setErrors(e => ({ ...e, [field]: null }))
  }

  // ── Validation ──────────────────────────────────────────────────────────────

  function validate() {
    const e = {}
    if (!form.name.trim())            e.name            = 'Name is required.'
    if (!form.unit_of_measure.trim()) e.unit_of_measure = 'Unit of measure is required.'

    if (form.check_type === 'MEASUREMENT') {
      if (form.measurement_minimum === '') e.measurement_minimum = 'Minimum value required for measurement items.'
      if (form.measurement_minimum !== '' && isNaN(Number(form.measurement_minimum)))
        e.measurement_minimum = 'Must be a number.'
      if (form.measurement_maximum !== '' && isNaN(Number(form.measurement_maximum)))
        e.measurement_maximum = 'Must be a number.'
      if (form.measurement_minimum !== '' && form.measurement_maximum !== '') {
        if (Number(form.measurement_minimum) >= Number(form.measurement_maximum))
          e.measurement_maximum = 'Maximum must be greater than minimum.'
      }
    }

    if (form.check_type === 'DATE_RECORD') {
      if (form.recurrence_days === '') e.recurrence_days = 'Recurrence days required for date record items.'
      else if (isNaN(Number(form.recurrence_days)) || Number(form.recurrence_days) < 1)
        e.recurrence_days = 'Must be a whole number greater than 0.'
    }

    return e
  }

  // ── Submit ──────────────────────────────────────────────────────────────────

  async function handleSubmit(e) {
    e.preventDefault()
    const validationErrors = validate()
    if (Object.keys(validationErrors).length) { setErrors(validationErrors); return }

    setSubmitting(true)
    setGlobalError(null)

    const payload = {
      name:                 form.name.trim(),
      category:             form.category,
      check_type:           form.check_type,
      unit_of_measure:      form.unit_of_measure.trim(),
      controlled_substance: form.controlled_substance,
      active:               form.active,
      measurement_minimum:  form.check_type === 'MEASUREMENT' && form.measurement_minimum !== ''
                              ? Number(form.measurement_minimum) : null,
      measurement_maximum:  form.check_type === 'MEASUREMENT' && form.measurement_maximum !== ''
                              ? Number(form.measurement_maximum) : null,
      recurrence_days:      form.check_type === 'DATE_RECORD' && form.recurrence_days !== ''
                              ? Number(form.recurrence_days) : null,
      alternate_names:      form.alternate_names.trim()     || null,
      ai_tags:              form.ai_tags.trim()             || null,
      barcode:              form.barcode.trim()             || null,
      reference_image_url:  form.reference_image_url.trim() || null,
    }

    try {
      const saved = isEditMode
        ? await adminApi.updateItem(item.item_id, payload, getToken)
        : await adminApi.createItem(payload, getToken)
      onSaved(saved)
    } catch (err) {
      setGlobalError(err.message ?? 'Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  const isMeasurement = form.check_type === 'MEASUREMENT'
  const isDateRecord  = form.check_type === 'DATE_RECORD'

  return (
    <form className="item-form" onSubmit={handleSubmit} noValidate>

      <div className="item-form__header">
        <h2 className="item-form__title">{isEditMode ? 'Edit Item' : 'Add Item'}</h2>
        <p className="item-form__subtitle">
          {isEditMode ? item.name : 'New item will be available in the catalog immediately.'}
        </p>
      </div>

      {globalError && (
        <div className="item-form__global-error" role="alert">{globalError}</div>
      )}

      {/* ── Required fields ──────────────────────────────────────────────── */}

      <Field label="Item name" required error={errors.name}>
        <input
          className="item-form__input"
          value={form.name}
          onChange={e => set('name', e.target.value)}
          placeholder="e.g. NRB Mask Adult"
          maxLength={150}
          autoFocus
        />
      </Field>

      <Field label="Category" required>
        <select
          className="item-form__select"
          value={form.category}
          onChange={e => set('category', e.target.value)}
        >
          {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </Field>

      <Field label="Check type" required>
        <select
          className="item-form__select"
          value={form.check_type}
          onChange={e => set('check_type', e.target.value)}
        >
          {CHECK_TYPES.map(ct => (
            <option key={ct.value} value={ct.value}>{ct.label} — {ct.hint}</option>
          ))}
        </select>
      </Field>

      <Field
        label="Unit of measure"
        required
        hint={isMeasurement ? 'Reading unit, e.g. PSI, °F, mg/dL' : 'e.g. each, box, roll, mL'}
        error={errors.unit_of_measure}
      >
        <input
          className="item-form__input"
          value={form.unit_of_measure}
          onChange={e => set('unit_of_measure', e.target.value)}
          placeholder={isMeasurement ? 'PSI' : 'each'}
          maxLength={30}
        />
      </Field>

      {/* ── Conditional: Measurement ─────────────────────────────────────── */}

      {isMeasurement && (
        <>
          <Field
            label="Minimum acceptable reading"
            required
            hint="Readings below this value will be flagged as LOW."
            error={errors.measurement_minimum}
          >
            <input
              className="item-form__input"
              type="number"
              value={form.measurement_minimum}
              onChange={e => set('measurement_minimum', e.target.value)}
              placeholder="e.g. 500"
            />
          </Field>
          <Field
            label="Maximum acceptable reading (optional)"
            hint="Readings above this value will be flagged. Leave blank if no upper limit applies."
            error={errors.measurement_maximum}
          >
            <input
              className="item-form__input"
              type="number"
              value={form.measurement_maximum}
              onChange={e => set('measurement_maximum', e.target.value)}
              placeholder="e.g. 2200"
            />
          </Field>
        </>
      )}

      {/* ── Conditional: Date Record ─────────────────────────────────────── */}

      {isDateRecord && (
        <Field
          label="Recurrence — max days between events"
          required
          hint="A check will be flagged OVERDUE if this many days pass without a new record. e.g. 90 for AED charge."
          error={errors.recurrence_days}
        >
          <input
            className="item-form__input"
            type="number"
            min={1}
            value={form.recurrence_days}
            onChange={e => set('recurrence_days', e.target.value)}
            placeholder="e.g. 90"
          />
        </Field>
      )}

      {/* ── Optional toggles ─────────────────────────────────────────────── */}

      <div className="item-form__toggle-row">
        <label className="item-form__toggle-label">
          <input
            type="checkbox"
            checked={form.controlled_substance}
            onChange={e => set('controlled_substance', e.target.checked)}
            className="item-form__checkbox"
          />
          <span>
            <strong>Controlled substance</strong>
            <span className="item-form__hint-inline"> — requires dual-signature verification</span>
          </span>
        </label>
      </div>

      {isEditMode && isAdmin && (
        <div className="item-form__toggle-row">
          <label className="item-form__toggle-label">
            <input
              type="checkbox"
              checked={form.active}
              onChange={e => set('active', e.target.checked)}
              className="item-form__checkbox"
            />
            <span>
              <strong>Active</strong>
              <span className="item-form__hint-inline"> — inactive items are hidden from operational views</span>
            </span>
          </label>
        </div>
      )}

      {/* ── AI identification fields — Admin only ────────────────────────── */}

      {isAdmin && (
        <div className="item-form__ai-section">
          <button
            type="button"
            className="item-form__ai-toggle"
            onClick={() => setShowAI(v => !v)}
            aria-expanded={showAI}
          >
            <span>AI &amp; Scanner fields</span>
            <span className="item-form__ai-toggle-hint">
              {showAI ? 'Hide' : 'Alternate names, barcode, AI tags — for future scanner/AI features'}
            </span>
            <span aria-hidden="true">{showAI ? '▲' : '▼'}</span>
          </button>

          {showAI && (
            <div className="item-form__ai-fields">
              <Field
                label="Alternate names"
                hint="Other names crews use. Comma-separated. e.g. NRB, non-rebreather, O2 mask"
              >
                <input
                  className="item-form__input"
                  value={form.alternate_names}
                  onChange={e => set('alternate_names', e.target.value)}
                  placeholder="e.g. NRB, non-rebreather"
                  maxLength={500}
                />
              </Field>

              <Field
                label="AI tags"
                hint="Keywords an AI classifier might return. Comma-separated."
              >
                <input
                  className="item-form__input"
                  value={form.ai_tags}
                  onChange={e => set('ai_tags', e.target.value)}
                  placeholder="e.g. mask,oxygen,NRB"
                  maxLength={500}
                />
              </Field>

              <Field
                label="Barcode (UPC / GS1)"
                hint="Unique barcode for scanner identification."
              >
                <input
                  className="item-form__input"
                  value={form.barcode}
                  onChange={e => set('barcode', e.target.value)}
                  placeholder="e.g. 012345678901"
                  maxLength={100}
                />
              </Field>

              <Field
                label="Reference image URL"
                hint="Azure Blob Storage URL of a reference photo. Used by the AI pipeline to verify a visual match."
              >
                <input
                  className="item-form__input"
                  value={form.reference_image_url}
                  onChange={e => set('reference_image_url', e.target.value)}
                  placeholder="https://storage.blob.core.windows.net/…"
                  maxLength={500}
                />
              </Field>
            </div>
          )}
        </div>
      )}

      {/* ── Actions ──────────────────────────────────────────────────────── */}

      <div className="item-form__actions">
        <button
          type="submit"
          className="btn btn--primary btn--full"
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Saving…' : isEditMode ? 'Save Changes' : 'Add Item'}
        </button>
        <button
          type="button"
          className="btn btn--secondary btn--full"
          onClick={onCancel}
          disabled={isSubmitting}
        >
          Cancel
        </button>
      </div>

    </form>
  )
}
