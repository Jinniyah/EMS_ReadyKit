/**
 * modules/check-history/components/ExportPanel.jsx
 * F-5G3a: compliance CSV export -- lets a Supervisor+ pick a date range and
 * which vehicles/jump bag(s)/whole station to include, then download either
 * a Simplified (one line per check) or Detailed (every item checked) CSV
 * for a station-license inspection. Manual download only -- the caller
 * uploads the file wherever it needs to go.
 *
 * Collapsed by default (rare action, not a daily one) -- same pattern as
 * CsvImport.jsx's import panel.
 */

import React, { useState, useMemo } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import Spinner from '../../../shared/components/Spinner.jsx'
import { checkHistoryApi } from '../api/checkHistoryApi.js'

const MAX_EXPORT_DAYS = 400

function isoDate(d) {
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-')
}

function defaultDates() {
  const to = new Date()
  const from = new Date()
  from.setDate(from.getDate() - 29) // last 30 days by default
  return { from: isoDate(from), to: isoDate(to) }
}

export default function ExportPanel({ station }) {
  const { getToken } = useAuth()

  const [expanded, setExpanded] = useState(false)
  const [{ from, to }, setDates] = useState(defaultDates)
  const [wholeStation, setWholeStation] = useState(true)
  const [selectedVehicleIds, setSelectedVehicleIds] = useState(() => new Set())
  const [selectedLocationIds, setSelectedLocationIds] = useState(() => new Set())

  const [downloading, setDownloading] = useState(null) // 'simplified' | 'detailed' | null
  const [error, setError] = useState(null)

  // Load vehicles/jump bags/supply room the first time the panel opens (and
  // again on every re-expand -- keeps the list fresh if a vehicle changed
  // while the panel was closed, same tradeoff the rest of this screen's tabs
  // already make). Guarding the fetch itself with a ternary inside fetchFn,
  // rather than a custom effect, is this codebase's established pattern for
  // "only fetch when a condition holds" (see index.jsx's allChecks/
  // deletedChecks calls and ComplianceCalendar.jsx's supplyRoom calls) --
  // useApi's ref-based cancellation guard avoids a footgun a hand-rolled
  // effect fell into here: including the fetched data itself (or a loading
  // flag set inside the effect) in that effect's own dependency array
  // creates a self-cancelling race, where setting the data re-triggers the
  // effect, whose cleanup fires before the promise chain's own .finally()
  // gets a chance to run and clear the loading flag.
  const {
    data: entities,
    isLoading: loadingEntities,
    error: entitiesError,
  } = useApi(
    () => expanded
      ? Promise.all([
          checkHistoryApi.getStationVehicles(station.station_id, getToken),
          checkHistoryApi.getStationLocations(station.station_id, getToken).catch(() => []),
          checkHistoryApi.getSupplyRoom(station.station_id, getToken),
        ]).then(([vehiclesRaw, locationsRaw, supplyRoom]) => ({
          // Retired vehicles are still exportable via "whole station" (the
          // backend deliberately keeps their history), but aren't offered
          // as individual checkboxes -- picking one going forward doesn't
          // make sense once it's retired (active vs retired_at, BUG-AD1).
          vehicles: vehiclesRaw.filter(v => v.active && !v.retired_at),
          jumpBags: locationsRaw.filter(loc => loc.location_type === 'JUMP_BAG'),
          supplyRoom: supplyRoom && !supplyRoom.retired_at ? supplyRoom : null,
        }))
      : Promise.resolve(null),
    [expanded, station.station_id]
  )

  const dayCount = useMemo(() => {
    const d1 = new Date(`${from}T00:00:00`)
    const d2 = new Date(`${to}T00:00:00`)
    return Math.round((d2 - d1) / 86400000)
  }, [from, to])

  const rangeInvalid = dayCount < 0
  const rangeTooLong = dayCount > MAX_EXPORT_DAYS
  const hasSelection = wholeStation || selectedVehicleIds.size > 0 || selectedLocationIds.size > 0
  const canDownload = hasSelection && !rangeInvalid && !rangeTooLong && !downloading

  function toggleVehicle(id) {
    setSelectedVehicleIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  function toggleLocation(id) {
    setSelectedLocationIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  async function handleDownload(format) {
    setError(null)
    setDownloading(format)
    try {
      const { blob, filename } = await checkHistoryApi.exportChecks(station.station_id, getToken, {
        from,
        to,
        format,
        wholeStation,
        vehicleIds: wholeStation ? [] : [...selectedVehicleIds],
        locationIds: wholeStation ? [] : [...selectedLocationIds],
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err.message ?? 'Export failed. Please try again.')
    } finally {
      setDownloading(null)
    }
  }

  return (
    <div className="export-panel">
      <button
        type="button"
        className="export-panel__toggle"
        onClick={() => setExpanded(v => !v)}
        aria-expanded={expanded}
      >
        <span>⬇ Export for compliance</span>
        <span className="export-panel__toggle-hint" aria-hidden="true">
          {expanded ? 'Hide' : 'Download check records for a station license inspection'}
        </span>
        <span aria-hidden="true">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="export-panel__body">

          {/* Date range */}
          <div className="export-panel__section">
            <p className="export-panel__section-label">Date range</p>
            <div className="export-panel__date-row">
              <label className="export-panel__date-field">
                <span>From</span>
                <input
                  type="date"
                  value={from}
                  onChange={e => setDates(d => ({ ...d, from: e.target.value }))}
                />
              </label>
              <label className="export-panel__date-field">
                <span>To</span>
                <input
                  type="date"
                  value={to}
                  onChange={e => setDates(d => ({ ...d, to: e.target.value }))}
                />
              </label>
            </div>
            {rangeInvalid && (
              <p className="export-panel__warning">The "From" date must be before the "To" date.</p>
            )}
            {!rangeInvalid && rangeTooLong && (
              <p className="export-panel__warning">Please pick a range of {MAX_EXPORT_DAYS} days or less.</p>
            )}
          </div>

          {/* What to include */}
          <div className="export-panel__section">
            <p className="export-panel__section-label">What to include</p>
            <label className="export-panel__checkbox-row export-panel__checkbox-row--whole">
              <input
                type="checkbox"
                checked={wholeStation}
                onChange={e => setWholeStation(e.target.checked)}
              />
              Whole station (everything)
            </label>

            {!wholeStation && (
              loadingEntities ? <Spinner label="Loading vehicles…" size="sm" /> :
              entitiesError   ? <p className="export-panel__warning">Could not load vehicles and locations. Try again.</p> :
              entities && (
                <div className="export-panel__entities">
                  {entities.vehicles.length > 0 && (
                    <div className="export-panel__entity-group">
                      <p className="export-panel__entity-group-label">Vehicles</p>
                      {entities.vehicles.map(v => (
                        <label key={v.vehicle_id} className="export-panel__checkbox-row">
                          <input
                            type="checkbox"
                            checked={selectedVehicleIds.has(v.vehicle_id)}
                            onChange={() => toggleVehicle(v.vehicle_id)}
                          />
                          Unit {v.vehicle_number}
                        </label>
                      ))}
                    </div>
                  )}
                  {entities.jumpBags.length > 0 && (
                    <div className="export-panel__entity-group">
                      <p className="export-panel__entity-group-label">Jump Bag(s)</p>
                      {entities.jumpBags.map(loc => (
                        <label key={loc.location_id} className="export-panel__checkbox-row">
                          <input
                            type="checkbox"
                            checked={selectedLocationIds.has(loc.location_id)}
                            onChange={() => toggleLocation(loc.location_id)}
                          />
                          {loc.label}
                        </label>
                      ))}
                    </div>
                  )}
                  {entities.supplyRoom && (
                    <div className="export-panel__entity-group">
                      <label className="export-panel__checkbox-row">
                        <input
                          type="checkbox"
                          checked={selectedLocationIds.has(entities.supplyRoom.location_id)}
                          onChange={() => toggleLocation(entities.supplyRoom.location_id)}
                        />
                        Station Supply Room
                      </label>
                    </div>
                  )}
                </div>
              )
            )}
            {!wholeStation && !hasSelection && (
              <p className="export-panel__warning">Pick at least one vehicle, jump bag, or the whole station.</p>
            )}
          </div>

          {/* Format -- direct, obvious buttons rather than a hidden toggle */}
          <div className="export-panel__section">
            <p className="export-panel__section-label">Choose a format</p>
            <button
              type="button"
              className="btn btn--primary btn--large"
              disabled={!canDownload}
              onClick={() => handleDownload('simplified')}
            >
              {downloading === 'simplified' ? 'Downloading…' : '⬇ Download Simplified'}
            </button>
            <p className="export-panel__format-hint">Date, who checked it, pass/fail — one line per check.</p>

            <button
              type="button"
              className="btn btn--secondary btn--large"
              disabled={!canDownload}
              onClick={() => handleDownload('detailed')}
            >
              {downloading === 'detailed' ? 'Downloading…' : '⬇ Download Detailed'}
            </button>
            <p className="export-panel__format-hint">Every item that was checked — best for a full inspection record.</p>
          </div>

          {error && (
            <div className="export-panel__error" role="alert">
              ⚠ {error}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
