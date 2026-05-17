/**
 * shared/hooks/useRoleMode.jsx
 * Display-only crew/supervisor mode switching for Supervisor and Administrator.
 *
 * From ADR-005 Decision 4: role switching changes only the UI.
 * The JWT is unchanged — all API permissions remain at the real role level.
 * Crew mode preference resets on logout (never stored in sessionStorage).
 *
 * Usage:
 *   const { isCrewMode, isSupervisorMode, toggleCrewMode } = useRoleMode()
 */

import { useState, useCallback } from 'react'
import { useAuth, ROLE_SUPERVISOR, ROLE_ADMINISTRATOR } from './useAuth.jsx'

const STORAGE_KEY = 'ems_role_mode'

export function useRoleMode() {
  const { user } = useAuth()

  const canSwitch = user?.role === ROLE_SUPERVISOR || user?.role === ROLE_ADMINISTRATOR

  // Read initial value from localStorage but only for eligible roles.
  const [mode, setMode] = useState(() => {
    if (!canSwitch) return 'supervisor'
    return localStorage.getItem(STORAGE_KEY) ?? 'supervisor'
  })

  const isCrewMode = canSwitch && mode === 'crew'
  const isSupervisorMode = !isCrewMode

  const toggleCrewMode = useCallback(() => {
    if (!canSwitch) return
    setMode(prev => {
      const next = prev === 'crew' ? 'supervisor' : 'crew'
      localStorage.setItem(STORAGE_KEY, next)
      return next
    })
  }, [canSwitch])

  const setCrewMode = useCallback(() => {
    if (!canSwitch) return
    localStorage.setItem(STORAGE_KEY, 'crew')
    setMode('crew')
  }, [canSwitch])

  const setSupervisorMode = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, 'supervisor')
    setMode('supervisor')
  }, [])

  return {
    isCrewMode,
    isSupervisorMode,
    toggleCrewMode,
    setCrewMode,
    setSupervisorMode,
    canSwitch,
  }
}
