/**
 * shared/hooks/useDraft.js
 * localStorage draft save/resume/discard for daily inventory checks.
 *
 * Phase 5 change — multiple checks per day:
 *
 *   OLD key: ems_draft_{vehicleId}_{checkDate}
 *     → only one draft per vehicle per day; collides when a second check
 *       is started on the same day (post-call restock, shift-end check).
 *
 *   NEW key: ems_draft_{vehicleId}_{startedAt}
 *     → startedAt is an ISO timestamp generated at draft creation time
 *       (in index.jsx handleVehicleSelect). Each check gets a unique key
 *       regardless of how many happen on the same calendar day.
 *     → startedAt is also used as the submission timestamp so the DB record
 *       reflects when the check was started, not when Submit was tapped.
 *
 *   BACKWARDS COMPATIBILITY:
 *     Old drafts with the key format ems_draft_{vehicleId}_{YYYY-MM-DD} are
 *     still found by useDraftIndex (it scans all ems_draft_* keys). When
 *     HomePage passes the explicit draftKey from the index entry, useDraft
 *     uses it directly rather than reconstructing it — so old-format drafts
 *     remain resumable until they are submitted or discarded.
 *
 * useDraftIndex groups multiple drafts for the same vehicle/date into a
 * single DraftGroup object so the home screen can show one banner per
 * vehicle (with a count) rather than one banner per draft.
 *
 * IMPORTANT — compartment key type:
 *   Compartment IDs are numbers in JS but JSON.parse converts object keys to
 *   strings. All compartment lookups use String(compartmentId) so the key
 *   type is consistent whether the draft was just written or loaded from
 *   localStorage.
 */
import { useState, useCallback, useEffect, useRef } from 'react'

// ── Key construction ──────────────────────────────────────────────────────────

/**
 * Builds a draft key from vehicleId (or locationId for portable locations)
 * and a startedAt ISO timestamp.
 *
 * startedAt is generated at draft creation time in handleVehicleSelect so
 * it is consistent across all saves and used as the submission timestamp.
 */
export function draftKey(vehicleOrLocationId, startedAt) {
  return `ems_draft_${vehicleOrLocationId}_${startedAt}`
}

// ── useDraft ──────────────────────────────────────────────────────────────────

/**
 * @param {string|number|null} vehicleOrLocationId
 * @param {string|null}        startedAt  — ISO timestamp set at draft creation
 * @param {string|null}        explicitKey — when resuming an existing draft,
 *                                           pass the key directly so old-format
 *                                           keys are honoured without reconstruction
 */
export function useDraft(vehicleOrLocationId, startedAt, explicitKey = null) {
  // Use the explicit key when resuming; otherwise build from parts.
  const key = explicitKey
    ?? (vehicleOrLocationId && startedAt ? draftKey(vehicleOrLocationId, startedAt) : null)

  const [draft, setDraft]     = useState(() => _load(key))
  const [savedAt, setSavedAt] = useState(() => {
    const d = _load(key)
    return d?.saved_at ? new Date(d.saved_at) : null
  })

  const keyRef = useRef(key)
  useEffect(() => { keyRef.current = key }, [key])

  useEffect(() => {
    const loaded = _load(key)
    setDraft(loaded)
    setSavedAt(loaded?.saved_at ? new Date(loaded.saved_at) : null)
  }, [key])

  const saveDraft = useCallback((updates) => {
    if (!keyRef.current) return
    setDraft(prev => {
      const now  = new Date().toISOString()
      const next = { ...(prev ?? {}), ...updates, saved_at: now }
      _persist(keyRef.current, next)
      setSavedAt(new Date(now))
      return next
    })
  }, [])

  const saveLineItem = useCallback((compartmentId, compartmentMeta, lineItem) => {
    if (!keyRef.current) return
    const compKey = String(compartmentId)
    setDraft(prev => {
      const now              = new Date().toISOString()
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
      setSavedAt(new Date(now))
      return next
    })
  }, [])

  const discardDraft = useCallback(() => {
    if (!keyRef.current) return
    _remove(keyRef.current)
    setDraft(null)
    setSavedAt(null)
  }, [])

  const clearDraft = discardDraft

  return { draft, savedAt, hasDraft: draft !== null, saveDraft, saveLineItem, discardDraft, clearDraft }
}

// ── useDraftIndex ─────────────────────────────────────────────────────────────

/**
 * Returns all draft groups for the given station, grouped by vehicle/location
 * so the home screen can show one banner per vehicle with a count of how many
 * in-progress checks exist for that vehicle today.
 *
 * Each group shape:
 *   {
 *     groupKey:       string,           // "vehicle_{vehicleId}" or "location_{locationId}"
 *     selectionLabel: string,           // e.g. "Unit 712 BLS"
 *     checkDate:      string,           // most recent check_date in the group
 *     count:          number,           // number of in-progress drafts
 *     drafts: [
 *       { key: string, draft: object, savedAt: Date }
 *     ]
 *   }
 *
 * Sorted by most recently saved first within each group; groups sorted by
 * most recently saved draft.
 */
export function useDraftIndex(stationId = null) {
  const [groups, setGroups] = useState(() => _groupDrafts(stationId))

  useEffect(() => {
    setGroups(_groupDrafts(stationId))
    const handler = () => setGroups(_groupDrafts(stationId))
    window.addEventListener('storage', handler)
    return () => window.removeEventListener('storage', handler)
  }, [stationId])

  return groups
}

// ── localStorage helpers ──────────────────────────────────────────────────────

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

/**
 * Load all ems_draft_* keys, filter by station, and group by vehicle/location.
 */
function _groupDrafts(stationId = null) {
  try {
    const allEntries = Object.keys(localStorage)
      .filter(k => k.startsWith('ems_draft_'))
      .map(key => {
        const draft = _load(key)
        return draft ? { key, draft } : null
      })
      .filter(Boolean)
      .filter(({ draft }) =>
        stationId == null || draft.station_id === stationId
      )
      .sort((a, b) => {
        const aTime = a.draft.saved_at ?? ''
        const bTime = b.draft.saved_at ?? ''
        return bTime.localeCompare(aTime)
      })

    // Group by vehicle_id or location_id
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
      // Keep checkDate as the most recent date in the group
      if ((draft.check_date ?? '') > groupMap[gKey].checkDate) {
        groupMap[gKey].checkDate = draft.check_date ?? ''
      }
    }

    // Sort groups by most recently saved draft
    return Object.values(groupMap).sort((a, b) => {
      const aTime = a.drafts[0]?.draft.saved_at ?? ''
      const bTime = b.drafts[0]?.draft.saved_at ?? ''
      return bTime.localeCompare(aTime)
    })
  } catch { return [] }
}
