import { vi } from 'vitest'

export const useMsal = vi.fn(() => ({
  instance: {
    loginRedirect:         vi.fn(),
    logoutRedirect:        vi.fn(),
    acquireTokenSilent:    vi.fn().mockResolvedValue({ accessToken: 'mock-token' }),
    acquireTokenRedirect:  vi.fn(),
  },
  accounts:   [],
  inProgress: 'none',
}))

export const useIsAuthenticated = vi.fn(() => true)

export const MsalProvider          = ({ children }) => children
export const AuthenticatedTemplate = ({ children }) => children
export const UnauthenticatedTemplate = () => null
