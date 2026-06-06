/**
 * modules/check-wizard/components/SubmittedScreen.jsx
 * Confirmation screen after a successful check submission.
 *
 * Design principle: the screen content must match reality.
 * - PASS: truck is cleared, clear positive message.
 * - NEEDS_RESTOCK: truck can go out but needs attention soon.
 * - FAIL: truck has issues. Never tell a tired responder "truck is cleared"
 *   when it has failed items — that's the exact failure mode we're preventing.
 *   Show a prominent prompt to file a repair request so the supervisor is
 *   alerted immediately and the issue doesn't get forgotten.
 *
 * "The goal is to make failure less likely with a stressed, tired EMS Responder
 *  so that when ambulances go out they have the right supplies to save lives."
 */
import React, { useState, useMemo } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { vehicleApi } from '../../vehicles/api/vehicleApi.js'
import { formatCheckDate, formatTime } from '../../../shared/utils/dateHelpers.js'

export default function SubmittedScreen({
  checkId, draft, vehicle, selectionLabel, submittedAt,
  overallStatus, repairNeeded, repairNotes,
  onStartNew, onGoHome,
}) {
  const { getToken } = useAuth()
  const [repairFiled, setRepairFiled]     = useState(false)
  const [repairError, setRepairError]     = useState(null)
  const [isFilingRepair, setFilingRepair] = useState(false)
  const [showRestock, setShowRestock]     = useState(false)

  const isFail    = overallStatus === 'FAIL'
  const isRestock = overallStatus === 'NEEDS_RESTOCK'
  const isPass    = !isFail && !isRestock

  // Build restock list from draft — items below par, grouped by compartment name
  const restockList = useMemo(() => {
    const groups = []
    for (const cd of Object.values(draft?.compartments ?? {})) {
      const short = (cd.line_items ?? []).filter(li =>
        li.check_type === 'SUPPLY' &&
        li.quantity_found != null &&
        li.quantity_needed != null &&
        li.quantity_found < li.quantity_needed
      )
      if (short.length > 0) groups.push({ name: cd.name ?? 'Compartment', items: short })
    }
    return groups
  }, [draft])

  const checkSubject = vehicle?.vehicle_number
    ? `Unit ${vehicle.vehicle_number}`
    : selectionLabel || `Check #${checkId}`

  async function handleFileRepair() {
    if (!vehicle?.vehicle_id) return
    setFilingRepair(true)
    setRepairError(null)
    try {
      await vehicleApi.createRepairRequest(
        vehicle.vehicle_id,
        {
          severity: 'ROUTINE',
          description: repairNotes
            ? `From failed check #${checkId}: ${repairNotes}`
            : `Failed items found during daily check #${checkId}. Please review check history.`,
        },
        getToken
      )
      setRepairFiled(true)
    } catch (err) {
      setRepairError(err.message)
    } finally {
      setFilingRepair(false)
    }
  }

  return (
    <div className="submitted-screen">

      {/* ── Status icon — reflects actual outcome ── */}
      <div
        className={`submitted-screen__checkmark ${isFail ? 'submitted-screen__checkmark--fail' : isRestock ? 'submitted-screen__checkmark--warn' : ''}`}
        aria-label={isFail ? 'Check failed' : isRestock ? 'Check needs restock' : 'Check submitted successfully'}
      >
        {isFail ? '⚠' : isRestock ? '!' : '✓'}
      </div>

      {/* ── Title — honest about the outcome ── */}
      {isPass && (
        <>
          <h1 className="submitted-screen__title">
            {checkSubject} is ready
          </h1>
          <p className="submitted-screen__cleared">
            Truck is cleared for service
          </p>
        </>
      )}

      {isRestock && (
        <>
          <h1 className="submitted-screen__title submitted-screen__title--warn">
            {checkSubject} needs restocking
          </h1>
          <p className="submitted-screen__cleared submitted-screen__cleared--warn">
            Truck can go out — restock when possible
          </p>
        </>
      )}

      {isFail && (
        <>
          <h1 className="submitted-screen__title submitted-screen__title--fail">
            {checkSubject} has failed items
          </h1>
          <p className="submitted-screen__cleared submitted-screen__cleared--fail">
            Supervisor has been notified via check history
          </p>
        </>
      )}

      {/* ── Reference ── */}
      <div className="submitted-screen__ref" aria-label={`Check reference number ${checkId}`}>
        <div className="submitted-screen__ref-label">Check reference</div>
        <div className="submitted-screen__ref-id">#{checkId}</div>
      </div>

      <div className="submitted-screen__meta">
        <div>{formatCheckDate(draft?.check_date)}</div>
        <div>
          Submitted {formatTime(submittedAt)}
          {draft?.second_crew && <> · {draft.second_crew}</>}
        </div>
      </div>

      {/* ── FAIL: prominent repair request prompt ── */}
      {isFail && !repairFiled && vehicle?.vehicle_id && (
        <div className="submitted-screen__repair-prompt">
          <p className="submitted-screen__repair-prompt-title">
            🔧 Report a problem?
          </p>
          <p className="submitted-screen__repair-prompt-body">
            This will alert your supervisor immediately and create a record
            in Vehicle &amp; Equipment Status so nothing gets missed.
          </p>
          {repairNotes && (
            <div className="submitted-screen__repair-notes">
              {repairNotes}
            </div>
          )}
          {repairError && (
            <div className="submitted-screen__repair-error" role="alert">
              Something went wrong — please tell your supervisor directly.
            </div>
          )}
          <button
            className="btn btn--danger btn--full"
            onClick={handleFileRepair}
            disabled={isFilingRepair}
            type="button"
          >
            {isFilingRepair ? 'Reporting…' : '⚠ Report a Problem'}
          </button>
          <button
            className="btn btn--secondary btn--full"
            onClick={() => setRepairFiled(true)}
            type="button"
          >
            Skip — I'll do it later
          </button>
        </div>
      )}

      {/* ── Repair filed confirmation ── */}
      {isFail && repairFiled && (
        <div className="submitted-screen__repair-filed">
          ✓ Problem reported — supervisor will be notified
        </div>
      )}

      {/* ── RESTOCK: restock list ── */}
      {isRestock && restockList.length > 0 && (
        <div className="submitted-screen__restock-section">
          <button
            className="btn btn--secondary btn--full"
            onClick={() => setShowRestock(s => !s)}
            type="button"
          >
            {showRestock ? 'Hide restock list' : 'View restock list'}
          </button>
          {showRestock && (
            <div className="submitted-screen__restock-list">
              {restockList.map(group => (
                <div key={group.name} className="submitted-screen__restock-group">
                  <div className="submitted-screen__restock-group-name">{group.name}</div>
                  {group.items.map(li => (
                    <div key={li.item_id} className="submitted-screen__restock-row">
                      <span className="submitted-screen__restock-item">{li.item_name}</span>
                      <span className="submitted-screen__restock-qty">
                        Need {li.quantity_needed - li.quantity_found} more
                        <span className="submitted-screen__restock-qty-detail">
                          {' '}({li.quantity_found} of {li.quantity_needed})
                        </span>
                      </span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Actions ── */}
      <div className="submitted-screen__actions">
        <button
          className="btn btn--primary"
          onClick={onGoHome}
          type="button"
        >
          ← Back to home
        </button>
        <button
          className="btn btn--secondary"
          onClick={onStartNew}
          type="button"
        >
          Start another check
        </button>
      </div>
    </div>
  )
}
