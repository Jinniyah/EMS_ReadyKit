/**
 * modules/admin/components/MemberList.jsx
 * Lists current members of a station with role badge and remove button.
 */
import React, { useState } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { canAccess } from '../../../shared/utils/roleGuard.js'
import { adminApi } from '../api/adminApi.js'

const ROLE_BADGE = {
  Administrator: 'member-badge--admin',
  Supervisor:    'member-badge--supervisor',
  Responder:     'member-badge--responder',
}

const ROLE_ORDER = { Administrator: 0, Supervisor: 1, Responder: 2 }

export default function MemberList({ stationId, members, onMembersChanged }) {
  const { user, getToken } = useAuth()
  const isAdmin = canAccess(user, 'administrator')
  const [removing, setRemoving] = useState(null)
  const [error, setError]       = useState(null)

  async function handleRemove(member) {
    if (!window.confirm(
      `Remove ${member.preferred_name || member.user_id} from this station?`
    )) return

    setRemoving(member.user_id)
    setError(null)
    try {
      await adminApi.removeMember(stationId, member.user_id, getToken)
      onMembersChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setRemoving(null)
    }
  }

  function canRemove(member) {
    // Can't remove yourself
    if (member.user_id === user?.email) return false
    // Only admins can remove other admins
    if (member.role === 'Administrator' && !isAdmin) return false
    return true
  }

  if (members.length === 0) {
    return (
      <p className="member-list__empty">No members assigned to this station yet.</p>
    )
  }

  const sorted = [...members].sort((a, b) => {
    const roleDiff = (ROLE_ORDER[a.role] ?? 9) - (ROLE_ORDER[b.role] ?? 9)
    if (roleDiff !== 0) return roleDiff
    const nameA = (a.preferred_name || a.user_id).toLowerCase()
    const nameB = (b.preferred_name || b.user_id).toLowerCase()
    return nameA.localeCompare(nameB)
  })

  return (
    <div className="member-list">
      {error && (
        <div className="member-list__error" role="alert">⚠ {error}</div>
      )}
      {sorted.map(member => (
        <div key={member.member_id} className="member-row">
          <div className="member-row__info">
            <span className="member-row__name">
              {member.preferred_name || member.user_id}
            </span>
            {member.preferred_name && (
              <span className="member-row__email">{member.user_id}</span>
            )}
            <span className={`member-badge ${ROLE_BADGE[member.role] ?? ''}`}>
              {member.role}
            </span>
          </div>
          {canRemove(member) ? (
            <button
              className="member-row__remove"
              onClick={() => handleRemove(member)}
              disabled={removing === member.user_id}
              type="button"
            >
              {removing === member.user_id ? 'Removing…' : 'Remove'}
            </button>
          ) : member.user_id === user?.email ? (
            <span className="member-row__you">You</span>
          ) : null}
        </div>
      ))}
    </div>
  )
}
