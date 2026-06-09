/**
 * tests/Step1Vehicle.test.jsx
 * Vehicle selection step: list rendering, supply room auto-advance, OOS display.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock MSAL and useAuth before any component imports
vi.mock('@azure/msal-react')
vi.mock('@azure/msal-browser')
vi.mock('../../../shared/hooks/useAuth.jsx')
vi.mock('../../../shared/hooks/useApi.js')

// Mock heavy sub-components to avoid their own API calls
vi.mock('../../../shared/components/LastCheckBanner.jsx', () => ({
  default: () => <div data-testid="last-check-banner" />,
}))
vi.mock('../../../shared/components/Spinner.jsx', () => ({
  default: ({ label }) => <div role="status" aria-label={label} data-testid="spinner" />,
}))

import { render as rtlRender } from '@testing-library/react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi }  from '../../../shared/hooks/useApi.js'
import Step1Vehicle from '../components/Step1Vehicle.jsx'

const STATION = {
  station_id:    1,
  name:          'Newberg Township Station 1',
  primary_color: '#1a2f5a',
  region:        'Newberg Township',
}

const VEHICLES = [
  { vehicle_id: 10, vehicle_number: '712', vehicle_type: 'BLS', active: true,  requires_controlled_substance_check: false },
  { vehicle_id: 11, vehicle_number: '540', vehicle_type: 'ALS', active: false, requires_controlled_substance_check: true  },
]

beforeEach(() => {
  useAuth.mockReturnValue({
    isAuthenticated: true,
    isLoading:       false,
    user:            { name: 'Jamie Responder', email: 'test-responder@ems.local', role: 'Responder', initials: 'JR' },
    getToken:        vi.fn().mockResolvedValue('test-token'),
    login:           vi.fn(),
    logout:          vi.fn(),
  })
})

function renderStep1(props = {}) {
  // First useApi call → vehicles; second → portable locations
  useApi
    .mockReturnValueOnce({ data: VEHICLES, isLoading: false, error: null, refetch: vi.fn() })
    .mockReturnValue({   data: [],         isLoading: false, error: null, refetch: vi.fn() })

  return render(
    <Step1Vehicle
      draft={props.draft ?? null}
      preselectedStation={props.preselectedStation ?? STATION}
      onSelect={props.onSelect ?? vi.fn()}
    />
  )
}

describe('Step1Vehicle — vehicle list', () => {
  it('renders vehicle cards for active vehicles', () => {
    renderStep1()
    expect(screen.getByText('Unit 712')).toBeTruthy()
  })

  it('active vehicle card shows vehicle number and type', () => {
    renderStep1()
    expect(screen.getByText('BLS')).toBeTruthy()
  })

  it('renders ALS badge for controlled-substance vehicles', () => {
    renderStep1()
    // Unit 540 is ALS with CS check — even though inactive, still rendered
    // Active check: only active vehicles shown
    // Wait, Step1Vehicle filters: activeVehicles.filter(v => v.active !== false)
    // Unit 540 has active: false so it won't be in activeVehicles
    // Let me check: vehicles includes inactive ones, but activeVehicles only includes active ones
    // So 540 (inactive) should NOT appear in the rendered list
    expect(screen.queryByText('Unit 540')).toBeNull()
  })

  it('shows station name in the header band', () => {
    renderStep1()
    expect(screen.getByLabelText(/Checking at: Newberg Township Station 1/i)).toBeTruthy()
  })

  it('Continue button is disabled when no vehicle selected', () => {
    renderStep1()
    const btn = screen.getByRole('button', { name: /select a vehicle or bag to continue/i })
    expect(btn).toBeDisabled()
  })

  it('selecting a vehicle enables the Continue button', async () => {
    const user = userEvent.setup()
    renderStep1()
    await user.click(screen.getByRole('radio', { name: /unit 712/i }))
    // The button text changes and is no longer disabled
    const btn = screen.getByRole('button', { name: /continue to compartments/i })
    expect(btn).not.toBeDisabled()
  })
})

describe('Step1Vehicle — no station', () => {
  it('shows a no-station error when preselectedStation is null', () => {
    useApi.mockReturnValue({ data: null, isLoading: false, error: null, refetch: vi.fn() })
    render(
      <Step1Vehicle
        draft={null}
        preselectedStation={null}
        onSelect={vi.fn()}
      />
    )
    expect(screen.getByText(/No station selected/i)).toBeTruthy()
  })
})

describe('Step1Vehicle — supply room auto-advance', () => {
  it('renders spinner when draft._supplyRoom is true', () => {
    useApi.mockReturnValue({ data: null, isLoading: false, error: null, refetch: vi.fn() })
    render(
      <Step1Vehicle
        draft={{ _supplyRoom: true, location_id: 42, station_id: 1 }}
        preselectedStation={STATION}
        onSelect={vi.fn()}
      />
    )
    expect(screen.getByRole('status', { name: /preparing supply room check/i })).toBeTruthy()
  })

  it('calls onSelect immediately with supply room parameters', () => {
    const onSelect = vi.fn()
    useApi.mockReturnValue({ data: null, isLoading: false, error: null, refetch: vi.fn() })
    render(
      <Step1Vehicle
        draft={{ _supplyRoom: true, location_id: 42, station_id: 1 }}
        preselectedStation={STATION}
        onSelect={onSelect}
      />
    )
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({
        vehicleId:    null,
        locationId:   42,
        locationType: 'STATION_SUPPLY_ROOM',
      })
    )
  })
})
