/**
 * modules/admin/components/MemberManagementSection.jsx
 * Station member list with add, edit (name), role management, and CSV import.
 *
 * Moved from modules/settings/ (Session AE, MERGE-1) — member management was
 * split across Station Administration -> Members (broken removal, no
 * multi-role/CSV support) and Settings -> Team Members (working, fuller
 * featured). Consolidated here as the single source of truth. Settings is
 * now reserved for admin-only configuration only.
 *
 * ACC-B6: Edit preferred name on an existing member.
 * ACC-B7: A person can hold multiple roles — each role is a separate row.
 *         Adding a second role for an existing person creates a second row.
 * ACC-B8: CSV bulk import — same pattern as items import.
 *
 * Visible to Supervisor+. Administrator-only actions (adding Administrator
 * role, importing Administrator rows) are gated in the API; the UI reflects
 * the same restriction by hiding the Administrator option for Supervisors.
 *
 * Design constraints (Earl persona):
 *   - 60px minimum tap targets on all interactive elements
 *   - Plain English labels — no "PATCH" or "member_id" visible anywhere
 *   - Inline error messages, not modal alerts
 *   - Grouped by person (email), not by row, so it reads as a member list
 *     not a raw database dump
 */
import React, { useState, useCallback, useRef } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import { canAccess } from '../../../shared/utils/roleGuard.js'
import { membersApi } from '../api/membersApi.js'
import Spinner from '../../../shared/components/Spinner.jsx'

