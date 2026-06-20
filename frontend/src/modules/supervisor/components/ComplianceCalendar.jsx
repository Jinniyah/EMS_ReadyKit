/**
 * modules/supervisor/components/ComplianceCalendar.jsx  (F-5F2)
 *
 * Week view  — horizontal grid: each row = one active (non-retired) vehicle
 *              or jump bag, each column = one day. The Station Supply Room
 *              does NOT get a row here — it's checked every few months, not
 *              daily, so a row in a daily grid would mostly be empty space.
 * Month view — traditional Su–Sa calendar grid for one selected vehicle or
 *              jump bag, picked from a combined chip picker.
 *
 * Jump bags are checked alongside vehicles (same cadence, easy-access gear)
 * and so share the vehicle/jump-bag picker and grid rows, in both week and
 * month view. The Station Supply Room is kept out of that picker/grid
 * entirely and instead gets a standing reminder strip directly under the
 * Week/Month toggle, visible no matter which view is selected (B-AF1,
 * moved under the toolbar per Jennifer's feedback after launch — a chip
 * inside month view would get seen far less often than something that's
 * always on screen).
 */

import React, { useState, useMemo } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import Spinner from '../../../shared/components/Spinner.jsx'
import { supervisorApi } from '../api/supervisorApi.js'

// ── Date helpers ──────────────────────────────────────────────────────────────

function localIso(d) {
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, '0'),
    String(d.getDate()).padStart(2, '0'),
  ].join('-')
}

function startOfIsoWeek(d) {
  const copy = new Date(d)
  const day  = copy.getDay() === 0 ? 7 : copy.getDay()
  copy.setDate(copy.getDate() - day + 1)
  copy.setHours(0, 0, 0, 0)
  return copy
}

function dateRange(start, n) {
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(start)
    d.setDate(d.getDate() + i)
    return d
  })
}

const WEEKDAY_ABBR = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const DOW_LABELS   = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTH_NAMES  = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

// ── Status display ────────────────────────────────────────────────────────────

const STATUS_GLYPH = {
  PASS:          { glyph: '✅', label: 'Pass',         cls: 'cal-cell--pass'    },
  FAIL:          { glyph: '❌', label: 'Fail',         cls: 'cal-cell--fail'    },
  NEEDS_RESTOCK: { glyph: '🟡', label: 'Needs restock',cls: 'cal-cell--restock' },
}

function worstStatus(statuses) {
  if (statuses.includes('FAIL'))          return 'FAIL'
  if (statuses.includes('NEEDS_RESTOCK')) return 'NEEDS_RESTOCK'
  if (statuses.includes('PASS'))          return 'PASS'
  return null
}

function vehicleColor(vehicle, station) {
  return vehicle.vehicle_color ?? station?.primary_color ?? 'var(--color-brand)'
}

// A unified row/picker entity for either a vehicle or a jump bag.
// key:  'v:{vehicle_id}' or 'l:{location_id}' — matches the `index` map keys.
function entityKey(entity) {
  return entity.kind === 'vehicle' ? `v:${entity.vehicle_id}` : `l:${entity.location_id}`
}

// ── EntityPicker (month mode) — vehicles + jump bags together ────────────────

function EntityPicker({ entities, selectedKey, onChange }) {
  return (
    <div className="cal-vehicle-picker" role="listbox" aria-label="Vehicle or jump bag">
      {entities.map(entity => {
        const key      = entityKey(entity)
        const selected = key === selectedKey
        const label    = entity.kind === 'vehicle' ? entity.vehicle_number : entity.label
        return (
          <button
            key={key}
            type="button"
            role="option"
            aria-selected={selected}
            className={`cal-vehicle-chip ${selected ? 'cal-vehicle-chip--active' : ''}`}
            onClick={() => onChange(key)}
          >
            {entity.kind === 'jump_bag' && <span aria-hidden="true">🎒 </span>}
            {label}
          </button>
        )
      })}
    </div>
  )
}

// ── MonthCalendar — traditional Su–Sa grid ────────────────────────────────────

