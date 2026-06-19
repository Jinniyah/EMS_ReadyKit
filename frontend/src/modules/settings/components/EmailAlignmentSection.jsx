/**
 * modules/settings/components/EmailAlignmentSection.jsx
 * LAUNCH-OPS9 — Admin-only diagnostic panel.
 *
 * Runs GET /admin/email-alignment-check on demand (not a startup check —
 * membership rows can be added any time, so this is something an Admin
 * runs right after adding people or importing a CSV).
 *
 * If issues are found, lets the Admin pick recipients (existing
 * Administrators/Supervisors at the station, or freeform emails) and
 * drafts a notification email. No email is sent automatically — there's
 * no connected mail account here, so this hands the Admin a ready-to-send
 * draft (opens in their default mail app, or can be copied).
 *
 * Design constraints (Earl persona):
 *   - 60px minimum tap targets
 *   - Plain English — no "member_id" or raw API language in the UI
 *   - Inline results, no modal interruption
 */
import React, { useState } from 'react'
import { membersApi } from '../api/membersApi.js'

export default function EmailAlignmentSection({ station, getToken }) {
  const [checking, setChecking] = useState(false)
  const [result, setResult]     = useState(null)
  const [error, setError]       = useState(null)
  const [showNotify, setShowNotify] = useState(false)

  async function handleCheck() {
    setChecking(true)
    setError(null)
    setShowNotify(false)
    try {
      const res = await membersApi.checkEmailAlignment(station.station_id, getToken)
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="settings-section">
      <h2 className="settings-section__heading">Email Alignment Check</h2>

      <div className="settings-row">
        <div className="settings-row__content">
          <div className="settings-row__label">Check team member emails</div>
          <div className="settings-row__description">
            Scans the team member list for entries that don't look like real email
            addresses — usually a sign someone typed a name instead of an email
            when adding a member or importing a CSV. People with a bad entry
            can't sign in.
          </div>
        </div>
        <div className="settings-row__control">
          <button
            className="btn btn--secondary btn--small"
            onClick={handleCheck}
            disabled={checking}
            type="button"
          >
            {checking ? 'Checking…' : 'Run Check'}
          </button>
        </div>
      </div>

      {error && <p className="settings-screen__error" role="alert">{error}</p>}

      {result && (
        <EmailAlignmentResult
          result={result}
          station={station}
          getToken={getToken}
          showNotify={showNotify}
          onToggleNotify={() => setShowNotify(s => !s)}
        />
      )}
    </div>
  )
}

// ── Result display ────────────────────────────────────────────────────────────

function EmailAlignmentResult({ result, station, getToken, showNotify, onToggleNotify }) {
  if (result.flagged === 0) {
    return (
      <div className="email-alignment__clean" role="status">
        ✓ Checked {result.checked} {result.checked === 1 ? 'member' : 'members'} — all
        emails look good.
      </div>
    )
  }

  return (
    <div className="email-alignment__results">
      <p className="email-alignment__summary" role="alert">
        {result.flagged} of {result.checked} {result.checked === 1 ? 'entry' : 'entries'} need
        a closer look:
      </p>
      <ul className="email-alignment__issue-list">
        {result.issues.map(issue => (
          <li key={issue.member_id} className="email-alignment__issue">
            <span className="email-alignment__issue-name">
              {issue.preferred_name ?? '(no name set)'}
            </span>
            <span className="email-alignment__issue-value">"{issue.user_id}"</span>
            <span className="email-alignment__issue-reason">{issue.reason}</span>
          </li>
        ))}
      </ul>

      <button
        className="btn btn--primary btn--small"
        onClick={onToggleNotify}
        type="button"
      >
        {showNotify ? 'Hide' : 'Notify Someone About This'}
      </button>

      {showNotify && (
        <NotifyPanel issues={result.issues} station={station} getToken={getToken} />
      )}
    </div>
  )
}

// ── Notify panel — pick recipients, draft email ───────────────────────────────

function NotifyPanel({ issues, station, getToken }) {
  const [members, setMembers] = useState(null)
  const [loadingMembers, setLoadingMembers] = useState(true)

  React.useEffect(() => {
    let cancelled = false
    membersApi.listMembers(station.station_id, getToken)
      .then(data => { if (!cancelled) setMembers(data) })
      .catch(() => { if (!cancelled) setMembers([]) })
      .finally(() => { if (!cancelled) setLoadingMembers(false) })
    return () => { cancelled = true }
  }, [station.station_id, getToken])

  // Existing Administrators/Supervisors with a clean-looking email are the
  // natural "fix this" audience — exclude anyone who is themselves flagged,
  // since their address may not be reachable.
  const flaggedIds = new Set(issues.map(i => i.user_id))
  const candidateRecipients = (members ?? [])
    .filter(m => (m.role === 'Administrator' || m.role === 'Supervisor') && !flaggedIds.has(m.user_id))
    .reduce((acc, m) => {
      if (!acc.find(x => x.user_id === m.user_id)) acc.push(m)
      return acc
    }, [])

  const [selected, setSelected] = useState([])
  const [customEmail, setCustomEmail] = useState('')
  const [customList, setCustomList] = useState([])
  const [drafted, setDrafted] = useState(false)

  function toggleSelected(email) {
    setSelected(prev =>
      prev.includes(email) ? prev.filter(e => e !== email) : [...prev, email]
    )
  }

  function addCustomEmail() {
    const trimmed = customEmail.trim().toLowerCase()
    if (!trimmed) return
    if (!customList.includes(trimmed)) setCustomList(prev => [...prev, trimmed])
    setCustomEmail('')
  }

  function removeCustomEmail(email) {
    setCustomList(prev => prev.filter(e => e !== email))
  }

  const allRecipients = [...selected, ...customList]

  function buildEmailBody() {
    const lines = issues.map(
      i => `  - ${i.preferred_name ?? '(no name set)'} -- entered as "${i.user_id}" (${i.reason})`
    )
    return [
      'Hi,',
      '',
      `A check of the EMS ReadyKit team member list for ${issues[0]?.station_name ?? station.name} found ${issues.length} entr${issues.length === 1 ? 'y' : 'ies'} that don't look like valid email addresses:`,
      '',
      ...lines,
      '',
      "Each of these people will be silently blocked from signing in until the entry is corrected. To fix it:",
      '  1. Go to Settings -> Team Members',
      '  2. Remove the incorrect row',
      '  3. Re-add the person with their real sign-in email address',
      '',
      'Thanks,',
    ].join('\n')
  }

  return (
    <div className="email-alignment__notify-panel">
      <p className="email-alignment__notify-label">Send this to:</p>

      {loadingMembers && (
        <p className="email-alignment__notify-hint">Loading team members…</p>
      )}

      {!loadingMembers && candidateRecipients.length > 0 && (
        <div className="email-alignment__recipient-list">
          {candidateRecipients.map(m => (
            <label key={m.user_id} className="email-alignment__recipient-checkbox">
              <input
                type="checkbox"
                checked={selected.includes(m.user_id)}
                onChange={() => toggleSelected(m.user_id)}
              />
              <span>
                {m.preferred_name ?? m.user_id}{' '}
                <span className="email-alignment__recipient-role">({m.role})</span>
              </span>
            </label>
          ))}
        </div>
      )}

      <div className="email-alignment__custom-row">
        <input
          className="member-add-form__input"
          type="email"
          placeholder="Or type another email address"
          value={customEmail}
          onChange={e => setCustomEmail(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addCustomEmail() } }}
          aria-label="Additional recipient email"
        />
        <button
          className="btn btn--secondary btn--small"
          onClick={addCustomEmail}
          type="button"
        >
          Add
        </button>
      </div>

      {customList.length > 0 && (
        <div className="email-alignment__custom-list">
          {customList.map(email => (
            <span key={email} className="email-alignment__custom-chip">
              {email}
              <button
                type="button"
                onClick={() => removeCustomEmail(email)}
                aria-label={`Remove ${email}`}
              >
                ✕
              </button>
            </span>
          ))}
        </div>
      )}

      <button
        className="btn btn--primary btn--small"
        onClick={() => setDrafted(true)}
        disabled={allRecipients.length === 0}
        type="button"
      >
        Draft Email
      </button>

      {allRecipients.length === 0 && (
        <p className="email-alignment__notify-hint">
          Pick at least one recipient above, or add an email address.
        </p>
      )}

      {drafted && (
        <DraftedEmailPreview recipients={allRecipients} body={buildEmailBody()} />
      )}
    </div>
  )
}

// ── Drafted email preview — recipients + body, opens in mail app ──────────────

function DraftedEmailPreview({ recipients, body }) {
  const subject = 'EMS ReadyKit — a few team member emails need fixing'
  const mailtoHref = `mailto:${recipients.join(',')}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`

  return (
    <div className="email-alignment__draft-preview">
      <p className="email-alignment__draft-label">To: {recipients.join(', ')}</p>
      <p className="email-alignment__draft-label">Subject: {subject}</p>
      <pre className="email-alignment__draft-body">{body}</pre>
      <a className="btn btn--primary btn--small" href={mailtoHref}>
        Open in Mail App
      </a>
    </div>
  )
}
