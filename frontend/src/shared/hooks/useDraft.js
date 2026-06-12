/**
 * shared/hooks/useDraft.js
 * localStorage draft save/resume/discard for daily inventory checks.
 *
 * Drafts are station-scoped, not person-scoped. Any responder logged in
 * at the same station on the same device can see and resume an in-progress
 * check. This models real EMS shift handoffs — if one responder starts a
 * check at 7pm and a coworker comes on shift, they can pick it up and
 * file it without starting over.
 *
 * Draft visibility rules:
 *   - Show only drafts for the currently selected station.
 *   - When no station is selected (still loading), show nothing — we cannot
 *     know which station the user is at yet.
 *   - Legacy drafts with no station_id are shown when any station is active
 *     so they are not silently lost.
 *
 * TODO (F-UX-DRAFT-1 / F-UX35): RESOLVED — station_id type-coercion fix applied
 * and last-known station cached in localStorage as fallback during API load.
 */
import { useState, useCallback, useEffect, useRef } from 'react'

export function draftKey(vehicleOrLocationId, startedAt) {
  return `ems_draft_${vehicleOrLocationId}_${startedAt}`
}

// Internal broadcast so same-tab writes are visible to useDraftIndex.
// We can't use the native 'storage' event (browsers suppress it for the
// originating tab), so we use a tiny EventTarget instead.
const _draftBus = new EventTarget()
function _notifyDraftChanged() {
  _draftBus.dispatchEvent(new Event('change'))
}

export function useDraft(vehicleOrLocationId, startedAt, explicitKey = null) {
  const key = explicitKey
    ?? (vehicleOrLocationId && startedAt ? draftKey(vehicleOrLocationId, startedAt) : null)

  // Keep a ref that is ALWAYS current so callbacks never close over a stale key.
  const keyRef = useRef(key)
  useEffect(() => { keyRef.current = key }, [key])

  const [draft, setDraft]     = useState(() => _load(key))
  const [savedAt, setSavedAt] = useState(() => {
    const d = _load(key)
    return d?.saved_at ? new Date(d.saved_at) : null
  })

  // Mirror of draft state in a ref so write callbacks always see the latest
  // value without needing the functional-updater form (which runs in render).
  const draftRef = useRef(draft)

  useEffect(() => {
    const loaded = _load(key)
    draftRef.current = loaded
    setDraft(loaded)
    setSavedAt(loaded?.saved_at ? new Date(loaded.saved_at) : null)
  }, [key])

  const saveDraft = useCallback((updates, overrideKey = null) => {
    const k = overrideKey ?? keyRef.current
    if (!k) return
    const now  = new Date().toISOString()
    const next = { ...(draftRef.current ?? {}), ...updates, saved_at: now }
    _persist(k, next)
    if (k !== keyRef.current) keyRef.current = k
    draftRef.current = next
    setDraft(next)
    setSavedAt(new Date(now))
    _notifyDraftChanged()
  }, [])

  const saveLineItem = useCallback((compartmentId, compartmentMeta, lineItem) => {
    if (!keyRef.current) return
    const compKey = String(compartmentId)
    const now              = new Date().toISOString()
    const prev             = draftRef.current
    const prevCompartments = prev?.compartments ?? {}
    const prevComp         = prevCompartments[compKey] ?? {
      compartment_id:    compartmentId,
      name:              compartmentMeta.name,
      status:            'not_started',
      compartment_notes: '',
      line_items:        [],
    }
    const prevItems   = prevComp.line_items ?? []
    const existingIdx = prevItems.findIndex(li => li.item_id === lineItem.item_id)
    const nextItems   = existingIdx >= 0
      ? prevItems.map((li, i) => i === existingIdx ? { ...li, ...lineItem } : li)
      : [...prevItems, lineItem]
    const nextComp = { ...prevComp, ...compartmentMeta, line_items: nextItems }
    const next = {
      ...(prev ?? {}),
      saved_at: now,
      compartments: { ...prevCompartments, [compKey]: nextComp },
    }
    _persist(keyRef.current, next)
    draftRef.current = next
    setDraft(next)
    setSavedAt(new Date(now))
    _notifyDraftChanged()
  }, [])

  const discardDraft = useCallback(() => {
    if (!keyRef.current) return
    _remove(keyRef.current)
    draftRef.current = null
    setDraft(null)
    setSavedAt(null)
    _notifyDraftChanged()
  }, [])

  const clearDraft = discardDraft

  return { draft, savedAt, hasDraft: draft !== null, saveDraft, saveLineItem, discardDraft, clearDraft, draftRef }
}

