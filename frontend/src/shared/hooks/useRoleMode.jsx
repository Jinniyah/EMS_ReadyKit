/**
 * shared/hooks/useRoleMode.jsx
 * Role switching for users who hold multiple roles at a station (ACC-B7).
 *
 * Previously this was a binary crew/supervisor toggle for Supervisor+.
 * Now it supports any combination of roles by fetching the user's active
 * roles at the current station from GET /stations/my/roles.
 *
 * Role hierarchy (highest-privilege wins for initial selection):
 *   Administrator > Supervisor > Responder
 *
 * The active role is stored in localStorage so it persists across page
 * refreshes but resets when the station changes.
 *
 * Usage:
 *   const { activeRole, availableRoles, setActiveRole, isCrewMode } = useRoleMode(stationId, getToken)
 *
 * isCrewMode is kept for backward compatibility — true when activeRole === 'Responder'
 * and the user also holds a higher role.
 */

import { useState, useEffect, useCallback } from 'react'
import { useAuth, ROLE_ADMINISTRATOR, ROLE_SUPERVISOR, ROLE_RESPONDER } from './useAuth.jsx'
import { apiGet } from '../api/client.js'

const STORAGE_KEY = 'ems_active_role'
const ROLE_LEVEL  = { Administrator: 3, Supervisor: 2, Responder: 1 }

function highestRole(roles) {
  if (!roles?.length) return ROLE_RESPONDER
  return roles.reduce((best, r) => (ROLE_LEVEL[r] ?? 0) > (ROLE_LEVEL[best] ?? 0) ? r : best, roles[0])
}

export function useRoleMode(stationId = null, getToken = null) {
  const { user, _isDev } = useAuth()

  // In dev mode, available roles are the three fixed personas — no API call needed.
  const [availableRoles, setAvailableRoles] = useState(() =>
    _isDev ? [user?.role].filter(Boolean) : [user?.role].filter(Boolean)
  )
  const [activeRole, setActiveRoleState] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ?? user?.role ?? ROLE_RESPONDER
  })
  const [loading, setLoading] = useState(false)

  // Fetch available roles from the API when stationId is known (production only).
  useEffect(() => {
    if (!stationId || !getToken || _isDev) return
    if (!user?.email) return

    setLoading(true)
    apiGet(`/api/v1/stations/my/roles?station_id=${stationId}`, getToken)
      .then(roles => {
        if (!Array.isArray(roles) || roles.length === 0) return
        setAvailableRoles(roles)
        // If the stored role is not in available roles, reset to highest available.
        const stored = localStorage.getItem(STORAGE_KEY)
        if (!stored || !roles.includes(stored)) {
          const best = highestRole(roles)
          localStorage.setItem(STORAGE_KEY, best)
          setActiveRoleState(best)
        }
      })
      .catch(() => {
        // Fall back to JWT role — non-fatal
        setAvailableRoles([user?.role].filter(Boolean))
      })
      .finally(() => setLoading(false))
  }, [stationId, getToken, user?.email, _isDev])

  const setActiveRole = useCallback((role) => {
    localStorage.setItem(STORAGE_KEY, role)
    setActiveRoleState(role)
  }, [])

  // Backward-compat: crew mode = user has a higher role but is working as Responder
  const canSwitch = availableRoles.length > 1
  const isCrewMode = canSwitch && activeRole === ROLE_RESPONDER
  const isSupervisorMode = !isCrewMode

  // Legacy toggle (kept for any code still using it)
  const toggleCrewMode = useCallback(() => {
    if (!canSwitch) return
    if (isCrewMode) {
      // Switch to highest non-Responder role
      const higher = availableRoles.filter(r => r !== ROLE_RESPONDER)
      setActiveRole(highestRole(higher.length ? higher : availableRoles))
    } else {
      setActiveRole(ROLE_RESPONDER)
    }
  }, [canSwitch, isCrewMode, availableRoles, setActiveRole])

  return {
    activeRole,
    availableRoles,
    setActiveRole,
    canSwitch,
    loading,
    // Backward compat
    isCrewMode,
    isSupervisorMode,
    toggleCrewMode,
  }
}
