/**
 * tests/VehicleCard.test.jsx
 * OOS badge, RTS/OOS toggle role-gating, open repair count badge.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('@azure/msal-react')
vi.mock('@azure/msal-browser')
vi.mock('../../../shared/hooks/useAuth.jsx')
vi.mock('../../../shared/hooks/useApi.js')

// Stub sub-components to avoid their own API calls and complex rendering
vi.mock('../components/RepairRequestList.jsx', () => ({
  default: ({ requests }) => (
    <ul data-testid="repair-list">
      {(requests ?? []).map(r => <li key={r.repair_id}>{r.description}</li>)}
    </ul>
  ),
}))
vi.mock('../components/RepairRequestForm.jsx', () => ({
  default: ({ onCancel }) => (
    <div data-testid="repair-form">
      <button onClick={onCancel} type="button">Cancel</button>
    </div>
  ),
}))

import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi }  from '../../../shared/hooks/useApi.js'
import VehicleCard from '../components/VehicleCard.jsx'

const ACTIVE_VEHICLE = {
  vehicle_id:     10,
  vehicle_number: '712',
  vehicle_type:   'BLS',
  active:         true,
  inactive_reason: null,
}

const OOS_VEHICLE = {
  ...ACTIVE_VEHICLE,
  active:         false,
  inactive_reason: 'Transmission failure',
}

const OPEN_REPAIRS = [
  { repair_id: 1, status: 'OPEN',        description: 'Broken seat belt' },
  { repair_id: 2, status: 'IN_PROGRESS', description: 'Oil leak' },
]

function asJamie() {
  useAuth.mockReturnValue({
    isAuthenticated: true,
    isLoading:       false,
    user:            { name: 'Jamie', email: 'test-responder@ems.local', role: 'Responder', initials: 'JR' },
    getToken:        vi.fn().mockResolvedValue('test-token'),
    login: vi.fn(), logout: vi.fn(),
  })
}

function asEarl() {
  useAuth.mockReturnValue({
    isAuthenticated: true,
    isLoading:       false,
    user:            { name: 'Earl', email: 'test-supervisor@ems.local', role: 'Supervisor', initials: 'ES' },
    getToken:        vi.fn().mockResolvedValue('test-token'),
    login: vi.fn(), logout: vi.fn(),
  })
}

describe('VehicleCard — OOS badge', () => {
  beforeEach(() => {
    asJamie()
    useApi.mockReturnValue({ data: [], isLoading: false, error: null, refetch: vi.fn() })
  })

  it('shows Out of Service badge when vehicle.active is false', () => {
    render(<VehicleCard vehicle={OOS_VEHICLE} onVehicleUpdated={vi.fn()} />)
    expect(screen.getByText('Out of Service')).toBeTruthy()
  })

  it('does not show OOS badge when vehicle is active', () => {
    render(<VehicleCard vehicle={ACTIVE_VEHICLE} onVehicleUpdated={vi.fn()} />)
    expect(screen.queryByText('Out of Service')).toBeNull()
  })
})

describe('VehicleCard — open repair count badge', () => {
  it('shows open count badge when there are open/in-progress repairs', () => {
    asJamie()
    useApi.mockReturnValue({ data: OPEN_REPAIRS, isLoading: false, error: null, refetch: vi.fn() })
    render(<VehicleCard vehicle={ACTIVE_VEHICLE} onVehicleUpdated={vi.fn()} />)
    expect(screen.getByText('2 open')).toBeTruthy()
  })

  it('does not show badge when no open repairs', () => {
    asJamie()
    useApi.mockReturnValue({ data: [], isLoading: false, error: null, refetch: vi.fn() })
    render(<VehicleCard vehicle={ACTIVE_VEHICLE} onVehicleUpdated={vi.fn()} />)
    expect(screen.queryByText(/open/)).toBeNull()
  })
})

describe('VehicleCard — RTS/OOS toggle role-gating', () => {
  it('Supervisor sees Mark Out of Service for active vehicle (expanded)', async () => {
    asEarl()
    useApi.mockReturnValue({ data: [], isLoading: false, error: null, refetch: vi.fn() })
    const user = userEvent.setup()
    render(<VehicleCard vehicle={ACTIVE_VEHICLE} onVehicleUpdated={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /^712/i }))
    expect(screen.getByRole('button', { name: /mark out of service/i })).toBeTruthy()
  })

  it('Responder does NOT see Mark Out of Service (expanded)', async () => {
    asJamie()
    useApi.mockReturnValue({ data: [], isLoading: false, error: null, refetch: vi.fn() })
    const user = userEvent.setup()
    render(<VehicleCard vehicle={ACTIVE_VEHICLE} onVehicleUpdated={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /^712/i }))
    expect(screen.queryByRole('button', { name: /mark out of service/i })).toBeNull()
  })

  it('Supervisor sees Return to Service for OOS vehicle (expanded)', async () => {
    asEarl()
    useApi.mockReturnValue({ data: [], isLoading: false, error: null, refetch: vi.fn() })
    const user = userEvent.setup()
    render(<VehicleCard vehicle={OOS_VEHICLE} onVehicleUpdated={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /^712/i }))
    expect(screen.getByRole('button', { name: /return to service/i })).toBeTruthy()
  })

  it('Responder does NOT see Return to Service (expanded)', async () => {
    asJamie()
    useApi.mockReturnValue({ data: [], isLoading: false, error: null, refetch: vi.fn() })
    const user = userEvent.setup()
    render(<VehicleCard vehicle={OOS_VEHICLE} onVehicleUpdated={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /^712/i }))
    expect(screen.queryByRole('button', { name: /return to service/i })).toBeNull()
  })
})

describe('VehicleCard — Report an Issue (all roles)', () => {
  it('Report an Issue button is visible to Responder after expansion', async () => {
    asJamie()
    useApi.mockReturnValue({ data: [], isLoading: false, error: null, refetch: vi.fn() })
    const user = userEvent.setup()
    render(<VehicleCard vehicle={ACTIVE_VEHICLE} onVehicleUpdated={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /^712/i }))
    expect(screen.getByRole('button', { name: /report an issue/i })).toBeTruthy()
  })
})
