/**
 * Manual mock for shared/hooks/useAuth.jsx
 * Used by vi.mock('...useAuth.jsx') in component tests.
 *
 * Personas mirror the backend Bearer test-{role} token pattern:
 *   Jamie  — Responder  — test-responder@ems.local
 *   Earl   — Supervisor — test-supervisor@ems.local
 *   Jennifer — Administrator — test-admin@ems.local
 */
import { vi } from 'vitest'

export const ROLE_ADMINISTRATOR = 'Administrator'
export const ROLE_SUPERVISOR    = 'Supervisor'
export const ROLE_RESPONDER     = 'Responder'

export const TEST_USERS = {
  jamie: {
    name:     'Jamie Responder',
    email:    'test-responder@ems.local',
    role:     ROLE_RESPONDER,
    initials: 'JR',
  },
  earl: {
    name:     'Earl Supervisor',
    email:    'test-supervisor@ems.local',
    role:     ROLE_SUPERVISOR,
    initials: 'ES',
  },
  jennifer: {
    name:     'Jennifer Admin',
    email:    'test-admin@ems.local',
    role:     ROLE_ADMINISTRATOR,
    initials: 'JA',
  },
}

export const useAuth = vi.fn(() => ({
  isAuthenticated: true,
  isLoading:       false,
  user:            TEST_USERS.jamie,
  getToken:        vi.fn().mockResolvedValue('test-token'),
  login:           vi.fn(),
  logout:          vi.fn(),
}))
