/**
 * modules/admin/components/ItemCatalog.jsx
 *
 * Item catalog browser with typeahead search, cabinet-group filter chips,
 * active/inactive toggle, and add/edit form.
 *
 * UX principles (tired crew / end-of-shift user):
 *   - Items shown as large, easy-to-read cards — not a table
 *   - Search bar at top — type to filter instantly client-side
 *   - Cabinet filter chips below search — one tap to narrow by physical location
 *   - Each card shows the essential fields at a glance:
 *       name · category badge · check type · unit
 *   - Edit button on each card — one tap to enter edit mode
 *   - "Add item" is a prominent button at the top, not buried
 *   - No pagination — all active items load once, filtered in memory
 */

import React, { useState, useMemo } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import { canAccess } from '../../../shared/utils/roleGuard.js'
import Spinner from '../../../shared/components/Spinner.jsx'
import ErrorBoundary from '../../../shared/components/ErrorBoundary.jsx'
import ItemForm from './ItemForm.jsx'
import ItemAssignments from './ItemAssignments.jsx'
import CsvImport from './CsvImport.jsx'
import { adminApi } from '../api/adminApi.js'
import { vehicleApi } from '../../vehicles/api/vehicleApi.js'

const CATEGORY_BADGE = {
  Medication: 'item-badge--medication',
  Consumable: 'item-badge--consumable',
  Equipment:  'item-badge--equipment',
  Document:   'item-badge--document',
}

const CHECK_TYPE_LABEL = {
  SUPPLY:      { label: 'Count',           icon: '🔢' },
  MEASUREMENT: { label: 'Measurement',     icon: '📏' },
  FUNCTIONAL:  { label: 'Pass / Fail',     icon: '✓✗' },
  DATE_RECORD: { label: 'Date Record',     icon: '📅' },
  DOCUMENT:    { label: 'Present/Missing', icon: '📄' },
}

// Cabinet groups from BASE_ITEM_SEED (ITM-3 / migration 0029)
const CABINET_CHIPS = [
  { value: 'All',                                     label: 'All' },
  { value: 'Airway & Respiratory',                    label: 'Airway' },
  { value: 'Wound Care & Trauma Supplies',            label: 'Wound Care' },
  { value: 'PPE & Cleaning',                          label: 'PPE' },
  { value: 'Diagnostic & Monitoring Equipment',       label: 'Diagnostic' },
  { value: 'Medications & Controlled Substances',     label: 'Medications' },
  { value: 'Documents, Linens & Patient Comfort',     label: 'Documents' },
  { value: 'Vehicle Operations',                      label: 'Vehicle Ops' },
]