function MonthCalendar({ todayIso, days, index, selectedKey, onViewCheck }) {
  // How many empty cells before day 1 (Sunday = 0 ... Saturday = 6)
  const leadingBlanks = days[0].getDay()
  const totalCells    = leadingBlanks + days.length
  const trailingBlanks = (7 - (totalCells % 7)) % 7

  function checksForDay(dateIso) {
    return index[selectedKey]?.[dateIso] ?? []
  }

  function handleCellClick(dateIso) {
    const dayChecks = checksForDay(dateIso)
    if (!dayChecks.length) return
    const order  = { FAIL: 0, NEEDS_RESTOCK: 1, PASS: 2 }
    const sorted = [...dayChecks].sort((a, b) => (order[a.status] ?? 3) - (order[b.status] ?? 3))
    onViewCheck(sorted[0].check_id)
  }

  return (
    <div className="cal__month-grid" role="grid" aria-label="Monthly compliance calendar">

      {/* Day-of-week header row */}
      {DOW_LABELS.map(wd => (
        <div key={wd} className="cal__month-dow" role="columnheader">{wd}</div>
      ))}

      {/* Leading blank cells */}
      {Array.from({ length: leadingBlanks }, (_, i) => (
        <div key={`pre-${i}`} className="cal__month-cell cal__month-cell--empty"
          role="gridcell" aria-hidden="true" />
      ))}

      {/* Day cells */}
      {days.map(d => {
        const iso       = localIso(d)
        const isToday   = iso === todayIso
        const isPast    = iso < todayIso
        const dayChecks = checksForDay(iso)
        const status    = worstStatus(dayChecks.map(c => c.status))
        const isMissed  = isPast && !status
        const isClickable = !!status

        const meta = STATUS_GLYPH[status] ?? {
          glyph: isMissed ? '—' : '',
          label: isMissed ? 'Missed' : 'No check',
          cls:   isMissed ? 'cal-cell--missed' : '',
        }

        return (
          <div
            key={iso}
            role="gridcell"
            tabIndex={isClickable ? 0 : -1}
            className={[
              'cal__month-cell',
              meta.cls,
              isToday     && 'cal__month-cell--today',
              isMissed    && 'cal__month-cell--missed',
              isClickable && 'cal__month-cell--clickable',
            ].filter(Boolean).join(' ')}
            aria-label={`${d.getDate()}: ${meta.label}`}
            onClick={() => isClickable && handleCellClick(iso)}
            onKeyDown={e => {
              if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
                e.preventDefault()
                handleCellClick(iso)
              }
            }}
          >
            <span className="cal__month-cell__num"
              style={isToday ? { background: 'var(--station-primary, var(--color-brand))', color: '#fff' } : undefined}>
              {d.getDate()}
            </span>
            {meta.glyph && (
              <span className="cal__month-cell__glyph" aria-hidden="true">{meta.glyph}</span>
            )}
          </div>
        )
      })}

      {/* Trailing blank cells */}
      {Array.from({ length: trailingBlanks }, (_, i) => (
        <div key={`post-${i}`} className="cal__month-cell cal__month-cell--empty"
          role="gridcell" aria-hidden="true" />
      ))}
    </div>
  )
}

// ── SupplyRoomReminder — standing reminder, always visible under the
//    Week/Month toggle regardless of which view is selected. Shows the most
//    recent count overall (not scoped to whatever date range happens to be
//    on screen) and clicking it opens that same most-recent count — display
//    text and click target now read from the exact same data, so they can
//    never disagree (the previous bug: the reminder's text and its click
//    target were fed by two differently-scoped fetches that could disagree
//    — e.g. showing "No count on record" while still opening a real count
//    when tapped). ────────────────────────────────────────────────────────

