/**
 * modules/check-wizard/index.jsx
 * Check wizard orchestrator — 5-step flow.
 */
import React, { useState, useCallback, useEffect } from 'react'
import { useAuth }             from '../../shared/hooks/useAuth.jsx'
import { useApi }              from '../../shared/hooks/useApi.js'
import { useDraft, draftKey }    from '../../shared/hooks/useDraft.js'
import { todayIso }            from '../../shared/utils/dateHelpers.js'
import { draftNeedsReconcile, deriveDraftItemStatus, lineItemStatus } from '../../shared/utils/statusCalc.js'
import ErrorBoundary           from '../../shared/components/ErrorBoundary.jsx'
import Modal                   from '../../shared/components/Modal.jsx'
import Spinner                 from '../../shared/components/Spinner.jsx'
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

/** Derive overall status from draft compartments — mirrors backend logic */
function deriveOverallStatus(compartments) {
  const allItems = Object.values(compartments ?? {}).flatMap(c => c.line_items ?? [])
  const hasFail = allItems.some(li => {
    const s = li.status ?? deriveDraftItemStatus(li)
    return s ? lineItemStatus(s).severity === 'fail' : false
  })
  const hasWarn = !hasFail && allItems.some(li => {
    const s = li.status ?? deriveDraftItemStatus(li)
    return s ? lineItemStatus(s).severity === 'warn' : false
  })
  return hasFail ? 'FAIL' : hasWarn ? 'NEEDS_RESTOCK' : 'PASS'
}

