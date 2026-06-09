/**
 * tests/DraftBanner.test.jsx
 * Resume-draft banner: shown/hidden logic, station label, resume button.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DraftBanner from '../components/DraftBanner.jsx'

function makeDraft(overrides = {}) {
  return {
    saved_at:     new Date().toISOString(),
    started_at:   new Date().toISOString(),
    notes:        null,
    compartments: {},
    ...overrides,
  }
}

function makeGroup(overrides = {}) {
  return {
    selectionLabel: 'Unit 712 BLS',
    checkDate:      '2026-06-09',
    count:          1,
    drafts:         [{ key: 'ems_draft_712_2026-06-09', draft: makeDraft() }],
    ...overrides,
  }
}

describe('DraftBanner — hidden states', () => {
  it('renders nothing when group is null', () => {
    const { container } = render(
      <DraftBanner group={null} onResume={vi.fn()} onDiscard={vi.fn()} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when group.count is 0', () => {
    const { container } = render(
      <DraftBanner group={{ ...makeGroup(), count: 0 }} onResume={vi.fn()} onDiscard={vi.fn()} />
    )
    expect(container.firstChild).toBeNull()
  })
})

describe('DraftBanner — single draft', () => {
  it('renders the banner when count is 1', () => {
    render(<DraftBanner group={makeGroup()} onResume={vi.fn()} onDiscard={vi.fn()} />)
    expect(screen.getByRole('note')).toBeTruthy()
  })

  it('displays the selection label (station/vehicle name)', () => {
    render(<DraftBanner group={makeGroup()} onResume={vi.fn()} onDiscard={vi.fn()} />)
    expect(screen.getByText(/Unit 712 BLS/)).toBeTruthy()
  })

  it('Resume button has no count for a single draft', () => {
    render(<DraftBanner group={makeGroup()} onResume={vi.fn()} onDiscard={vi.fn()} />)
    const resumeBtn = screen.getByRole('button', { name: /resume/i })
    expect(resumeBtn.textContent).toBe('Resume')
  })

  it('Resume button calls onResume with the draft key and data', async () => {
    const user    = userEvent.setup()
    const onResume = vi.fn()
    const group   = makeGroup()
    render(<DraftBanner group={group} onResume={onResume} onDiscard={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /^resume$/i }))
    expect(onResume).toHaveBeenCalledWith(group.drafts[0].key, group.drafts[0].draft)
  })

  it('Discard button opens confirmation dialog', async () => {
    const user = userEvent.setup()
    render(<DraftBanner group={makeGroup()} onResume={vi.fn()} onDiscard={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /discard/i }))
    expect(screen.getByRole('dialog')).toBeTruthy()
  })
})

describe('DraftBanner — multiple drafts', () => {
  function makeMultiGroup() {
    const drafts = [
      { key: 'k1', draft: makeDraft({ saved_at: new Date().toISOString() }) },
      { key: 'k2', draft: makeDraft({ saved_at: new Date().toISOString() }) },
    ]
    return makeGroup({ count: 2, drafts })
  }

  it('Resume button shows count for multiple drafts', () => {
    render(<DraftBanner group={makeMultiGroup()} onResume={vi.fn()} onDiscard={vi.fn()} />)
    expect(screen.getByRole('button', { name: /resume \(2\)/i })).toBeTruthy()
  })

  it('title shows multiple checks in progress', () => {
    render(<DraftBanner group={makeMultiGroup()} onResume={vi.fn()} onDiscard={vi.fn()} />)
    expect(screen.getByText(/2 checks in progress/i)).toBeTruthy()
  })

  it('clicking Resume opens the draft picker dialog', async () => {
    const user = userEvent.setup()
    render(<DraftBanner group={makeMultiGroup()} onResume={vi.fn()} onDiscard={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /resume \(2\)/i }))
    expect(screen.getByRole('dialog', { name: /choose which check to resume/i })).toBeTruthy()
  })
})