function SupplyRoomReminder({ history, isLoading, onViewCheck }) {
  const latest = useMemo(() => {
    if (!history?.length) return null
    return [...history].sort((a, b) => (a.check_date < b.check_date ? 1 : -1))[0]
  }, [history])

  if (isLoading) return null

  const status = latest ? (STATUS_GLYPH[latest.status] ?? STATUS_GLYPH.PASS) : null

  let daysAgoLabel = 'No count on record yet'
  if (latest) {
    const last = new Date(latest.check_date + 'T00:00:00')
    const days = Math.floor((Date.now() - last.getTime()) / 86400000)
    daysAgoLabel = days <= 0 ? 'Counted today'
      : days === 1 ? 'Counted 1 day ago'
      : `Counted ${days} days ago`
  }

  return (
    <button
      type="button"
      className="cal__supply-reminder"
      onClick={() => latest && onViewCheck(latest.check_id)}
      disabled={!latest}
    >
      <span className="cal__supply-reminder__icon" aria-hidden="true">📦</span>
      <span className="cal__supply-reminder__text">
        <span className="cal__supply-reminder__title">Station Supplies Count</span>
        <span className="cal__supply-reminder__meta">{daysAgoLabel} — every few months</span>
      </span>
      {status && (
        <span aria-hidden="true" className="cal__supply-reminder__glyph">{status.glyph}</span>
      )}
    </button>
  )
}

// ── ComplianceCalendar ────────────────────────────────────────────────────────

