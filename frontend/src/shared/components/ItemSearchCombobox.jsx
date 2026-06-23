/**
 * shared/components/ItemSearchCombobox.jsx
 *
 * Accessible typeahead combobox for selecting an item from the catalog.
 * Used on the par level form, item catalog filter bar, and — when the AI
 * image recognition module is built — the AI confirmation flow
 * ("AI identified this as NRB Mask — is that right?").
 *
 * Design principles:
 *   - Results appear after 1 character — no minimum length barrier
 *   - 150ms debounce — feels instant, doesn't thrash the API
 *   - Matching text highlighted in results — "NRB" lights up in "NRB Mask"
 *   - Category badge on each row — visual confirmation before tapping
 *   - Keyboard: ArrowUp/ArrowDown to navigate, Enter to select, Escape to close
 *   - Mobile: 48px minimum row height, full-width results panel
 *   - Fails gracefully — error clears the results silently
 *   - Can be pre-populated (for AI confirmation flow or edit mode)
 *
 * Props:
 *   onSelect(item)        called when the user selects an item
 *   initialItem           optional — pre-populate with an existing item
 *   placeholder           input placeholder text
 *   disabled              disable the input
 *   autoFocus             focus the input on mount
 */

import React, { useState, useEffect, useRef, useCallback, useId } from 'react'
import { useAuth } from '../hooks/useAuth.jsx'
import { adminApi } from '../../modules/admin/api/adminApi.js'

const DEBOUNCE_MS = 150

const CATEGORY_BADGE = {
  Medication:  { label: 'Medication',  className: 'item-combobox__badge--medication'  },
  Consumable:  { label: 'Consumable',  className: 'item-combobox__badge--consumable'  },
  Equipment:   { label: 'Equipment',   className: 'item-combobox__badge--equipment'   },
  Document:    { label: 'Document',    className: 'item-combobox__badge--document'    },
}

const CHECK_TYPE_LABEL = {
  SUPPLY:      'Count',
  MEASUREMENT: 'Measurement',
  FUNCTIONAL:  'Pass/Fail',
  DATE_RECORD: 'Date',
  DOCUMENT:    'Present/Missing',
}

/**
 * Wrap matched characters in a <mark> element.
 * Returns an array of React nodes safe to render.
 */
function highlight(text, query) {
  if (!query || !text) return text
  const idx = text.toLowerCase().indexOf(query.toLowerCase())
  if (idx === -1) return text
  return [
    text.slice(0, idx),
    <mark key="h" className="item-combobox__highlight">{text.slice(idx, idx + query.length)}</mark>,
    text.slice(idx + query.length),
  ]
}

