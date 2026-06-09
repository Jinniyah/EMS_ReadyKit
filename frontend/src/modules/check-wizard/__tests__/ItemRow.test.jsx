/**
 * tests/ItemRow.test.jsx
 * Per-item row — all five check types, No Change mode, damaged badge.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ItemRow from '../components/ItemRow.jsx'

function makeItem(overrides = {}) {
  return {
    item_id:           1,
    name:              'Test Item',
    check_type:        'SUPPLY',
    unit_of_measure:   'ea',
    controlled_substance: false,
    ...overrides,
  }
}

function makeParLevel(overrides = {}) {
  return { min_quantity: 5, is_damaged: false, ...overrides }
}

describe('ItemRow — SUPPLY check type', () => {
  it('renders counter buttons (+ and −)', () => {
    render(
      <ItemRow
        item={makeItem()}
        parLevel={makeParLevel()}
        lot={null}
        draftItem={null}
        onUpdate={vi.fn()}
        onTouched={vi.fn()}
      />
    )
    expect(screen.getByRole('button', { name: /increase quantity/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /decrease quantity/i })).toBeTruthy()
  })

  it('shows the quantity needed', () => {
    const { container } = render(
      <ItemRow
        item={makeItem()}
        parLevel={makeParLevel({ min_quantity: 8 })}
        lot={null}
        draftItem={null}
        onUpdate={vi.fn()}
        onTouched={vi.fn()}
      />
    )
    // "Need: <strong>8</strong>" — text split across elements; check parent's textContent
    expect(container.querySelector('.item-row__need').textContent).toContain('8')
  })

  it('confirms all-present when "All N present" clicked', async () => {
    const user     = userEvent.setup()
    const onUpdate = vi.fn()
    render(
      <ItemRow
        item={makeItem()}
        parLevel={makeParLevel({ min_quantity: 4 })}
        lot={null}
        draftItem={null}
        onUpdate={onUpdate}
        onTouched={vi.fn()}
      />
    )
    await user.click(screen.getByRole('button', { name: /all 4 present/i }))
    expect(onUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ quantity_found: 4, confirmed: true })
    )
  })
})

describe('ItemRow — MEASUREMENT check type', () => {
  it('renders a number input for the reading', () => {
    render(
      <ItemRow
        item={makeItem({ check_type: 'MEASUREMENT', unit_of_measure: 'PSI' })}
        parLevel={makeParLevel({ min_quantity: 0 })}
        lot={null}
        draftItem={null}
        onUpdate={vi.fn()}
        onTouched={vi.fn()}
      />
    )
    expect(screen.getByLabelText(/PSI reading/i)).toBeTruthy()
  })

  it('shows type badge Reading', () => {
    render(
      <ItemRow
        item={makeItem({ check_type: 'MEASUREMENT', unit_of_measure: 'PSI' })}
        parLevel={makeParLevel()}
        lot={null}
        draftItem={null}
        onUpdate={vi.fn()}
        onTouched={vi.fn()}
      />
    )
    expect(screen.getByText('Reading')).toBeTruthy()
  })
})

describe('ItemRow — FUNCTIONAL check type', () => {
  it('renders Pass and Fail radio buttons', () => {
    render(
      <ItemRow
        item={makeItem({ check_type: 'FUNCTIONAL' })}
        parLevel={makeParLevel()}
        lot={null}
        draftItem={null}
        onUpdate={vi.fn()}
        onTouched={vi.fn()}
      />
    )
    expect(screen.getByRole('radio', { name: /pass/i })).toBeTruthy()
    expect(screen.getByRole('radio', { name: /fail/i })).toBeTruthy()
  })

  it('clicking Pass calls onUpdate with functional_pass=true confirmed=true', async () => {
    const user     = userEvent.setup()
    const onUpdate = vi.fn()
    render(
      <ItemRow
        item={makeItem({ check_type: 'FUNCTIONAL' })}
        parLevel={makeParLevel()}
        lot={null}
        draftItem={null}
        onUpdate={onUpdate}
        onTouched={vi.fn()}
      />
    )
    await user.click(screen.getByRole('radio', { name: /pass/i }))
    expect(onUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ functional_pass: true, confirmed: true })
    )
  })
})

describe('ItemRow — DATE_RECORD check type', () => {
  it('renders a date input (expiration date)', () => {
    render(
      <ItemRow
        item={makeItem({ check_type: 'DATE_RECORD' })}
        parLevel={makeParLevel()}
        lot={null}
        draftItem={null}
        onUpdate={vi.fn()}
        onTouched={vi.fn()}
      />
    )
    expect(screen.getByLabelText(/expiration date/i)).toBeTruthy()
  })

  it('renders Today button', () => {
    render(
      <ItemRow
        item={makeItem({ check_type: 'DATE_RECORD' })}
        parLevel={makeParLevel()}
        lot={null}
        draftItem={null}
        onUpdate={vi.fn()}
        onTouched={vi.fn()}
      />
    )
    expect(screen.getByRole('button', { name: /set date to today/i })).toBeTruthy()
  })
})

describe('ItemRow — DOCUMENT check type', () => {
  it('renders counter buttons like SUPPLY', () => {
    render(
      <ItemRow
        item={makeItem({ check_type: 'DOCUMENT' })}
        parLevel={makeParLevel()}
        lot={null}
        draftItem={null}
        onUpdate={vi.fn()}
        onTouched={vi.fn()}
      />
    )
    expect(screen.getByRole('button', { name: /increase quantity/i })).toBeTruthy()
  })
})

describe('ItemRow — confirmed / locked state', () => {
  it('confirmed item shows edit button', () => {
    render(
      <ItemRow
        item={makeItem()}
        parLevel={makeParLevel()}
        lot={null}
        draftItem={{ quantity_found: 5, confirmed: true }}
        onUpdate={vi.fn()}
        onTouched={vi.fn()}
      />
    )
    expect(screen.getByRole('button', { name: /edit test item/i })).toBeTruthy()
  })

  it('confirmed item does not show counter buttons', () => {
    render(
      <ItemRow
        item={makeItem()}
        parLevel={makeParLevel()}
        lot={null}
        draftItem={{ quantity_found: 5, confirmed: true }}
        onUpdate={vi.fn()}
        onTouched={vi.fn()}
      />
    )
    expect(screen.queryByRole('button', { name: /increase quantity/i })).toBeNull()
  })
})

describe('ItemRow — damaged badge', () => {
  it('shows Damaged badge when is_damaged=true', () => {
    render(
      <ItemRow
        item={makeItem()}
        parLevel={makeParLevel({ is_damaged: true })}
        lot={null}
        draftItem={null}
        onUpdate={vi.fn()}
        onTouched={vi.fn()}
      />
    )
    expect(screen.getByLabelText(/item marked damaged/i)).toBeTruthy()
  })

  it('does not show Damaged badge when is_damaged=false', () => {
    render(
      <ItemRow
        item={makeItem()}
        parLevel={makeParLevel({ is_damaged: false })}
        lot={null}
        draftItem={null}
        onUpdate={vi.fn()}
        onTouched={vi.fn()}
      />
    )
    expect(screen.queryByLabelText(/item marked damaged/i)).toBeNull()
  })

  it('onMarkDamaged called with true when Mark Damaged clicked', async () => {
    const user           = userEvent.setup()
    const onMarkDamaged  = vi.fn()
    const item           = makeItem()
    const parLevel       = makeParLevel({ is_damaged: false })
    render(
      <ItemRow
        item={item}
        parLevel={parLevel}
        lot={null}
        draftItem={null}
        onUpdate={vi.fn()}
        onTouched={vi.fn()}
        onMarkDamaged={onMarkDamaged}
      />
    )
    await user.click(screen.getByRole('button', { name: /mark test item as damaged/i }))
    expect(onMarkDamaged).toHaveBeenCalledWith(item, parLevel, true)
  })
})
