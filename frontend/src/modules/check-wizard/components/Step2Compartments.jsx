/**
 * modules/check-wizard/components/Step2Compartments.jsx
 * Step 2: Compartment list with status badges.
 *
 * Uses String(compartment_id) for all draft lookups — JSON round-trip
 * through localStorage converts numeric object keys to strings.
 */
import React from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import { checkApi } from '../api/checkApi.js'
import { compartmentStatus } from '../../../shared/utils/statusCalc.js'
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

  return (
    <div className="wizard-step">
      <h2 className="wizard-step__title">Step 2 — Compartments</h2>
      <p className="wizard-step__subtitle">
        Tap a compartment to begin checking its items.
      </p>

      <div className="compartment-list" role="list">
        {compartments?.map((comp, idx) => {
          const cd         = draft?.compartments?.[String(comp.compartment_id)]
          const lineItems  = cd?.line_items ?? []
          const done       = cd?.status === 'complete'
          const inProgress = cd?.status === 'in_progress'
          const status     = done
            ? compartmentStatus(lineItems)
            : inProgress
              ? { label: 'In progress', severity: 'warn', icon: '…' }
              : { label: 'Not started', severity: 'ok', icon: '○' }

          return (
            <button
              key={comp.compartment_id}
              role="listitem"
              className={`compartment-card ${done ? 'compartment-card--done' : ''}`}
              onClick={() => onSelectCompartment(comp)}
              type="button"
              aria-label={`${comp.name}${comp.location_descriptor ? ` — ${comp.location_descriptor}` : ''}, ${status.label}`}
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
                {done ? (
                  <StatusBadge
                    status={
                      status.severity === 'fail' ? 'FAIL' :
                      status.severity === 'warn' ? 'NEEDS_RESTOCK' : 'PASS'
                    }
                    size="sm"
                  />
                ) : (
                  <span className="compartment-card__status-text" aria-hidden="true">
                    {status.icon} {status.label}
                  </span>
                )}
                <span className="compartment-card__chevron" aria-hidden="true">›</span>
              </div>
            </button>
          )
        })}
      </div>

      {!allDone && (
        <p className="wizard-step__hint">
          Complete all compartments before submitting.
        </p>
      )}

      <button
        className="btn btn--primary btn--large"
        onClick={onReview}
        disabled={!allDone}
        type="button"
      >
        Review and submit →
      </button>
    </div>
  )
}
