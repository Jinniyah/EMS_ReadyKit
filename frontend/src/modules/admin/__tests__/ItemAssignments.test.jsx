/**
 * tests/ItemAssignments.test.jsx — ITM-8
 *
 * Covers the "Where" picker paths (vehicle / jump bag / supply room),
 * auto-select for supply room, correct payload shapes, assignment display
 * (location_label for non-vehicle), and the post-assign confirmation flow
 * introduced by ITM-7.
 *
 * Mock strategy for useApi:
 *   ItemAssignments' assignments list:  deps = [boolean, number, number]
 *   AddAssignmentForm's compartments:   deps = [string,  string, string]
 * We distinguish them by typeof deps[0] to avoid fragile call-count sequencing.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('@azure/msal-react')
vi.mock('@azure/msal-browser')
vi.mock('../../../shared/hooks/useAuth.jsx')
vi.mock('../../../shared/hooks/useApi.js')
vi.mock('../api/adminApi.js')

import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi }  from '../../../shared/hooks/useApi.js'
import { adminApi } from '../api/adminApi.js'
import ItemAssignments from '../components/ItemAssignments.jsx'

// ── Fixtures ─────────────────────────────────────────────────────────────────

const ITEM = { item_id: 1, name: 'Gauze 3x3' }

const VEHICLE = {
  vehicle_id: 10, vehicle_number: '712', vehicle_type: 'BLS',
  active: true, retired_at: null,
}

const JUMP_BAG = {
  location_id: 20, label: 'Jump Bag A',
  location_type: 'JUMP_BAG', retired_at: null,
}

const SUPPLY_ROOM = {
  location_id: 30, label: 'Station Supply Room',
  location_type: 'STATION_SUPPLY_ROOM', retired_at: null,
}

const COMPARTMENTS = [
  { compartment_id: 100, name: 'PC 8' },
  { compartment_id: 101, name: 'Airway Box' },
]

const VEHICLE_ASSIGNMENT = {
  par_id: 200,
  vehicle_id: 10,
  vehicle_number: '712',
  location_id: null,
  location_label: null,
  compartment_id: 100,
  compartment_name: 'PC 8',
  min_quantity: 1,
  max_quantity: 4,
}

const JUMP_BAG_ASSIGNMENT = {
  par_id: 201,
  vehicle_id: null,
  vehicle_number: null,
  location_id: 20,
  location_label: 'Jump Bag A',
  compartment_id: 101,
  compartment_name: 'Front Pocket',
  min_quantity: 2,
  max_quantity: 6,
}

// ── useApi mock helpers ───────────────────────────────────────────────────────

// deps[0] is boolean (expanded) for the assignments list call.
// deps[0] is string (locType) for the AddAssignmentForm compartments call.
function mockApiFor({ assignments = [], compartments = COMPARTMENTS } = {}) {
  useApi.mockImplementation((_fn, deps) => {
    if (Array.isArray(deps) && typeof deps[0] === 'string') {
      return { data: compartments, isLoading: false, error: null }
    }
    return { data: assignments, isLoading: false, error: null }
  })
}

function setupAuth() {
  useAuth.mockReturnValue({
    isAuthenticated: true,
    isLoading: false,
    user: { name: 'Earl', email: 'test-supervisor@ems.local', role: 'Supervisor', initials: 'ES' },
    getToken: vi.fn().mockResolvedValue('test-token'),
    login: vi.fn(),
    logout: vi.fn(),
  })
}

beforeEach(() => {
  setupAuth()
  adminApi.assignItem        = vi.fn().mockResolvedValue({})
  adminApi.deactivateParLevel = vi.fn().mockResolvedValue({})
  adminApi.updateParLevel    = vi.fn().mockResolvedValue({})
})

// Helper: render expanded with the add form open
async function renderAndOpenAddForm(props = {}) {
  const user = userEvent.setup()
  render(
    <ItemAssignments
      item={ITEM}
      stationId={1}
      vehicles={[VEHICLE]}
      locations={[JUMP_BAG, SUPPLY_ROOM]}
      {...props}
    />
  )
  await user.click(screen.getByRole('button', { name: /gauze 3x3/i }))
  await user.click(screen.getByRole('button', { name: /\+ add assignment/i }))
  return user
}

// ── Assignment display row ────────────────────────────────────────────────────

describe('ItemAssignments — assignment display row', () => {
  it('shows vehicle number for vehicle assignments', async () => {
    mockApiFor({ assignments: [VEHICLE_ASSIGNMENT] })
    const user = userEvent.setup()
    render(<ItemAssignments item={ITEM} stationId={1} vehicles={[VEHICLE]} locations={[]} />)
    await user.click(screen.getByRole('button', { name: /gauze 3x3/i }))
    expect(screen.getByText('712')).toBeTruthy()
    expect(screen.getByText('PC 8')).toBeTruthy()
  })

  it('shows location_label for non-vehicle assignments', async () => {
    mockApiFor({ assignments: [JUMP_BAG_ASSIGNMENT] })
    const user = userEvent.setup()
    render(<ItemAssignments item={ITEM} stationId={1} vehicles={[]} locations={[JUMP_BAG]} />)
    await user.click(screen.getByRole('button', { name: /gauze 3x3/i }))
    expect(screen.getByText('Jump Bag A')).toBeTruthy()
    expect(screen.getByText('Front Pocket')).toBeTruthy()
  })
})

// ── Vehicle path ──────────────────────────────────────────────────────────────

describe('ItemAssignments — vehicle assignment', () => {
  it('submits vehicle_id and compartment_id in payload', async () => {
    mockApiFor()
    const user = await renderAndOpenAddForm()

    // Where defaults to "Vehicle" — select the vehicle
    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[1], '712 (BLS)')

    // Compartment select now visible — select PC 8
    await user.selectOptions(screen.getAllByRole('combobox')[2], 'PC 8')

    await user.click(screen.getByRole('button', { name: /^assign$/i }))

    await waitFor(() =>
      expect(adminApi.assignItem).toHaveBeenCalledWith(
        ITEM.item_id,
        expect.objectContaining({
          vehicle_id:    VEHICLE.vehicle_id,
          compartment_id: 100,
          min_quantity:  1,
          max_quantity:  4,
        }),
        expect.any(Function)
      )
    )
    expect(adminApi.assignItem.mock.calls[0][1]).not.toHaveProperty('location_id')
  })
})

// ── Jump bag path ─────────────────────────────────────────────────────────────

describe('ItemAssignments — jump bag assignment', () => {
  it('submits location_id (not vehicle_id) for a jump bag', async () => {
    mockApiFor()
    const user = await renderAndOpenAddForm()

    // Switch Where to Jump Bag
    await user.selectOptions(screen.getAllByRole('combobox')[0], 'Jump Bag')

    // Jump Bag select appears — pick Jump Bag A
    await user.selectOptions(screen.getAllByRole('combobox')[1], 'Jump Bag A')

    // Compartment select appears
    await user.selectOptions(screen.getAllByRole('combobox')[2], 'PC 8')

    await user.click(screen.getByRole('button', { name: /^assign$/i }))

    await waitFor(() =>
      expect(adminApi.assignItem).toHaveBeenCalledWith(
        ITEM.item_id,
        expect.objectContaining({
          location_id:   JUMP_BAG.location_id,
          compartment_id: 100,
        }),
        expect.any(Function)
      )
    )
    expect(adminApi.assignItem.mock.calls[0][1]).not.toHaveProperty('vehicle_id')
  })
})

// ── Supply room path ──────────────────────────────────────────────────────────

describe('ItemAssignments — supply room assignment', () => {
  it('auto-shows supply room label when supply room type is chosen', async () => {
    mockApiFor()
    const user = await renderAndOpenAddForm()

    await user.selectOptions(screen.getAllByRole('combobox')[0], 'Station Supply Room')

    // The <p class="assignment-location-label"> appears (distinct from the <option> text)
    expect(screen.getByText('Station Supply Room', { selector: 'p' })).toBeTruthy()
  })

  it('submits supply room location_id without vehicle_id', async () => {
    mockApiFor()
    const user = await renderAndOpenAddForm()

    await user.selectOptions(screen.getAllByRole('combobox')[0], 'Station Supply Room')

    // After auto-select, compartment select should be visible (supply room is auto-selected)
    await waitFor(() => expect(screen.getAllByRole('combobox').length).toBeGreaterThanOrEqual(2))
    await user.selectOptions(screen.getAllByRole('combobox')[1], 'PC 8')

    await user.click(screen.getByRole('button', { name: /^assign$/i }))

    await waitFor(() =>
      expect(adminApi.assignItem).toHaveBeenCalledWith(
        ITEM.item_id,
        expect.objectContaining({
          location_id:   SUPPLY_ROOM.location_id,
          compartment_id: 100,
        }),
        expect.any(Function)
      )
    )
    expect(adminApi.assignItem.mock.calls[0][1]).not.toHaveProperty('vehicle_id')
  })
})

// ── Confirmation state after assign (ITM-7) ───────────────────────────────────

describe('ItemAssignments — post-assign confirmation (ITM-7)', () => {
  async function assignVehicleCompartment(user) {
    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[1], '712 (BLS)')
    await user.selectOptions(screen.getAllByRole('combobox')[2], 'PC 8')
    await user.click(screen.getByRole('button', { name: /^assign$/i }))
    await waitFor(() => expect(adminApi.assignItem).toHaveBeenCalled())
  }

  it('shows confirmation with vehicle number and compartment name after assign', async () => {
    mockApiFor()
    const user = await renderAndOpenAddForm()
    await assignVehicleCompartment(user)

    // Confirmation state: Done button appears, Assign button is gone
    await waitFor(() => expect(screen.getByRole('button', { name: /^done$/i })).toBeTruthy())
    expect(screen.queryByRole('button', { name: /^assign$/i })).toBeNull()

    // Confirmation message contains vehicle number and compartment name
    // Use getAllByText to avoid RTL throwing on multiple ancestor-element matches
    const msgs = screen.getAllByText((content) => content.includes('712') && content.includes('PC 8'))
    expect(msgs.length).toBeGreaterThan(0)
  })

  it('"+ Assign to another location" resets form and carries over min/max', async () => {
    mockApiFor()
    const user = await renderAndOpenAddForm()

    // Select vehicle + compartment so quantity inputs become visible
    await user.selectOptions(screen.getAllByRole('combobox')[1], '712 (BLS)')
    await user.selectOptions(screen.getAllByRole('combobox')[2], 'PC 8')

    // Change min/max from defaults (1 / 4)
    const minInput = screen.getByRole('spinbutton', { name: /needs at least/i })
    await user.clear(minInput)
    await user.type(minInput, '3')
    const maxInput = screen.getByRole('spinbutton', { name: /restock to/i })
    await user.clear(maxInput)
    await user.type(maxInput, '8')

    // Submit
    await user.click(screen.getByRole('button', { name: /^assign$/i }))
    await waitFor(() => screen.getByText(/✓ Assigned to/i))

    // Click "+ Assign to another location"
    await user.click(screen.getByRole('button', { name: /\+ assign to another location/i }))

    // Form is reset — re-select vehicle + compartment to reveal qty inputs
    await user.selectOptions(screen.getAllByRole('combobox')[1], '712 (BLS)')
    await user.selectOptions(screen.getAllByRole('combobox')[2], 'PC 8')

    // Min/max should carry over from the previous assignment
    expect(screen.getByRole('spinbutton', { name: /needs at least/i }).value).toBe('3')
    expect(screen.getByRole('spinbutton', { name: /restock to/i }).value).toBe('8')
  })

  it('"Done" button closes the add form', async () => {
    mockApiFor()
    const user = await renderAndOpenAddForm()
    await assignVehicleCompartment(user)
    await waitFor(() => screen.getByRole('button', { name: /^done$/i }))

    await user.click(screen.getByRole('button', { name: /^done$/i }))

    // After Done, add form is gone — the "+ Add assignment" button should return
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /\+ add assignment/i })).toBeTruthy()
    )
    expect(screen.queryByRole('button', { name: /^done$/i })).toBeNull()
  })
})
