/**
 * tests/UsageItemPicker.test.jsx — FE-TEST-11
 * Item picker: catalog render, search, +/- controls, selected highlight, sections.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import UsageItemPicker from '../components/UsageItemPicker.jsx'

const CATALOG = [
  { item_id: 1, item_name: 'Gloves Medium' },
  { item_id: 2, item_name: 'Gauze Sponges 4x4' },
  { item_id: 3, item_name: 'Bandage Large' },
]

const FREQUENT = [
  { item_id: 1, item_name: 'Gloves Medium', total_used: 10 },
]

function renderPicker(overrides = {}) {
  const onQuantityChange = vi.fn()
  const props = {
    catalogItems: CATALOG,
    frequentItems: [],
    quantities: {},
    onQuantityChange,
    ...overrides,
  }
  const result = render(<UsageItemPicker {...props} />)
  return { ...result, onQuantityChange }
}

describe('UsageItemPicker — catalog rendering', () => {
  it('renders all catalog item names', () => {
    renderPicker()
    expect(screen.getByText('Gloves Medium')).toBeTruthy()
    expect(screen.getByText('Gauze Sponges 4x4')).toBeTruthy()
    expect(screen.getByText('Bandage Large')).toBeTruthy()
  })
})

describe('UsageItemPicker — search', () => {
  it('filters items by item_name when searching', async () => {
    const user = userEvent.setup()
    renderPicker()
    await user.type(screen.getByRole('searchbox', { name: /search items/i }), 'gloves')
    expect(screen.getByText('Gloves Medium')).toBeTruthy()
    expect(screen.queryByText('Gauze Sponges 4x4')).toBeNull()
    expect(screen.queryByText('Bandage Large')).toBeNull()
  })

  it('shows empty state when search has no matches', async () => {
    const user = userEvent.setup()
    renderPicker()
    await user.type(screen.getByRole('searchbox'), 'zzznomatch')
    expect(screen.getByText(/no items match/i)).toBeTruthy()
  })
})

describe('UsageItemPicker — +/- controls', () => {
  it('increment button calls onQuantityChange with qty + 1', async () => {
    const user = userEvent.setup()
    const { onQuantityChange } = renderPicker()
    await user.click(screen.getByRole('button', { name: /add one gloves medium/i }))
    expect(onQuantityChange).toHaveBeenCalledWith(1, 1)
  })

  it('decrement button is disabled when qty = 0', () => {
    renderPicker()
    const buttons = screen.getAllByRole('button', { name: /remove one/i })
    expect(buttons[0].disabled).toBe(true)
  })

  it('decrement button calls onQuantityChange with qty - 1 when qty > 0', async () => {
    const user = userEvent.setup()
    const { onQuantityChange } = renderPicker({ quantities: { 1: 2 } })
    await user.click(screen.getByRole('button', { name: /remove one gloves medium/i }))
    expect(onQuantityChange).toHaveBeenCalledWith(1, 1)
  })
})

describe('UsageItemPicker — selected item highlight', () => {
  it('applies selected class to items with qty > 0', () => {
    const { container } = renderPicker({ quantities: { 1: 3 } })
    expect(container.querySelectorAll('.uip__item--selected').length).toBe(1)
  })

  it('does not apply selected class when qty = 0', () => {
    const { container } = renderPicker({ quantities: { 1: 0 } })
    expect(container.querySelectorAll('.uip__item--selected').length).toBe(0)
  })
})

describe('UsageItemPicker — "Used most often" section', () => {
  it('shows "Used most often" section when frequentItems provided', () => {
    renderPicker({ frequentItems: FREQUENT })
    expect(screen.getByText('Used most often')).toBeTruthy()
  })

  it('does not show history improvement note when history exists', () => {
    renderPicker({ frequentItems: FREQUENT })
    expect(screen.queryByText(/get better over time/i)).toBeNull()
  })
})

describe('UsageItemPicker — "Common items" fallback', () => {
  it('shows "Common items" section when no history', () => {
    renderPicker({ frequentItems: [] })
    expect(screen.getByText('Common items')).toBeTruthy()
  })

  it('shows history improvement note when no frequentItems', () => {
    renderPicker({ frequentItems: [] })
    expect(screen.getByText(/get better over time/i)).toBeTruthy()
  })
})
