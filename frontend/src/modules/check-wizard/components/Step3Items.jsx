/**
 * modules/check-wizard/components/Step3Items.jsx
 *
 * Every ItemRow interaction writes directly to the draft immediately.
 * "Touched" = draftItem exists (any interaction was recorded).
 * "Confirmed" = draftItem.confirmed = true (Submit count or All present tapped).
 *
 * Save compartment button unlocks when every item has been touched
 * (draftItem !== null). It does NOT require confirmed=true.
 *
 * "Save compartment" is the ONLY navigation trigger — there is NO auto-save.
 * confirmed is a pure UI display flag with zero effect on navigation.
 */
import React, { useMemo, useCallback, useEffect, useState } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import { checkApi } from '../api/checkApi.js'
import ItemRow from './ItemRow.jsx'
import Spinner from '../../../shared/components/Spinner.jsx'

export default function Step3Items({
  compartment,
  locationId,
  allCompartments,
  draft,
  onUpdateItem,
  onSaveCompartment,
  onNavigateCompartment,
  onBackToList,
}) {
  const { getToken } = useAuth()

  const { data: parLevels,  isLoading: loadingPar  } = useApi(
    () => checkApi.getParLevels(locationId, getToken), [locationId]
  )
  const { data: stockLots,  isLoading: loadingLots } = useApi(
    () => checkApi.getStockLots(locationId, getToken), [locationId]
  )
  const { data: items,      isLoading: loadingItems } = useApi(
    () => checkApi.getItems(getToken), []
  )

  const isLoading = loadingPar || loadingLots || loadingItems

  const compartmentPars = useMemo(() =>
    (parLevels ?? []).filter(pl => pl.compartment_id === compartment.compartment_id),
    [parLevels, compartment.compartment_id]
  )

  const itemMap = useMemo(() =>
    Object.fromEntries((items ?? []).map(it => [it.item_id, it])),
    [items]
  )
  const lotMap = useMemo(() => {
    const map = {}
    for (const lot of stockLots ?? []) {
      if (!map[lot.item_id]) map[lot.item_id] = lot
    }
    return map
  }, [stockLots])

  // String key — consistent after JSON localStorage round-trip
  const compKey = String(compartment.compartment_id)
  const cd      = draft?.compartments?.[compKey]

  const lineItemDraftMap = useMemo(() => {
    const map = {}
    for (const li of cd?.line_items ?? []) map[li.item_id] = li
    return map
  }, [cd])

  // ── Touched tracking ──────────────────────────────────────────────────────
  // touchedIds tracks items interacted with this session before they appear
  // in the draft. Once draftItem exists, lineItemDraftMap is the truth.
  const [touchedIds, setTouchedIds] = useState(() => new Set())

  // Reset local touched tracking when entering a new compartment
  useEffect(() => { setTouchedIds(new Set()) }, [compartment.compartment_id])

  const handleItemTouched = useCallback((itemId) => {
    setTouchedIds(prev => {
      if (prev.has(itemId)) return prev
      const next = new Set(prev)
      next.add(itemId)
      return next
    })
  }, [])

  // ── All touched: every item has a draftItem OR was touched this session ───
  const allTouched = compartmentPars.length > 0 &&
    compartmentPars.every(pl =>
      lineItemDraftMap[pl.item_id] !== undefined || touchedIds.has(pl.item_id)
    )

  const untouchedCount = compartmentPars.filter(
    pl => lineItemDraftMap[pl.item_id] === undefined && !touchedIds.has(pl.item_id)
  ).length

  // ── Compartment navigation ────────────────────────────────────────────────
  const currentIdx = allCompartments.findIndex(c => c.compartment_id === compartment.compartment_id)
  const prevComp   = currentIdx > 0 ? allCompartments[currentIdx - 1] : null
  const nextComp   = currentIdx < allCompartments.length - 1 ? allCompartments[currentIdx + 1] : null

  const handleUpdateItem = useCallback((payload) => {
    onUpdateItem(compartment.compartment_id, payload)
    handleItemTouched(payload.item_id)
  }, [compartment.compartment_id, onUpdateItem, handleItemTouched])

  const handleSave = useCallback(() => {
    onSaveCompartment(compartment.compartment_id)
  }, [compartment.compartment_id, onSaveCompartment])

  if (isLoading) return <Spinner label="Loading items…" />

  const saveButtonLabel  = allTouched
    ? nextComp ? `Next — ${nextComp.name}` : `Done — ${compartment.name}`
    : `${untouchedCount} remaining`
  const saveButtonActive = allTouched

  return (
    <div className="wizard-step">
      {/* Compartment nav header */}
      <div className="step3-header">
        <button
          className="step3-header__nav-btn"
          onClick={() => prevComp && onNavigateCompartment(prevComp)}
          disabled={!prevComp}
          type="button"
          aria-label={prevComp ? `Go to ${prevComp.name}` : 'No previous compartment'}
        >‹</button>

        <div className="step3-header__info">
          <h2 className="step3-header__name">{compartment.name}</h2>
          {compartment.location_descriptor && (
            <p className="step3-header__location">{compartment.location_descriptor}</p>
          )}
          {compartment.restriction_note && (
            <p className="step3-header__restriction" role="alert">
              ⚠ {compartment.restriction_note}
            </p>
          )}
          <p className="step3-header__count">
            {compartment.als_only && <span className="badge badge--als">ALS only</span>}
            {compartmentPars.length} item{compartmentPars.length !== 1 ? 's' : ''}
          </p>
        </div>

        <button
          className="step3-header__nav-btn"
          onClick={() => nextComp && onNavigateCompartment(nextComp)}
          disabled={!nextComp}
          type="button"
          aria-label={nextComp ? `Go to ${nextComp.name}` : 'No next compartment'}
        >›</button>
      </div>

      {untouchedCount > 0 && (
        <div className="step3-unchecked" role="status" aria-live="polite">
          {untouchedCount} item{untouchedCount !== 1 ? 's' : ''} not yet reviewed
        </div>
      )}

      {compartmentPars.length === 0 ? (
        <div className="step3-empty">
          <p>No items configured for this compartment.</p>
          <button className="btn btn--secondary" onClick={handleSave} type="button">
            Mark complete and continue
          </button>
        </div>
      ) : (
        <div className="item-list">
          {compartmentPars.map(pl => {
            const item = itemMap[pl.item_id]
            if (!item) return null
            return (
              <ItemRow
                key={pl.item_id}
                item={item}
                parLevel={pl}
                lot={lotMap[pl.item_id] ?? null}
                draftItem={lineItemDraftMap[pl.item_id] ?? null}
                onUpdate={handleUpdateItem}
                onTouched={handleItemTouched}
              />
            )
          })}
        </div>
      )}

      {/* Footer — always visible. Save compartment is the ONLY navigation trigger. */}
      <div className="step3-footer">
        <button className="btn btn--secondary" onClick={onBackToList} type="button">
          ← Back
        </button>
        <button
          className="btn btn--primary"
          onClick={saveButtonActive ? handleSave : undefined}
          disabled={!saveButtonActive}
          type="button"
        >
          {saveButtonLabel}
        </button>
      </div>
    </div>
  )
}
