/**
 * tests/UsageLogScreen.test.jsx -- FE-TEST-12
 * Full flow: unit picker (vehicles + portable locations), single-unit skip,
 * item step, Done payload, Nothing used, error.
 *
 * USAGE-B1/B2: payload now carries vehicle_id OR location_id, never both.
 * Picker prompt changed from "which vehicle" to "which unit".
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('@azure/msal-react')
vi.mock('@azure/msal-browser')
vi.mock('../../../shared/hooks/useAuth.jsx')
vi.mock('../../vehicles/api/vehicleApi.js')
vi.mock('../../check-wizard/api/checkApi.js')
vi.mock('../../supply-room/api/supplyApi.js')
vi.mock('../api/usageApi.js')

import { useAuth }    from '../../../shared/hooks/useAuth.jsx'
import { vehicleApi } from '../../vehicles/api/vehicleApi.js'
import { checkApi }   from '../../check-wizard/api/checkApi.js'
import { supplyApi }  from '../../supply-room/api/supplyApi.js'
import { usageApi }   from '../api/usageApi.js'
import UsageLogScreen from '../index.jsx'

const STATION = { station_id: 1, name: 'Test Station' }

const VEHICLE_712 = { vehicle_id: 10, vehicle_number: '712', status: 'ACTIVE' }
const VEHICLE_540 = { vehicle_id: 11, vehicle_number: '540', status: 'ACTIVE' }
const JUMP_BAG    = { location_id: 20, label: 'Jump Bag', location_type: 'JUMP_BAG', retired_at: null }

const CATALOG = [
  { item_id: 1, item_name: 'Gloves Medium', check_type: 'SUPPLY' },
  { item_id: 2, item_name: 'Gauze 4x4',    check_type: 'SUPPLY' },
]

function setupMocks({ vehicles = [VEHICLE_712, VEHICLE_540], locations = [] } = {}) {
  useAuth.mockReturnValue({
    isAuthenticated: true,
    isLoading:       false,
    user:            { name: 'Jamie', role: 'Responder' },
    getToken:        vi.fn().mockResolvedValue('test-token'),
    login:           vi.fn(),
    logout:          vi.fn(),
  })
  vehicleApi.getStationVehicles     = vi.fn().mockResolvedValue(vehicles)
  checkApi.getStationLocations      = vi.fn().mockResolvedValue(locations)
  supplyApi.getCatalog              = vi.fn().mockResolvedValue(CATALOG)
  usageApi.getFrequentItems         = vi.fn().mockResolvedValue([])
  usageApi.logUsage                 = vi.fn().mockResolvedValue({})
}

// ---------------------------------------------------------------------------
// Unit picker
// ---------------------------------------------------------------------------

describe('UsageLogScreen -- unit picker', () => {
  it('shows unit picker prompt for multi-vehicle stations', async () => {
    setupMocks({ vehicles: [VEHICLE_712, VEHICLE_540] })
    render(<UsageLogScreen station={STATION} onBack={vi.fn()} />)
    await waitFor(() => expect(screen.getByText(/which unit/i)).toBeTruthy())
    expect(screen.getByText('712')).toBeTruthy()
    expect(screen.getByText('540')).toBeTruthy()
  })

  it('shows portable locations alongside vehicles in picker', async () => {
    setupMocks({ vehicles: [VEHICLE_712], locations: [JUMP_BAG] })
    render(<UsageLogScreen station={STATION} onBack={vi.fn()} />)
    await waitFor(() => expect(screen.getByText(/which unit/i)).toBeTruthy())
    expect(screen.getByText('712')).toBeTruthy()
    expect(screen.getByText('Jump Bag')).toBeTruthy()
  })

  it('auto-skips unit picker when there is exactly one unit total', async () => {
    setupMocks({ vehicles: [VEHICLE_712], locations: [] })
    render(<UsageLogScreen station={STATION} onBack={vi.fn()} />)
    await waitFor(() => expect(screen.queryByText(/which unit/i)).toBeNull())
    expect(screen.getByText('Gloves Medium')).toBeTruthy()
  })

  it('auto-skips unit picker for single portable location with no vehicles', async () => {
    setupMocks({ vehicles: [], locations: [JUMP_BAG] })
    render(<UsageLogScreen station={STATION} onBack={vi.fn()} />)
    await waitFor(() => expect(screen.queryByText(/which unit/i)).toBeNull())
    expect(screen.getByText('Gloves Medium')).toBeTruthy()
  })
})

// ---------------------------------------------------------------------------
// Item step
// ---------------------------------------------------------------------------

describe('UsageLogScreen -- item step', () => {
  it('renders catalog items in the picker', async () => {
    setupMocks({ vehicles: [VEHICLE_712] })
    render(<UsageLogScreen station={STATION} onBack={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('Gloves Medium')).toBeTruthy())
    expect(screen.getByText('Gauze 4x4')).toBeTruthy()
  })
})

// ---------------------------------------------------------------------------
// Done -- payload correctness (USAGE-B1/B2)
// ---------------------------------------------------------------------------

describe('UsageLogScreen -- Done submits correct payload', () => {
  it('sends vehicle_id (not location_id) when a vehicle is selected', async () => {
    setupMocks({ vehicles: [VEHICLE_712] })
    const user = userEvent.setup()
    render(<UsageLogScreen station={STATION} onBack={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('Gloves Medium')).toBeTruthy())

    await user.click(screen.getByRole('button', { name: /add one gloves medium/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /done/i }).disabled).toBe(false)
    )
    await user.click(screen.getByRole('button', { name: /done/i }))

    await waitFor(() => expect(screen.getByText(/logged/i)).toBeTruthy())
    expect(usageApi.logUsage).toHaveBeenCalledWith(
      expect.objectContaining({
        station_id:  STATION.station_id,
        vehicle_id:  VEHICLE_712.vehicle_id,
        location_id: null,
        items: [{ item_id: 1, quantity_used: 1 }],
      }),
      expect.any(Function)
    )
  })

  it('sends location_id (not vehicle_id) when a portable location is selected', async () => {
    setupMocks({ vehicles: [], locations: [JUMP_BAG] })
    const user = userEvent.setup()
    render(<UsageLogScreen station={STATION} onBack={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('Gloves Medium')).toBeTruthy())

    await user.click(screen.getByRole('button', { name: /add one gloves medium/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /done/i }).disabled).toBe(false)
    )
    await user.click(screen.getByRole('button', { name: /done/i }))

    await waitFor(() => expect(screen.getByText(/logged/i)).toBeTruthy())
    expect(usageApi.logUsage).toHaveBeenCalledWith(
      expect.objectContaining({
        station_id:  STATION.station_id,
        vehicle_id:  null,
        location_id: JUMP_BAG.location_id,
        items: [{ item_id: 1, quantity_used: 1 }],
      }),
      expect.any(Function)
    )
  })
})

// ---------------------------------------------------------------------------
// Nothing used
// ---------------------------------------------------------------------------

describe('UsageLogScreen -- Nothing used', () => {
  it('"Nothing used" calls onBack without submitting', async () => {
    setupMocks({ vehicles: [VEHICLE_712] })
    const onBack = vi.fn()
    const user   = userEvent.setup()
    render(<UsageLogScreen station={STATION} onBack={onBack} />)
    await waitFor(() => expect(screen.getByText('Gloves Medium')).toBeTruthy())

    await user.click(screen.getByRole('button', { name: /nothing used/i }))
    expect(onBack).toHaveBeenCalled()
    expect(usageApi.logUsage).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// Submit error
// ---------------------------------------------------------------------------

describe('UsageLogScreen -- submit error', () => {
  it('shows error alert when logUsage rejects', async () => {
    setupMocks({ vehicles: [VEHICLE_712] })
    usageApi.logUsage = vi.fn().mockRejectedValue({ message: 'Network error' })
    const user = userEvent.setup()
    render(<UsageLogScreen station={STATION} onBack={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('Gloves Medium')).toBeTruthy())

    await user.click(screen.getByRole('button', { name: /add one gloves medium/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /done/i }).disabled).toBe(false)
    )
    await user.click(screen.getByRole('button', { name: /done/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
  })
})