const LAST_STATION_KEY = 'ems_last_station_id'

/**
 * useDraftIndex — returns all draft groups for the selected station.
 *
 * Station-scoped: only shows drafts for the currently selected station.
 * Any responder at the station on this device can resume any draft.
 *
 * F-UX35: While the station API is loading (stationId is null), falls back
 * to the last known station_id from localStorage so drafts are visible
 * immediately on page load rather than being hidden during the API round-trip.
 */
export function useDraftIndex(stationId = null) {
  // F-UX35: persist last known station so drafts show during API loading
  useEffect(() => {
    if (stationId != null) {
      try { localStorage.setItem(LAST_STATION_KEY, String(stationId)) } catch { /* ignore */ }
    }
  }, [stationId])

  // Derive effectiveId reactively so the effect below re-runs whenever it changes.
  const effectiveId = stationId != null
    ? String(stationId)
    : (() => { try { return localStorage.getItem(LAST_STATION_KEY) } catch { return null } })()

  const [groups, setGroups] = useState(() => _groupDrafts(effectiveId))

  useEffect(() => {
    // Re-read immediately when effectiveId changes (station selected, etc.)
    setGroups(_groupDrafts(effectiveId))

    // Listen to same-tab draft writes via our internal bus
    const onBusChange = () => setGroups(_groupDrafts(effectiveId))
    _draftBus.addEventListener('change', onBusChange)

    // Also listen to cross-tab writes via native storage event
    const onStorage = () => setGroups(_groupDrafts(effectiveId))
    window.addEventListener('storage', onStorage)

    return () => {
      _draftBus.removeEventListener('change', onBusChange)
      window.removeEventListener('storage', onStorage)
    }
  }, [effectiveId])

  return groups
}

function _load(key) {
  if (!key) return null
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

function _persist(key, data) {
  if (!key) return
  try {
    localStorage.setItem(key, JSON.stringify(data))
  } catch (e) {
    console.warn('[useDraft] localStorage write failed:', e)
  }
}

function _remove(key) {
  if (!key) return
  try { localStorage.removeItem(key) } catch { /* ignore */ }
}

function _groupDrafts(stationId = null) {
  // Cannot show station-scoped drafts without knowing which station
  if (stationId == null) return []

  try {
    const allEntries = Object.keys(localStorage)
      .filter(k => k.startsWith('ems_draft_'))
      .map(key => {
        const draft = _load(key)
        return draft ? { key, draft } : null
      })
      .filter(Boolean)
      .filter(({ draft }) =>
        // Use string coercion to avoid type mismatch (API returns number, draft may store string)
        // Also surface legacy drafts with no station_id so they are never silently lost
        String(draft.station_id) === String(stationId) || !draft.station_id
      )
      .sort((a, b) => {
        const aTime = a.draft.saved_at ?? ''
        const bTime = b.draft.saved_at ?? ''
        return bTime.localeCompare(aTime)
      })

    const groupMap = {}
    for (const entry of allEntries) {
      const { draft, key } = entry
      const gKey = draft.vehicle_id
        ? `vehicle_${draft.vehicle_id}`
        : draft.location_id
          ? `location_${draft.location_id}`
          : `unknown_${key}`

      if (!groupMap[gKey]) {
        groupMap[gKey] = {
          groupKey:       gKey,
          selectionLabel: draft.selection_label ?? (draft.vehicle_id ? `Vehicle #${draft.vehicle_id}` : 'Check'),
          checkDate:      draft.check_date ?? '',
          count:          0,
          drafts:         [],
        }
      }
      groupMap[gKey].count++
      groupMap[gKey].drafts.push({
        key,
        draft,
        savedAt: draft.saved_at ? new Date(draft.saved_at) : null,
      })
      if ((draft.check_date ?? '') > groupMap[gKey].checkDate) {
        groupMap[gKey].checkDate = draft.check_date ?? ''
      }
    }

    return Object.values(groupMap).sort((a, b) => {
      const aTime = a.drafts[0]?.draft.saved_at ?? ''
      const bTime = b.drafts[0]?.draft.saved_at ?? ''
      return bTime.localeCompare(aTime)
    })
  } catch { return [] }
}
