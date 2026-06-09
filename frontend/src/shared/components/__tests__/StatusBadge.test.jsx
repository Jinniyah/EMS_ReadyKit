/**
 * tests/StatusBadge.test.jsx
 * Renders correct color/label for check-level and line-item-level statuses.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import StatusBadge from '../StatusBadge.jsx'

describe('StatusBadge — check level (default)', () => {
  it('PASS shows Pass label', () => {
    render(<StatusBadge status="PASS" />)
    expect(screen.getByRole('generic', { name: /Status: Pass/i })).toBeTruthy()
  })

  it('PASS badge has ok severity class', () => {
    const { container } = render(<StatusBadge status="PASS" />)
    expect(container.querySelector('.status-badge--ok')).toBeTruthy()
  })

  it('NEEDS_RESTOCK shows Restock needed label', () => {
    render(<StatusBadge status="NEEDS_RESTOCK" />)
    expect(screen.getByLabelText('Status: Restock needed')).toBeTruthy()
  })

  it('NEEDS_RESTOCK badge has warn severity class', () => {
    const { container } = render(<StatusBadge status="NEEDS_RESTOCK" />)
    expect(container.querySelector('.status-badge--warn')).toBeTruthy()
  })

  it('FAIL shows Problem found label', () => {
    render(<StatusBadge status="FAIL" />)
    expect(screen.getByLabelText('Status: Problem found')).toBeTruthy()
  })

  it('FAIL badge has fail severity class', () => {
    const { container } = render(<StatusBadge status="FAIL" />)
    expect(container.querySelector('.status-badge--fail')).toBeTruthy()
  })
})

describe('StatusBadge — line item level', () => {
  it('OK shows OK label', () => {
    render(<StatusBadge status="OK" level="item" />)
    expect(screen.getByLabelText('Status: OK')).toBeTruthy()
  })

  it('OK has ok severity class', () => {
    const { container } = render(<StatusBadge status="OK" level="item" />)
    expect(container.querySelector('.status-badge--ok')).toBeTruthy()
  })

  it('SHORT has warn severity class', () => {
    const { container } = render(<StatusBadge status="SHORT" level="item" />)
    expect(container.querySelector('.status-badge--warn')).toBeTruthy()
  })

  it('LOW has warn severity class', () => {
    const { container } = render(<StatusBadge status="LOW" level="item" />)
    expect(container.querySelector('.status-badge--warn')).toBeTruthy()
  })

  it('MISSING has fail severity class', () => {
    const { container } = render(<StatusBadge status="MISSING" level="item" />)
    expect(container.querySelector('.status-badge--fail')).toBeTruthy()
  })

  it('EXPIRED shows Expired label', () => {
    render(<StatusBadge status="EXPIRED" level="item" />)
    expect(screen.getByLabelText('Status: Expired')).toBeTruthy()
  })

  it('FAIL shows Problem found label for item level (mirrors check-level label)', () => {
    render(<StatusBadge status="FAIL" level="item" />)
    expect(screen.getByLabelText('Status: Problem found')).toBeTruthy()
  })

  it('OVERDUE shows Overdue label', () => {
    render(<StatusBadge status="OVERDUE" level="item" />)
    expect(screen.getByLabelText('Status: Overdue')).toBeTruthy()
  })
})

describe('StatusBadge — size prop', () => {
  it('sm size adds sm class', () => {
    const { container } = render(<StatusBadge status="PASS" size="sm" />)
    expect(container.querySelector('.status-badge--sm')).toBeTruthy()
  })

  it('md size is the default', () => {
    const { container } = render(<StatusBadge status="PASS" />)
    expect(container.querySelector('.status-badge--md')).toBeTruthy()
  })
})
