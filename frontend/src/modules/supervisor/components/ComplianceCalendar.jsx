/**
 * modules/supervisor/components/ComplianceCalendar.jsx  (F-5F2)
 *
 * Week view  — horizontal grid: each row = one vehicle, each column = one day.
 * Month view — traditional Su–Sa calendar grid for the selected vehicle.
 *
 * In month mode the vehicle label column is gone; the VehiclePicker chips
 * above the calendar handle vehicle selection. Switching to month mode
 * auto-selects the first vehicle if none is active.
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

function startOfMonth(d) { return new Date(d.getFullYear(), d.getMonth(), 1) }
function endOfMonth(d)   { return new Date(d.getFullYear(), d.getMonth() + 1, 0) }

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

// ── VehiclePicker ─────────────────────────────────────────────────────────────

function VehiclePicker({ vehicles, selectedId, onChange }) {
  return (
    <div className="cal-vehicle-picker" role="listbox" aria-label="Vehicle">
      {vehicles.map(v => {
        const selected = v.vehicle_id === selectedId
        return (
          <button
            key={v.vehicle_id}
            type="button"
            role="option"
            aria-selected={selected}
            className={`cal-vehicle-chip ${selected ? 'cal-vehicle-chip--active' : ''}`}
            onClick={() => onChange(v.vehicle_id)}
          >
            {v.vehicle_number}
          </button>
        )
      })}
    </div>
  )
}

// ── MonthCalendar — traditional Su–Sa grid ────────────────────────────────────

function MonthCalendar({ todayIso, days, index, vehicles, selectedVehicleId, onViewCheck }) {
  // How many empty cells before day 1 (Sunday = 0 ... Saturday = 6)
  const leadingBlanks = days[0].getDay()
  const totalCells    = leadingBlanks + days.length
  const trailingBlanks = (7 - (totalCells % 7)) % 7

  function checksForDay(dateIso) {
    if (selectedVehicleId) {
      return index[selectedVehicleId]?.[dateIso] ?? []
    }
    return vehicles.flatMap(v => index[v.vehicle_id]?.[dateIso] ?? [])
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

// ── ComplianceCalendar ────────────────────────────────────────────────────────

export default function ComplianceCalendar({ station, vehicles, onViewCheck }) {
  const { getToken } = useAuth()
  const today    = useMemo(() => new Date(), [])
  const todayIso = useMemo(() => localIso(today), [today])

  const [mode, setMode]                           = useState('week')
  const [selectedVehicleId, setSelectedVehicleId] = useState(null)
  const [viewedYear,  setViewedYear]  = useState(today.getFullYear())
  const [viewedMonth, setViewedMonth] = useState(today.getMonth()) // 0-indexed

  const activeVehicles = vehicles.filter(v => v.active)

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

  // Index: vehicleId → date → checks[]
  const index = useMemo(() => {
    if (!checks) return {}
    const map = {}
    for (const chk of checks) {
      const vid = chk.vehicle_id
      const dt  = chk.check_date
      if (!map[vid]) map[vid] = {}
      if (!map[vid][dt]) map[vid][dt] = []
      map[vid][dt].push(chk)
    }
    return map
  }, [checks])

  // Week mode: vehicles × days grid — show all vehicles
  const displayVehicles = useMemo(() => {
    if (mode === 'week') return activeVehicles
    if (selectedVehicleId === null) return activeVehicles
    return activeVehicles.filter(v => v.vehicle_id === selectedVehicleId)
  }, [mode, activeVehicles, selectedVehicleId])

  // ── Cell click (week view) ────────────────────────────────────────────────

  function handleWeekCellClick(vehicleId, dateIso) {
    const dayChecks = index[vehicleId]?.[dateIso]
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

  if (!activeVehicles.length) {
    return <div className="cal-empty">No active vehicles to display.</div>
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
            onClick={() => {
              setMode('month')
              if (selectedVehicleId === null && activeVehicles.length > 0) {
                setSelectedVehicleId(activeVehicles[0].vehicle_id)
              }
            }}
            aria-pressed={mode === 'month'}
          >
            Month
          </button>
        </div>
      </div>

      {/* ── Vehicle picker (month mode only) ─────────────────────────────── */}
      {mode === 'month' && activeVehicles.length > 1 && (
        <VehiclePicker
          vehicles={activeVehicles}
          selectedId={selectedVehicleId}
          onChange={id => setSelectedVehicleId(id)}
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

            {/* Vehicle rows */}
            {displayVehicles.map(vehicle => {
              const color = vehicleColor(vehicle, station)
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
                    const dayChecks = index[vehicle.vehicle_id]?.[iso] ?? []
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
                        onClick={() => isClickable && handleWeekCellClick(vehicle.vehicle_id, iso)}
                        onKeyDown={e => {
                          if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
                            e.preventDefault()
                            handleWeekCellClick(vehicle.vehicle_id, iso)
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

      {!isLoading && !error && mode === 'month' && (
        <MonthCalendar
          todayIso={todayIso}
          days={days}
          index={index}
          vehicles={activeVehicles}
          selectedVehicleId={selectedVehicleId}
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
