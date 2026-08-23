/**
 * tests/ExportPanel.test.jsx
 * F-5G3a: compliance CSV export filter panel.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('../../../shared/hooks/useAuth.jsx')
vi.mock('../api/checkHistoryApi.js', () => ({
  checkHistoryApi: {
    getStationVehicles: vi.fn(),
    getStationLocations: vi.fn(),
    getSupplyRoom: vi.fn(),
    exportChecks: vi.fn(),
  },
}))

import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { checkHistoryApi } from '../api/checkHistoryApi.js'
import ExportPanel from '../components/ExportPanel.jsx'

const STATION = { station_id: 1, name: 'Test Station' }

const VEHICLES = [
  { vehicle_id: 10, vehicle_number: '712', active: true, retired_at: null },
]
const LOCATIONS = [
  { location_id: 20, label: 'Jump Bag A', location_type: 'JUMP_BAG' },
]
const SUPPLY_ROOM = { location_id: 30, retired_at: null }

function setup() {
  useAuth.mockReturnValue({
    isAuthenticated: true, isLoading: false,
    user: { name: 'Earl', email: 'test-supervisor@ems.local', role: 'Supervisor', initials: 'ES' },
    getToken: vi.fn().mockResolvedValue('test-token'),
    login: vi.fn(), logout: vi.fn(),
  })
  checkHistoryApi.getStationVehicles.mockResolvedValue(VEHICLES)
  checkHistoryApi.getStationLocations.mockResolvedValue(LOCATIONS)
  checkHistoryApi.getSupplyRoom.mockResolvedValue(SUPPLY_ROOM)
}

async function openPanel(user) {
  render(<ExportPanel station={STATION} />)
  await user.click(screen.getByRole('button', { name: /export for compliance/i }))
}

beforeEach(() => {
  vi.clearAllMocks()
  setup()
  global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
  global.URL.revokeObjectURL = vi.fn()
})

describe('ExportPanel', () => {
  it('is collapsed by default', () => {
    render(<ExportPanel station={STATION} />)
    expect(screen.queryByText(/what to include/i)).toBeNull()
  })

  it('whole station is checked by default and hides individual pickers', async () => {
    const user = userEvent.setup()
    await openPanel(user)
    expect(screen.getByLabelText(/whole station/i).checked).toBe(true)
    expect(screen.queryByText(/vehicles/i)).toBeNull()
  })

  it('unchecking whole station reveals individual vehicle/jump bag/supply room pickers', async () => {
    const user = userEvent.setup()
    await openPanel(user)
    await user.click(screen.getByLabelText(/whole station/i))
    await waitFor(() => expect(screen.getByText(/unit 712/i)).toBeTruthy())
    expect(screen.getByText(/jump bag a/i)).toBeTruthy()
    expect(screen.getByText(/station supply room/i)).toBeTruthy()
  })

  it('download buttons are disabled with nothing selected and whole station off', async () => {
    const user = userEvent.setup()
    await openPanel(user)
    await user.click(screen.getByLabelText(/whole station/i))
    await waitFor(() => expect(screen.getByText(/unit 712/i)).toBeTruthy())
    expect(screen.getByRole('button', { name: /download simplified/i }).disabled).toBe(true)
    expect(screen.getByRole('button', { name: /download detailed/i }).disabled).toBe(true)
    expect(screen.getByText(/pick at least one vehicle/i)).toBeTruthy()
  })

  it('download buttons are disabled when the date range exceeds 400 days', async () => {
    const user = userEvent.setup()
    await openPanel(user)
    const fromInput = screen.getByLabelText(/^from$/i)
    const toInput = screen.getByLabelText(/^to$/i)
    await user.clear(fromInput)
    await user.type(fromInput, '2024-01-01')
    await user.clear(toInput)
    await user.type(toInput, '2026-06-01')
    expect(screen.getByRole('button', { name: /download simplified/i }).disabled).toBe(true)
    expect(screen.getByText(/400 days or less/i)).toBeTruthy()
  })

  it('successful download triggers the blob-anchor pattern with the resolved filename', async () => {
    const user = userEvent.setup()
    checkHistoryApi.exportChecks.mockResolvedValue({
      blob: new Blob(['Check Date,Performed By\n'], { type: 'text/csv' }),
      filename: 'test-station_compliance_simplified_2026-06-01_to_2026-06-30.csv',
    })
    const clickSpy = vi.fn()
    const originalCreateElement = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation(tag => {
      const el = originalCreateElement(tag)
      if (tag === 'a') el.click = clickSpy
      return el
    })

    await openPanel(user)
    await user.click(screen.getByRole('button', { name: /download simplified/i }))

    await waitFor(() => expect(checkHistoryApi.exportChecks).toHaveBeenCalled())
    expect(checkHistoryApi.exportChecks.mock.calls[0][2]).toMatchObject({ wholeStation: true, format: 'simplified' })
    await waitFor(() => expect(clickSpy).toHaveBeenCalled())
  })

  it('surfaces the server error message when export fails', async () => {
    const user = userEvent.setup()
    checkHistoryApi.exportChecks.mockRejectedValue(new Error('Date range may not exceed 400 days.'))

    await openPanel(user)
    await user.click(screen.getByRole('button', { name: /download simplified/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
    expect(screen.getByRole('alert').textContent).toMatch(/date range may not exceed 400 days/i)
  })
})
