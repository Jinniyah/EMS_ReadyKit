/**
 * modules/admin/components/AddMemberForm.jsx
 * Form to add a new user to a station.
 *
 * Fields:
 *   - Email (user_id) — required, Azure AD preferred_username
 *   - Preferred name — optional display name
 *   - Role — Administrator (Admin only) | Supervisor | Responder
 */
import React, { useState } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { canAccess } from '../../../shared/utils/roleGuard.js'
import { adminApi } from '../api/adminApi.js'

const ROLES = ['Responder', 'Supervisor', 'Administrator']

export default function AddMemberForm({ stationId, onMembersChanged, onCancel }) {
  const { user, getToken } = useAuth()
  const isAdmin = canAccess(user, 'administrator')

  const availableRoles = isAdmin ? ROLES : ROLES.filter(r => r !== 'Administrator')

  const [form, setForm]       = useState({ user_id: '', preferred_name: '', role: 'Responder' })
  const [saving, setSaving]   = useState(false)
  const [error, setError]     = useState(null)

  function handleChange(e) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  async function handleSubmit() {
    if (!form.user_id.trim()) {
      setError('Email is required.')
      return
    }
    if (!form.user_id.includes('@')) {
      setError('Please enter a valid email address.')
      return
    }

    setSaving(true)
    setError(null)
    try {
      await adminApi.addMember(stationId, {
        user_id:        form.user_id.trim().toLowerCase(),
        preferred_name: form.preferred_name.trim() || null,
        role:           form.role,
      }, getToken)
      onMembersChanged()
      onCancel()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="add-member-form">
      <h3 className="add-member-form__title">Add member</h3>

      {error && (
        <div className="add-member-form__error" role="alert">⚠ {error}</div>
      )}

      <div className="add-member-form__field">
        <label htmlFor="user_id" className="add-member-form__label">
          Email <span aria-hidden="true">*</span>
        </label>
        <input
          id="user_id"
          name="user_id"
          type="email"
          className="add-member-form__input"
          placeholder="crew@example.com"
          value={form.user_id}
          onChange={handleChange}
          autoComplete="off"
          autoCapitalize="off"
        />
        <p className="add-member-form__hint">
          Use the email address they sign in with. For Gmail accounts invited
          as guests, use their Gmail address (e.g. cindy@gmail.com).
        </p>
      </div>

      <div className="add-member-form__field">
        <label htmlFor="preferred_name" className="add-member-form__label">
          Preferred name
        </label>
        <input
          id="preferred_name"
          name="preferred_name"
          type="text"
          className="add-member-form__input"
          placeholder="Cindy Smith"
          value={form.preferred_name}
          onChange={handleChange}
        />
        <p className="add-member-form__hint">
          How their name will appear in the app. Leave blank to show their email.
        </p>
      </div>

      <div className="add-member-form__field">
        <label htmlFor="role" className="add-member-form__label">
          Role <span aria-hidden="true">*</span>
        </label>
        <select
          id="role"
          name="role"
          className="add-member-form__select"
          value={form.role}
          onChange={handleChange}
        >
          {availableRoles.map(r => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </div>

      <div className="add-member-form__actions">
        <button
          className="btn btn--primary"
          onClick={handleSubmit}
          disabled={saving}
          type="button"
        >
          {saving ? 'Adding…' : 'Add member'}
        </button>
        <button
          className="btn btn--secondary"
          onClick={onCancel}
          disabled={saving}
          type="button"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
