/**
 * tests/WizardProgress.test.jsx
 * Progress bar: correct step highlighted, completed steps marked, labels visible.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import WizardProgress from '../components/WizardProgress.jsx'

const STEP_LABELS = ['Vehicle', 'Compartments', 'Items', 'Restock', 'Submit']

describe('WizardProgress — step labels', () => {
  it('all five step labels are always rendered', () => {
    render(<WizardProgress step={1} draft={null} compartments={[]} />)
    for (const label of STEP_LABELS) {
      expect(screen.getByText(label)).toBeTruthy()
    }
  })
})

describe('WizardProgress — active step', () => {
  it('step 1 has aria-current=step', () => {
    render(<WizardProgress step={1} draft={null} compartments={[]} />)
    const steps = document.querySelectorAll('[aria-current="step"]')
    expect(steps).toHaveLength(1)
    expect(steps[0].textContent).toContain('Vehicle')
  })

  it('step 3 marks step 3 as current', () => {
    render(<WizardProgress step={3} draft={null} compartments={[]} />)
    const activeStep = document.querySelector('[aria-current="step"]')
    expect(activeStep?.textContent).toContain('Items')
  })

  it('step 5 marks Submit as current', () => {
    render(<WizardProgress step={5} draft={null} compartments={[]} />)
    const activeStep = document.querySelector('[aria-current="step"]')
    expect(activeStep?.textContent).toContain('Submit')
  })
})

describe('WizardProgress — completed steps', () => {
  it('shows checkmarks for steps before the current one', () => {
    render(<WizardProgress step={3} draft={null} compartments={[]} />)
    const dots = document.querySelectorAll('.wizard-progress__step-dot')
    // Steps 1 and 2 should show ✓
    expect(dots[0].textContent).toBe('✓')
    expect(dots[1].textContent).toBe('✓')
    // Step 3 is current — shows number
    expect(dots[2].textContent).toBe('3')
    // Steps 4 and 5 are future — show numbers
    expect(dots[3].textContent).toBe('4')
    expect(dots[4].textContent).toBe('5')
  })

  it('step 1 has done class for steps before it', () => {
    render(<WizardProgress step={3} draft={null} compartments={[]} />)
    const steps = document.querySelectorAll('.wizard-progress__step')
    expect(steps[0].className).toContain('wizard-progress__step--done')
    expect(steps[1].className).toContain('wizard-progress__step--done')
    expect(steps[2].className).toContain('wizard-progress__step--active')
  })
})

describe('WizardProgress — progress bar', () => {
  it('progress bar not shown on step 1', () => {
    render(<WizardProgress step={1} draft={null} compartments={[{ id: 1 }]} />)
    expect(document.querySelector('.wizard-progress__bar')).toBeNull()
  })

  it('progress bar shown on step 2 when compartments exist', () => {
    const draft = { compartments: { 1: { status: 'complete', line_items: [] } } }
    render(<WizardProgress step={2} draft={draft} compartments={[{ id: 1 }]} />)
    expect(document.querySelector('[role="progressbar"]')).toBeTruthy()
  })

  it('progress bar aria-valuenow reflects completion fraction', () => {
    const draft = {
      compartments: {
        1: { status: 'complete', line_items: [] },
        2: { status: 'pending',  line_items: [] },
      },
    }
    const compartments = [{ id: 1 }, { id: 2 }]
    render(<WizardProgress step={2} draft={draft} compartments={compartments} />)
    const bar = document.querySelector('[role="progressbar"]')
    expect(bar.getAttribute('aria-valuenow')).toBe('50')
  })
})
