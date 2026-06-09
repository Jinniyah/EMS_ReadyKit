/**
 * tests/ItemCatalog.test.jsx
 * Item catalog: list renders, search filters, add button role-gating.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('@azure/msal-react')
vi.mock('@azure/msal-browser')
vi.mock('../../../shared/hooks/useAuth.jsx')
vi.mock('../../../shared/hooks/useApi.js')

// Stub subcomponents that make their own API calls or are too complex to render
vi.mock('../components/ItemForm.jsx', () => ({
  default: ({ onCancel }) => (
    <div data-testid="item-form">
      <button onClick={onCancel} type="button">Cancel</button>
    </div>
  ),
}))
vi.mock('../components/ItemAssignments.jsx', () => ({
  default: () => <div data-testid="item-assignments" />,
}))
vi.mock('../components/CsvImport.jsx', () => ({
  default: () => <div data-testid="csv-import" />,
}))
vi.mock('../../../shared/components/ErrorBoundary.jsx', () => ({
  default: ({ children }) => <>{children}</>,
}))

import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi }  from '../../../shared/hooks/useApi.js'
import ItemCatalog from '../components/ItemCatalog.jsx'

const ITEMS = [
  {
    item_id:       1,
    name:          'Bandage',
    category:      'Consumable',
    check_type:    'SUPPLY',
    unit_of_measure: 'ea',
    active:        true,
    controlled_substance: false,
    assignment_count: 0,
  },
  {
    item_id:       2,
    name:          'AED Battery',
    category:      'Equipment',
    check_type:    'FUNCTIONAL',
    unit_of_measure: 'ea',
    active:        true,
    controlled_substance: false,
    assignment_count: 0,
  },
  {
    item_id:       3,
    name:          'Morphine',
    category:      'Medication',
    check_type:    'SUPPLY',
    unit_of_measure: 'mg',
    active:        true,
    controlled_substance: true,
    assignment_count: 0,
  },
]

function setupApiMocks() {
  // First call → vehicles (empty); second call → items
  useApi
    .mockReturnValueOnce({ data: [],   isLoading: false, error: null, refetch: vi.fn() })
    .mockReturnValue(   { data: ITEMS, isLoading: false, error: null, refetch: vi.fn() })
}

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

function asJennifer() {
  useAuth.mockReturnValue({
    isAuthenticated: true, isLoading: false,
    user: { name: 'Jennifer', email: 'test-admin@ems.local', role: 'Administrator', initials: 'JA' },
    getToken: vi.fn().mockResolvedValue('test-token'),
    login: vi.fn(), logout: vi.fn(),
  })
}

describe('ItemCatalog — item list renders', () => {
  beforeEach(() => { asEarl(); setupApiMocks() })

  it('renders item names from the API', () => {
    render(<ItemCatalog stationId={1} />)
    expect(screen.getByText('Bandage')).toBeTruthy()
    expect(screen.getByText('AED Battery')).toBeTruthy()
  })

  it('shows item count in the title', () => {
    render(<ItemCatalog stationId={1} />)
    expect(screen.getByText(/\(3\)/)).toBeTruthy()
  })

  it('shows category group headings', () => {
    render(<ItemCatalog stationId={1} />)
    // Use heading role to distinguish the h3 from category filter chips and item badges
    expect(screen.getByRole('heading', { level: 3, name: 'Consumable' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 3, name: 'Equipment' })).toBeTruthy()
  })
})

describe('ItemCatalog — search filters results', () => {
  beforeEach(() => { asEarl(); setupApiMocks() })

  it('typing in search hides non-matching items', async () => {
    const user = userEvent.setup()
    render(<ItemCatalog stationId={1} />)
    await user.type(screen.getByRole('searchbox', { name: /search items/i }), 'AED')
    expect(screen.getByText('AED Battery')).toBeTruthy()
    expect(screen.queryByText('Bandage')).toBeNull()
  })

  it('clearing the search restores all items', async () => {
    const user = userEvent.setup()
    render(<ItemCatalog stationId={1} />)
    const searchInput = screen.getByRole('searchbox', { name: /search items/i })
    await user.type(searchInput, 'AED')
    await user.clear(searchInput)
    expect(screen.getByText('Bandage')).toBeTruthy()
  })

  it('shows empty message when no items match', async () => {
    const user = userEvent.setup()
    render(<ItemCatalog stationId={1} />)
    await user.type(screen.getByRole('searchbox', { name: /search items/i }), 'zzznomatch')
    expect(screen.getByText(/no items match/i)).toBeTruthy()
  })
})

describe('ItemCatalog — Add item button role-gating', () => {
  it('Supervisor sees Add item button', () => {
    asEarl(); setupApiMocks()
    render(<ItemCatalog stationId={1} />)
    expect(screen.getByRole('button', { name: /\+ add item/i })).toBeTruthy()
  })

  it('Administrator sees Add item button', () => {
    asJennifer(); setupApiMocks()
    render(<ItemCatalog stationId={1} />)
    expect(screen.getByRole('button', { name: /\+ add item/i })).toBeTruthy()
  })

  it('Responder does NOT see Add item button', () => {
    asJamie(); setupApiMocks()
    render(<ItemCatalog stationId={1} />)
    expect(screen.queryByRole('button', { name: /\+ add item/i })).toBeNull()
  })
})

describe('ItemCatalog — Admin-only Show inactive toggle', () => {
  it('Administrator sees Show inactive items toggle', () => {
    asJennifer(); setupApiMocks()
    render(<ItemCatalog stationId={1} />)
    expect(screen.getByLabelText(/show inactive items/i)).toBeTruthy()
  })

  it('Supervisor does NOT see Show inactive items toggle', () => {
    asEarl(); setupApiMocks()
    render(<ItemCatalog stationId={1} />)
    expect(screen.queryByLabelText(/show inactive items/i)).toBeNull()
  })
})
