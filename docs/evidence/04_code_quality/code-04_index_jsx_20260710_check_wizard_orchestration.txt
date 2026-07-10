/**
 * modules/check-wizard/index.jsx
 * Check wizard orchestrator -- 5-step flow.
 *
 * CQ-F1: Replaced 18 useState calls with useReducer.
 * Submission result fields are grouped into a single submissionResult object.
 * No functional change.
 */
import React, { useReducer, useCallback, useEffect } from 'react'
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

/** Derive overall status from draft compartments -- mirrors backend logic */
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

// -- Reducer ------------------------------------------------------------------

const initialState = (initialDraft, preselectedStation) => ({
  step:             initialDraft ? STEP.COMPARTMENTS : STEP.VEHICLE,
  vehicleId:        initialDraft?.vehicle_id   ?? null,
  locationId:       initialDraft?.location_id  ?? null,
  stationId:        initialDraft?.station_id   ?? preselectedStation?.station_id ?? null,
  checkDate:        initialDraft?.check_date   ?? todayIso(),
  startedAt:        initialDraft?.started_at   ?? null,
  vehicle:          null,
  selectionLabel:   initialDraft?.selection_label ?? '',
  activeCompartment:  null,
  compartmentList:    [],
  submissionResult:   null,   // { checkId, submittedAt, status, repairNeeded, repairNotes }
  isSubmitting:       false,
  submitError:        null,
  showDiscardModal:   false,
})

function reducer(state, action) {
  switch (action.type) {
    case 'VEHICLE_SELECTED':
      return {
        ...state,
        step:           STEP.COMPARTMENTS,
        stationId:      action.stationId,
        vehicleId:      action.vehicleId ?? null,
        locationId:     action.locationId ?? null,
        checkDate:      action.checkDate,
        startedAt:      action.startedAt,
        vehicle:        action.vehicle ?? null,
        selectionLabel: action.selectionLabel ?? '',
      }
    case 'LOCATION_RESOLVED':
      return { ...state, locationId: action.locationId }
    case 'SELECT_COMPARTMENT':
      return { ...state, activeCompartment: action.compartment, step: STEP.ITEMS }
    case 'COMPARTMENTS_LOADED':
      return { ...state, compartmentList: action.compartments }
    case 'REVIEW':
      return { ...state, step: action.needsReconcile ? STEP.RECONCILE : STEP.SUBMIT }
    case 'RECONCILE_CONTINUE':
      return { ...state, step: STEP.SUBMIT }
    case 'BACK_TO_COMPARTMENTS':
      return { ...state, step: STEP.COMPARTMENTS, activeCompartment: null }
    case 'BACK_FROM_SUBMIT':
      return { ...state, step: action.needsReconcile ? STEP.RECONCILE : STEP.COMPARTMENTS }
    case 'SUBMIT_START':
      return { ...state, isSubmitting: true, submitError: null }
    case 'SUBMIT_SUCCESS':
      return {
        ...state,
        isSubmitting: false,
        step: STEP.SUBMITTED,
        submissionResult: {
          checkId:      action.checkId,
          submittedAt:  action.submittedAt,
          status:       action.status,
          repairNeeded: action.repairNeeded,
          repairNotes:  action.repairNotes,
        },
      }
    case 'SUBMIT_ERROR':
      return { ...state, isSubmitting: false, submitError: action.error }
    case 'SHOW_DISCARD_MODAL':
      return { ...state, showDiscardModal: true }
    case 'HIDE_DISCARD_MODAL':
      return { ...state, showDiscardModal: false }
    case 'RESET':
      return initialState(null, action.preselectedStation)
    default:
      return state
  }
}

// -- Component ----------------------------------------------------------------

