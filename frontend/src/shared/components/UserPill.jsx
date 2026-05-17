/**
 * shared/components/UserPill.jsx
 * Logged-in user identity pill — shown on every screen in the app header.
 *
 * Displays: initials avatar, name, role badge, and a dropdown menu with:
 *   - Sign out
 *   - Switch to crew mode (Supervisor and Administrator only)
 *   - Dev role switcher (development only)
 *
 * From ADR-005 Decision 4: role switching is display-only, no JWT change.
 * The amber "CREW MODE" badge appears in the pill when crew mode is active.
 *
 * Accessibility:
 *   - Dropdown button is keyboard-accessible (Enter/Space/Escape)
 *   - Dropdown closes on outside click or Escape
 *   - All interactive elements are 48×48px minimum tap targets
 */

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { useAuth, ROLE_SUPERVISOR, ROLE_ADMINISTRATOR } from '../hooks/useAuth.jsx'
import { useRoleMode } from '../hooks/useRoleMode.jsx'

export default function UserPill() {
  const { user, logout } = useAuth()
  const { isCrewMode, toggleCrewMode } = useRoleMode()
  const [open, setOpen] = useState(false)
  const buttonRef = useRef(null)
  const menuRef = useRef(null)

  const canSwitchRole = user?.role === ROLE_SUPERVISOR || user?.role === ROLE_ADMINISTRATOR

  // Close on outside click
  useEffect(() => {
    if (!open) return
    function handler(e) {
      if (menuRef.current && !menuRef.current.contains(e.target) &&
          buttonRef.current && !buttonRef.current.contains(e.target)) {
        setOpen(false)
      }
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

  const handleToggleCrewMode = useCallback(() => {
    setOpen(false)
    toggleCrewMode()
  }, [toggleCrewMode])

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
        aria-label={`${user.name}, ${user.role}${isCrewMode ? ', crew mode active' : ''}. Open menu`}
        type="button"
      >
        <span className="user-pill__avatar" aria-hidden="true">
          {user.initials}
        </span>
        <span className="user-pill__info">
          <span className="user-pill__name">{user.name}</span>
          <span className="user-pill__role">
            {isCrewMode
              ? `${user.role} (crew mode)`
              : user.role}
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

          {canSwitchRole && (
            <button
              className="user-pill__menu-item"
              onClick={handleToggleCrewMode}
              role="menuitem"
              type="button"
            >
              {isCrewMode ? '↑ Switch to supervisor view' : '↓ Switch to crew mode'}
            </button>
          )}

          <DevRoleSwitcher />

          <div className="user-pill__menu-divider" role="separator" />

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
      <div className="user-pill__menu-dev-label">Dev: switch role</div>
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
