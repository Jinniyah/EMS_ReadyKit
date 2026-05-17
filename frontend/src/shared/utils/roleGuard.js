/**
 * shared/utils/roleGuard.js
 * Role-based render guards.
 *
 * Usage:
 *   import { canAccess, RoleGuard } from '../utils/roleGuard.js'
 *
 *   // Programmatic check
 *   if (canAccess(user, 'supervisor')) { ... }
 *
 *   // JSX guard (renders children or fallback)
 *   <RoleGuard role="supervisor" user={user}>
 *     <SupervisorDashboard />
 *   </RoleGuard>
 */

import React from 'react'
import { ROLE_ADMINISTRATOR, ROLE_SUPERVISOR, ROLE_RESPONDER } from '../hooks/useAuth.jsx'

// Role hierarchy — higher index = more privilege
const ROLE_LEVEL = {
  [ROLE_RESPONDER]:     1,
  [ROLE_SUPERVISOR]:    2,
  [ROLE_ADMINISTRATOR]: 3,
}

/**
 * Returns true if the user's role meets or exceeds the required level.
 *
 * @param {{ role: string } | null} user
 * @param {'responder' | 'supervisor' | 'administrator'} required
 */
export function canAccess(user, required) {
  if (!user) return false
  const userLevel     = ROLE_LEVEL[user.role] ?? 0
  const requiredLevel = ROLE_LEVEL[_normalise(required)] ?? 99
  return userLevel >= requiredLevel
}

/**
 * JSX wrapper that renders children only if the user meets the role requirement.
 * Renders `fallback` (default: null) if the user does not qualify.
 */
export function RoleGuard({ role, user, children, fallback = null }) {
  return canAccess(user, role) ? children : fallback
}

// Normalise shorthand role strings to the canonical enum values
function _normalise(role) {
  const map = {
    administrator: ROLE_ADMINISTRATOR,
    supervisor:    ROLE_SUPERVISOR,
    responder:     ROLE_RESPONDER,
    // Accept canonical values too
    [ROLE_ADMINISTRATOR]: ROLE_ADMINISTRATOR,
    [ROLE_SUPERVISOR]:    ROLE_SUPERVISOR,
    [ROLE_RESPONDER]:     ROLE_RESPONDER,
  }
  return map[role?.toLowerCase?.()] ?? role
}
