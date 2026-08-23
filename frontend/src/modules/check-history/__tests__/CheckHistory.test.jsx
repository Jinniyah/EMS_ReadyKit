/**
 * tests/CheckHistory.test.jsx
 * My Checks tab, All Checks tab (Supervisor+ only), soft-deleted checks.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('@azure/msal-react')
vi.mock('@azure/msal-browser')
vi.mock('../../../shared/hooks/useAuth.jsx')
vi.mock('../../../shared/hooks/useApi.js')

// Stub sub-components that have their own API dependencies
vi.mock('../components/CheckList.jsx', () => ({
  default: ({ checks, showPerformedBy }) => (
    <ul data-testid="check-list" data-show-performed-by={showPerformedBy ? 'true' : 'false'}>
      {(checks ?? []).map(c => (
        <li key={c.check_id} data-testid={`check-${c.check_id}`}>
          {c.performed_by}
        </li>
      ))}
    </ul>
  ),
}))
vi.mock('../components/CheckDetail.jsx', () => ({
  default: ({ check, onBack }) => (
    <div data-testid="check-detail">
      <button onClick={onBack} type="button">Back</button>
    </div>
  ),
}))
vi.mock('../../../shared/components/ErrorBoundary.jsx', () => ({
  default: ({ children }) => <>{children}</>,
}))
vi.mock('../components/ExportPanel.jsx', () => ({
  default: () => <div data-testid="export-panel" />,
}))

import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi }  from '../../../shared/hooks/useApi.js'
import CheckHistoryScreen from '../index.jsx'

const STATION = { station_id: 1, name: 'Test Station' }

const MY_CHECKS = [
  { check_id: 1, performed_by: 'test-responder@ems.local', status: 'PASS',        check_date: '2026-06-09' },
  { check_id: 2, performed_by: 'test-responder@ems.local', status: 'NEEDS_RESTOCK', check_date: '2026-06-08' },
]

const ALL_CHECKS = [
  ...MY_CHECKS,
  { check_id: 3, performed_by: 'other-user@ems.local', status: 'FAIL', check_date: '2026-06-09' },
]

function asJamie() {
  useAuth.mockReturnValue({
    isAuthenticated: true, isLoading: false,
    user: { name: 'Jamie', email: 'test-responder@ems.local', role: 'Responder', initials: 'JR' },
    getToken: vi.fn().mockResolvedValue('test-token'),
    login: vi.fn(), logout: vi.fn(),
  })
}

function asEarl() {
  useAuth.mockReturnValue({
    isAuthenticated: true, isLoading: false,
    user: { name: 'Earl', email: 'test-supervisor@ems.local', role: 'Supervisor', initials: 'ES' },
    getToken: vi.fn().mockResolvedValue('test-token'),
    login: vi.fn(), logout: vi.fn(),
  })
}

describe('CheckHistory — Responder view', () => {
  beforeEach(() => {
    asJamie()
    // For Responder: only myChecks fires (isSupervisor=false, activeTab='mine')
    // The deleted and all checks calls return null (guard: isSupervisor && activeTab === 'xxx')
    useApi
      .mockReturnValueOnce({ data: MY_CHECKS, isLoading: false, error: null, refetch: vi.fn() }) // myChecks
      .mockReturnValueOnce({ data: null,      isLoading: false, error: null, refetch: vi.fn() }) // deletedChecks (guarded)
      .mockReturnValue(   { data: null,        isLoading: false, error: null, refetch: vi.fn() }) // allChecks (guarded)
  })

  it('renders My Checks list', () => {
    render(<CheckHistoryScreen station={STATION} onBack={vi.fn()} onNavigateToVehicles={vi.fn()} />)
    expect(screen.getByTestId('check-list')).toBeTruthy()
  })

  it('My Checks list receives all user checks from the API', () => {
    render(<CheckHistoryScreen station={STATION} onBack={vi.fn()} onNavigateToVehicles={vi.fn()} />)
    expect(screen.getByTestId('check-1')).toBeTruthy()
    expect(screen.getByTestId('check-2')).toBeTruthy()
  })

  it('does NOT show the All Checks tab', () => {
    render(<CheckHistoryScreen station={STATION} onBack={vi.fn()} onNavigateToVehicles={vi.fn()} />)
    expect(screen.queryByRole('tab', { name: /all checks/i })).toBeNull()
  })

  it('does NOT show the Deleted tab — soft-deleted checks hidden from Responders', () => {
    render(<CheckHistoryScreen station={STATION} onBack={vi.fn()} onNavigateToVehicles={vi.fn()} />)
    expect(screen.queryByRole('tab', { name: /deleted/i })).toBeNull()
  })

  it('does NOT show a tablist at all', () => {
    render(<CheckHistoryScreen station={STATION} onBack={vi.fn()} onNavigateToVehicles={vi.fn()} />)
    expect(screen.queryByRole('tablist')).toBeNull()
  })

  it('does NOT render the compliance export panel (Responder has no All Checks tab)', () => {
    render(<CheckHistoryScreen station={STATION} onBack={vi.fn()} onNavigateToVehicles={vi.fn()} />)
    expect(screen.queryByTestId('export-panel')).toBeNull()
  })
})

describe('CheckHistory — Supervisor view', () => {
  beforeEach(() => {
    asEarl()
    // Supervisor: isSupervisor=true, initial tab='all'
    useApi
      .mockReturnValueOnce({ data: MY_CHECKS,  isLoading: false, error: null, refetch: vi.fn() }) // myChecks
      .mockReturnValueOnce({ data: null,        isLoading: false, error: null, refetch: vi.fn() }) // deletedChecks (not on 'deleted' tab)
      .mockReturnValue(   { data: ALL_CHECKS,   isLoading: false, error: null, refetch: vi.fn() }) // allChecks
  })

  it('shows the All Checks tab', () => {
    render(<CheckHistoryScreen station={STATION} onBack={vi.fn()} onNavigateToVehicles={vi.fn()} />)
    expect(screen.getByRole('tab', { name: /all checks/i })).toBeTruthy()
  })

  it('shows the Deleted tab', () => {
    render(<CheckHistoryScreen station={STATION} onBack={vi.fn()} onNavigateToVehicles={vi.fn()} />)
    expect(screen.getByRole('tab', { name: /deleted/i })).toBeTruthy()
  })

  it('My Checks tab is also visible to Supervisor', () => {
    render(<CheckHistoryScreen station={STATION} onBack={vi.fn()} onNavigateToVehicles={vi.fn()} />)
    expect(screen.getByRole('tab', { name: /my checks/i })).toBeTruthy()
  })

  it('All Checks tab is active by default for Supervisor', () => {
    render(<CheckHistoryScreen station={STATION} onBack={vi.fn()} onNavigateToVehicles={vi.fn()} />)
    const allTab = screen.getByRole('tab', { name: /all checks/i })
    expect(allTab.getAttribute('aria-selected')).toBe('true')
  })

  it('clicking My Checks tab switches to My Checks list', async () => {
    const user = userEvent.setup()
    // Re-setup for tab switch — need extra API calls
    useApi
      .mockReturnValueOnce({ data: MY_CHECKS, isLoading: false, error: null, refetch: vi.fn() })
      .mockReturnValueOnce({ data: null,      isLoading: false, error: null, refetch: vi.fn() })
      .mockReturnValue(   { data: ALL_CHECKS, isLoading: false, error: null, refetch: vi.fn() })

    render(<CheckHistoryScreen station={STATION} onBack={vi.fn()} onNavigateToVehicles={vi.fn()} />)
    await user.click(screen.getByRole('tab', { name: /my checks/i }))
    const myTab = screen.getByRole('tab', { name: /my checks/i })
    expect(myTab.getAttribute('aria-selected')).toBe('true')
  })

  it('station name appears in the header', () => {
    render(<CheckHistoryScreen station={STATION} onBack={vi.fn()} onNavigateToVehicles={vi.fn()} />)
    expect(screen.getByText('Test Station')).toBeTruthy()
  })

  it('shows the compliance export panel on the All Checks tab', () => {
    render(<CheckHistoryScreen station={STATION} onBack={vi.fn()} onNavigateToVehicles={vi.fn()} />)
    expect(screen.getByTestId('export-panel')).toBeTruthy()
  })
})
