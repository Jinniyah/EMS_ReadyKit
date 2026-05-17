/**
 * shared/hooks/useAuth.jsx
 * Authentication state hook — real MSAL in production, dev fake in development.
 *
 * ## Production (VITE_APP_ENV=production)
 * Wraps @azure/msal-react.  Parses Azure AD roles from the JWT id_token.
 * Provides getToken() which silently acquires a fresh access token for the API.
 *
 * ## Development (VITE_APP_ENV=development)
 * DevAuthProvider replaces MSAL entirely.  No Azure AD setup needed.
 * The dev banner lets you switch between three roles, which sets the token
 * to "test-administrator", "test-supervisor", or "test-responder" — the exact
 * tokens the FastAPI backend accepts in dev mode.
 *
 * ## useAuth() return shape
 * {
 *   isAuthenticated: boolean
 *   isLoading:       boolean
 *   user:            { name, email, role, initials } | null
 *   getToken:        () => Promise<string>     — returns Bearer token value
 *   login:           () => void
 *   logout:          () => void
 * }
 */

import React, { createContext, useContext, useState, useCallback } from 'react'
import { useMsal, useIsAuthenticated } from '@azure/msal-react'
import { apiTokenRequest } from '../api/authConfig.js'

// ── Roles as defined in Azure AD App Registration ─────────────────────────────
export const ROLE_ADMINISTRATOR = 'Administrator'
export const ROLE_SUPERVISOR    = 'Supervisor'
export const ROLE_RESPONDER     = 'Responder'

// ── Auth context (used by DevAuthProvider only) ───────────────────────────────
const DevAuthContext = createContext(null)

// ── Dev fake users ────────────────────────────────────────────────────────────
const DEV_USERS = {
  administrator: {
    name: 'Test Administrator',
    email: 'admin@ems.local',
    role: ROLE_ADMINISTRATOR,
    initials: 'TA',
    token: 'test-administrator',
  },
  supervisor: {
    name: 'Test Supervisor',
    email: 'supervisor@ems.local',
    role: ROLE_SUPERVISOR,
    initials: 'TS',
    token: 'test-supervisor',
  },
  responder: {
    name: 'Test Responder',
    email: 'responder@ems.local',
    role: ROLE_RESPONDER,
    initials: 'TR',
    token: 'test-responder',
  },
}

// ── DevAuthProvider ───────────────────────────────────────────────────────────
/**
 * Replaces MsalProvider in development.
 * Reads the active dev role from localStorage so role choice persists across
 * hot reloads but resets when the browser tab is closed.
 */
export function DevAuthProvider({ children }) {
  const [roleKey, setRoleKey] = useState(
    () => localStorage.getItem('ems_dev_role') ?? 'administrator'
  )
  const [isAuthenticated, setIsAuthenticated] = useState(true)

  const user = DEV_USERS[roleKey] ?? DEV_USERS.administrator

  const getToken = useCallback(async () => user.token, [user.token])

  const login = useCallback(() => setIsAuthenticated(true), [])
  const logout = useCallback(() => setIsAuthenticated(false), [])

  const switchRole = useCallback((key) => {
    localStorage.setItem('ems_dev_role', key)
    setRoleKey(key)
  }, [])

  const value = {
    isAuthenticated,
    isLoading: false,
    user: isAuthenticated ? user : null,
    getToken,
    login,
    logout,
    // Dev-only
    _isDev: true,
    _devRoleKey: roleKey,
    _switchRole: switchRole,
    _devUsers: DEV_USERS,
  }

  return (
    <DevAuthContext.Provider value={value}>
      {children}
    </DevAuthContext.Provider>
  )
}

// ── useAuth ───────────────────────────────────────────────────────────────────
/**
 * Primary auth hook — works identically in dev and production.
 * Components always call useAuth(); they never import MSAL directly.
 */
export function useAuth() {
  // Dev path
  const devCtx = useContext(DevAuthContext)
  if (devCtx !== null) return devCtx

  // Production path — delegate to MSAL hooks
  // eslint-disable-next-line react-hooks/rules-of-hooks
  return useMsalAuth()
}

// ── Production MSAL implementation ────────────────────────────────────────────
function useMsalAuth() {
  const { instance, accounts, inProgress } = useMsal()
  const isAuthenticated = useIsAuthenticated()

  const account = accounts[0] ?? null

  // Parse role from JWT id_token claims.
  // Azure AD sends roles as an array claim; we take the highest-privilege one.
  const role = _extractRole(account?.idTokenClaims?.roles)

  const user = account
    ? {
        name:     account.name ?? account.username,
        email:    account.username,
        role,
        initials: _initials(account.name ?? account.username),
      }
    : null

  const getToken = useCallback(async () => {
    if (!account) throw new Error('Not authenticated')
    const result = await instance.acquireTokenSilent({
      ...apiTokenRequest,
      account,
    })
    return result.accessToken
  }, [instance, account])

  const login = useCallback(() => {
    instance.loginPopup(apiTokenRequest).catch(console.error)
  }, [instance])

  const logout = useCallback(() => {
    instance.logoutPopup({ account }).catch(console.error)
  }, [instance, account])

  return {
    isAuthenticated,
    isLoading: inProgress !== 'none',
    user,
    getToken,
    login,
    logout,
    _isDev: false,
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Pick the highest-privilege role from the roles array claim.
 * Azure AD sends all groups the user belongs to; we pick in priority order.
 */
function _extractRole(roles) {
  if (!Array.isArray(roles)) return ROLE_RESPONDER
  if (roles.includes(ROLE_ADMINISTRATOR)) return ROLE_ADMINISTRATOR
  if (roles.includes(ROLE_SUPERVISOR))    return ROLE_SUPERVISOR
  return ROLE_RESPONDER
}

function _initials(name) {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  return parts[0].slice(0, 2).toUpperCase()
}
