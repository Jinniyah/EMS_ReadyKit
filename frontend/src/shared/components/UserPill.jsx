/**
 * shared/components/UserPill.jsx
 * Logged-in user identity pill — shown on every screen in the app header.
 *
 * Displays: initials avatar, name, active role badge, and a dropdown menu with:
 *   - One button per available role (ACC-B7: multi-role switching)
 *   - Sign out
 *   - Dev role switcher (development only)
 *
 * ACC-B7: If the user holds multiple roles at the current station, all roles
 * are listed in the dropdown. The active role is stored in localStorage and
 * drives UI rendering (canAccess checks, crew mode badge, etc).
 * The JWT is unchanged -- all API permissions remain at the real role level.
 *
 * Accessibility:
 *   - Dropdown button is keyboard-accessible (Enter/Space/Escape)
 *   - Dropdown closes on outside click or Escape
 *   - All interactive elements are 48px minimum tap targets
 */

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { useAuth, ROLE_RESPONDER } from '../hooks/useAuth.jsx'
import { useRoleMode } from '../hooks/useRoleMode.jsx'

const ROLE_ICONS = {
  Administrator: '🛡',
  Supervisor:    '👁',
  Responder:     '🚑',
}

export default function UserPill({ stationId = null }) {
  const { user, logout, getToken } = useAuth()
  const {
    activeRole,
    availableRoles,
    setActiveRole,
    canSwitch,
    isCrewMode,
  } = useRoleMode(stationId, getToken)

  const [open, setOpen]     = useState(false)
  const buttonRef           = useRef(null)
  const menuRef             = useRef(null)

  // Display role: use activeRole when available, fall back to JWT role
  const displayRole = activeRole ?? user?.role

  // Close on outside click
  useEffect(() => {
    if (!open) return
    function handler(e) {
      if (
        menuRef.current && !menuRef.current.contains(e.target) &&
        buttonRef.current && !buttonRef.current.contains(e.target)
      ) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    function handler(e) {
      if (e.key === 'Escape') {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open])

  const handleLogout = useCallback(() => {
    setOpen(false)
    logout()
  }, [logout])

  const handleRoleSwitch = useCallback((role) => {
    setOpen(false)
    setActiveRole(role)
  }, [setActiveRole])

  if (!user) return null

  return (
    <div className="user-pill">
      {/* Trigger button */}
      <button
        ref={buttonRef}
        className={`user-pill__trigger ${isCrewMode ? 'user-pill__trigger--crew' : ''}`}
        onClick={() => setOpen(o => !o)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label={`${user.name}, ${displayRole}${isCrewMode ? ', crew mode active' : ''}. Open menu`}
        type="button"
      >
        <span className="user-pill__avatar" aria-hidden="true">
          {user.initials}
        </span>
        <span className="user-pill__info">
          <span className="user-pill__name">{user.name}</span>
          <span className="user-pill__role">
            {ROLE_ICONS[displayRole] ?? ''} {displayRole}
            {isCrewMode ? ' (crew)' : ''}
          </span>
        </span>
        {isCrewMode && (
          <span className="user-pill__crew-badge" aria-label="Crew mode active">
            CREW
          </span>
        )}
        <span className="user-pill__chevron" aria-hidden="true">
          {open ? '▲' : '▼'}
        </span>
      </button>

      {/* Dropdown menu */}
      {open && (
        <div
          ref={menuRef}
          className="user-pill__menu"
          role="menu"
          aria-label="User menu"
        >
          <div className="user-pill__menu-header">
            <div className="user-pill__menu-name">{user.name}</div>
            <div className="user-pill__menu-email">{user.email}</div>
          </div>

          <div className="user-pill__menu-divider" role="separator" />

          {/* Role switcher — shown when user holds more than one role */}
          {canSwitch && (
            <>
              <div className="user-pill__menu-section-label">Switch role</div>
              {availableRoles.map(role => (
                <button
                  key={role}
                  className={`user-pill__menu-item ${activeRole === role ? 'user-pill__menu-item--active' : ''}`}
                  onClick={() => handleRoleSwitch(role)}
                  role="menuitem"
                  type="button"
                  aria-current={activeRole === role ? 'true' : undefined}
                >
                  {activeRole === role ? '● ' : '○ '}
                  {ROLE_ICONS[role] ?? ''} {role}
                </button>
              ))}
              <div className="user-pill__menu-divider" role="separator" />
            </>
          )}

          <DevRoleSwitcher />

          <button
            className="user-pill__menu-item user-pill__menu-item--danger"
            onClick={handleLogout}
            role="menuitem"
            type="button"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}

// ── Dev-only role switcher (shown only in development) ────────────────────────

function DevRoleSwitcher() {
  const { _isDev, _devRoleKey, _switchRole, _devUsers } = useAuth()
  if (!_isDev) return null

  return (
    <>
      <div className="user-pill__menu-divider" role="separator" />
      <div className="user-pill__menu-dev-label">Dev: switch persona</div>
      {Object.entries(_devUsers).map(([key, u]) => (
        <button
          key={key}
          className={`user-pill__menu-item user-pill__menu-item--dev ${_devRoleKey === key ? 'user-pill__menu-item--active' : ''}`}
          onClick={() => _switchRole(key)}
          role="menuitem"
          type="button"
        >
          {_devRoleKey === key ? '● ' : '○ '}{u.role}
        </button>
      ))}
    </>
  )
}
