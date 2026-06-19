/**
 * tests/VehiclesScreen.test.jsx
 * BUG-AD1 (Session AD): retired vehicles were leaking into this screen.
 *
 * Jennifer found in UAT: after retiring "TEST UAT" from Settings, it still
 * appeared in Admin -> Vehicles with the "Show out-of-service vehicles"
 * checkbox unchecked, and offered a working "Return to Service" action.
 *
 * Root cause: the screen's display filter only checked `v.active`, but
 * retired vehicles are a permanently separate state from temporary
 * out-of-service (`active=false`, `retired_at=null`). This file locks in
 * the fix: retired vehicles are excluded from this screen outright,
 * regardless of the "Show out-of-service vehicles" toggle.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('@azure/msal-react')
vi.mock('@azure/msal-browser')
vi.mock('../../../shared/hooks/useAuth.jsx')
vi.mock('../../../shared/hooks/useApi.js')

vi.mock('../../vehicles/api/vehicleApi.js', () => ({
  vehicleApi: { getStationVehicles: vi.fn() },
}))

import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi }  from '../../../shared/hooks/useApi.js'
import VehiclesScreen from '../components/VehiclesScreen.jsx'

const STATION = { station_id: 1, name: 'Newberg Township Station' }

const ACTIVE_VEHICLE = {
  vehicle_id: 1, vehicle_number: '712', vehicle_type: 'BLS',
  active: true, retired_at: null,
}

const OOS_VEHICLE = {
  vehicle_id: 2, vehicle_number: '540', vehicle_type: 'ALS',
  active: false, retired_at: null, inactive_reason: 'Scheduled maintenance',
}

const RETIRED_VEHICLE = {
  vehicle_id: 3, vehicle_number: 'TEST UAT', vehicle_type: 'BLS',
  active: false, retired_at: '2026-06-11T00:00:00Z',
  retired_by: 'jinniyah@gmail.com', retirement_reason: 'UAT Testing',
}

function asJennifer() {
  useAuth.mockReturnValue({
    isAuthenticated: true, isLoading: false,
    user: { name: 'Jennifer', email: 'test-administrator@ems.local', role: 'Administrator', initials: 'JA' },
    getToken: vi.fn().mockResolvedValue('test-token'),
    login: vi.fn(), logout: vi.fn(),
  })
}

describe('VehiclesScreen — retired vehicles excluded (BUG-AD1)', () => {
  beforeEach(() => {
    asJennifer()
  })

  it('does not show a retired vehicle by default', () => {
    useApi.mockReturnValue({
      data: [ACTIVE_VEHICLE, RETIRED_VEHICLE],
      isLoading: false, error: null, refetch: vi.fn(),
    })
    render(<VehiclesScreen station={STATION} onBack={vi.fn()} />)
    expect(screen.getByText('712')).toBeTruthy()
    expect(screen.queryByText('TEST UAT')).toBeNull()
  })

  it('still does not show a retired vehicle when "Show out-of-service vehicles" is checked', async () => {
    useApi.mockReturnValue({
      data: [ACTIVE_VEHICLE, OOS_VEHICLE, RETIRED_VEHICLE],
      isLoading: false, error: null, refetch: vi.fn(),
    })
    const user = userEvent.setup()
    render(<VehiclesScreen station={STATION} onBack={vi.fn()} />)

    // Genuinely out-of-service vehicle is hidden before toggling...
    expect(screen.queryByText('540')).toBeNull()
    expect(screen.queryByText('TEST UAT')).toBeNull()

    await user.click(screen.getByLabelText(/show out-of-service vehicles/i))

    // ...and appears after toggling, but the retired vehicle still does not.
    expect(screen.getByText('540')).toBeTruthy()
    expect(screen.queryByText('TEST UAT')).toBeNull()
  })

  it('shows only the active vehicle count, excluding retired, in the empty-state message', () => {
    useApi.mockReturnValue({
      data: [RETIRED_VEHICLE],
      isLoading: false, error: null, refetch: vi.fn(),
    })
    render(<VehiclesScreen station={STATION} onBack={vi.fn()} />)
    expect(screen.getByText(/no active vehicles/i)).toBeTruthy()
  })
})
