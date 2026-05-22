/**
 * modules/check-wizard/index.jsx
 * Check wizard orchestrator — 5-step flow.
 *
 * Steps:
 *   1 — Vehicle/bag selection
 *   2 — Compartments
 *   3 — Items
 *   4 — Reconcile  (shown when any warn OR fail items exist; skipped if all clear)
 *   5 — Submit     (was Step 4 Review)
 *   6 — Submitted  (confirmation screen, not a numbered step)
 *
 * Routing from Step 2 button:
 *   draftNeedsReconcile() === true  → STEP.RECONCILE (4)
 *   draftNeedsReconcile() === false → STEP.SUBMIT    (5)
 *
 * Compartment name fix:
 *   handleUpdateItem reads the compartment name from `activeCompartment`
 *   (always set while on Step 3) rather than from `compartmentList` (which
 *   was never populated and always returned undefined). This ensures the
 *   draft compartment object has a real name, which flows through to
 *   buildAutoRepairNotes() on Step 5.
 */
import React, { useState, useCallback, useEffect } from 'react'
import { useAuth }             from '../../shared/hooks/useAuth.jsx'
import { useApi }              from '../../shared/hooks/useApi.js'
import { useDraft }            from '../../shared/hooks/useDraft.js'
import { todayIso }            from '../../shared/utils/dateHelpers.js'
import { draftNeedsReconcile } from '../../shared/utils/statusCalc.js'
import ErrorBoundary           from '../../shared/components/ErrorBoundary.jsx'
import Modal                   from '../../shared/components/Modal.jsx'
import WizardProgress          from './components/WizardProgress.jsx'
import Step1Vehicle            from './components/Step1Vehicle.jsx'
import Step2Compartments       from './components/Step2Compartments.jsx'
import Step3Items              from './components/Step3Items.jsx'
import Step4Reconcile          from './components/Step4Reconcile.jsx'
import Step5Submit             from './components/Step5Submit.jsx'
import SubmittedScreen         from './components/SubmittedScreen.jsx'
import { checkApi }            from './api/checkApi.js'

const STEP = {
  VEHICLE:      1,
  COMPARTMENTS: 2,
  ITEMS:        3,
  RECONCILE:    4,
  SUBMIT:       5,
  SUBMITTED:    6,
}