export default function ItemSearchCombobox({
  onSelect,
  initialItem  = null,
  placeholder  = 'Type to search items…',
  disabled     = false,
  autoFocus    = false,
  stationId    = undefined,
}) {
  const { getToken } = useAuth()
  const comboId = useId()
  const listId  = `${comboId}-list`

  const [inputValue, setInputValue]   = useState(initialItem?.name ?? '')
  const [results, setResults]         = useState([])
  const [open, setOpen]               = useState(false)
  const [activeIdx, setActiveIdx]     = useState(-1)
  const [selected, setSelected]       = useState(initialItem ?? null)

  const inputRef    = useRef(null)
  const listRef     = useRef(null)
  const debounceRef = useRef(null)

  // ── Search ──────────────────────────────────────────────────────────────────

  const runSearch = useCallback(async (q) => {
    if (!q.trim()) { setResults([]); setOpen(false); return }
    try {
      const items = await adminApi.searchItems(q, getToken, { limit: 10, stationId })
      setResults(items ?? [])
      setOpen((items?.length ?? 0) > 0)
      setActiveIdx(-1)
    } catch {
      setResults([])
      setOpen(false)
    }
  }, [getToken, stationId])

  function handleInputChange(e) {
    const val = e.target.value
    setInputValue(val)
    setSelected(null)

    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => runSearch(val), DEBOUNCE_MS)
  }

  useEffect(() => () => clearTimeout(debounceRef.current), [])

  // ── Selection ───────────────────────────────────────────────────────────────

  function handleSelect(item) {
    setSelected(item)
    setInputValue(item.name)
    setOpen(false)
    setResults([])
    setActiveIdx(-1)
    onSelect?.(item)
    inputRef.current?.focus()
  }

  // ── Keyboard navigation ─────────────────────────────────────────────────────

  function handleKeyDown(e) {
    if (!open) return

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIdx(i => Math.min(i + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIdx(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (activeIdx >= 0 && results[activeIdx]) handleSelect(results[activeIdx])
    } else if (e.key === 'Escape') {
      setOpen(false)
      setActiveIdx(-1)
    }
  }

  // Scroll active item into view
  useEffect(() => {
    if (activeIdx < 0 || !listRef.current) return
    const row = listRef.current.children[activeIdx]
    row?.scrollIntoView({ block: 'nearest' })
  }, [activeIdx])

  // ── Close on outside click ──────────────────────────────────────────────────

  useEffect(() => {
    function handleOutside(e) {
      if (!listRef.current?.contains(e.target) && !inputRef.current?.contains(e.target)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handleOutside)
    return () => document.removeEventListener('mousedown', handleOutside)
  }, [open])

  // ── Render ──────────────────────────────────────────────────────────────────

  const categoryMeta = selected ? (CATEGORY_BADGE[selected.category] ?? {}) : null

  return (
    <div className="item-combobox" role="combobox" aria-expanded={open} aria-haspopup="listbox">

      {/* Input */}
      <input
        ref={inputRef}
        id={comboId}
        type="text"
        className={`item-combobox__input ${selected ? 'item-combobox__input--selected' : ''}`}
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        autoComplete="off"
        aria-autocomplete="list"
        aria-controls={open ? listId : undefined}
        aria-activedescendant={activeIdx >= 0 ? `${listId}-${activeIdx}` : undefined}
      />

      {/* Selected item detail strip — shows category + check type once chosen */}
      {selected && (
        <div className="item-combobox__selected-detail">
          <span className={`item-combobox__badge ${categoryMeta?.className ?? ''}`}>
            {selected.category}
          </span>
          <span className="item-combobox__check-type">
            {CHECK_TYPE_LABEL[selected.check_type] ?? selected.check_type}
          </span>
          <span className="item-combobox__unit">{selected.unit_of_measure}</span>
          <button
            type="button"
            className="item-combobox__clear"
            aria-label="Clear selection"
            onClick={() => {
              setSelected(null)
              setInputValue('')
              onSelect?.(null)
              inputRef.current?.focus()
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Results dropdown */}
      {open && results.length > 0 && (
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          aria-label="Item search results"
          className="item-combobox__list"
        >
          {results.map((item, idx) => {
            const catMeta  = CATEGORY_BADGE[item.category] ?? {}
            const isActive = idx === activeIdx
            return (
              <li
                key={item.item_id}
                id={`${listId}-${idx}`}
                role="option"
                aria-selected={isActive}
                className={`item-combobox__row ${isActive ? 'item-combobox__row--active' : ''}`}
                onMouseDown={() => handleSelect(item)}
                onMouseEnter={() => setActiveIdx(idx)}
              >
                <div className="item-combobox__row-main">
                  <span className="item-combobox__row-name">
                    {highlight(item.name, inputValue)}
                  </span>
                  <span className={`item-combobox__badge ${catMeta.className ?? ''}`}>
                    {item.category}
                  </span>
                </div>
                <div className="item-combobox__row-meta">
                  <span>{CHECK_TYPE_LABEL[item.check_type] ?? item.check_type}</span>
                  <span>·</span>
                  <span>{item.unit_of_measure}</span>
                  {item.controlled_substance && (
                    <span className="item-combobox__cs-flag">CS</span>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
