/**
 * modules/check-wizard/components/Step2Compartments.jsx
 * Step 2: Priority items + compartment list with inline reading confirmations.
 *
 * Priority items (priority_check=true) are pulled above the compartment list.
 *
 * Each compartment card (not-started state) shows:
 *   • Reading confirmations — MEASUREMENT/FUNCTIONAL/DATE_RECORD items with
 *     last recorded value. Responder confirms inline; readings pre-populate Step 3.
 *   • Stock preview — first 3 SUPPLY items with current stock vs par.
 *   • No Change — enabled once all readings confirmed; attests SUPPLY items at par.
 *   • Modify  — opens Step 3 (readings pre-filled if already confirmed).
 *
 * No Change is BLOCKED (hidden) when:
 *   • comp.requires_full_check === true
 *   • the compartment contains a priority item
 * No Change is DISABLED (grayed) when readings exist but are not all confirmed.
 *
 * inProgress = cd?.status === 'in_progress' — only true after entering Step 3.
 * Confirming readings on the card keeps status as 'not_started'.
 */
import React, { useState, useMemo, useEffect } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import { checkApi } from '../api/checkApi.js'
import { compartmentStatus, draftNeedsReconcile } from '../../../shared/utils/statusCalc.js'
import StatusBadge from '../../../shared/components/StatusBadge.jsx'
import Spinner from '../../../shared/components/Spinner.jsx'
import ItemRow from './ItemRow.jsx'

const READING_TYPES = new Set(['MEASUREMENT', 'FUNCTIONAL', 'DATE_RECORD', 'EXPIRY_DATE'])

const TODAY = new Date().toISOString().slice(0, 10)