export default function CheckWizard({
  initialDraft    = null,
  initialDraftKey = null,
  preselectedStation = null,
  onExit = null,
}) {
  const { getToken } = useAuth()

  const [step, setStep]               = useState(STEP.VEHICLE)
  const [vehicleId, setVehicleId]     = useState(initialDraft?.vehicle_id   ?? null)
  const [stationId, setStationId]     = useState(
    initialDraft?.station_id ?? preselectedStation?.station_id ?? null
  )
  const [checkDate, setCheckDate]     = useState(initialDraft?.check_date   ?? todayIso())
  const [startedAt, setStartedAt]     = useState(initialDraft?.started_at   ?? null)
  const [vehicle, setVehicle]         = useState(null)
  const [locationId, setLocationId]   = useState(initialDraft?.location_id  ?? null)
  const [selectionLabel, setSelectionLabel] = useState(initialDraft?.selection_label ?? '')
  const [activeCompartment, setActiveCompartment] = useState(null)
  const [compartmentList, setCompartmentList]     = useState([])
  const [submittedCheckId, setSubmittedCheckId]   = useState(null)
  const [submittedAt, setSubmittedAt]             = useState(null)
  const [submittedStatus, setSubmittedStatus]     = useState(null)  // NEW
  const [submittedRepairNeeded, setSubmittedRepairNeeded] = useState(false) // NEW
  const [submittedRepairNotes, setSubmittedRepairNotes]   = useState('')    // NEW
  const [isSubmitting, setIsSubmitting]           = useState(false)
  const [submitError, setSubmitError]             = useState(null)
  const [showDiscardModal, setShowDiscardModal]   = useState(false)

  const { draft, savedAt, saveDraft, saveLineItem, clearDraft } =
    useDraft(vehicleId ?? locationId, startedAt, initialDraftKey)

  useEffect(() => {
    if (initialDraft) {
      if (initialDraft.vehicle_id)       setVehicleId(initialDraft.vehicle_id)
      else if (initialDraft.location_id) setLocationId(initialDraft.location_id)
      setStationId(initialDraft.station_id)
      setCheckDate(initialDraft.check_date)
      setStartedAt(initialDraft.started_at ?? null)
      setSelectionLabel(initialDraft.selection_label ?? '')
      setStep(STEP.COMPARTMENTS)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const { data: locations } = useApi(
    () => vehicleId && stationId
      ? checkApi.getLocations(stationId, getToken)
      : Promise.resolve(null),
    [vehicleId, stationId]
  )
  useEffect(() => {
    if (locations && vehicleId) {
      const loc = locations.find(
        l => l.vehicle_id === vehicleId && l.location_type === 'VEHICLE'
      )
      if (loc) setLocationId(loc.location_id)
    }
  }, [locations, vehicleId])

  const handleVehicleSelect = useCallback(({
    stationId: sid, vehicleId: vid, locationId: directLocationId,
    checkDate: cd, secondCrew, vehicle: v, selectionLabel: label,
  }) => {
    const now = new Date().toISOString()
    setStationId(sid)
    setCheckDate(cd)
    setStartedAt(now)
    setVehicle(v ?? null)
    setSelectionLabel(label ?? '')

    if (directLocationId) {
      setVehicleId(null)
      setLocationId(directLocationId)
      // Compute key explicitly — state hasn't flushed yet so keyRef is still null.
      const firstKey = draftKey(directLocationId, now)
      saveDraft({
        vehicle_id: null, location_id: directLocationId,
        station_id: sid, check_date: cd, started_at: now,
        second_crew: secondCrew || null, selection_label: label,
      }, firstKey)
    } else {
      setVehicleId(vid)
      setLocationId(null)
      // For vehicle drafts, location_id is resolved async later.
      // Key is based on vehicle_id + now so it is stable and unique.
      const firstKey = draftKey(vid, now)
      saveDraft({
        vehicle_id: vid, location_id: null,
        station_id: sid, check_date: cd, started_at: now,
        second_crew: secondCrew || null, selection_label: label,
      }, firstKey)
    }
    setStep(STEP.COMPARTMENTS)
  }, [saveDraft])

  const handleSelectCompartment = useCallback((comp) => {
    setActiveCompartment(comp)
    setStep(STEP.ITEMS)
  }, [])

  const handleReview = useCallback(() => {
    if (draftNeedsReconcile(draft?.compartments)) {
      setStep(STEP.RECONCILE)
    } else {
      setStep(STEP.SUBMIT)
    }
  }, [draft])

  const handleUpdateItem = useCallback((compartmentId, payload) => {
    const compKey = String(compartmentId)
    saveLineItem(compartmentId, {
      name:              activeCompartment?.name ?? draft?.compartments?.[compKey]?.name ?? '',
      status:            'in_progress',
      compartment_notes: draft?.compartments?.[compKey]?.compartment_notes ?? '',
    }, payload)
  }, [activeCompartment, draft, saveLineItem])

  const handleUpdatePriorityItem = useCallback((comp, payload) => {
    const compKey = String(comp.compartment_id)
    saveLineItem(comp.compartment_id, {
      name:              comp.name,
      status:            'in_progress',
      compartment_notes: draft?.compartments?.[compKey]?.compartment_notes ?? '',
    }, payload)
  }, [draft, saveLineItem])

  const handleConfirmReadingItem = useCallback((comp, payload) => {
    // Store reading confirmation as a line item but preserve compartment status
    // (stays 'not_started' so the action card remains visible).
    saveLineItem(comp.compartment_id, {
      compartment_id: comp.compartment_id,
      name:           comp.name,
    }, payload)
  }, [saveLineItem])

  const handleNoChangeCompartment = useCallback((comp, supplyLineItems) => {
    const compKey = String(comp.compartment_id)
    // Merge any pre-confirmed readings (MEASUREMENT/FUNCTIONAL/DATE_RECORD) with SUPPLY items.
    const readingTypes = new Set(['MEASUREMENT', 'FUNCTIONAL', 'DATE_RECORD', 'EXPIRY_DATE'])
    const existingItems = draft?.compartments?.[compKey]?.line_items ?? []
    const confirmedReadings = existingItems.filter(li => readingTypes.has(li.check_type))
    const mergedItems = [
      ...confirmedReadings,
      ...supplyLineItems.filter(li => !confirmedReadings.some(r => r.item_id === li.item_id)),
    ]
    saveDraft({
      compartments: {
        ...(draft?.compartments ?? {}),
        [compKey]: {
          ...(draft?.compartments?.[compKey] ?? {}),
          compartment_id: comp.compartment_id,
          name:           comp.name,
          status:         'complete',
          no_change:      true,
          line_items:     mergedItems,
        },
      },
    })
  }, [draft, saveDraft])

  const handleUndoCompartment = useCallback((compartmentId) => {
    const newCompartments = { ...(draft?.compartments ?? {}) }
    delete newCompartments[String(compartmentId)]
    saveDraft({ compartments: newCompartments })
  }, [draft, saveDraft])

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

  const handleReconcileContinue = useCallback(() => {
    setStep(STEP.SUBMIT)
  }, [])

  const handleSubmit = useCallback(async ({ overallNotes, repairNeeded, repairNotes }) => {
    setIsSubmitting(true)
    setSubmitError(null)

    // Capture status and repair details BEFORE clearing the draft
    const overallStatus = deriveOverallStatus(draft?.compartments)

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
          date_value:        li.date_value        ?? null,
          notes:             li.notes             ?? null,
        })
      }
    }

    const notes = [
      overallNotes,
      draft?.second_crew ? `Second crew: ${draft.second_crew}` : null,
      repairNeeded       ? `REPAIR NEEDED: ${repairNotes}`     : null,
      selectionLabel     ? `Check subject: ${selectionLabel}`  : null,
    ].filter(Boolean).join('\n') || null

    const submissionTimestamp = draft?.started_at ?? startedAt ?? new Date().toISOString()

    try {
      const result = await checkApi.submitCheck({
        vehicle_id:  vehicleId,
        // Send location_id only for portable checks (vehicleId null).
        // For vehicle checks, locationId is the vehicle's inventory location
        // (resolved internally) — that is NOT stored on the check record.
        location_id: vehicleId ? null : locationId,
        station_id:  stationId,
        check_date:  checkDate,
        timestamp:   submissionTimestamp,
        notes,
        line_items:  lineItems,
      }, getToken)

      clearDraft()
      setSubmittedCheckId(result.check_id)
      setSubmittedAt(new Date())
      setSubmittedStatus(overallStatus)
      setSubmittedRepairNeeded(repairNeeded)
      setSubmittedRepairNotes(repairNotes ?? '')
      setStep(STEP.SUBMITTED)
    } catch (err) {
      setSubmitError(err.message ?? 'Submission failed — please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }, [draft, vehicleId, stationId, checkDate, startedAt, selectionLabel, getToken, clearDraft])

  const handleDiscardConfirm = useCallback(() => {
    clearDraft()
    setShowDiscardModal(false)
    if (onExit) onExit()
  }, [clearDraft, onExit])

  const handleStartNew = useCallback(() => {
    setStep(STEP.VEHICLE)
    setVehicleId(null)
    setStationId(preselectedStation?.station_id ?? null)
    setCheckDate(todayIso())
    setStartedAt(null)
    setVehicle(null)
    setLocationId(null)
    setSelectionLabel('')
    setActiveCompartment(null)
    setCompartmentList([])
    setSubmittedCheckId(null)
    setSubmittedAt(null)
    setSubmittedStatus(null)
    setSubmittedRepairNeeded(false)
    setSubmittedRepairNotes('')
    setSubmitError(null)
  }, [preselectedStation])

  const showDiscardBtn = step >= STEP.COMPARTMENTS && step < STEP.SUBMITTED
  const showAutoSaved  = step >= STEP.COMPARTMENTS && step < STEP.SUBMITTED && savedAt
  const progressStep   = step === STEP.SUBMITTED ? 5 : step

  return (
    <div className="check-wizard">

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

      {step !== STEP.SUBMITTED && (
        <WizardProgress step={progressStep} draft={draft} compartments={compartmentList} />
      )}

      {step === STEP.VEHICLE && (
        <ErrorBoundary moduleName="Step 1 — Vehicle">
          <Step1Vehicle
            draft={draft}
            preselectedStation={preselectedStation}
            onSelect={handleVehicleSelect}
          />
        </ErrorBoundary>
      )}

      {step === STEP.COMPARTMENTS && !locationId && vehicleId && (
        <Spinner label="Resolving vehicle location…" />
      )}

      {step === STEP.COMPARTMENTS && locationId && (
        <ErrorBoundary moduleName="Step 2 — Compartments">
          <Step2Compartments
            locationId={locationId}
            vehicleId={vehicleId}
            draft={draft}
            onSelectCompartment={handleSelectCompartment}
            onReview={handleReview}
            onUpdatePriorityItem={handleUpdatePriorityItem}
            onNoChangeCompartment={handleNoChangeCompartment}
            onUndoCompartment={handleUndoCompartment}
            onConfirmReadingItem={handleConfirmReadingItem}
            onCompartmentsLoaded={setCompartmentList}
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
          overallStatus={submittedStatus}
          repairNeeded={submittedRepairNeeded}
          repairNotes={submittedRepairNotes}
          onStartNew={handleStartNew}
          onGoHome={onExit}
        />
      )}
    </div>
  )
}
