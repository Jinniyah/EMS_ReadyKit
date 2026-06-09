import { vi } from 'vitest'

export class InteractionRequiredAuthError extends Error {
  constructor(message) {
    super(message)
    this.name = 'InteractionRequiredAuthError'
  }
}

export const PublicClientApplication = vi.fn(() => ({
  initialize:           vi.fn().mockResolvedValue(undefined),
  loginRedirect:        vi.fn(),
  logoutRedirect:       vi.fn(),
  acquireTokenSilent:   vi.fn().mockResolvedValue({ accessToken: 'mock-token' }),
  acquireTokenRedirect: vi.fn(),
}))

export const LogLevel = { Error: 0, Warning: 1, Info: 2, Verbose: 3 }
