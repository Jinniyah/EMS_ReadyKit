/**
 * modules/check-wizard/components/Step2Compartments.jsx
 * Step 2: Compartment list with status badges.
 *
 * Button logic:
 *   draftNeedsReconcile() === true  → "Reconcile →"
 *   draftNeedsReconcile() === false → "Review and Submit →"
 *
 * draftNeedsReconcile() returns true for both warn (SHORT) and fail
 * (FUNCTIONAL FAIL, MISSING) items — so a check with only failed items
 * (no short/missing supply) still routes through the Reconcile screen
 * so the responder sees the supervisor-attention section.
 */
import React from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import { checkApi } from '../api/checkApi.js'
import { compartmentStatus, draftNeedsReconcile } from '../../../shared/utils/statusCalc.js'
import StatusBadge from '../../../shared/components/StatusBadge.jsx'
import Spinner from '../../../shared/components/Spinner.jsx'

export default function Step2Compartments({
  locationId,
  draft,
  onSelectCompartment,
  onReview,
}) {
  const { getToken } = useAuth()

  const { data: compartments, isLoading } = useApi(
    () => checkApi.getCompartments(locationId, getToken),
    [locationId]
  )

  if (isLoading) return <Spinner label="Loading compartments…" />

  const allDone = compartments?.every(c => {
    const cd = draft?.compartments?.[String(c.compartment_id)]
    return cd?.status === 'complete'
  })

  // Show "Reconcile →" if any warn or fail items exist across all compartments.
  // Fail-only checks (e.g. functional fail, no short supply) must also route
  // through Reconcile so the responder sees the supervisor-attention section.
  const needsReconcile = allDone && draftNeedsReconcile(draft?.compartments)

  return (
    <div className="wizard-step">
      <h2 className="wizard-step__title">Step 2 — Compartments</h2>
      <p className="wizard-step__subtitle">
        Tap a compartment to check its items. Yellow means restock needed; red flags for supervisor.
      </p>

      <div className="compartment-list" role="list">
        {compartments?.map((comp, idx) => {
          const cd         = draft?.compartments?.[String(comp.compartment_id)]
          const lineItems  = cd?.line_items ?? []
          const done       = cd?.status === 'complete'
          const inProgress = !!cd && cd.status !== 'complete'

          const itemStatus = (done || inProgress)
            ? compartmentStatus(lineItems)
            : null

          const badgeStatus = itemStatus
            ? (itemStatus.severity === 'fail'  ? 'FAIL'
              : itemStatus.severity === 'warn' ? 'NEEDS_RESTOCK'
              : 'PASS')
            : null

          return (
            <button
              key={comp.compartment_id}
              role="listitem"
              className={`compartment-card ${done ? 'compartment-card--done' : ''}`}
              onClick={() => onSelectCompartment(comp)}
              type="button"
              aria-label={`${comp.name}${comp.location_descriptor ? ` — ${comp.location_descriptor}` : ''}, ${
                !cd ? 'Not started'
                : inProgress ? `In progress — ${itemStatus?.label ?? ''}`
                : itemStatus?.label ?? ''
              }`}
            >
              <div className="compartment-card__number" aria-hidden="true">
                {idx + 1}
              </div>

              <div className="compartment-card__info">
                <div className="compartment-card__name">{comp.name}</div>
                {comp.location_descriptor && (
                  <div className="compartment-card__location">
                    {comp.location_descriptor}
                  </div>
                )}
                {comp.restriction_note && (
                  <div className="compartment-card__restriction" role="note">
                    ⚠ {comp.restriction_note}
                  </div>
                )}
              </div>

              <div className="compartment-card__status">
                {!cd ? (
                  <span className="compartment-card__status-text" aria-hidden="true">
                    ○ Not started
                  </span>
                ) : (
                  <div className="compartment-card__status-stack">
                    <StatusBadge status={badgeStatus} size="sm" />
                    {inProgress && (
                      <span className="compartment-card__in-progress-label">
                        In progress
                      </span>
                    )}
                  </div>
                )}
                <span className="compartment-card__chevron" aria-hidden="true">›</span>
              </div>
            </button>
          )
        })}
      </div>

      {!allDone && (
        <p className="wizard-step__hint">
          Complete all compartments before continuing.
        </p>
      )}

      <button
        className="btn btn--primary btn--large"
        onClick={onReview}
        disabled={!allDone}
        type="button"
      >
        {!allDone
          ? 'Complete all compartments to continue'
          : needsReconcile
            ? 'Reconcile →'
            : 'Review and Submit →'}
      </button>
    </div>
  )
}
