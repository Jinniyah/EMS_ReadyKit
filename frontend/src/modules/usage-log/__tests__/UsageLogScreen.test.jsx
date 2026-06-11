/**
 * tests/UsageLogScreen.test.jsx — FE-TEST-12
 * Full flow: vehicle picker, single-vehicle skip, item step, Done payload, Nothing used, error.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('@azure/msal-react')
vi.mock('@azure/msal-browser')
vi.mock('../../../shared/hooks/useAuth.jsx')
vi.mock('../../vehicles/api/vehicleApi.js')
vi.mock('../../supply-room/api/supplyApi.js')
vi.mock('../api/usageApi.js')

import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { vehicleApi } from '../../vehicles/api/vehicleApi.js'
import { supplyApi } from '../../supply-room/api/supplyApi.js'
import { usageApi } from '../api/usageApi.js'
import UsageLogScreen from '../index.jsx'

const STATION = { station_id: 1, name: 'Test Station' }

const VEHICLE_712 = { vehicle_id: 10, vehicle_number: '712', status: 'ACTIVE' }
const VEHICLE_540 = { vehicle_id: 11, vehicle_number: '540', status: 'ACTIVE' }

const CATALOG = [
  { item_id: 1, item_name: 'Gloves Medium', check_type: 'SUPPLY' },
  { item_id: 2, item_name: 'Gauze 4x4',    check_type: 'SUPPLY' },
]

function setupMocks(vehicleList = [VEHICLE_712, VEHICLE_540]) {
  useAuth.mockReturnValue({
    isAuthenticated: true,
    isLoading:       false,
    user:            { name: 'Jamie', role: 'Responder' },
    getToken:        vi.fn().mockResolvedValue('test-token'),
    login:           vi.fn(),
    logout:          vi.fn(),
  })
  vehicleApi.getStationVehicles = vi.fn().mockResolvedValue(vehicleList)
  supplyApi.getCatalog          = vi.fn().mockResolvedValue(CATALOG)
  usageApi.getFrequentItems     = vi.fn().mockResolvedValue([])
  usageApi.logUsage             = vi.fn().mockResolvedValue({})
}

describe('UsageLogScreen — vehicle picker', () => {
  it('shows vehicle picker prompt for multi-vehicle stations', async () => {
    setupMocks([VEHICLE_712, VEHICLE_540])
    render(<UsageLogScreen station={STATION} onBack={vi.fn()} />)
    await waitFor(() => expect(screen.getByText(/which vehicle/i)).toBeTruthy())
    expect(screen.getByText('712')).toBeTruthy()
    expect(screen.getByText('540')).toBeTruthy()
  })

  it('auto-skips vehicle picker for single-vehicle stations', async () => {
    setupMocks([VEHICLE_712])
    render(<UsageLogScreen station={STATION} onBack={vi.fn()} />)
    await waitFor(() => expect(screen.queryByText(/which vehicle/i)).toBeNull())
    expect(screen.getByText('Gloves Medium')).toBeTruthy()
  })
})

describe('UsageLogScreen — item step', () => {
  it('renders catalog items in the picker', async () => {
    setupMocks([VEHICLE_712])
    render(<UsageLogScreen station={STATION} onBack={vi.fn()} />)
    await waitFor(() => expect(screen.getByText('Gloves Medium')).toBeTruthy())
    expect(screen.getByText('Gauze 4x4')).toBeTruthy()
  })
})

describe('UsageLogScreen — Done submits correct payload', () => {
  it('calls logUsage with station_id, vehicle_id, and items on Done', async () => {
    setupMocks([VEHICLE_712])
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
        station_id: STATION.station_id,
        vehicle_id: VEHICLE_712.vehicle_id,
        items: [{ item_id: 1, quantity_used: 1 }],
      }),
      expect.any(Function)
    )
  })
})

describe('UsageLogScreen — Nothing used', () => {
  it('"Nothing used" calls onBack without submitting', async () => {
    setupMocks([VEHICLE_712])
    const onBack = vi.fn()
    const user   = userEvent.setup()
    render(<UsageLogScreen station={STATION} onBack={onBack} />)
    await waitFor(() => expect(screen.getByText('Gloves Medium')).toBeTruthy())

    await user.click(screen.getByRole('button', { name: /nothing used/i }))
    expect(onBack).toHaveBeenCalled()
    expect(usageApi.logUsage).not.toHaveBeenCalled()
  })
})

describe('UsageLogScreen — submit error', () => {
  it('shows error alert when logUsage rejects', async () => {
    setupMocks([VEHICLE_712])
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
