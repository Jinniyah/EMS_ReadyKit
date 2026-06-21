/**
 * supply-room/components/SupplyCatalogView.jsx
 * SR-F3: View Supplies — catalog from SR-B1, inline count correction (SR-B2).
 * SR-F7: Inline lot expiry correction via PUT /inventory/lots/{id}.
 * DMG-F3: Damaged items show ⚠ badge.
 * SS-F2: Supervisor+ sees "+ Add Item" per shelf section.
 *
 * Responders: view only (no count or expiry editing).
 * Supervisors+: tap item → count correction + lot expiry editing.
 */
import React, { useState } from 'react'
import { supplyApi } from '../api/supplyApi.js'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { canAccess } from '../../../shared/utils/roleGuard.js'
import CompartmentParLevels from '../../admin/components/CompartmentParLevels.jsx'

function itemColor(item) {
  if (item.on_hand === 0) return 'out'
  if (item.par_min != null && item.on_hand < item.par_min) return 'low'
  return 'ok'
}

function formatExpiry(isoDate) {
  if (!isoDate) return 'No expiry'
  return new Date(isoDate + 'T12:00:00').toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

export default function SupplyCatalogView({ stationId, locationId, items, loading, error, onRefresh }) {
  const { user, getToken } = useAuth()
  const isSupervisor = canAccess(user, 'supervisor')

  // Group items by shelf/compartment for SS-F2
  function groupByShelf(itemList) {
    const shelves = new Map()
    const uncatalogued = []
    for (const item of itemList) {
      if (item.compartment_id != null) {
        if (!shelves.has(item.compartment_id)) {
          shelves.set(item.compartment_id, { id: item.compartment_id, name: item.compartment_name, items: [] })
        }
        shelves.get(item.compartment_id).items.push(item)
      } else {
        uncatalogued.push(item)
      }
    }
    const groups = [...shelves.values()]
    if (uncatalogued.length) groups.push({ id: null, name: null, items: uncatalogued })
    return groups
  }

  // Count correction state
  const [expandedId, setExpandedId]   = useState(null)
  const [editQty, setEditQty]         = useState('')
  const [editComment, setEditComment] = useState('')
  const [saving, setSaving]           = useState(false)
  const [saveError, setSaveError]     = useState(null)

  // Lot expiry editing state (SR-F7)
  const [lotEditId, setLotEditId]     = useState(null)
  const [lotExpiry, setLotExpiry]     = useState('')
  const [lotSaving, setLotSaving]     = useState(false)
  const [lotError, setLotError]       = useState(null)

  // Lot retirement state (RET-F3)
  const [retireLotId, setRetireLotId]   = useState(null)
  const [retireReason, setRetireReason] = useState('')
  const [retireSaving, setRetireSaving] = useState(false)
  const [retireError, setRetireError]   = useState(null)

  // Search + filter state
  const [searchQuery, setSearchQuery] = useState('')
  const [activeChip, setActiveChip]   = useState('all') // 'all' | 'out' | 'low' | 'damaged'

  const hasDamagedItems = (items ?? []).some(i => i.is_damaged)
  const outCount        = (items ?? []).filter(i => i.on_hand === 0).length
  const lowCount        = (items ?? []).filter(i => i.on_hand > 0 && i.par_min != null && i.on_hand < i.par_min).length
  const damagedCount    = (items ?? []).filter(i => i.is_damaged).length

  const q = searchQuery.trim().toLowerCase()
  const filteredItems = (items ?? []).filter(item => {
    const matchesSearch  = !q || item.item_name.toLowerCase().includes(q)
    const matchesChip    =
      activeChip === 'all'     ? true :
      activeChip === 'out'     ? item.on_hand === 0 :
      activeChip === 'low'     ? item.on_hand > 0 && item.par_min != null && item.on_hand < item.par_min :
      activeChip === 'damaged' ? item.is_damaged :
      true
    return matchesSearch && matchesChip
  })
  const isSearching = q.length > 0 || activeChip !== 'all'

  if (loading) {
    return <div className="sr-center">Loading supplies…</div>
  }
  if (error) {
    return (
      <div className="sr-error">
        <strong>Could not load supplies</strong>
        <p style={{ margin: '4px 0 8px' }}>{error}</p>
        <button className="btn btn--secondary" onClick={onRefresh} type="button">Retry</button>
      </div>
    )
  }
  if (!items?.length) {
    return (
      <div className="sr-center">
        No supply items configured. Ask an administrator to add items to the catalog.
      </div>
    )
  }

  function handleTap(itemId) {
    if (!isSupervisor) return
    if (expandedId === itemId) {
      setExpandedId(null)
      setEditQty('')
      setEditComment('')
      setSaveError(null)
      setLotEditId(null)
      setLotError(null)
    } else {
      const item = items.find(i => i.item_id === itemId)
      setExpandedId(itemId)
      setEditQty(String(item?.on_hand ?? ''))
      setEditComment('')
      setSaveError(null)
      setLotEditId(null)
      setLotError(null)
    }
  }

  async function handleSaveCount(item) {
    const qty = parseInt(editQty, 10)
    if (isNaN(qty) || qty < 0) {
      setSaveError('Enter a whole number (0 or more).')
      return
    }
    setSaving(true)
    setSaveError(null)
    try {
      await supplyApi.patchCount(
        item.item_id,
        { location_id: locationId, quantity: qty, comment: editComment || null },
        getToken,
      )
      setExpandedId(null)
      setEditQty('')
      setEditComment('')
      onRefresh()
    } catch (e) {
      setSaveError(e.message ?? 'Could not save. Try again.')
    } finally {
      setSaving(false)
    }
  }

  function handleEditLot(lot) {
    setLotEditId(lot.lot_id)
    setLotExpiry(lot.expiration_date ?? '')
    setLotError(null)
  }

  async function handleSaveLotExpiry(lot) {
    setLotSaving(true)
    setLotError(null)
    try {
      await supplyApi.putLot(
        lot.lot_id,
        { expiration_date: lotExpiry || null },
        getToken,
      )
      setLotEditId(null)
      onRefresh()
    } catch (e) {
      setLotError(e.message ?? 'Could not save. Try again.')
    } finally {
      setLotSaving(false)
    }
  }

  async function handleRetireLot() {
    if (!retireReason.trim()) return
    setRetireSaving(true)
    setRetireError(null)
    try {
      await supplyApi.retireLot(retireLotId, retireReason, getToken)
      setRetireLotId(null)
      setRetireReason('')
      onRefresh()
    } catch (e) {
      setRetireError(e.message ?? 'Could not retire lot. Try again.')
    } finally {
      setRetireSaving(false)
    }
  }

  const shelves = isSearching
    ? [{ id: '__search__', name: null, items: filteredItems }]
    : groupByShelf(filteredItems)

  return (
    <div className="sr-catalog">
      {/* Search bar */}
      <div className="sr-catalog-search">
        <input
          className="sr-catalog-search__input"
          type="search"
          placeholder="Search items…"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          aria-label="Search supply items"
        />
        {q && (
          <span className="sr-catalog-search__count" aria-live="polite">
            {filteredItems.length} result{filteredItems.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>
      {/* Filter chips */}
      <div className="sr-catalog-chips" role="group" aria-label="Filter items">
        {[
          { id: 'all',     label: 'All',     count: (items ?? []).length },
          { id: 'out',     label: 'Out',     count: outCount,     hide: outCount === 0 },
          { id: 'low',     label: 'Low',     count: lowCount,     hide: lowCount === 0 },
          { id: 'damaged', label: 'Damaged', count: damagedCount, hide: !hasDamagedItems },
        ].filter(c => !c.hide).map(chip => (
          <button
            key={chip.id}
            className={`sr-catalog-chip ${
              activeChip === chip.id ? 'sr-catalog-chip--active' : ''
            } ${
              chip.id === 'out'     ? 'sr-catalog-chip--out'     :
              chip.id === 'low'     ? 'sr-catalog-chip--low'     :
              chip.id === 'damaged' ? 'sr-catalog-chip--damaged'  : ''
            }`}
            onClick={() => setActiveChip(chip.id)}
            type="button"
            aria-pressed={activeChip === chip.id}
          >
            {chip.label}
            <span className="sr-catalog-chip__count">{chip.count}</span>
          </button>
        ))}
      </div>
      {/* RET-F3: Lot retirement confirmation sheet */}
      {retireLotId && (
        <div className="ems-confirm-overlay" role="dialog" aria-modal="true">
          <div className="ems-confirm-sheet">
            <p className="ems-confirm-sheet__title">Dispose this lot?</p>
            <p className="ems-confirm-sheet__desc">
              This marks the lot as retired and sets its quantity to zero.
              Record the reason (e.g. "Expired — disposed per protocol").
            </p>
            <textarea
              placeholder="Reason (required)"
              value={retireReason}
              onChange={e => setRetireReason(e.target.value)}
              maxLength={500}
            />
            {retireError && (
              <p className="ems-confirm-sheet__error">{retireError}</p>
            )}
            <div className="ems-confirm-sheet__actions">
              <button
                className="ems-confirm-sheet__cancel"
                onClick={() => { setRetireLotId(null); setRetireReason(''); setRetireError(null) }}
                type="button"
              >
                Cancel
              </button>
              <button
                className="ems-confirm-sheet__confirm"
                onClick={handleRetireLot}
                disabled={!retireReason.trim() || retireSaving}
                type="button"
              >
                {retireSaving ? 'Disposing…' : 'Dispose Lot'}
              </button>
            </div>
          </div>
        </div>
      )}
      {filteredItems.length === 0 && (
        <div className="sr-center">
          {q ? `No items match "${searchQuery}"` : 'No items match the current filter.'}
        </div>
      )}
      {shelves.map(shelf => (
        <div key={shelf.id ?? 'uncatalogued'} className="sr-catalog-shelf">
          {shelf.name && (
            <div className="sr-catalog-shelf__heading">{shelf.name}</div>
          )}
          {shelf.items.map(item => {
        const color    = itemColor(item)
        const expanded = expandedId === item.item_id
        const lots     = item.lots ?? []

        return (
          <div
            key={item.item_id}
            className={`sr-catalog-item sr-catalog-item--${color}`}
          >
            {/* ── Row header ─────────────────────────────────────────────── */}
            <button
              className="sr-catalog-item__header"
              onClick={() => handleTap(item.item_id)}
              type="button"
              aria-expanded={isSupervisor ? expanded : undefined}
              disabled={!isSupervisor}
              style={{ cursor: isSupervisor ? 'pointer' : 'default' }}
            >
              <div className="sr-catalog-item__name">
                {item.item_name}
                {item.is_damaged && (
                  <span className="sr-catalog-item__damaged" aria-label="Item marked damaged">
                    {' '}⚠ Damaged
                  </span>
                )}
              </div>
              <div className="sr-catalog-item__qty-block">
                <span className={`sr-catalog-item__qty sr-catalog-item__qty--${color}`}>
                  {item.on_hand}
                </span>
                {item.par_min != null ? (
                  <span className="sr-catalog-item__par">
                    / {item.par_min} {item.unit_of_measure}
                  </span>
                ) : (
                  <span className="sr-catalog-item__par">{item.unit_of_measure}</span>
                )}
                {isSupervisor && (
                  <span className="sr-catalog-item__edit-hint" aria-hidden="true">
                    {expanded ? '▲' : '✎'}
                  </span>
                )}
              </div>
            </button>

            {/* ── Expanded: count correction + lot list ──────────────────── */}
            {expanded && isSupervisor && (
              <div className="sr-catalog-item__editor">

                {/* Count correction (SR-F3 / SR-B2) */}
                <label className="sr-catalog-item__editor-label">
                  Correct count for {item.item_name}
                </label>
                <div className="sr-catalog-item__editor-row">
                  <input
                    className="sr-catalog-item__editor-input"
                    type="number"
                    min="0"
                    step="1"
                    value={editQty}
                    onChange={e => setEditQty(e.target.value)}
                    aria-label={`New count for ${item.item_name}`}
                    autoFocus
                  />
                  <span className="sr-catalog-item__editor-unit">{item.unit_of_measure}</span>
                </div>
                <input
                  className="sr-catalog-item__editor-comment"
                  type="text"
                  placeholder="Reason (optional)"
                  maxLength={500}
                  value={editComment}
                  onChange={e => setEditComment(e.target.value)}
                  aria-label="Reason for count correction"
                />
                {saveError && (
                  <div className="sr-catalog-item__editor-error">{saveError}</div>
                )}
                <div className="sr-catalog-item__editor-actions">
                  <button
                    className="btn btn--secondary btn--sm"
                    onClick={() => { setExpandedId(null); setSaveError(null) }}
                    type="button"
                    disabled={saving}
                  >
                    Cancel
                  </button>
                  <button
                    className="btn btn--primary"
                    onClick={() => handleSaveCount(item)}
                    type="button"
                    disabled={saving}
                  >
                    {saving ? 'Saving…' : 'Save Count'}
                  </button>
                </div>

                {/* Lot list with expiry editing (SR-F7) */}
                {lots.length > 0 && (
                  <div className="sr-lot-list">
                    <div className="sr-lot-list__heading">Stock lots</div>
                    {lots.map(lot => {
                      const editingThis = lotEditId === lot.lot_id
                      return (
                        <div key={lot.lot_id} className="sr-lot-row">
                          <div className="sr-lot-row__info">
                            <span className="sr-lot-row__qty">{lot.quantity}</span>
                            {lot.lot_number && (
                              <span className="sr-lot-row__num">Lot {lot.lot_number}</span>
                            )}
                            {!editingThis && (
                              <span className="sr-lot-row__expiry">
                                {formatExpiry(lot.expiration_date)}
                              </span>
                            )}
                          </div>

                          {!editingThis ? (
                            <div style={{ display: 'flex', gap: 'var(--space-xs)', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                              <button
                                className="sr-lot-row__edit-btn"
                                onClick={() => handleEditLot(lot)}
                                type="button"
                                aria-label={`Correct expiry date for lot ${lot.lot_number ?? lot.lot_id}`}
                              >
                                Correct expiry
                              </button>
                              <button
                                className="sr-lot-row__edit-btn"
                                style={{ color: 'var(--color-danger)', borderColor: 'var(--color-danger)' }}
                                onClick={() => { setRetireLotId(lot.lot_id); setRetireReason(''); setRetireError(null) }}
                                type="button"
                                aria-label={`Dispose lot ${lot.lot_number ?? lot.lot_id}`}
                              >
                                Dispose
                              </button>
                            </div>
                          ) : (
                            <div className="sr-lot-row__expiry-editor">
                              <input
                                type="date"
                                className="sr-lot-row__date-input"
                                value={lotExpiry}
                                onChange={e => setLotExpiry(e.target.value)}
                                aria-label="Corrected expiry date"
                              />
                              {lotError && (
                                <div className="sr-catalog-item__editor-error">{lotError}</div>
                              )}
                              <div className="sr-catalog-item__editor-actions">
                                <button
                                  className="btn btn--secondary btn--sm"
                                  onClick={() => { setLotEditId(null); setLotError(null) }}
                                  type="button"
                                  disabled={lotSaving}
                                >
                                  Cancel
                                </button>
                                <button
                                  className="btn btn--primary btn--sm"
                                  onClick={() => handleSaveLotExpiry(lot)}
                                  type="button"
                                  disabled={lotSaving}
                                >
                                  {lotSaving ? 'Saving…' : 'Save Date'}
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}

              </div>
            )}
          </div>
        )
      })}

          {/* SS-F2: Add item to this shelf — hidden during search */}
          {isSupervisor && shelf.id != null && !isSearching && (
            <CompartmentParLevels
              compartmentId={shelf.id}
              locationId={locationId}
              stationId={stationId}
            />
          )}
        </div>
      ))}
    </div>
  )
}