export default function CheckWizard({
  initialDraft = null,
  preselectedStation = null,
  onExit = null,
}) {
  const { getToken } = useAuth()

  const [step, setStep]               = useState(STEP.VEHICLE)
  const [vehicleId, setVehicleId]     = useState(initialDraft?.vehicle_id ?? null)
  const [stationId, setStationId]     = useState(
    initialDraft?.station_id ?? preselectedStation?.station_id ?? null
  )
  const [checkDate, setCheckDate]     = useState(initialDraft?.check_date ?? todayIso())
  const [vehicle, setVehicle]         = useState(null)
  const [locationId, setLocationId]   = useState(initialDraft?.location_id ?? null)
  const [selectionLabel, setSelectionLabel] = useState(initialDraft?.selection_label ?? '')
  const [activeCompartment, setActiveCompartment] = useState(null)
  const [compartmentList, setCompartmentList]     = useState([])
  const [submittedCheckId, setSubmittedCheckId]   = useState(null)
  const [submittedAt, setSubmittedAt]             = useState(null)
  const [isSubmitting, setIsSubmitting]           = useState(false)
  const [submitError, setSubmitError]             = useState(null)
  const [showDiscardModal, setShowDiscardModal]   = useState(false)

  const { draft, savedAt, saveDraft, saveLineItem, clearDraft } =
    useDraft(vehicleId ?? locationId, checkDate)

  // Resume from initial draft
  useEffect(() => {
    if (initialDraft) {
      if (initialDraft.vehicle_id)       setVehicleId(initialDraft.vehicle_id)
      else if (initialDraft.location_id) setLocationId(initialDraft.location_id)
      setStationId(initialDraft.station_id)
      setCheckDate(initialDraft.check_date)
      setSelectionLabel(initialDraft.selection_label ?? '')
      setStep(STEP.COMPARTMENTS)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Resolve vehicle → location_id
  const { data: locations } = useApi(
    () => vehicleId ? checkApi.getLocations(getToken) : Promise.resolve(null),
    [vehicleId]
  )
  useEffect(() => {
    if (locations && vehicleId) {
      const loc = locations.find(
        l => l.vehicle_id === vehicleId && l.location_type === 'VEHICLE'
      )
      if (loc) setLocationId(loc.location_id)
    }
  }, [locations, vehicleId])

  // ── Step 1 → 2 ────────────────────────────────────────────────────────────
  const handleVehicleSelect = useCallback(({
    stationId: sid, vehicleId: vid, locationId: directLocationId,
    checkDate: cd, secondCrew, vehicle: v, selectionLabel: label,
  }) => {
    setStationId(sid)
    setCheckDate(cd)
    setVehicle(v ?? null)
    setSelectionLabel(label ?? '')

    if (directLocationId) {
      setVehicleId(null)
      setLocationId(directLocationId)
      saveDraft({
        vehicle_id: null, location_id: directLocationId,
        station_id: sid, check_date: cd,
        second_crew: secondCrew || null, selection_label: label,
      })
    } else {
      setVehicleId(vid)
      setLocationId(null)
      saveDraft({
        vehicle_id: vid, location_id: null,
        station_id: sid, check_date: cd,
        second_crew: secondCrew || null, selection_label: label,
      })
    }
    setStep(STEP.COMPARTMENTS)
  }, [saveDraft])

  // ── Step 2 → 3 ────────────────────────────────────────────────────────────
  const handleSelectCompartment = useCallback((comp) => {
    setActiveCompartment(comp)
    setStep(STEP.ITEMS)
  }, [])

  // ── Step 2 advance button ─────────────────────────────────────────────────
  const handleReview = useCallback(() => {
    if (draftNeedsReconcile(draft?.compartments)) {
      setStep(STEP.RECONCILE)
    } else {
      setStep(STEP.SUBMIT)
    }
  }, [draft])

  // ── Step 3: update one item ───────────────────────────────────────────────
  // Uses activeCompartment.name directly — this is always set while on Step 3
  // and is the only reliable source of the compartment name at write time.
  // Previously this read from compartmentList which was never populated,
  // causing draft compartment objects to have name: '' → "Unknown compartment"
  // in buildAutoRepairNotes() on Step 5.
  const handleUpdateItem = useCallback((compartmentId, payload) => {
    const compKey = String(compartmentId)
    saveLineItem(compartmentId, {
      name:              activeCompartment?.name ?? draft?.compartments?.[compKey]?.name ?? '',
      status:            'in_progress',
      compartment_notes: draft?.compartments?.[compKey]?.compartment_notes ?? '',
    }, payload)
  }, [activeCompartment, draft, saveLineItem])

  // ── Step 3: save/complete compartment ─────────────────────────────────────
  const handleSaveCompartment = useCallback((compartmentId) => {
    const compKey = String(compartmentId)
    const cd      = draft?.compartments?.[compKey]
    const confirmedItems = (cd?.line_items ?? []).map(li =>
      li.confirmed ? li : { ...li, confirmed: true }
    )
    saveDraft({
      compartments: {
        ...(draft?.compartments ?? {}),
        [compKey]: { ...(cd ?? {}), status: 'complete', line_items: confirmedItems },
      },
    })
    setStep(STEP.COMPARTMENTS)
    setActiveCompartment(null)
  }, [draft, saveDraft])

  const handleBackToList = useCallback(() => {
    setStep(STEP.COMPARTMENTS)
    setActiveCompartment(null)
  }, [])

  // ── Step 4 Reconcile → Step 5 Submit ──────────────────────────────────────
  const handleReconcileContinue = useCallback(() => {
    setStep(STEP.SUBMIT)
  }, [])

  // ── Step 5: submit ────────────────────────────────────────────────────────
  const handleSubmit = useCallback(async ({ overallNotes, repairNeeded, repairNotes }) => {
    setIsSubmitting(true)
    setSubmitError(null)

    const lineItems = []
    for (const cd of Object.values(draft?.compartments ?? {})) {
      for (const li of cd.line_items ?? []) {
        lineItems.push({
          compartment_id:    parseInt(cd.compartment_id ?? li.compartment_id),
          item_id:           li.item_id,
          quantity_needed:   li.quantity_needed   ?? 0,
          quantity_found:    li.quantity_found    ?? 0,
          lot_id:            li.lot_id            ?? null,
          measurement_value: li.measurement_value ?? null,
          functional_pass:   li.functional_pass   ?? null,
          date_value:        li.date_value         ?? null,
          notes:             li.notes              ?? null,
        })
      }
    }

    const notes = [
      overallNotes,
      draft?.second_crew ? `Second crew: ${draft.second_crew}` : null,
      repairNeeded       ? `REPAIR NEEDED: ${repairNotes}`     : null,
      selectionLabel     ? `Check subject: ${selectionLabel}`  : null,
    ].filter(Boolean).join('\n') || null

    try {
      const result = await checkApi.submitCheck({
        vehicle_id: vehicleId, station_id: stationId,
        check_date: checkDate, timestamp: new Date().toISOString(),
        notes, line_items: lineItems,
      }, getToken)

      clearDraft()
      setSubmittedCheckId(result.check_id)
      setSubmittedAt(new Date())
      setStep(STEP.SUBMITTED)
    } catch (err) {
      setSubmitError(err.message ?? 'Submission failed — please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }, [draft, vehicleId, stationId, checkDate, selectionLabel, getToken, clearDraft])

  // ── Discard ────────────────────────────────────────────────────────────────
  const handleDiscardConfirm = useCallback(() => {
    clearDraft()
    setShowDiscardModal(false)
    if (onExit) onExit()
  }, [clearDraft, onExit])

  // ── Reset (after submit) ──────────────────────────────────────────────────
  const handleStartNew = useCallback(() => {
    setStep(STEP.VEHICLE)
    setVehicleId(null)
    setStationId(preselectedStation?.station_id ?? null)
    setCheckDate(todayIso())
    setVehicle(null)
    setLocationId(null)
    setSelectionLabel('')
    setActiveCompartment(null)
    setSubmittedCheckId(null)
    setSubmittedAt(null)
    setSubmitError(null)
  }, [preselectedStation])

  const showDiscardBtn = step >= STEP.COMPARTMENTS && step < STEP.SUBMITTED
  const showAutoSaved  = step >= STEP.COMPARTMENTS && step < STEP.SUBMITTED && savedAt
  const progressStep   = step === STEP.SUBMITTED ? 5 : step

  return (
    <div className="check-wizard">

      {/* ── Wizard header ─────────────────────────────────────────────────── */}
      <div className="wizard-header">
        {onExit && (
          <button className="wizard-back-home" onClick={onExit} type="button"
            aria-label="Back to home screen">
            ← Home
          </button>
        )}
        {showAutoSaved && (
          <div className="autosave-indicator" aria-live="polite">
            <span aria-hidden="true">☁</span> Auto-saved
          </div>
        )}
        {showDiscardBtn && (
          <button
            className="btn-text btn-text--danger wizard-discard-btn"
            onClick={() => setShowDiscardModal(true)}
            type="button"
            aria-label="Discard this check and return to home"
          >
            Discard check
          </button>
        )}
      </div>

      {/* ── Discard modal ─────────────────────────────────────────────────── */}
      <Modal
        open={showDiscardModal}
        title="Discard this check?"
        confirmLabel="Yes, discard"
        cancelLabel="Keep working"
        onConfirm={handleDiscardConfirm}
        onCancel={() => setShowDiscardModal(false)}
        danger
      >
        <p>All progress on this check will be permanently deleted.</p>
        {(draft?.vehicle_id || draft?.location_id) && (
          <p style={{ marginTop: '8px' }}>
            <strong>{selectionLabel || `Vehicle #${draft?.vehicle_id}`}</strong>
            {draft?.check_date && <> · <strong>{draft.check_date}</strong></>}
          </p>
        )}
        <p style={{ marginTop: '8px', color: 'var(--color-text-muted)', fontSize: '15px' }}>
          This cannot be undone. You can start a fresh check from the home screen.
        </p>
      </Modal>

      {/* ── Progress bar (steps 1–5) ──────────────────────────────────────── */}
      {step !== STEP.SUBMITTED && (
        <WizardProgress
          step={progressStep}
          draft={draft}
          compartments={compartmentList}
        />
      )}

      {/* ── Steps ─────────────────────────────────────────────────────────── */}
      {step === STEP.VEHICLE && (
        <ErrorBoundary moduleName="Step 1 — Vehicle">
          <Step1Vehicle
            draft={draft}
            preselectedStation={preselectedStation}
            onSelect={handleVehicleSelect}
          />
        </ErrorBoundary>
      )}

      {step === STEP.COMPARTMENTS && locationId && (
        <ErrorBoundary moduleName="Step 2 — Compartments">
          <Step2Compartments
            locationId={locationId}
            draft={draft}
            onSelectCompartment={handleSelectCompartment}
            onReview={handleReview}
          />
        </ErrorBoundary>
      )}

      {step === STEP.ITEMS && activeCompartment && locationId && (
        <ErrorBoundary moduleName="Step 3 — Items">
          <Step3Items
            compartment={activeCompartment}
            locationId={locationId}
            allCompartments={compartmentList}
            draft={draft}
            onUpdateItem={handleUpdateItem}
            onSaveCompartment={handleSaveCompartment}
            onNavigateCompartment={setActiveCompartment}
            onBackToList={handleBackToList}
          />
        </ErrorBoundary>
      )}

      {step === STEP.RECONCILE && (
        <ErrorBoundary moduleName="Step 4 — Reconcile">
          <Step4Reconcile
            draft={draft}
            selectionLabel={selectionLabel}
            onUpdateItem={handleUpdateItem}
            onContinue={handleReconcileContinue}
            onBack={() => setStep(STEP.COMPARTMENTS)}
          />
        </ErrorBoundary>
      )}

      {step === STEP.SUBMIT && (
        <ErrorBoundary moduleName="Step 5 — Submit">
          <Step5Submit
            draft={draft}
            checkDate={checkDate}
            vehicle={vehicle}
            selectionLabel={selectionLabel}
            compartments={compartmentList}
            onSubmit={handleSubmit}
            onBack={() => setStep(
              draftNeedsReconcile(draft?.compartments) ? STEP.RECONCILE : STEP.COMPARTMENTS
            )}
            isSubmitting={isSubmitting}
            submitError={submitError}
          />
        </ErrorBoundary>
      )}

      {step === STEP.SUBMITTED && (
        <SubmittedScreen
          checkId={submittedCheckId}
          draft={draft}
          vehicle={vehicle}
          selectionLabel={selectionLabel}
          submittedAt={submittedAt}
          onStartNew={handleStartNew}
          onGoHome={onExit}
        />
      )}
    </div>
  )
}
