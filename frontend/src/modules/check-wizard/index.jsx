/**
 * modules/check-wizard/index.jsx
 * Check wizard orchestrator.
 *
 * Compartment key note: all draft.compartments lookups use String(compartmentId)
 * because JSON.parse converts numeric object keys to strings.
 */
import React, { useState, useCallback, useEffect } from 'react'
import { useAuth } from '../../shared/hooks/useAuth.jsx'
import { useApi } from '../../shared/hooks/useApi.js'
import { useDraft } from '../../shared/hooks/useDraft.js'
import { todayIso } from '../../shared/utils/dateHelpers.js'
import ErrorBoundary from '../../shared/components/ErrorBoundary.jsx'
import WizardProgress from './components/WizardProgress.jsx'
import Step1Vehicle from './components/Step1Vehicle.jsx'
import Step2Compartments from './components/Step2Compartments.jsx'
import Step3Items from './components/Step3Items.jsx'
import Step4Review from './components/Step4Review.jsx'
import SubmittedScreen from './components/SubmittedScreen.jsx'
import { checkApi } from './api/checkApi.js'

const STEP = { VEHICLE: 1, COMPARTMENTS: 2, ITEMS: 3, REVIEW: 4, SUBMITTED: 5 }

export default function CheckWizard({
  initialDraft = null,
  preselectedStation = null,
  onExit = null,
}) {
  const { getToken } = useAuth()

  const [step, setStep]                           = useState(STEP.VEHICLE)
  const [vehicleId, setVehicleId]                 = useState(initialDraft?.vehicle_id ?? null)
  const [stationId, setStationId]                 = useState(
    initialDraft?.station_id ?? preselectedStation?.station_id ?? null
  )
  const [checkDate, setCheckDate]   = useState(initialDraft?.check_date ?? todayIso())
  const [vehicle, setVehicle]       = useState(null)
  const [locationId, setLocationId] = useState(null)
  const [activeCompartment, setActiveCompartment] = useState(null)
  const [compartmentList, setCompartmentList]     = useState([])
  const [submittedCheckId, setSubmittedCheckId]   = useState(null)
  const [submittedAt, setSubmittedAt]             = useState(null)
  const [isSubmitting, setIsSubmitting]           = useState(false)
  const [submitError, setSubmitError]             = useState(null)

  const { draft, savedAt, saveDraft, saveLineItem, clearDraft } =
    useDraft(vehicleId, checkDate)

  // Resume from initial draft
  useEffect(() => {
    if (initialDraft && initialDraft.vehicle_id && !vehicle) {
      setVehicleId(initialDraft.vehicle_id)
      setStationId(initialDraft.station_id)
      setCheckDate(initialDraft.check_date)
      setStep(STEP.COMPARTMENTS)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Load inventory location when vehicle is known
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
    stationId: sid, vehicleId: vid, checkDate: cd, secondCrew, vehicle: v,
  }) => {
    setStationId(sid)
    setVehicleId(vid)
    setCheckDate(cd)
    setVehicle(v)
    saveDraft({ vehicle_id: vid, station_id: sid, check_date: cd, second_crew: secondCrew || null })
    setStep(STEP.COMPARTMENTS)
  }, [saveDraft])

  // ── Step 2 → 3 ────────────────────────────────────────────────────────────
  const handleSelectCompartment = useCallback((comp) => {
    setActiveCompartment(comp)
    setStep(STEP.ITEMS)
  }, [])

  // ── Step 3: update one item — writes immediately to draft ─────────────────
  const handleUpdateItem = useCallback((compartmentId, payload) => {
    const comp    = compartmentList.find(c => c.compartment_id === compartmentId)
    const compKey = String(compartmentId)
    saveLineItem(compartmentId, {
      name:              comp?.name ?? '',
      status:            'in_progress',
      compartment_notes: draft?.compartments?.[compKey]?.compartment_notes ?? '',
    }, payload)
  }, [compartmentList, draft, saveLineItem])

  // ── Step 3: save/complete compartment ────────────────────────────────────
  const handleSaveCompartment = useCallback((compartmentId) => {
    const compKey = String(compartmentId)
    const cd      = draft?.compartments?.[compKey]
    saveDraft({
      compartments: {
        ...(draft?.compartments ?? {}),
        [compKey]: { ...(cd ?? {}), status: 'complete' },
      },
    })
    setStep(STEP.COMPARTMENTS)
    setActiveCompartment(null)
  }, [draft, saveDraft])

  const handleBackToList = useCallback(() => {
    setStep(STEP.COMPARTMENTS)
    setActiveCompartment(null)
  }, [])

  const handleGoToReview = useCallback(() => setStep(STEP.REVIEW), [])

  // ── Step 4: submit ────────────────────────────────────────────────────────
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
  }, [draft, vehicleId, stationId, checkDate, getToken, clearDraft])

  // ── Reset ─────────────────────────────────────────────────────────────────
  const handleStartNew = useCallback(() => {
    setStep(STEP.VEHICLE)
    setVehicleId(null)
    setStationId(preselectedStation?.station_id ?? null)
    setCheckDate(todayIso())
    setVehicle(null)
    setLocationId(null)
    setActiveCompartment(null)
    setSubmittedCheckId(null)
    setSubmittedAt(null)
    setSubmitError(null)
  }, [preselectedStation])

  const showAutoSaved = step >= STEP.COMPARTMENTS && step < STEP.SUBMITTED && savedAt

  return (
    <div className="check-wizard">
      {onExit && (
        <button className="wizard-back-home" onClick={onExit} type="button" aria-label="Back to home screen">
          ← Home
        </button>
      )}

      {showAutoSaved && (
        <div className="autosave-indicator" aria-live="polite">
          <span aria-hidden="true">☁</span> Auto-saved
        </div>
      )}

      {step < STEP.SUBMITTED && (
        <WizardProgress step={step} draft={draft} compartments={compartmentList} />
      )}

      {step === STEP.VEHICLE && (
        <ErrorBoundary moduleName="Step 1 — Vehicle">
          <Step1Vehicle draft={draft} preselectedStation={preselectedStation} onSelect={handleVehicleSelect} />
        </ErrorBoundary>
      )}

      {step === STEP.COMPARTMENTS && locationId && (
        <ErrorBoundary moduleName="Step 2 — Compartments">
          <Step2Compartments
            locationId={locationId}
            draft={draft}
            onSelectCompartment={handleSelectCompartment}
            onReview={handleGoToReview}
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

      {step === STEP.REVIEW && (
        <ErrorBoundary moduleName="Step 4 — Review">
          <Step4Review
            draft={draft}
            vehicle={vehicle}
            compartments={compartmentList}
            onSubmit={handleSubmit}
            onBack={() => setStep(STEP.COMPARTMENTS)}
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
          submittedAt={submittedAt}
          onStartNew={handleStartNew}
          onGoHome={onExit}
        />
      )}
    </div>
  )
}
