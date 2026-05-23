/**
 * components/VehicleCard.jsx
 * Expandable card — vehicle identity always spans full width at top,
 * action buttons stack full-width below in the expanded body.
 */

import React, { useState } from 'react'
import { useApi } from '../../../shared/hooks/useApi.js'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { canAccess } from '../../../shared/utils/roleGuard.js'
import RepairRequestForm from './RepairRequestForm.jsx'
import RepairRequestList from './RepairRequestList.jsx'
import { vehicleApi } from '../api/vehicleApi.js'

function InactiveConfirmForm({ onConfirm, onCancel, isSubmitting }) {
  const [reason, setReason] = useState('')
  const [error, setError]   = useState(null)

  function handleSubmit(e) {
    e.preventDefault()
    if (reason.trim().length < 5) {
      setError('Please provide a reason (at least 5 characters).')
      return
    }
    onConfirm({ active: false, inactive_reason: reason.trim() })
  }

  return (
    <form className="inactive-confirm" onSubmit={handleSubmit} noValidate>
      <p className="inactive-confirm__prompt">
        Why is this vehicle being taken out of service?
      </p>
      <input
        className="inactive-confirm__input"
        type="text"
        value={reason}
        onChange={e => setReason(e.target.value)}
        placeholder="e.g. Transmission failure — awaiting repair"
        maxLength={200}
        autoFocus
      />
      {error && <div className="inactive-confirm__error" role="alert">{error}</div>}
      <div className="inactive-confirm__actions">
        <button type="submit" className="btn btn--danger btn--full" disabled={isSubmitting}>
          {isSubmitting ? 'Saving…' : 'Confirm — Mark Out of Service'}
        </button>
        <button type="button" className="btn btn--secondary btn--full"
          onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </button>
      </div>
    </form>
  )
}

export default function VehicleCard({ vehicle, onVehicleUpdated }) {
  const { user, getToken } = useAuth()
  const [expanded, setExpanded]         = useState(false)
  const [activePanel, setActivePanel]   = useState(null)
  const [submitError, setSubmitError]   = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isUpdating, setIsUpdating]     = useState(false)

  const isSupervisor = canAccess(user, 'supervisor')

  const {
    data: repairs,
    isLoading: loadingRepairs,
    error: repairsError,
    refetch: refetchRepairs,
  } = useApi(
    () => expanded ? vehicleApi.getRepairRequests(vehicle.vehicle_id, getToken) : Promise.resolve(null),
    [expanded, vehicle.vehicle_id]
  )

  async function handleStatusToggle(payload) {
    setIsSubmitting(true)
    setSubmitError(null)
    try {
      const updated = await vehicleApi.updateVehicleStatus(vehicle.vehicle_id, payload, getToken)
      onVehicleUpdated(updated)
      setActivePanel(null)
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleRepairSubmit(payload) {
    setIsSubmitting(true)
    setSubmitError(null)
    try {
      await vehicleApi.createRepairRequest(vehicle.vehicle_id, payload, getToken)
      setActivePanel(null)
      refetchRepairs()
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleRepairUpdate(repair, payload, onDone) {
    setIsUpdating(true)
    setSubmitError(null)
    try {
      await vehicleApi.updateRepairRequest(vehicle.vehicle_id, repair.repair_id, payload, getToken)
      refetchRepairs()
      onDone()
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setIsUpdating(false)
    }
  }

  const openCount = (repairs ?? []).filter(r => r.status !== 'RESOLVED').length

  return (
    <div className={`vehicle-card ${!vehicle.active ? 'vehicle-card--inactive' : ''}`}>

      {/* ── Header row: identity left, status badges + chevron right ── */}
      <button
        className="vehicle-card__header"
        onClick={() => { setExpanded(e => !e); setActivePanel(null) }}
        aria-expanded={expanded}
        type="button"
      >
        <div className="vehicle-card__identity">
          <span className="vehicle-card__icon" aria-hidden="true">
            {vehicle.active ? '🚑' : '🚫'}
          </span>
          <div>
            <div className="vehicle-card__number">{vehicle.vehicle_number}</div>
            <div className="vehicle-card__type">{vehicle.vehicle_type}</div>
          </div>
        </div>
        <div className="vehicle-card__summary">
          {!vehicle.active && (
            <span className="badge badge--inactive">Out of Service</span>
          )}
          {openCount > 0 && (
            <span className="badge badge--open">{openCount} open</span>
          )}
          <span className="vehicle-card__chevron" aria-hidden="true">
            {expanded ? '▲' : '▼'}
          </span>
        </div>
      </button>

      {/* ── Expanded body: always below the header ── */}
      {expanded && (
        <div className="vehicle-card__body">

          {submitError && (
            <div className="vehicle-card__error" role="alert">⚠ {submitError}</div>
          )}

          {/* Out-of-service reason strip */}
          {!vehicle.active && vehicle.inactive_reason && (
            <div className="vehicle-card__inactive-strip">
              {vehicle.inactive_reason}
            </div>
          )}

          {/* Action buttons — shown when no panel is open */}
          {activePanel === null && (
            <div className="vehicle-card__actions">
              <button
                className="btn btn--primary btn--full"
                onClick={() => setActivePanel('repair-form')}
                type="button"
              >
                🔧 Report an Issue
              </button>

              {isSupervisor && vehicle.active && (
                <button
                  className="btn btn--secondary btn--full"
                  onClick={() => setActivePanel('inactive-confirm')}
                  type="button"
                >
                  Mark Out of Service
                </button>
              )}

              {isSupervisor && !vehicle.active && (
                <button
                  className="btn btn--primary btn--full"
                  onClick={() => handleStatusToggle({ active: true })}
                  disabled={isSubmitting}
                  type="button"
                >
                  {isSubmitting ? 'Saving…' : '✓ Return to Service'}
                </button>
              )}
            </div>
          )}

          {/* Inline panels */}
          {activePanel === 'repair-form' && (
            <RepairRequestForm
              vehicle={vehicle}
              onSubmit={handleRepairSubmit}
              onCancel={() => setActivePanel(null)}
              isSubmitting={isSubmitting}
            />
          )}

          {activePanel === 'inactive-confirm' && (
            <InactiveConfirmForm
              onConfirm={handleStatusToggle}
              onCancel={() => setActivePanel(null)}
              isSubmitting={isSubmitting}
            />
          )}

          {/* Repair request list — Supervisor+ only */}
          {isSupervisor && (
            <div className="vehicle-card__section">
              <h4 className="vehicle-card__section-title">Repair Requests</h4>
              {loadingRepairs ? (
                <div className="vehicle-card__loading">Loading…</div>
              ) : repairsError ? (
                <div className="vehicle-card__error">Could not load repair requests.</div>
              ) : (
                <RepairRequestList
                  requests={repairs}
                  canManage={isSupervisor}
                  onUpdate={handleRepairUpdate}
                  isUpdating={isUpdating}
                />
              )}
            </div>
          )}

        </div>
      )}
    </div>
  )
}