export default function ItemCatalog({ stationId }) {
  const { user, getToken } = useAuth()
  const isAdmin          = canAccess(user, 'administrator')
  const isSupervisorPlus = canAccess(user, 'supervisor')

  const [showInactive, setShowInactive]     = useState(false)
  const [editingItem, setEditingItem]       = useState(null)
  const [searchQuery, setSearchQuery]       = useState('')
  const [cabinetFilter, setCabinetFilter]   = useState('All')
  const [catalogKey, setCatalogKey]         = useState(0)

  // Vehicles fetched once — passed down to ItemAssignments for the cascade picker
  const { data: vehicles } = useApi(
    () => stationId ? vehicleApi.getStationVehicles(stationId, getToken) : Promise.resolve([]),
    [stationId]
  )

  // Locations (jump bags + supply room) — passed to ItemAssignments for the "Where" picker
  const { data: locations } = useApi(
    () => stationId ? adminApi.getStationLocations(stationId, getToken) : Promise.resolve([]),
    [stationId]
  )

  const {
    data: items,
    isLoading,
    error,
  } = useApi(
    () => stationId
      ? adminApi.listItems(getToken, { stationId, active: showInactive ? null : true })
      : Promise.resolve([]),
    [catalogKey, showInactive, stationId]
  )

  // ── Client-side filter ──────────────────────────────────────────────────────

  const filtered = useMemo(() => {
    if (!items) return []
    const q = searchQuery.trim().toLowerCase()
    return items.filter(item => {
      const matchesCabinet = cabinetFilter === 'All' || item.category_group === cabinetFilter
      const matchesSearch  = !q
        || item.name.toLowerCase().includes(q)
        || item.alternate_names?.toLowerCase().includes(q)
        || item.ai_tags?.toLowerCase().includes(q)
      return matchesCabinet && matchesSearch
    })
  }, [items, searchQuery, cabinetFilter])

  // Group by category_group (physical cabinet); fall back to category for items missing it
  const grouped = useMemo(() => {
    const groups = {}
    for (const item of filtered) {
      const key = item.category_group ?? item.category ?? 'Other'
      if (!groups[key]) groups[key] = []
      groups[key].push(item)
    }
    return groups
  }, [filtered])

  function handleSaved() {
    setEditingItem(null)
    setCatalogKey(k => k + 1)
  }

  // ── Edit / Create form ──────────────────────────────────────────────────────

  if (editingItem !== null) {
    return (
      <ErrorBoundary moduleName="Item Form">
        <ItemForm
          item={editingItem === 'new' ? null : editingItem}
          onSaved={handleSaved}
          onCancel={() => setEditingItem(null)}
        />
      </ErrorBoundary>
    )
  }

  // ── Catalog list ────────────────────────────────────────────────────────────

  return (
    <div className="item-catalog">

      {/* Header row */}
      <div className="item-catalog__header">
        <h2 className="item-catalog__title">
          Item Catalog
          {items && (
            <span className="item-catalog__count"> ({items.length})</span>
          )}
        </h2>
        {isSupervisorPlus && (
          <button
            className="btn btn--primary btn--sm"
            onClick={() => setEditingItem('new')}
            type="button"
          >
            + Add item
          </button>
        )}
      </div>

      {/* CSV import */}
      <CsvImport onImported={() => setCatalogKey(k => k + 1)} />

      {/* Search bar */}
      <div className="item-catalog__search-row">
        <input
          className="item-catalog__search"
          type="search"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="Search by name, alternate name, or tag…"
          aria-label="Search items"
        />
      </div>

      {/* Cabinet filter chips */}
      <div className="item-catalog__filters" role="group" aria-label="Filter by cabinet">
        {CABINET_CHIPS.map(chip => (
          <button
            key={chip.value}
            type="button"
            className={`item-catalog__chip ${cabinetFilter === chip.value ? 'item-catalog__chip--active' : ''}`}
            onClick={() => setCabinetFilter(chip.value)}
          >
            {chip.label}
          </button>
        ))}
      </div>

      {/* Show inactive toggle (Admin only) */}
      {isAdmin && (
        <label className="item-catalog__inactive-toggle">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={e => setShowInactive(e.target.checked)}
          />
          <span>Show inactive items</span>
        </label>
      )}

      {/* Content */}
      {isLoading ? (
        <Spinner label="Loading catalog…" />
      ) : error ? (
        <div className="item-catalog__error" role="alert">
          ⚠ Could not load items — {error.message}
        </div>
      ) : filtered.length === 0 ? (
        <div className="item-catalog__empty">
          {searchQuery
            ? `No items match "${searchQuery}"`
            : 'No items in the catalog yet. Add one above.'}
        </div>
      ) : (
        Object.entries(grouped).map(([groupName, groupItems]) => (
          <div key={groupName} className="item-catalog__group">
            <h3 className="item-catalog__group-title">{groupName}</h3>
            <div className="item-catalog__cards">
              {groupItems.map(item => {
                const ctMeta  = CHECK_TYPE_LABEL[item.check_type] ?? { label: item.check_type, icon: '' }
                const badgeCls = CATEGORY_BADGE[item.category] ?? ''
                return (
                  <div
                    key={item.item_id}
                    className={`item-card ${!item.active ? 'item-card--inactive' : ''}`}
                  >
                    <div className="item-card__top">
                      <div className="item-card__name">
                        {item.name}
                        {!item.active && (
                          <span className="item-card__inactive-badge">Inactive</span>
                        )}
                        {item.controlled_substance && (
                          <span className="item-card__cs-badge">CS</span>
                        )}
                      </div>
                      <span className={`item-badge ${badgeCls}`}>{item.category}</span>
                    </div>

                    <div className="item-card__meta">
                      <span className="item-card__check-type">
                        {ctMeta.icon} {ctMeta.label}
                      </span>
                      <span className="item-card__unit">· {item.unit_of_measure}</span>
                      {item.barcode && (
                        <span className="item-card__barcode" title="Barcode registered">🔲</span>
                      )}
                      {item.ai_tags && (
                        <span className="item-card__ai-flag" title="AI tags configured">🤖</span>
                      )}
                    </div>

                    <div className="item-card__actions">
                      <button
                        type="button"
                        className="btn btn--secondary btn--sm"
                        onClick={() => setEditingItem(item)}
                      >
                        Edit
                      </button>
                    </div>

                    <ItemAssignments
                      item={item}
                      stationId={stationId}
                      vehicles={vehicles ?? []}
                      locations={locations ?? []}
                      initialCount={item.assignment_count ?? 0}
                    />
                  </div>
                )
              })}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
