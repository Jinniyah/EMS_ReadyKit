/**
 * components/RepairRequestForm.jsx
 * Form for filing a new repair request against a vehicle.
 * All authenticated roles can file; URGENT triggers a visual warning banner.
 */

import React, { useState } from 'react'

const SEVERITIES = [
  {
    value: 'ROUTINE',
    label: 'Routine',
    description: 'Normal wear — schedule at next opportunity',
    icon: '🔧',
  },
  {
    value: 'URGENT',
    label: 'Urgent',
    description: 'Safety-affecting — vehicle should be taken out of service',
    icon: '⚠️',
  },
]

export default function RepairRequestForm({ vehicle, onSubmit, onCancel, isSubmitting }) {
  const [severity, setSeverity]       = useState('ROUTINE')
  const [description, setDescription] = useState('')
  const [error, setError]             = useState(null)

  function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    if (description.trim().length < 5) {
      setError('Please describe the issue in at least 5 characters.')
      return
    }
    onSubmit({ severity, description: description.trim() })
  }

  return (
    <form className="repair-form" onSubmit={handleSubmit} noValidate>
      <h3 className="repair-form__title">
        Report an Issue — {vehicle.vehicle_number}
      </h3>

      <fieldset className="repair-form__fieldset">
        <legend className="repair-form__legend">Severity</legend>
        <div className="repair-form__severity-options">
          {SEVERITIES.map(s => (
            <label
              key={s.value}
              className={`severity-option ${severity === s.value ? 'severity-option--selected' : ''} ${s.value === 'URGENT' ? 'severity-option--urgent' : ''}`}
            >
              <input
                type="radio"
                name="severity"
                value={s.value}
                checked={severity === s.value}
                onChange={() => setSeverity(s.value)}
                className="severity-option__input"
              />
              <span className="severity-option__icon" aria-hidden="true">{s.icon}</span>
              <span className="severity-option__label">{s.label}</span>
              <span className="severity-option__description">{s.description}</span>
            </label>
          ))}
        </div>
      </fieldset>

      {severity === 'URGENT' && (
        <div className="repair-form__urgent-banner" role="alert">
          <strong>⚠️ Urgent request</strong> — supervisors will be alerted immediately.
          Consider marking this vehicle inactive until the issue is resolved.
        </div>
      )}

      <div className="repair-form__field">
        <label className="repair-form__label" htmlFor="repair-description">
          Description <span aria-hidden="true">*</span>
        </label>
        <textarea
          id="repair-description"
          className="repair-form__textarea"
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Describe the issue clearly — what you observed, when it started, any safety concerns…"
          rows={4}
          maxLength={500}
          required
          aria-describedby={error ? 'repair-description-error' : undefined}
        />
        <div className="repair-form__char-count">{description.length}/500</div>
        {error && (
          <div id="repair-description-error" className="repair-form__error" role="alert">
            {error}
          </div>
        )}
      </div>

      <div className="repair-form__actions">
        <button
          type="submit"
          className={`btn btn--full ${severity === 'URGENT' ? 'btn--danger' : 'btn--primary'}`}
          disabled={isSubmitting}
        >
          {isSubmitting
            ? 'Submitting…'
            : severity === 'URGENT'
            ? '⚠️ Submit Urgent Request'
            : 'Submit Request'}
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
