/**
 * tests/roleGuard.test.js
 * canAccess() for all three roles including the 'admin' alias regression
 * (Session J bug — canAccess(user, 'admin') silently returned false before fix).
 */
import { describe, it, expect, vi } from 'vitest'

// Mock useAuth.jsx so the constants are available without loading MSAL.
vi.mock('../hooks/useAuth.jsx', () => ({
  ROLE_ADMINISTRATOR: 'Administrator',
  ROLE_SUPERVISOR:    'Supervisor',
  ROLE_RESPONDER:     'Responder',
}))

import { canAccess } from '../roleGuard.js'

const responder     = { role: 'Responder' }
const supervisor    = { role: 'Supervisor' }
const administrator = { role: 'Administrator' }

describe('canAccess — null / missing user', () => {
  it('null user returns false for any role', () => {
    expect(canAccess(null, 'responder')).toBe(false)
    expect(canAccess(null, 'supervisor')).toBe(false)
    expect(canAccess(null, 'administrator')).toBe(false)
  })

  it('undefined user returns false', () => {
    expect(canAccess(undefined, 'responder')).toBe(false)
  })
})

describe('canAccess — Responder', () => {
  it('can access responder-level routes', () => {
    expect(canAccess(responder, 'responder')).toBe(true)
  })

  it('cannot access supervisor routes', () => {
    expect(canAccess(responder, 'supervisor')).toBe(false)
  })

  it('cannot access administrator routes', () => {
    expect(canAccess(responder, 'administrator')).toBe(false)
  })

  it('cannot access via admin alias', () => {
    expect(canAccess(responder, 'admin')).toBe(false)
  })
})

describe('canAccess — Supervisor', () => {
  it('can access responder-level routes', () => {
    expect(canAccess(supervisor, 'responder')).toBe(true)
  })

  it('can access supervisor routes', () => {
    expect(canAccess(supervisor, 'supervisor')).toBe(true)
  })

  it('cannot access administrator routes', () => {
    expect(canAccess(supervisor, 'administrator')).toBe(false)
  })

  it('cannot access via admin alias', () => {
    expect(canAccess(supervisor, 'admin')).toBe(false)
  })
})

describe('canAccess — Administrator', () => {
  it('can access responder-level routes', () => {
    expect(canAccess(administrator, 'responder')).toBe(true)
  })

  it('can access supervisor routes', () => {
    expect(canAccess(administrator, 'supervisor')).toBe(true)
  })

  it('can access administrator routes', () => {
    expect(canAccess(administrator, 'administrator')).toBe(true)
  })

  it("'admin' alias resolves to Administrator — Session J regression", () => {
    expect(canAccess(administrator, 'admin')).toBe(true)
  })

  it('canonical role string works', () => {
    expect(canAccess(administrator, 'Administrator')).toBe(true)
  })
})

describe('canAccess — activeRole override (ACC-B7 multi-role regression)', () => {
  // When a user holds all three roles in Azure AD, user.role is always
  // Administrator (highest-privilege wins in _extractRole). The role switcher
  // sets activeRole to let them see lower-privilege views.  canAccess must
  // respect activeRole so that switching to Responder actually hides admin UI.
  const adminSwitchedToResponder = { role: 'Administrator', activeRole: 'Responder' }
  const adminSwitchedToSupervisor = { role: 'Administrator', activeRole: 'Supervisor' }
  const adminNoOverride = { role: 'Administrator', activeRole: 'Administrator' }

  it('admin switched to Responder: can access responder routes', () => {
    expect(canAccess(adminSwitchedToResponder, 'responder')).toBe(true)
  })

  it('admin switched to Responder: cannot access supervisor routes', () => {
    expect(canAccess(adminSwitchedToResponder, 'supervisor')).toBe(false)
  })

  it('admin switched to Responder: cannot access administrator routes', () => {
    expect(canAccess(adminSwitchedToResponder, 'administrator')).toBe(false)
  })

  it('admin switched to Supervisor: can access supervisor routes', () => {
    expect(canAccess(adminSwitchedToSupervisor, 'supervisor')).toBe(true)
  })

  it('admin switched to Supervisor: cannot access administrator routes', () => {
    expect(canAccess(adminSwitchedToSupervisor, 'administrator')).toBe(false)
  })

  it('admin with activeRole=Administrator: still has full access', () => {
    expect(canAccess(adminNoOverride, 'administrator')).toBe(true)
  })

  it('user with no activeRole field falls back to role', () => {
    expect(canAccess({ role: 'Supervisor' }, 'administrator')).toBe(false)
    expect(canAccess({ role: 'Supervisor' }, 'supervisor')).toBe(true)
  })
})
