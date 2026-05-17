/**
 * shared/hooks/useDraft.js
 * localStorage draft save/resume/discard for daily inventory checks.
 *
 * IMPORTANT — compartment key type:
 *   Compartment IDs are numbers in JS but JSON.parse converts object keys to
 *   strings. All compartment lookups use String(compartmentId) so the key type
 *   is consistent whether the draft was just written or loaded from localStorage.
 */
import { useState, useCallback, useEffect, useRef } from 'react'

export function draftKey(vehicleId, checkDate) {
  return `ems_draft_${vehicleId}_${checkDate}`
}

export function useDraft(vehicleId, checkDate) {
  const key = vehicleId && checkDate ? draftKey(vehicleId, checkDate) : null

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
    // Always use String key — JSON.parse turns numeric object keys into strings,
    // so using a number key after a localStorage round-trip would miss the data.
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
export function useDraftIndex(stationId = null) {
  const [drafts, setDrafts] = useState(() => _listAllDrafts(stationId))

  useEffect(() => {
    setDrafts(_listAllDrafts(stationId))
    const handler = () => setDrafts(_listAllDrafts(stationId))
    window.addEventListener('storage', handler)
    return () => window.removeEventListener('storage', handler)
  }, [stationId])

  return drafts
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

function _listAllDrafts(stationId = null) {
  try {
    return Object.keys(localStorage)
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
  } catch { return [] }
}