function fmtDate(d) {
  if (!d) return null
  return new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
function daysAgo(d) {
  if (!d) return null
  const n = Math.floor((Date.now() - new Date(d + 'T00:00:00').getTime()) / 86400000)
  return n === 0 ? 'today' : n === 1 ? 'yesterday' : `${n} days ago`
}

/** Build SUPPLY/DOCUMENT "No Change" line items — readings are merged separately. */
function buildNoChangeLineItems(compParLevels, itemMap) {
  return compParLevels
    .filter(pl => pl.active !== false)
    .reduce((acc, pl) => {
      const item = itemMap[pl.item_id]
      const checkType = item?.check_type ?? 'SUPPLY'
      // Reading types are confirmed inline on the card — skip here.
      if (READING_TYPES.has(checkType)) return acc
      acc.push({
        item_id:           pl.item_id,
        item_name:         item?.name ?? '',
        check_type:        checkType,
        quantity_needed:   pl.min_quantity,
        min_value:         pl.min_value ?? item?.measurement_minimum ?? null,
        quantity_found:    pl.min_quantity,
        measurement_value: null,
        functional_pass:   null,
        date_value:        null,
        notes:             null,
        confirmed:         true,
      })
      return acc
    }, [])
}

export default function Step2Compartments({
  locationId,
  vehicleId,
  draft,
  onSelectCompartment,
  onReview,
  onUpdatePriorityItem,
  onNoChangeCompartment,
  onUndoCompartment,
  onConfirmReadingItem,
  onCompartmentsLoaded,
}) {
  const { getToken } = useAuth()
  const [expandedPriorityId, setExpandedPriorityId] = useState(null)
  const [editingReadingId,   setEditingReadingId]   = useState(null)
  const [editValue,          setEditValue]          = useState('')

  const { data: compartments,  isLoading: loadingComps  } = useApi(
    () => checkApi.getCompartments(locationId, getToken), [locationId]
  )

  useEffect(() => {
    if (compartments && onCompartmentsLoaded) onCompartmentsLoaded(compartments)
  }, [compartments, onCompartmentsLoaded])
  const { data: parLevels,    isLoading: loadingPar   } = useApi(
    () => checkApi.getParLevels(locationId, getToken), [locationId]
  )
  const { data: items,        isLoading: loadingItems } = useApi(
    () => checkApi.getItems(getToken), []
  )
  const { data: stockLots } = useApi(
    () => checkApi.getStockLots(locationId, getToken), [locationId]
  )
  const { data: lastReadings } = useApi(
    () => checkApi.getLastReadings(vehicleId, locationId, getToken),
    [vehicleId, locationId]
  )

  const isLoading = loadingComps || loadingPar || loadingItems

  const itemMap = useMemo(
    () => Object.fromEntries((items ?? []).map(it => [it.item_id, it])),
    [items]
  )
  const compartmentMap = useMemo(
    () => Object.fromEntries((compartments ?? []).map(c => [c.compartment_id, c])),
    [compartments]
  )
  const lastReadingMap = useMemo(() => {
    const m = {}
    for (const r of lastReadings ?? []) m[r.item_id] = r
    return m
  }, [lastReadings])

  // Last check quantity per item — source of truth for vehicle on-hand counts.
  // Stock lots track supply room inventory; once items leave the room they are
  // no longer the room's concern. Vehicle on-hand = what was last counted here.
  const lastQtyMap = useMemo(() => {
    const m = {}
    for (const r of lastReadings ?? []) {
      if (r.quantity_found != null) m[r.item_id] = r.quantity_found
    }
    return m
  }, [lastReadings])

  const lotMap = useMemo(() => {
    const m = {}
    for (const lot of stockLots ?? []) { if (!m[lot.item_id]) m[lot.item_id] = lot }
    return m
  }, [stockLots])

  const priorityItems = useMemo(
    () => (parLevels ?? []).filter(pl => pl.priority_check === true),
    [parLevels]
  )

  if (isLoading) return <Spinner label="Loading compartments…" />

  const allDone = compartments?.every(c => {
    const cd = draft?.compartments?.[String(c.compartment_id)]
    return cd?.status === 'complete'
  })
  const needsReconcile = allDone && draftNeedsReconcile(draft?.compartments)

  const priorityAllDone = priorityItems.length === 0 || priorityItems.every(pl => {
    const compDraft = draft?.compartments?.[String(pl.compartment_id)]
    return (compDraft?.line_items ?? []).some(li => li.item_id === pl.item_id && li.confirmed === true)
  })

  return (
    <div className="wizard-step">
      <h2 className="wizard-step__title">Step 2 — Compartments</h2>

      {/* ── Priority items — confirmed inline before compartment walk ─────── */}
      {priorityItems.length > 0 && (
        <section className="priority-section" aria-label="Priority items">
          <div className="priority-section__header">
            <span className={`priority-section__title ${priorityAllDone ? 'priority-section__title--done' : ''}`}>
              {priorityAllDone ? '✓ Priority items confirmed' : '! Check these first'}
            </span>
          </div>
          <div className="priority-items-list">
            {priorityItems.map(pl => {
              const item = itemMap[pl.item_id]
              const comp = compartmentMap[pl.compartment_id]
              if (!item || !comp) return null

              const compDraft  = draft?.compartments?.[String(pl.compartment_id)]
              const draftItem  = (compDraft?.line_items ?? []).find(li => li.item_id === pl.item_id) ?? null
              const isConfirmed = draftItem?.confirmed === true
              const isExpanded  = expandedPriorityId === pl.par_id
              const questionText = pl.priority_question || item.name

              const lastReading    = lastReadingMap[pl.item_id]
              const lastCheckDate  = lastReading?.check_date
              const lastFuncPass   = lastReading?.functional_pass
              const daysSinceLast  = lastCheckDate
                ? Math.floor((Date.now() - new Date(lastCheckDate + 'T00:00:00').getTime()) / 86400000)
                : null
              const lastConfirmedAmber = daysSinceLast != null && daysSinceLast > 7
              const lastConfirmedRed   = daysSinceLast != null && daysSinceLast > 14

              return (
                <div
                  key={pl.par_id}
                  className={`priority-card ${isConfirmed ? 'priority-card--confirmed' : 'priority-card--pending'}`}
                >
                  <button
                    className="priority-card__toggle"
                    onClick={() => setExpandedPriorityId(isExpanded ? null : pl.par_id)}
                    type="button"
                    aria-expanded={isExpanded}
                  >
                    <span className="priority-card__indicator" aria-hidden="true">
                      {isConfirmed ? '✓' : '!'}
                    </span>
                    <span className="priority-card__question-block">
                      <span className="priority-card__question">{questionText}</span>
                      {lastCheckDate && lastFuncPass !== false && (
                        <span
                          className="priority-card__last-confirmed"
                          style={{
                            color: lastConfirmedRed
                              ? 'var(--color-status-fail)'
                              : lastConfirmedAmber
                              ? 'var(--color-status-warn)'
                              : 'var(--color-text-muted)',
                          }}
                        >
                          Last confirmed: {fmtDate(lastCheckDate)} · {daysAgo(lastCheckDate)}
                        </span>
                      )}
                      {lastCheckDate && lastFuncPass === false && (
                        <span className="priority-card__last-confirmed" style={{ color: 'var(--color-status-fail)' }}>
                          Last check: {fmtDate(lastCheckDate)} — FAILED
                        </span>
                      )}
                      {!lastCheckDate && (
                        <span className="priority-card__last-confirmed" style={{ color: 'var(--color-text-muted)' }}>
                          Not yet confirmed
                        </span>
                      )}
                    </span>
                    <span className="priority-card__chevron" aria-hidden="true">
                      {isExpanded ? '∧' : '∨'}
                    </span>
                  </button>

                  {isExpanded && (
                    <div className="priority-card__body">
                      <ItemRow
                        item={item}
                        parLevel={pl}
                        lot={lotMap[pl.item_id] ?? null}
                        draftItem={draftItem}
                        onUpdate={(payload) => onUpdatePriorityItem(comp, payload)}
                        onTouched={() => {}}
                      />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      )}

      <p className="wizard-step__subtitle">
        Tap a compartment to check its items. Yellow means restock needed; red flags for supervisor.
      </p>

      {/* ── Compartment list ─────────────────────────────────────────────── */}
      <div className="compartment-list" role="list">
        {compartments?.map((comp) => {
          const compKey    = String(comp.compartment_id)
          const cd         = draft?.compartments?.[compKey]
          const done       = cd?.status === 'complete'
          const noChange   = done && cd?.no_change === true
          const inProgress = cd?.status === 'in_progress'

          // Compartment-level par levels (for preview + No Change)
          const compPars = (parLevels ?? []).filter(
            pl => pl.compartment_id === comp.compartment_id && pl.active !== false
          )
          const hasPriorityItem  = compPars.some(pl => pl.priority_check === true)
          const damagedCount     = compPars.filter(pl => pl.is_damaged).length
          const noChangeBlocked  = comp.requires_full_check || hasPriorityItem || damagedCount > 0
          const noChangeBlockMsg = comp.requires_full_check ? 'Full check required'
                                 : hasPriorityItem          ? 'Has priority items'
                                 : damagedCount > 0         ? 'Has damaged items'
                                 : ''

          // Reading items: MEASUREMENT/FUNCTIONAL/DATE_RECORD, not flagged as priority,
          // and not in a requires_full_check compartment (those items show in Step 3 only).
          const readingPars = comp.requires_full_check ? [] : compPars.filter(pl =>
            READING_TYPES.has(itemMap[pl.item_id]?.check_type) && !pl.priority_check
          )
          const confirmedReadingIds = new Set(
            (cd?.line_items ?? [])
              .filter(li => li.confirmed && READING_TYPES.has(li.check_type))
              .map(li => li.item_id)
          )
          const allReadingsConfirmed = readingPars.length === 0 ||
            readingPars.every(pl => confirmedReadingIds.has(pl.item_id))

          // Preview: first 3 SUPPLY/DOCUMENT items (most meaningful for stock display)
          const supplyPars  = compPars.filter(pl => {
            const ct = itemMap[pl.item_id]?.check_type ?? 'SUPPLY'
            return ct === 'SUPPLY' || ct === 'DOCUMENT'
          })
          const previewPars = supplyPars.slice(0, 3)
          const hiddenCount = supplyPars.length - previewPars.length

          // Short count: items below par based on last check quantities.
          // Only non-zero when a previous check exists (lastQtyMap is empty otherwise).
          const shortCount = supplyPars.filter(pl =>
            lastQtyMap[pl.item_id] != null && lastQtyMap[pl.item_id] < pl.min_quantity
          ).length

          // Status for completed compartments
          const lineItems  = cd?.line_items ?? []
          const itemStatus = done || inProgress ? compartmentStatus(lineItems) : null
          const badgeStatus = itemStatus
            ? (itemStatus.severity === 'fail' ? 'FAIL'
              : itemStatus.severity === 'warn' ? 'NEEDS_RESTOCK'
              : 'PASS')
            : null

          if (noChange) {
            return (
              <div key={comp.compartment_id} id={`comp-${comp.compartment_id}`} role="listitem"
                className="compartment-card compartment-card--no-change">
                <div className="compartment-card__number compartment-card__number--done" aria-hidden="true">✓</div>
                <div className="compartment-card__info">
                  <div className="compartment-card__name">{comp.name}</div>
                  <div className="compartment-card__location" style={{ color: 'var(--color-no-change)' }}>
                    No Change confirmed
                  </div>
                </div>
                <button
                  className="btn btn--secondary compartment-card__undo-btn"
                  onClick={() => onUndoCompartment(comp.compartment_id)}
                  type="button"
                  aria-label={`Undo No Change for ${comp.name}`}
                >
                  Undo
                </button>
              </div>
            )
          }

          if (done) {
            return (
              <button
                key={comp.compartment_id}
                id={`comp-${comp.compartment_id}`}
                role="listitem"
                className="compartment-card compartment-card--done"
                onClick={() => onSelectCompartment(comp)}
                type="button"
                aria-label={`${comp.name}, done — ${itemStatus?.label ?? ''}`}
              >
                <div className="compartment-card__number compartment-card__number--done" aria-hidden="true">✓</div>
                <div className="compartment-card__info">
                  <div className="compartment-card__name">{comp.name}</div>
                  {comp.location_descriptor && (
                    <div className="compartment-card__location">{comp.location_descriptor}</div>
                  )}
                </div>
                <div className="compartment-card__status">
                  <StatusBadge status={badgeStatus} size="sm" />
                  <span className="compartment-card__chevron" aria-hidden="true">›</span>
                </div>
              </button>
            )
          }

          if (inProgress) {
            return (
              <button
                key={comp.compartment_id}
                id={`comp-${comp.compartment_id}`}
                role="listitem"
                className="compartment-card compartment-card--in-progress"
                onClick={() => onSelectCompartment(comp)}
                type="button"
                aria-label={`${comp.name}, in progress — ${itemStatus?.label ?? ''}`}
              >
                <div className="compartment-card__number" aria-hidden="true">…</div>
                <div className="compartment-card__info">
                  <div className="compartment-card__name">{comp.name}</div>
                  {comp.location_descriptor && (
                    <div className="compartment-card__location">{comp.location_descriptor}</div>
                  )}
                </div>
                <div className="compartment-card__status">
                  <div className="compartment-card__status-stack">
                    <StatusBadge status={badgeStatus} size="sm" />
                    <span className="compartment-card__in-progress-label">In progress</span>
                  </div>
                  <span className="compartment-card__chevron" aria-hidden="true">›</span>
                </div>
              </button>
            )
          }

          // Not started — show reading confirmations + preview + No Change / Modify
          return (
            <div key={comp.compartment_id} id={`comp-${comp.compartment_id}`} role="listitem" className="compartment-card compartment-card--actions">
              <div className="compartment-card__header-row">
                <div className="compartment-card__info">
                  <div className="compartment-card__name">{comp.name}</div>
                  {comp.location_descriptor && (
                    <div className="compartment-card__location">{comp.location_descriptor}</div>
                  )}
                  {comp.restriction_note && (
                    <div className="compartment-card__restriction" role="note">
                      ⚠ {comp.restriction_note}
                    </div>
                  )}
                  {damagedCount > 0 && (
                    <div className="compartment-card__damaged-badge" role="note">
                      ⚠ {damagedCount} damaged item{damagedCount !== 1 ? 's' : ''}
                    </div>
                  )}
                </div>
              </div>

              {/* ── Reading confirmations ───────────────────────────────── */}
              {readingPars.length > 0 && (
                <div className="reading-checks">
                  {readingPars.map(pl => {
                    const item      = itemMap[pl.item_id]
                    const checkType = item?.check_type ?? 'SUPPLY'
                    const last      = lastReadingMap[pl.item_id]
                    const draftItem = (cd?.line_items ?? []).find(li => li.item_id === pl.item_id)
                    const confirmed = draftItem?.confirmed === true
                    const isEditing = editingReadingId === pl.item_id

                    const confirmPayload = (overrides) => ({
                      item_id:           pl.item_id,
                      item_name:         item?.name ?? '',
                      check_type:        checkType,
                      quantity_needed:   pl.min_quantity,
                      quantity_found:    pl.min_quantity,
                      measurement_value: null,
                      functional_pass:   null,
                      date_value:        null,
                      notes:             null,
                      confirmed:         true,
                      ...overrides,
                    })

                    if (checkType === 'MEASUREMENT') {
                      const lastVal = last?.measurement_value
                      const currentVal = draftItem?.measurement_value
                      const displayVal = confirmed ? currentVal : lastVal
                      const minLabel = item?.measurement_minimum != null ? ` (min ${item.measurement_minimum})` : ''
                      return (
                        <div key={pl.par_id} className={`reading-row ${confirmed ? 'reading-row--confirmed' : ''}`}>
                          <div className="reading-row__info">
                            <span className="reading-row__name">{item?.name ?? `Item #${pl.item_id}`}</span>
                            {displayVal != null && !isEditing && (
                              <span className="reading-row__last">
                                {confirmed ? `✓ ${displayVal} ${item?.unit_of_measure ?? ''}` : `Last: ${displayVal}${minLabel}`}
                              </span>
                            )}
                            {!displayVal && !confirmed && !isEditing && (
                              <span className="reading-row__last reading-row__last--none">No previous reading</span>
                            )}
                          </div>
                          {isEditing ? (
                            <div className="reading-row__edit">
                              <input
                                className="reading-row__input"
                                type="number"
                                inputMode="decimal"
                                defaultValue={displayVal ?? ''}
                                id={`reading-edit-${pl.item_id}`}
                                autoFocus
                              />
                              <span className="reading-row__unit">{item?.unit_of_measure ?? ''}</span>
                              <button className="btn btn--primary btn--sm" type="button"
                                onClick={() => {
                                  const v = parseFloat(document.getElementById(`reading-edit-${pl.item_id}`)?.value)
                                  if (!isNaN(v)) {
                                    onConfirmReadingItem(comp, confirmPayload({ measurement_value: v }))
                                  }
                                  setEditingReadingId(null)
                                }}>Save</button>
                              <button className="btn btn--secondary btn--sm" type="button"
                                onClick={() => setEditingReadingId(null)}>Cancel</button>
                            </div>
                          ) : confirmed ? (
                            <button className="btn btn--secondary btn--sm reading-row__edit-btn" type="button"
                              onClick={() => { setEditValue(String(currentVal ?? '')); setEditingReadingId(pl.item_id) }}>
                              Edit
                            </button>
                          ) : lastVal != null ? (
                            <div className="reading-row__actions">
                              <button className="btn btn--secondary btn--sm" type="button"
                                onClick={() => onConfirmReadingItem(comp, confirmPayload({ measurement_value: lastVal }))}>
                                Same
                              </button>
                              <button className="btn btn--secondary btn--sm" type="button"
                                onClick={() => { setEditValue(''); setEditingReadingId(pl.item_id) }}>
                                Different
                              </button>
                            </div>
                          ) : (
                            <button className="btn btn--primary btn--sm" type="button"
                              onClick={() => { setEditValue(''); setEditingReadingId(pl.item_id) }}>
                              Enter
                            </button>
                          )}
                        </div>
                      )
                    }

                    if (checkType === 'FUNCTIONAL') {
                      const lastPass = last?.functional_pass
                      const curPass  = draftItem?.functional_pass
                      return (
                        <div key={pl.par_id} className={`reading-row ${confirmed ? 'reading-row--confirmed' : ''}`}>
                          <div className="reading-row__info">
                            <span className="reading-row__name">{item?.name ?? `Item #${pl.item_id}`}</span>
                            {lastPass != null && !confirmed && (
                              <span className="reading-row__last">Last: {lastPass ? 'Pass' : 'Fail'}</span>
                            )}
                            {confirmed && (
                              <span className={`reading-row__last ${curPass ? 'reading-row__last--pass' : 'reading-row__last--fail'}`}>
                                {curPass ? '✓ Pass' : '✗ Fail'}
                              </span>
                            )}
                          </div>
                          <div className="reading-row__actions">
                            <button
                              className={`btn btn--sm ${confirmed && curPass === true ? 'btn--primary' : 'btn--secondary'}`}
                              type="button"
                              onClick={() => onConfirmReadingItem(comp, confirmPayload({ functional_pass: true }))}
                            >Pass</button>
                            <button
                              className={`btn btn--sm ${confirmed && curPass === false ? 'btn--warn' : 'btn--secondary'}`}
                              type="button"
                              onClick={() => onConfirmReadingItem(comp, confirmPayload({ functional_pass: false }))}
                            >Fail</button>
                          </div>
                        </div>
                      )
                    }

                    if (checkType === 'DATE_RECORD') {
                      const lastDate = last?.date_value
                      return (
                        <div key={pl.par_id} className={`reading-row ${confirmed ? 'reading-row--confirmed' : ''}`}>
                          <div className="reading-row__info">
                            <span className="reading-row__name">{item?.name ?? `Item #${pl.item_id}`}</span>
                            {lastDate && !confirmed && (
                              <span className="reading-row__last">Last: {fmtDate(lastDate)} ({daysAgo(lastDate)})</span>
                            )}
                            {confirmed && (
                              <span className="reading-row__last reading-row__last--pass">✓ Confirmed today</span>
                            )}
                          </div>
                          <button
                            className={`btn btn--sm ${confirmed ? 'btn--secondary' : 'btn--primary'}`}
                            type="button"
                            onClick={() => onConfirmReadingItem(comp, confirmPayload({ date_value: TODAY }))}
                          >
                            {confirmed ? 'Re-confirm' : 'Confirm Today'}
                          </button>
                        </div>
                      )
                    }

                    if (checkType === 'EXPIRY_DATE') {
                      const lastDate  = last?.date_value
                      const curDate   = draftItem?.date_value
                      const isExpired = lastDate && new Date(lastDate + 'T00:00:00') < new Date()
                      return (
                        <div key={pl.par_id} className={`reading-row ${confirmed ? 'reading-row--confirmed' : ''}`}>
                          <div className="reading-row__info">
                            <span className="reading-row__name">{item?.name ?? `Item #${pl.item_id}`}</span>
                            {lastDate && !confirmed && (
                              <span className={`reading-row__last${isExpired ? ' reading-row__last--fail' : ''}`}>
                                Expiry: {fmtDate(lastDate)}{isExpired ? ' ⚠ EXPIRED' : ''}
                              </span>
                            )}
                            {!lastDate && !confirmed && (
                              <span className="reading-row__last reading-row__last--none">No expiry date on file</span>
                            )}
                            {confirmed && (
                              <span className="reading-row__last reading-row__last--pass">✓ Expiry: {fmtDate(curDate)}</span>
                            )}
                          </div>
                          {isEditing ? (
                            <div className="reading-row__edit">
                              <input
                                className="reading-row__input"
                                type="date"
                                defaultValue={curDate ?? lastDate ?? ''}
                                id={`reading-edit-${pl.item_id}`}
                                autoFocus
                              />
                              <button className="btn btn--primary btn--sm" type="button"
                                onClick={() => {
                                  const v = document.getElementById(`reading-edit-${pl.item_id}`)?.value
                                  if (v) onConfirmReadingItem(comp, confirmPayload({ date_value: v }))
                                  setEditingReadingId(null)
                                }}>Save</button>
                              <button className="btn btn--secondary btn--sm" type="button"
                                onClick={() => setEditingReadingId(null)}>Cancel</button>
                            </div>
                          ) : confirmed ? (
                            <button className="btn btn--secondary btn--sm reading-row__edit-btn" type="button"
                              onClick={() => setEditingReadingId(pl.item_id)}>Edit</button>
                          ) : lastDate ? (
                            <div className="reading-row__actions">
                              <button className="btn btn--secondary btn--sm" type="button"
                                onClick={() => onConfirmReadingItem(comp, confirmPayload({ date_value: lastDate }))}>
                                Same
                              </button>
                              <button className="btn btn--secondary btn--sm" type="button"
                                onClick={() => setEditingReadingId(pl.item_id)}>
                                Different
                              </button>
                            </div>
                          ) : (
                            <button className="btn btn--primary btn--sm" type="button"
                              onClick={() => setEditingReadingId(pl.item_id)}>
                              Enter date
                            </button>
                          )}
                        </div>
                      )
                    }

                    return null
                  })}
                </div>
              )}

              {previewPars.length > 0 && (
                <div className="compartment-card__preview">
                  {previewPars.map(pl => {
                    const qty     = lastQtyMap[pl.item_id]
                    const known   = qty != null
                    const isShort = known && qty < pl.min_quantity
                    return (
                      <div key={pl.par_id} className={`preview-row ${isShort ? 'preview-row--short' : ''}`}>
                        <span className="preview-row__name">{itemMap[pl.item_id]?.name ?? `Item #${pl.item_id}`}</span>
                        <span className="preview-row__stock">
                          {known
                            ? (isShort ? `↓ ${qty} / ${pl.min_quantity}` : `${qty} / ${pl.min_quantity}`)
                            : `— / ${pl.min_quantity}`}
                        </span>
                      </div>
                    )
                  })}
                  {hiddenCount > 0 && (
                    <div className="preview-row preview-row--more">
                      +{hiddenCount} more item{hiddenCount > 1 ? 's' : ''}
                    </div>
                  )}
                </div>
              )}

              <div className="compartment-card__action-row">
                {noChangeBlocked ? (
                  <div className="compartment-card__no-change-blocked">
                    {noChangeBlockMsg || 'No Change not available'}
                  </div>
                ) : (
                  <button
                    className="btn btn--secondary compartment-card__no-change-btn"
                    onClick={() => {
                      const lineItems = buildNoChangeLineItems(compPars, itemMap)
                      onNoChangeCompartment(comp, lineItems)
                    }}
                    disabled={!allReadingsConfirmed}
                    type="button"
                    aria-label={
                      allReadingsConfirmed
                        ? `No Change — attest all items at par for ${comp.name}`
                        : 'Confirm readings above first'
                    }
                  >
                    {allReadingsConfirmed ? 'No Change' : 'Confirm readings first'}
                  </button>
                )}
                <button
                  className={`btn compartment-card__modify-btn ${shortCount > 0 ? 'btn--warn' : 'btn--primary'}`}
                  onClick={() => onSelectCompartment(comp)}
                  type="button"
                  aria-label={`Open ${comp.name} to check items`}
                >
                  {shortCount > 0
                    ? `${shortCount} item${shortCount > 1 ? 's' : ''} short`
                    : 'Modify ›'}
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Sticky jump button — scrolls to first unchecked compartment */}
      {(() => {
        if (allDone) return null
        const firstUnchecked = compartments?.find(c =>
          draft?.compartments?.[String(c.compartment_id)]?.status !== 'complete'
        )
        if (!firstUnchecked) return null
        return (
          <button
            className="jump-btn"
            type="button"
            onClick={() =>
              document.getElementById(`comp-${firstUnchecked.compartment_id}`)
                ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
            }
          >
            Next unchecked: {firstUnchecked.name} →
          </button>
        )
      })()}

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
            ? 'Review flagged items →'
            : 'Review and Submit →'}
      </button>
    </div>
  )
}
