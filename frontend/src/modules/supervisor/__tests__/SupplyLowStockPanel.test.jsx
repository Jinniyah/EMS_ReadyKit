/**
 * tests/SupplyLowStockPanel.test.jsx
 * SR-F5: expandable low-stock alert panel.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SupplyLowStockPanel from '../components/SupplyLowStockPanel.jsx'

const BELOW_PAR = [
  { item_name: 'Bandages', on_hand: 5,  par_min: 10, unit: 'pcs' },
  { item_name: 'Gloves',   on_hand: 3,  par_min: 20, unit: 'pairs' },
]

const WITH_OUT = [
  { item_name: 'Oxygen Mask', on_hand: 0, par_min: 2, unit: 'ea' },
  { item_name: 'Bandages',    on_hand: 5, par_min: 10, unit: 'pcs' },
]

describe('SupplyLowStockPanel', () => {
  it('renders nothing when alerts is empty', () => {
    const { container } = render(<SupplyLowStockPanel alerts={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when alerts is null', () => {
    const { container } = render(<SupplyLowStockPanel alerts={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('shows amber styling when all items are below par but none are out', () => {
    const { container } = render(<SupplyLowStockPanel alerts={BELOW_PAR} />)
    expect(container.querySelector('.sup-alert--supply-low')).toBeTruthy()
    expect(container.querySelector('.sup-alert--supply-out')).toBeNull()
  })

  it('summary text shows count of items below minimum', () => {
    render(<SupplyLowStockPanel alerts={BELOW_PAR} />)
    expect(screen.getByText(/2 supply items below minimum/i)).toBeTruthy()
  })

  it('shows red styling when any item is completely out', () => {
    const { container } = render(<SupplyLowStockPanel alerts={WITH_OUT} />)
    expect(container.querySelector('.sup-alert--supply-out')).toBeTruthy()
  })

  it('summary text shows out-of-stock count when items are out', () => {
    render(<SupplyLowStockPanel alerts={WITH_OUT} />)
    expect(screen.getByText(/1 supply item completely out/i)).toBeTruthy()
  })

  it('panel body is hidden by default', () => {
    render(<SupplyLowStockPanel alerts={BELOW_PAR} />)
    expect(screen.queryByRole('region', { name: /low supply items/i })).toBeNull()
  })

  it('expands to show items when tapped', async () => {
    const user = userEvent.setup()
    render(<SupplyLowStockPanel alerts={BELOW_PAR} />)
    const btn = screen.getByRole('button')
    await user.click(btn)
    expect(screen.getByRole('region', { name: /low supply items/i })).toBeTruthy()
    expect(screen.getByText('Bandages')).toBeTruthy()
    expect(screen.getByText('Gloves')).toBeTruthy()
  })

  it('collapses again on second tap', async () => {
    const user = userEvent.setup()
    render(<SupplyLowStockPanel alerts={BELOW_PAR} />)
    const btn = screen.getByRole('button')
    await user.click(btn)
    await user.click(btn)
    expect(screen.queryByRole('region', { name: /low supply items/i })).toBeNull()
  })

  it('out-of-stock item shows count as 0 / par', async () => {
    const user = userEvent.setup()
    render(<SupplyLowStockPanel alerts={WITH_OUT} />)
    await user.click(screen.getByRole('button'))
    expect(screen.getByText('0 / 2 ea')).toBeTruthy()
  })

  it('toggle button has aria-expanded=false when closed', () => {
    render(<SupplyLowStockPanel alerts={BELOW_PAR} />)
    expect(screen.getByRole('button').getAttribute('aria-expanded')).toBe('false')
  })

  it('toggle button has aria-expanded=true when open', async () => {
    const user = userEvent.setup()
    render(<SupplyLowStockPanel alerts={BELOW_PAR} />)
    await user.click(screen.getByRole('button'))
    expect(screen.getByRole('button').getAttribute('aria-expanded')).toBe('true')
  })
})
