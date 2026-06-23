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

const ROLE_LEVEL  = { Administrator: 3, Supervisor: 2, Responder: 1 }

function highestRole(roles) {
  if (!roles?.length) return ROLE_RESPONDER
  return roles.reduce((best, r) => (ROLE_LEVEL[r] ?? 0) > (ROLE_LEVEL[best] ?? 0) ? r : best, roles[0])
}

export function useRoleMode(stationId = null, getToken = null) {
  const { user, _isDev, setActiveRole } = useAuth()

  // activeRole lives in useAuth (persisted via localStorage + React state).
  // Reading it here keeps useRoleMode in sync with canAccess automatically.
  const activeRole = user?.activeRole ?? user?.role ?? ROLE_RESPONDER

  const [availableRoles, setAvailableRoles] = useState([user?.role].filter(Boolean))
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
        // If the current active role is not among the station's roles, reset to highest.
        if (!roles.includes(activeRole)) {
          setActiveRole(highestRole(roles))
        }
      })
      .catch(() => {
        setAvailableRoles([user?.role].filter(Boolean))
      })
      .finally(() => setLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stationId, getToken, user?.email, _isDev])

  // Backward-compat: crew mode = user has a higher role but is working as Responder
  const canSwitch = availableRoles.length > 1
  const isCrewMode = canSwitch && activeRole === ROLE_RESPONDER
  const isSupervisorMode = !isCrewMode

  // Legacy toggle (kept for any code still using it)
  const toggleCrewMode = useCallback(() => {
    if (!canSwitch) return
    if (isCrewMode) {
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
    isCrewMode,
    isSupervisorMode,
    toggleCrewMode,
  }
}