export default function ComplianceCalendar({ station, vehicles, portables = [], onViewCheck }) {
  const { getToken } = useAuth()
  const today    = useMemo(() => new Date(), [])
  const todayIso = useMemo(() => localIso(today), [today])

  const [mode, setMode]               = useState('week')
  const [selectedKey, setSelectedKey] = useState(null)
  const [viewedYear,  setViewedYear]  = useState(today.getFullYear())
  const [viewedMonth, setViewedMonth] = useState(today.getMonth()) // 0-indexed

  // Vehicles arrive already filtered to exclude retired ones (supervisorApi
  // filters at the source). Still check both fields defensively here — never
  // rely on `active` alone (CODEBASE_INDEX.md "active vs retired_at", BUG-AD1).
  const activeVehicles = vehicles.filter(v => v.active && !v.retired_at)

  // Jump bags join the vehicle rows/picker — same daily cadence, designed to
  // be grabbed alongside the truck. Equipment locations (if any) and the
  // Station Supply Room do NOT join this list; the supply room gets its own
  // standing reminder under the toolbar instead.
  const jumpBags = portables.filter(loc => loc.location_type === 'JUMP_BAG')

  const calendarEntities = useMemo(() => ([
    ...activeVehicles.map(v => ({ kind: 'vehicle', ...v })),
    ...jumpBags.map(loc => ({ kind: 'jump_bag', ...loc })),
  ]), [activeVehicles, jumpBags])

  // Station Supply Room — fetched separately; GET /stations/{id}/locations
  // only returns JUMP_BAG/EQUIPMENT, never STATION_SUPPLY_ROOM. Returns null
  // if the station hasn't set one up yet (or it's been retired).
  const { data: supplyRoom } = useApi(
    () => supervisorApi.getSupplyRoomLocation(station.station_id, getToken),
    [station.station_id]
  )

  // Supply room check history — fetched once, unconditionally (not gated to
  // month mode), over a generous lookback window so "most recent count" is
  // correct regardless of which week/month is currently being viewed. This
  // is the single source for both the reminder's display text and its click
  // target — fixing the previous bug where two separately-scoped fetches
  // could disagree with each other.
  const lookbackFrom = useMemo(() => {
    const d = new Date(today)
    d.setDate(d.getDate() - 730)
    return localIso(d)
  }, [today])

  const { data: supplyRoomHistory, isLoading: supplyRoomHistoryLoading } = useApi(
    () => supplyRoom
      ? supervisorApi.getComplianceRange(station.station_id, lookbackFrom, todayIso, getToken)
          .then(all => all.filter(c => c.location_id === supplyRoom.location_id))
      : Promise.resolve([]),
    [station.station_id, supplyRoom?.location_id, lookbackFrom, todayIso]
  )

  // ── Earliest check date — bounds backwards navigation ────────────────────

  const { data: dateRangeData } = useApi(
    () => supervisorApi.getCheckDateRange(station.station_id, getToken),
    [station.station_id]
  )

  const { earliestYear, earliestMonth } = useMemo(() => {
    if (!dateRangeData?.earliest) {
      return { earliestYear: today.getFullYear(), earliestMonth: today.getMonth() }
    }
    // Parse as local date to avoid UTC-midnight timezone shift
    const [y, m] = dateRangeData.earliest.split('-').map(Number)
    return { earliestYear: y, earliestMonth: m - 1 } // m-1 because JS months are 0-indexed
  }, [dateRangeData, today])

  // ── Month navigation ──────────────────────────────────────────────────────

  const isAtEarliest = viewedYear < earliestYear ||
    (viewedYear === earliestYear && viewedMonth <= earliestMonth)

  const isAtCurrentMonth = viewedYear > today.getFullYear() ||
    (viewedYear === today.getFullYear() && viewedMonth >= today.getMonth())

  function goBack() {
    if (viewedMonth === 0) { setViewedYear(y => y - 1); setViewedMonth(11) }
    else                   { setViewedMonth(m => m - 1) }
  }

  function goForward() {
    if (viewedMonth === 11) { setViewedYear(y => y + 1); setViewedMonth(0) }
    else                    { setViewedMonth(m => m + 1) }
  }

  // ── Date window ──────────────────────────────────────────────────────────

  const { days, fromIso, toIso } = useMemo(() => {
    if (mode === 'week') {
      const mon = startOfIsoWeek(today)
      const d   = dateRange(mon, 7)
      return { days: d, fromIso: localIso(d[0]), toIso: localIso(d[6]) }
    }
    // Month mode: use the viewed month, not today
    const first = new Date(viewedYear, viewedMonth, 1)
    const last  = new Date(viewedYear, viewedMonth + 1, 0)
    const d     = dateRange(first, last.getDate())
    return { days: d, fromIso: localIso(d[0]), toIso: localIso(d[d.length - 1]) }
  }, [mode, today, viewedYear, viewedMonth])

  // ── Data ─────────────────────────────────────────────────────────────────

  const { data: checks, isLoading, error } = useApi(
    () => supervisorApi.getComplianceRange(station.station_id, fromIso, toIso, getToken),
    [station.station_id, fromIso, toIso]
  )

  // Index: 'v:{vehicle_id}' → date → checks[]  for vehicles
  //         'l:{location_id}' → date → checks[]  for portable locations (jump bags)
  const index = useMemo(() => {
    if (!checks) return {}
    const map = {}
    for (const chk of checks) {
      const key = chk.vehicle_id != null ? `v:${chk.vehicle_id}` : `l:${chk.location_id}`
      const dt  = chk.check_date
      if (!map[key]) map[key] = {}
      if (!map[key][dt]) map[key][dt] = []
      map[key][dt].push(chk)
    }
    return map
  }, [checks])

  // Month mode: auto-select the first vehicle/jump bag if none chosen yet
  const effectiveSelectedKey = useMemo(() => {
    if (selectedKey && calendarEntities.some(e => entityKey(e) === selectedKey)) return selectedKey
    return calendarEntities.length > 0 ? entityKey(calendarEntities[0]) : null
  }, [selectedKey, calendarEntities])

  // ── Cell click (week view) ────────────────────────────────────────────────

  function handleWeekCellClick(key, dateIso) {
    const dayChecks = index[key]?.[dateIso]
    if (!dayChecks?.length) return
    const order  = { FAIL: 0, NEEDS_RESTOCK: 1, PASS: 2 }
    const sorted = [...dayChecks].sort((a, b) => (order[a.status] ?? 3) - (order[b.status] ?? 3))
    onViewCheck(sorted[0].check_id)
  }

  // ── Header label ──────────────────────────────────────────────────────────

  function weekLabel() {
    const from = days[0], to = days[6]
    if (from.getMonth() === to.getMonth()) {
      return `${MONTH_NAMES[from.getMonth()]} ${from.getDate()}–${to.getDate()}, ${from.getFullYear()}`
    }
    return `${MONTH_NAMES[from.getMonth()]} ${from.getDate()} – ${MONTH_NAMES[to.getMonth()]} ${to.getDate()}, ${to.getFullYear()}`
  }

  if (!calendarEntities.length && !supplyRoom) {
    return <div className="cal-empty">No active vehicles or equipment to display.</div>
  }

  return (
    <div className="cal">

      {/* ── Toolbar ──────────────────────────────────────────────────────── */}
      <div className="cal__toolbar">
        {mode === 'week' ? (
          <span className="cal__range-label">{weekLabel()}</span>
        ) : (
          <div className="cal__month-nav" role="group" aria-label="Month navigation">
            <button
              type="button"
              className="cal__month-nav-btn"
              onClick={goBack}
              disabled={isAtEarliest}
              aria-label="Previous month"
            >‹</button>
            <span className="cal__range-label">
              {MONTH_NAMES[viewedMonth]} {viewedYear}
            </span>
            <button
              type="button"
              className="cal__month-nav-btn"
              onClick={goForward}
              disabled={isAtCurrentMonth}
              aria-label="Next month"
            >›</button>
          </div>
        )}
        <div className="cal__mode-btns" role="group" aria-label="Calendar view">
          <button
            type="button"
            className={`cal__mode-btn ${mode === 'week' ? 'cal__mode-btn--active' : ''}`}
            onClick={() => setMode('week')}
            aria-pressed={mode === 'week'}
          >
            Week
          </button>
          <button
            type="button"
            className={`cal__mode-btn ${mode === 'month' ? 'cal__mode-btn--active' : ''}`}
            onClick={() => setMode('month')}
            aria-pressed={mode === 'month'}
          >
            Month
          </button>
        </div>
      </div>

      {/* ── Station Supply Room reminder — always visible here, under the
            Week/Month toggle, regardless of which view is selected. Moved
            out from under the month grid per Jennifer's feedback: a chip
            buried inside month view would get seen far less often than
            something that's always on screen. ────────────────────────────── */}
      {supplyRoom && (
        <SupplyRoomReminder
          history={supplyRoomHistory}
          isLoading={supplyRoomHistoryLoading}
          onViewCheck={onViewCheck}
        />
      )}

      {/* ── Vehicle + jump bag picker (month mode only) ──────────────────── */}
      {mode === 'month' && calendarEntities.length > 1 && (
        <EntityPicker
          entities={calendarEntities}
          selectedKey={effectiveSelectedKey}
          onChange={setSelectedKey}
        />
      )}

      {/* ── Loading / error ───────────────────────────────────────────────── */}
      {isLoading && <Spinner label="Loading calendar…" size="sm" />}
      {error && !isLoading && (
        <p className="cal__error" role="alert">⚠ Could not load compliance data.</p>
      )}

      {/* ── Grids ────────────────────────────────────────────────────────── */}
      {!isLoading && !error && mode === 'week' && (
        <div className="cal__scroll-wrap">
          <div
            className="cal__grid"
            role="grid"
            aria-label="Compliance calendar"
            style={{ '--cal-cols': days.length + 1 }}
          >
            {/* Column headers */}
            <div className="cal__header-row" role="row">
              <div className="cal__corner" role="columnheader" aria-label="Vehicle" />
              {days.map(d => {
                const iso     = localIso(d)
                const isToday = iso === todayIso
                const weekday = WEEKDAY_ABBR[(d.getDay() + 6) % 7]
                return (
                  <div
                    key={iso}
                    role="columnheader"
                    className={`cal__day-header ${isToday ? 'cal__day-header--today' : ''}`}
                    aria-label={isToday ? `${d.getDate()} ${weekday} (today)` : `${d.getDate()} ${weekday}`}
                  >
                    <span className="cal__day-num">{d.getDate()}</span>
                    <span className="cal__day-wd">{weekday}</span>
                  </div>
                )
              })}
            </div>

            {/* Vehicle rows — active (non-retired) only */}
            {activeVehicles.map(vehicle => {
              const color = vehicleColor(vehicle, station)
              const vkey  = `v:${vehicle.vehicle_id}`
              return (
                <div key={vehicle.vehicle_id} className="cal__row" role="row">
                  <div
                    className="cal__vehicle-label"
                    role="rowheader"
                    style={{ '--vcolor': color }}
                    title={vehicle.vehicle_number}
                  >
                    <span className="cal__vehicle-dot" style={{ background: color }} aria-hidden="true" />
                    <span className="cal__vehicle-num">{vehicle.vehicle_number}</span>
                  </div>
                  {days.map(d => {
                    const iso       = localIso(d)
                    const isToday   = iso === todayIso
                    const isPast    = iso < todayIso
                    const dayChecks = index[vkey]?.[iso] ?? []
                    const status    = worstStatus(dayChecks.map(c => c.status))
                    const isMissed  = isPast && !status
                    const isClickable = !!status
                    const { glyph, label, cls } = STATUS_GLYPH[status] ?? { glyph: '—', label: 'No check', cls: '' }
                    return (
                      <div
                        key={iso}
                        role="gridcell"
                        className={[
                          'cal-cell', cls,
                          isToday    && 'cal-cell--today',
                          isMissed   && 'cal-cell--missed',
                          isClickable && 'cal-cell--clickable',
                        ].filter(Boolean).join(' ')}
                        aria-label={`${vehicle.vehicle_number} ${d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}: ${label}`}
                        tabIndex={isClickable ? 0 : -1}
                        onClick={() => isClickable && handleWeekCellClick(vkey, iso)}
                        onKeyDown={e => {
                          if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
                            e.preventDefault()
                            handleWeekCellClick(vkey, iso)
                          }
                        }}
                      >
                        <span aria-hidden="true">{glyph}</span>
                      </div>
                    )
                  })}
                </div>
              )
            })}

            {/* Jump bag rows — same grid as vehicles, checked on the same cadence */}
            {jumpBags.map(loc => {
              const lkey = `l:${loc.location_id}`
              return (
                <div key={`loc-${loc.location_id}`} className="cal__row" role="row">
                  <div
                    className="cal__vehicle-label"
                    role="rowheader"
                    title={loc.label}
                  >
                    <span style={{ fontSize: '0.85rem', marginRight: '4px' }} aria-hidden="true">🎒</span>
                    <span className="cal__vehicle-num" style={{ fontSize: '0.75rem' }}>{loc.label}</span>
                  </div>
                  {days.map(d => {
                    const iso       = localIso(d)
                    const isToday   = iso === todayIso
                    const isPast    = iso < todayIso
                    const dayChecks = index[lkey]?.[iso] ?? []
                    const status    = worstStatus(dayChecks.map(c => c.status))
                    const isMissed  = isPast && !status
                    const isClickable = !!status
                    const { glyph, label, cls } = STATUS_GLYPH[status] ?? { glyph: '—', label: 'No check', cls: '' }
                    return (
                      <div
                        key={iso}
                        role="gridcell"
                        className={[
                          'cal-cell', cls,
                          isToday    && 'cal-cell--today',
                          isMissed   && 'cal-cell--missed',
                          isClickable && 'cal-cell--clickable',
                        ].filter(Boolean).join(' ')}
                        aria-label={`${loc.label} ${d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}: ${label}`}
                        tabIndex={isClickable ? 0 : -1}
                        onClick={() => isClickable && handleWeekCellClick(lkey, iso)}
                        onKeyDown={e => {
                          if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
                            e.preventDefault()
                            handleWeekCellClick(lkey, iso)
                          }
                        }}
                      >
                        <span aria-hidden="true">{glyph}</span>
                      </div>
                    )
                  })}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {!isLoading && !error && mode === 'month' && effectiveSelectedKey && (
        <MonthCalendar
          todayIso={todayIso}
          days={days}
          index={index}
          selectedKey={effectiveSelectedKey}
          onViewCheck={onViewCheck}
        />
      )}

      {/* ── Legend ───────────────────────────────────────────────────────── */}
      <div className="cal__legend" aria-label="Legend">
        <span className="cal__legend-item"><span aria-hidden="true">✅</span> Pass</span>
        <span className="cal__legend-item"><span aria-hidden="true">❌</span> Fail</span>
        <span className="cal__legend-item"><span aria-hidden="true">🟡</span> Needs restock</span>
        <span className="cal__legend-item cal__legend-item--missed"><span aria-hidden="true">—</span> Missed</span>
      </div>
    </div>
  )
}