export default function CheckWizard({
  initialDraft    = null,
  initialDraftKey = null,
  preselectedStation = null,
  onExit = null,
}) {
  const { getToken } = useAuth()

  const [state, dispatch] = useReducer(reducer, undefined, () =>
    initialState(initialDraft, preselectedStation)
  )

  const {
    step, vehicleId, locationId, stationId, checkDate, startedAt,
    vehicle, selectionLabel, activeCompartment, compartmentList,
    submissionResult, isSubmitting, submitError, showDiscardModal,
  } = state

  const { draft, savedAt, saveDraft, saveLineItem, clearDraft, draftRef } =
    useDraft(vehicleId ?? locationId, startedAt, initialDraftKey)

  useEffect(() => {
    if (initialDraft) {
      if (initialDraft.vehicle_id)       dispatch({ type: 'VEHICLE_SELECTED', vehicleId: initialDraft.vehicle_id, locationId: null, stationId: initialDraft.station_id, checkDate: initialDraft.check_date, startedAt: initialDraft.started_at ?? null, selectionLabel: initialDraft.selection_label ?? '' })
      else if (initialDraft.location_id) dispatch({ type: 'VEHICLE_SELECTED', vehicleId: null, locationId: initialDraft.location_id, stationId: initialDraft.station_id, checkDate: initialDraft.check_date, startedAt: initialDraft.started_at ?? null, selectionLabel: initialDraft.selection_label ?? '' })
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
      const loc = locations.find(l => l.vehicle_id === vehicleId && l.location_type === 'VEHICLE')
      if (loc) dispatch({ type: 'LOCATION_RESOLVED', locationId: loc.location_id })
    }
  }, [locations, vehicleId])

  const handleVehicleSelect = useCallback(({
    stationId: sid, vehicleId: vid, locationId: directLocationId,
    checkDate: cd, secondCrew, vehicle: v, selectionLabel: label,
  }) => {
    const now = new Date().toISOString()
    dispatch({ type: 'VEHICLE_SELECTED', stationId: sid, vehicleId: vid ?? null, locationId: directLocationId ?? null, checkDate: cd, startedAt: now, vehicle: v ?? null, selectionLabel: label ?? '' })

    if (directLocationId) {
      const firstKey = draftKey(directLocationId, now)
      saveDraft({ vehicle_id: null, location_id: directLocationId, station_id: sid, check_date: cd, started_at: now, second_crew: secondCrew || null, selection_label: label }, firstKey)
    } else {
      const firstKey = draftKey(vid, now)
      saveDraft({ vehicle_id: vid, location_id: null, station_id: sid, check_date: cd, started_at: now, second_crew: secondCrew || null, selection_label: label }, firstKey)
    }
  }, [saveDraft])

  const handleSelectCompartment = useCallback((comp) => {
    dispatch({ type: 'SELECT_COMPARTMENT', compartment: comp })
  }, [])

  const handleReview = useCallback(() => {
    dispatch({ type: 'REVIEW', needsReconcile: draftNeedsReconcile(draft?.compartments) })
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
      status:            draft?.compartments?.[compKey]?.status ?? undefined,
      compartment_notes: draft?.compartments?.[compKey]?.compartment_notes ?? '',
    }, payload)
  }, [draft, saveLineItem])

  const handleConfirmReadingItem = useCallback((comp, payload) => {
    saveLineItem(comp.compartment_id, { compartment_id: comp.compartment_id, name: comp.name }, payload)
  }, [saveLineItem])

  const handleNoChangeCompartment = useCallback((comp, supplyLineItems) => {
    const compKey = String(comp.compartment_id)
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
    saveDraft({
      compartments: {
        ...(draftRef.current?.compartments ?? {}),
        [compKey]: {
          ...(draftRef.current?.compartments?.[compKey] ?? {}),
          status: 'complete',
        },
      },
    })
    dispatch({ type: 'BACK_TO_COMPARTMENTS' })
  }, [saveDraft])

  const handleBackToList = useCallback(() => {
    dispatch({ type: 'BACK_TO_COMPARTMENTS' })
  }, [])

  const handleReconcileContinue = useCallback(() => {
    dispatch({ type: 'RECONCILE_CONTINUE' })
  }, [])

  const handleSubmit = useCallback(async ({ overallNotes, repairNeeded, repairNotes }) => {
    dispatch({ type: 'SUBMIT_START' })

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
        location_id: vehicleId ? null : locationId,
        station_id:  stationId,
        check_date:  checkDate,
        timestamp:   submissionTimestamp,
        notes,
        line_items:  lineItems,
      }, getToken)

      clearDraft()
      dispatch({
        type:         'SUBMIT_SUCCESS',
        checkId:      result.check_id,
        submittedAt:  new Date(),
        status:       overallStatus,
        repairNeeded,
        repairNotes:  repairNotes ?? '',
      })
    } catch (err) {
      dispatch({ type: 'SUBMIT_ERROR', error: err.message ?? 'Submission failed -- please try again.' })
    }
  }, [draft, vehicleId, stationId, checkDate, startedAt, selectionLabel, locationId, getToken, clearDraft])

  const handleDiscardConfirm = useCallback(() => {
    clearDraft()
    dispatch({ type: 'HIDE_DISCARD_MODAL' })
    if (onExit) onExit()
  }, [clearDraft, onExit])

  const handleStartNew = useCallback(() => {
    dispatch({ type: 'RESET', preselectedStation })
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
            onClick={() => dispatch({ type: 'SHOW_DISCARD_MODAL' })}
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
        onCancel={() => dispatch({ type: 'HIDE_DISCARD_MODAL' })}
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
        <WizardProgress step={progressStep} draft={draft} compartments={compartmentList} selectionLabel={selectionLabel} />
      )}

      {step === STEP.VEHICLE && (
        <ErrorBoundary moduleName="Step 1 -- Vehicle">
          <Step1Vehicle
            draft={draft}
            preselectedStation={preselectedStation}
            onSelect={handleVehicleSelect}
          />
        </ErrorBoundary>
      )}

      {step === STEP.COMPARTMENTS && !locationId && vehicleId && (
        <Spinner label="Resolving vehicle location..." />
      )}

      {step === STEP.COMPARTMENTS && locationId && (
        <ErrorBoundary moduleName="Step 2 -- Compartments">
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
            onCompartmentsLoaded={(comps) => dispatch({ type: 'COMPARTMENTS_LOADED', compartments: comps })}
          />
        </ErrorBoundary>
      )}

      {step === STEP.ITEMS && activeCompartment && locationId && (
        <ErrorBoundary moduleName="Step 3 -- Items">
          <Step3Items
            compartment={activeCompartment}
            locationId={locationId}
            allCompartments={compartmentList}
            draft={draft}
            onUpdateItem={handleUpdateItem}
            onSaveCompartment={handleSaveCompartment}
            onNavigateCompartment={(comp) => dispatch({ type: 'SELECT_COMPARTMENT', compartment: comp })}
            onBackToList={handleBackToList}
          />
        </ErrorBoundary>
      )}

      {step === STEP.RECONCILE && (
        <ErrorBoundary moduleName="Step 4 -- Reconcile">
          <Step4Reconcile
            draft={draft}
            selectionLabel={selectionLabel}
            onUpdateItem={handleUpdateItem}
            onContinue={handleReconcileContinue}
            onBack={() => dispatch({ type: 'BACK_TO_COMPARTMENTS' })}
          />
        </ErrorBoundary>
      )}

      {step === STEP.SUBMIT && (
        <ErrorBoundary moduleName="Step 5 -- Submit">
          <Step5Submit
            draft={draft}
            checkDate={checkDate}
            vehicle={vehicle}
            selectionLabel={selectionLabel}
            compartments={compartmentList}
            onSubmit={handleSubmit}
            onBack={() => dispatch({ type: 'BACK_FROM_SUBMIT', needsReconcile: draftNeedsReconcile(draft?.compartments) })}
            isSubmitting={isSubmitting}
            submitError={submitError}
          />
        </ErrorBoundary>
      )}

      {step === STEP.SUBMITTED && submissionResult && (
        <SubmittedScreen
          checkId={submissionResult.checkId}
          draft={draft}
          vehicle={vehicle}
          selectionLabel={selectionLabel}
          submittedAt={submissionResult.submittedAt}
          overallStatus={submissionResult.status}
          repairNeeded={submissionResult.repairNeeded}
          repairNotes={submissionResult.repairNotes}
          onStartNew={handleStartNew}
          onGoHome={onExit}
        />
      )}
    </div>
  )
}
