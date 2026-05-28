/**
 * shared/hooks/useAuth.jsx
 * Authentication state hook — real MSAL in production, dev fake in development.
 *
 * ## Production auth flow
 * Uses loginRedirect / logoutRedirect instead of loginPopup / logoutPopup.
 * Popup flow is unreliable on mobile Chrome and in incognito windows.
 * Redirect flow navigates to login.microsoftonline.com and back, which
 * works on all browsers and devices including mobile Chrome and incognito.
 *
 * ## MSAL initialization
 * msalInstance.initialize() is called in main.jsx before ReactDOM.createRoot.
 * MsalProvider handles handleRedirectPromise internally once the instance is
 * initialized — do NOT call it again here, it causes the
 * "uninitialized_public_client_application" error on page refresh.
 *
 * ## Development (VITE_APP_ENV=development)
 * DevAuthProvider replaces MSAL entirely. No Azure AD setup needed.
 * The dev banner lets you switch between three roles.
 *
 * ## useAuth() return shape
 * {
 *   isAuthenticated: boolean
 *   isLoading:       boolean
 *   user:            { name, email, role, initials } | null
 *   getToken:        () => Promise<string>
 *   login:           () => void
 *   logout:          () => void
 * }
 */

import React, { createContext, useContext, useCallback } from 'react'
import { useMsal, useIsAuthenticated } from '@azure/msal-react'
import { InteractionRequiredAuthError } from '@azure/msal-browser'
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
    email: 'test-administrator@ems.local',
    role: ROLE_ADMINISTRATOR,
    initials: 'TA',
    token: 'test-administrator',
  },
  supervisor: {
    name: 'Test Supervisor',
    email: 'test-supervisor@ems.local',
    role: ROLE_SUPERVISOR,
    initials: 'TS',
    token: 'test-supervisor',
  },
  responder: {
    name: 'Test Responder',
    email: 'test-responder@ems.local',
    role: ROLE_RESPONDER,
    initials: 'TR',
    token: 'test-responder',
  },
}

// ── DevAuthProvider ───────────────────────────────────────────────────────────
export function DevAuthProvider({ children }) {
  const [roleKey, setRoleKey] = React.useState(
    () => localStorage.getItem('ems_dev_role') ?? 'administrator'
  )
  const [isAuthenticated, setIsAuthenticated] = React.useState(true)

  const user = DEV_USERS[roleKey] ?? DEV_USERS.administrator

  const getToken    = useCallback(async () => user.token, [user.token])
  const login       = useCallback(() => setIsAuthenticated(true), [])
  const logout      = useCallback(() => setIsAuthenticated(false), [])
  const switchRole  = useCallback((key) => {
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
export function useAuth() {
  const devCtx = useContext(DevAuthContext)
  if (devCtx !== null) return devCtx
  // eslint-disable-next-line react-hooks/rules-of-hooks
  return useMsalAuth()
}

// ── Production MSAL implementation ────────────────────────────────────────────
function useMsalAuth() {
  const { instance, accounts, inProgress } = useMsal()
  const isAuthenticated = useIsAuthenticated()

  const account = accounts[0] ?? null
  const role    = _extractRole(account?.idTokenClaims?.roles)

  const user = account
    ? {
        name:     account.name ?? account.username,
        email:    account.username,
        role,
        initials: _initials(account.name ?? account.username),
      }
    : null

  // Silent token acquisition with redirect fallback.
  // If the silent call fails (expired session, consent required), fall back
  // to acquireTokenRedirect which navigates away and back.
  const getToken = useCallback(async () => {
    if (!account) throw new Error('Not authenticated')
    try {
      const result = await instance.acquireTokenSilent({
        ...apiTokenRequest,
        account,
      })
      return result.accessToken
    } catch (err) {
      if (err instanceof InteractionRequiredAuthError) {
        // Silent renewal failed — redirect the user to re-authenticate.
        await instance.acquireTokenRedirect({ ...apiTokenRequest, account })
        // This line is never reached — redirect navigates away.
      }
      throw err
    }
  }, [instance, account])

  // Redirect flow — navigates to login.microsoftonline.com and back.
  // Works on all browsers including mobile Chrome and incognito.
  const login = useCallback(() => {
    instance.loginRedirect(apiTokenRequest).catch((err) => {
      console.error('[MSAL] loginRedirect error:', err)
    })
  }, [instance])

  const logout = useCallback(() => {
    instance.logoutRedirect({ account }).catch((err) => {
      console.error('[MSAL] logoutRedirect error:', err)
    })
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
