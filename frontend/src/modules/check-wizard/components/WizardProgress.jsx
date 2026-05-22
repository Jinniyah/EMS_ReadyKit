/**
 * modules/check-wizard/components/WizardProgress.jsx
 * Persistent progress indicator shown on every wizard step (1–5).
 *
 * Steps:
 *   1 — Vehicle
 *   2 — Compartments
 *   3 — Items
 *   4 — Reconcile  (shown only when short items exist; skipped otherwise)
 *   5 — Submit
 *
 * The Reconcile step dot is always rendered so the progress bar is
 * consistent — whether the step was visited or skipped, it shows as
 * done once step >= 5.
 */
import React from 'react'

const STEPS = ['Vehicle', 'Compartments', 'Items', 'Reconcile', 'Submit']

export default function WizardProgress({ step, draft, compartments }) {
  const compDrafts        = Object.values(draft?.compartments ?? {})
  const totalCompartments = compartments?.length ?? 0
  const doneCompartments  = compDrafts.filter(c => c.status === 'complete').length

  const totalItems   = compDrafts.reduce((n, c) => n + (c.line_items?.length ?? 0), 0)
  const checkedItems = compDrafts.reduce(
    (n, c) => n + (c.line_items?.filter(li => li.confirmed).length ?? 0), 0
  )

  const pct = totalCompartments > 0
    ? Math.round((doneCompartments / totalCompartments) * 100)
    : 0

  return (
    <div className="wizard-progress" role="navigation" aria-label="Check progress">
      <div className="wizard-progress__steps">
        {STEPS.map((label, i) => (
          <div
            key={label}
            className={[
              'wizard-progress__step',
              i + 1 === step ? 'wizard-progress__step--active' : '',
              i + 1 < step   ? 'wizard-progress__step--done'   : '',
            ].join(' ')}
            aria-current={i + 1 === step ? 'step' : undefined}
          >
            <div className="wizard-progress__step-dot" aria-hidden="true">
              {i + 1 < step ? '✓' : i + 1}
            </div>
            <div className="wizard-progress__step-label">{label}</div>
          </div>
        ))}
      </div>

      {step >= 2 && totalCompartments > 0 && (
        <div className="wizard-progress__bar-wrap">
          <div
            className="wizard-progress__bar"
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`${doneCompartments} of ${totalCompartments} compartments done`}
          >
            <div className="wizard-progress__bar-fill" style={{ width: `${pct}%` }} />
          </div>
          <div className="wizard-progress__counts">
            <span>{doneCompartments}/{totalCompartments} compartments</span>
            {totalItems > 0 && (
              <span>{checkedItems}/{totalItems} items</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