const ROLES = ['Responder', 'Supervisor', 'Administrator']
const ROLE_BADGE_CLASS = {
  Administrator: 'badge--admin',
  Supervisor:    'badge--supervisor',
  Responder:     'badge--responder',
}

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Group flat member rows by user_id so each person appears once. */
function groupByUser(members) {
  const map = new Map()
  for (const m of members) {
    if (!map.has(m.user_id)) {
      map.set(m.user_id, { user_id: m.user_id, preferred_name: m.preferred_name, rows: [] })
    }
    map.get(m.user_id).rows.push(m)
    // Use most recently set preferred_name
    if (m.preferred_name) map.get(m.user_id).preferred_name = m.preferred_name
  }
  return Array.from(map.values()).sort((a, b) =>
    (a.preferred_name ?? a.user_id).localeCompare(b.preferred_name ?? b.user_id)
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function MemberManagementSection({ station, getToken }) {
  const { user } = useAuth()
  const isAdmin = canAccess(user, 'administrator')

  const [refreshKey, setRefreshKey] = useState(0)
  const refresh = useCallback(() => setRefreshKey(k => k + 1), [])

  const { data: members, isLoading, error } = useApi(
    () => membersApi.listMembers(station.station_id, getToken),
    [station.station_id, refreshKey]
  )

  const grouped = members ? groupByUser(members) : []

  return (
    <div className="settings-section">
      <div className="settings-section__header-row">
        <h2 className="settings-section__heading">Team Members</h2>
        <span className="settings-section__count">
          {grouped.length > 0 ? `${grouped.length} ${grouped.length === 1 ? 'person' : 'people'}` : ''}
        </span>
      </div>

      <AddMemberForm
        stationId={station.station_id}
        isAdmin={isAdmin}
        getToken={getToken}
        onAdded={refresh}
      />

      <CsvImportRow
        stationId={station.station_id}
        getToken={getToken}
        onImported={refresh}
      />

      <div className="member-list" role="list" aria-label="Station members">
        {isLoading && <Spinner label="Loading members…" />}
        {error && <p className="settings-screen__error">Could not load member list.</p>}
        {!isLoading && !error && grouped.length === 0 && (
          <p className="member-list__empty">No members yet. Add someone above or import a CSV.</p>
        )}
        {grouped.map(person => (
          <PersonRow
            key={person.user_id}
            person={person}
            stationId={station.station_id}
            isAdmin={isAdmin}
            currentUserEmail={user?.email}
            getToken={getToken}
            onChanged={refresh}
          />
        ))}
      </div>
    </div>
  )
}

// ── Add member form ───────────────────────────────────────────────────────────

function AddMemberForm({ stationId, isAdmin, getToken, onAdded }) {
  const [email, setEmail]       = useState('')
  const [name, setName]         = useState('')
  const [role, setRole]         = useState('Responder')
  const [saving, setSaving]     = useState(false)
  const [error, setError]       = useState(null)
  const [success, setSuccess]   = useState(false)

  const availableRoles = isAdmin ? ROLES : ROLES.filter(r => r !== 'Administrator')

  async function handleAdd() {
    if (!email.trim()) { setError('Email is required.'); return }
    if (!role) { setError('Role is required.'); return }
    setSaving(true)
    setError(null)
    setSuccess(false)
    try {
      await membersApi.addMember(stationId, {
        user_id: email.trim().toLowerCase(),
        preferred_name: name.trim() || null,
        role,
      }, getToken)
      setEmail('')
      setName('')
      setRole('Responder')
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
      onAdded()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="member-add-form">
      <div className="member-add-form__title">Add a team member</div>
      <div className="member-add-form__fields">
        <input
          className="member-add-form__input"
          type="email"
          placeholder="Email address"
          value={email}
          onChange={e => { setEmail(e.target.value); setError(null) }}
          aria-label="Email address"
          autoComplete="off"
        />
        <input
          className="member-add-form__input"
          type="text"
          placeholder="Display name (optional)"
          value={name}
          onChange={e => setName(e.target.value)}
          aria-label="Display name"
          autoComplete="off"
        />
        <select
          className="member-add-form__select"
          value={role}
          onChange={e => setRole(e.target.value)}
          aria-label="Role"
        >
          {availableRoles.map(r => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <button
          className="btn btn--primary member-add-form__btn"
          onClick={handleAdd}
          disabled={saving}
          type="button"
          aria-label="Add member"
        >
          {saving ? 'Adding…' : 'Add'}
        </button>
      </div>
      {error   && <p className="member-add-form__error"  role="alert">{error}</p>}
      {success && <p className="member-add-form__success" role="status">Member added.</p>}
    </div>
  )
}

// ── CSV import row ────────────────────────────────────────────────────────────

function CsvImportRow({ stationId, getToken, onImported }) {
  const fileRef             = useRef(null)
  const [importing, setImporting] = useState(false)
  const [result, setResult]       = useState(null)
  const [error, setError]         = useState(null)

  async function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    setResult(null)
    setError(null)
    try {
      const res = await membersApi.importCsv(stationId, file, getToken)
      setResult(res)
      onImported()
    } catch (e) {
      setError(e.message)
    } finally {
      setImporting(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <div className="member-csv-row">
      <a
        className="member-csv-row__template-link"
        href={membersApi.templateUrl(stationId)}
        download
      >
        Download CSV template
      </a>
      <span className="member-csv-row__separator">·</span>
      <button
        className="btn btn--secondary member-csv-row__btn"
        onClick={() => fileRef.current?.click()}
        disabled={importing}
        type="button"
      >
        {importing ? 'Importing…' : 'Import CSV'}
      </button>
      <input
        ref={fileRef}
        type="file"
        accept=".csv"
        onChange={handleFileChange}
        style={{ display: 'none' }}
        aria-hidden="true"
      />
      {result && (
        <p className="member-csv-row__result" role="status">
          Added {result.created}, reactivated {result.reactivated}, skipped {result.skipped}.
          {result.errors?.length > 0 && ` ${result.errors.length} row(s) had errors.`}
        </p>
      )}
      {error && <p className="member-csv-row__error" role="alert">{error}</p>}
    </div>
  )
}

// ── Person row ────────────────────────────────────────────────────────────────

function PersonRow({ person, stationId, isAdmin, currentUserEmail, getToken, onChanged }) {
  const [editing, setEditing]         = useState(false)
  const [editName, setEditName]       = useState(person.preferred_name ?? '')
  const [saving, setSaving]           = useState(false)
  const [removeId, setRemoveId]       = useState(null)
  const [error, setError]             = useState(null)

  const isSelf = person.user_id === currentUserEmail

  async function handleSaveName() {
    setSaving(true)
    setError(null)
    try {
      // Update using the first row's member_id — the API propagates the name to all rows
      await membersApi.updateMember(stationId, person.rows[0].member_id, {
        preferred_name: editName.trim() || null,
      }, getToken)
      setEditing(false)
      onChanged()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleRemoveRole(memberId) {
    setRemoveId(memberId)
    setError(null)
    try {
      await membersApi.removeMember(stationId, memberId, getToken)
      onChanged()
    } catch (e) {
      setError(e.message)
    } finally {
      setRemoveId(null)
    }
  }

  return (
    <div className="member-row" role="listitem">
      <div className="member-row__identity">
        <div className="member-row__avatar" aria-hidden="true">
          {(person.preferred_name ?? person.user_id).slice(0, 2).toUpperCase()}
        </div>
        <div className="member-row__info">
          {editing ? (
            <div className="member-row__edit-name">
              <input
                className="member-row__name-input"
                value={editName}
                onChange={e => setEditName(e.target.value)}
                aria-label="Display name"
                autoFocus
              />
              <button
                className="btn btn--primary btn--small"
                onClick={handleSaveName}
                disabled={saving}
                type="button"
              >
                {saving ? '…' : 'Save'}
              </button>
              <button
                className="btn btn--secondary btn--small"
                onClick={() => { setEditing(false); setEditName(person.preferred_name ?? '') }}
                type="button"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="member-row__name-row">
              <span className="member-row__name">
                {person.preferred_name ?? person.user_id}
              </span>
              <button
                className="member-row__edit-btn"
                onClick={() => setEditing(true)}
                type="button"
                aria-label={`Edit display name for ${person.preferred_name ?? person.user_id}`}
              >
                Edit name
              </button>
            </div>
          )}
          <span className="member-row__email">{person.user_id}</span>
          {isSelf && <span className="member-row__you-badge">You</span>}
        </div>
      </div>

      <div className="member-row__roles">
        {person.rows.map(row => (
          <div key={row.member_id} className="member-row__role-chip">
            <span className={`badge ${ROLE_BADGE_CLASS[row.role] ?? ''}`}>
              {row.role}
            </span>
            <button
              className="member-row__remove-btn"
              onClick={() => handleRemoveRole(row.member_id)}
              disabled={removeId === row.member_id}
              type="button"
              aria-label={`Remove ${row.role} role from ${person.preferred_name ?? person.user_id}`}
            >
              {removeId === row.member_id ? '…' : '✕'}
            </button>
          </div>
        ))}
      </div>

      {error && <p className="member-row__error" role="alert">{error}</p>}
    </div>
  )
}
