/**
 * UsageItemPicker.jsx
 * After-Call Reset — item selection with +/- quantity controls.
 *
 * Shows frequent items first (from usage history), then remaining
 * supply catalog items alphabetically. When no usage history exists,
 * shows common EMS consumables first with an "improving over time" note.
 */
import React, { useState, useMemo } from 'react'

// Default common consumables shown before real usage data accumulates.
// These names match items seeded for Unit 712. Update if inventory changes.
const DEFAULT_COMMON_NAMES = [
  'Gloves Medium',
  'Gloves Large',
  'Gloves Small',
  'Gloves X-Large',
  'Gauze Sponges 4x4',
  'ACE Wraps Various Sizes',
  'Gauze Bandage Various Sizes',
  'KERLIX PC13',
  'Tape Various Sizes',
  'Triangle Bandages',
  'ABD Pad 8x10',
  'ABD Pad 5x9',
  'Alcohol Prep PC18',
  'Sterile Saline Solution',
  'Occlusive Dressing',
]

function matchesDefault(name) {
  return DEFAULT_COMMON_NAMES.some(
    d => name.toLowerCase().includes(d.toLowerCase()) ||
         d.toLowerCase().includes(name.toLowerCase())
  )
}

export default function UsageItemPicker({
  catalogItems,       // [{item_id, item_name, ...}] — full SUPPLY catalog
  frequentItems,      // [{item_id, item_name, total_used}] — may be empty
  quantities,         // {item_id: qty} — controlled state
  onQuantityChange,   // (item_id, newQty) => void
}) {
  const [search, setSearch] = useState('')

  const hasHistory = frequentItems.length > 0

  const frequentIds = useMemo(
    () => new Set(frequentItems.map(f => f.item_id)),
    [frequentItems]
  )

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return catalogItems.filter(item =>
      !q || item.item_name.toLowerCase().includes(q)
    )
  }, [catalogItems, search])

  // When searching: flat sorted list. When not: frequent/defaults first.
  const sections = useMemo(() => {
    if (search.trim()) {
      return [{ title: null, items: filtered }]
    }

    if (hasHistory) {
      const frequentSection = frequentItems
        .map(f => catalogItems.find(c => c.item_id === f.item_id))
        .filter(Boolean)
      const rest = catalogItems.filter(c => !frequentIds.has(c.item_id))
      return [
        { title: 'Used most often', items: frequentSection },
        { title: 'All items', items: rest },
      ]
    }

    // No history yet — show default common items first
    const defaultSection = catalogItems.filter(c => matchesDefault(c.item_name))
    const rest = catalogItems.filter(c => !matchesDefault(c.item_name))
    return [
      { title: 'Common items', items: defaultSection, isDefault: true },
      { title: 'All items', items: rest },
    ]
  }, [search, filtered, hasHistory, frequentItems, frequentIds, catalogItems])

  function increment(itemId) {
    onQuantityChange(itemId, (quantities[itemId] ?? 0) + 1)
  }

  function decrement(itemId) {
    const cur = quantities[itemId] ?? 0
    if (cur > 0) onQuantityChange(itemId, cur - 1)
  }

  const selectedCount = Object.values(quantities).reduce((s, v) => s + (v > 0 ? 1 : 0), 0)

  return (
    <div className="uip">
      {/* Search */}
      <div className="uip__search-row">
        <input
          className="uip__search"
          type="search"
          placeholder="Search items…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          aria-label="Search items"
        />
      </div>

      {!hasHistory && !search.trim() && (
        <p className="uip__history-note">
          This list will get better over time as your team logs items used after calls.
        </p>
      )}

      {/* Item sections */}
      {sections.map((section, si) => (
        section.items.length === 0 ? null : (
          <div key={si} className="uip__section">
            {section.title && (
              <div className="uip__section-title">{section.title}</div>
            )}
            {section.isDefault && (
              <div className="uip__section-note">Most common EMS consumables</div>
            )}
            {section.items.map(item => {
              const qty = quantities[item.item_id] ?? 0
              return (
                <div
                  key={item.item_id}
                  className={`uip__item${qty > 0 ? ' uip__item--selected' : ''}`}
                >
                  <div className="uip__item-name">{item.item_name}</div>
                  <div className="uip__item-controls">
                    <button
                      className="uip__qty-btn"
                      onClick={() => decrement(item.item_id)}
                      disabled={qty === 0}
                      type="button"
                      aria-label={`Remove one ${item.item_name}`}
                    >
                      −
                    </button>
                    <span className="uip__qty-display" aria-live="polite">
                      {qty}
                    </span>
                    <button
                      className="uip__qty-btn"
                      onClick={() => increment(item.item_id)}
                      type="button"
                      aria-label={`Add one ${item.item_name}`}
                    >
                      +
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )
      ))}

      {filtered.length === 0 && search.trim() && (
        <p className="uip__empty">No items match "{search}"</p>
      )}

      {selectedCount > 0 && (
        <div className="uip__selection-summary" aria-live="polite">
          {selectedCount} item{selectedCount !== 1 ? 's' : ''} selected
        </div>
      )}
    </div>
  )
}
