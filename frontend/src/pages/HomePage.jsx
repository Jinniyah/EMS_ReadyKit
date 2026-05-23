/**
 * pages/HomePage.jsx
 * Application home screen.
 *
 * Phase 5E: Vehicle & Equipment Status module
 * Phase 5 (CH-F1–F5): Check History module
 */
import React, { useState, useEffect, lazy, Suspense } from 'react'
import { useAuth } from '../shared/hooks/useAuth.jsx'
import { useApi } from '../shared/hooks/useApi.js'
import { useDraftIndex } from '../shared/hooks/useDraft.js'
import { canAccess } from '../shared/utils/roleGuard.js'
import { stationColor } from '../shared/utils/stationColors.js'
import ErrorBoundary from '../shared/components/ErrorBoundary.jsx'
import DraftBanner from '../modules/check-wizard/components/DraftBanner.jsx'
import Spinner from '../shared/components/Spinner.jsx'
import { checkApi } from '../modules/check-wizard/api/checkApi.js'

const CheckWizard         = lazy(() => import('../modules/check-wizard/index.jsx'))
const VehicleStatusScreen = lazy(() => import('../modules/vehicles/index.jsx'))
const CheckHistoryScreen  = lazy(() => import('../modules/check-history/index.jsx'))

const STATION_STORAGE_KEY = 'ems_selected_station'

function loadSavedStation() {
  try {
    const raw = localStorage.getItem(STATION_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

function saveStation(station) {
  try {
    localStorage.setItem(STATION_STORAGE_KEY, JSON.stringify(station))
  } catch { /* ignore */ }
}

export default function HomePage() {
  const { user, getToken } = useAuth()

  const [activeWizard, setActiveWizard]       = useState(null)
  const [activeDraftKey, setActiveDraftKey]   = useState(null)
  const [activeModule, setActiveModule]       = useState(null) // 'vehicles' | 'history' | null
  const [selectedStation, setSelectedStation] = useState(loadSavedStation)
  const [pickingStation, setPickingStation]   = useState(false)

  const {
    data: stations,
    isLoading: loadingStations,
    error: stationsError,
  } = useApi(() => checkApi.getStations(getToken), [])

  const draftGroups = useDraftIndex(selectedStation?.station_id ?? null)

  useEffect(() => {
    if (!selectedStation && stations?.length === 1) {
      const s = stations[0]
      setSelectedStation(s)
      saveStation(s)
    }
  }, [stations, selectedStation])

  useEffect(() => {
    const idx = stations?.findIndex(s => s.station_id === selectedStation?.station_id) ?? 0
    if (selectedStation) {
      const { primary, text } = stationColor(selectedStation.name, idx >= 0 ? idx : 0)
      document.body.style.setProperty('--station-primary', primary)
      document.body.style.setProperty('--station-text', text)
    } else {
      document.body.style.setProperty('--station-primary', 'var(--color-brand)')
      document.body.style.setProperty('--station-text', '#ffffff')
    }
    return () => {
      document.body.style.removeProperty('--station-primary')
      document.body.style.removeProperty('--station-text')
    }
  }, [selectedStation, stations])

  function handleSelectStation(station) {
    setSelectedStation(station)
    saveStation(station)
    setPickingStation(false)
  }

  function handleStartNew() {
    setActiveDraftKey(null)
    setActiveWizard('new')
  }

  function handleResume(key, draft) {
    if (draft.station_id && stations) {
      const draftStation = stations.find(s => s.station_id === draft.station_id)
      if (draftStation) { setSelectedStation(draftStation); saveStation(draftStation) }
    }
    setActiveDraftKey(key)
    setActiveWizard(draft)
  }

  function handleDiscard(key) {
    localStorage.removeItem(key)
    window.dispatchEvent(new Event('storage'))
  }

  function handleWizardExit() {
    setActiveWizard(null)
    setActiveDraftKey(null)
  }

  // ── Active wizard ─────────────────────────────────────────────────────────
  if (activeWizard) {
    return (
      <ErrorBoundary moduleName="Check Wizard">
        <Suspense fallback={<Spinner label="Loading check wizard…" />}>
          <CheckWizard
            initialDraft={activeWizard === 'new' ? null : activeWizard}
            initialDraftKey={activeDraftKey}
            preselectedStation={selectedStation}
            onExit={handleWizardExit}
          />
        </Suspense>
      </ErrorBoundary>
    )
  }

  // ── Vehicle & Equipment Status ────────────────────────────────────────────
  if (activeModule === 'vehicles') {
    return (
      <ErrorBoundary moduleName="Vehicle & Equipment Status">
        <Suspense fallback={<Spinner label="Loading…" />}>
          <VehicleStatusScreen
            station={selectedStation}
            onBack={() => setActiveModule(null)}
          />
        </Suspense>
      </ErrorBoundary>
    )
  }

  // ── Check History ─────────────────────────────────────────────────────────
  if (activeModule === 'history') {
    return (
      <ErrorBoundary moduleName="Check History">
        <Suspense fallback={<Spinner label="Loading…" />}>
          <CheckHistoryScreen
            station={selectedStation}
            onBack={() => setActiveModule(null)}
          />
        </Suspense>
      </ErrorBoundary>
    )
  }

  const stationIdx = stations?.findIndex(s => s.station_id === selectedStation?.station_id) ?? 0
  const colors = selectedStation
    ? stationColor(selectedStation.name, stationIdx >= 0 ? stationIdx : 0)
    : null

  return (
    <div className="home-page">

      <div className="home-page__greeting">
        <h1 className="home-page__title">
          Good {_timeOfDay()}, {user?.name?.split(' ')[0] ?? 'there'}
        </h1>
        <p className="home-page__subtitle">{user?.role}</p>
      </div>

      <ErrorBoundary moduleName="Station Selector">
        {loadingStations ? (
          <Spinner label="Loading stations…" size="sm" />
        ) : stationsError ? (
          <div className="station-band station-band--error">
            <span>⚠ Could not load stations — is the backend running?</span>
          </div>
        ) : pickingStation || !selectedStation ? (
          <StationPicker
            stations={stations ?? []}
            currentStation={selectedStation}
            onSelect={handleSelectStation}
            onCancel={selectedStation ? () => setPickingStation(false) : null}
          />
        ) : (
          <StationBand
            station={selectedStation}
            colors={colors}
            onChangeStation={() => setPickingStation(true)}
            showChange={(stations?.length ?? 0) > 1}
          />
        )}
      </ErrorBoundary>

      {draftGroups.length > 0 && (
        <ErrorBoundary moduleName="Draft Banners">
          <section aria-label="In-progress checks">
            {draftGroups.map(group => (
              <DraftBanner
                key={group.groupKey}
                group={group}
                onResume={handleResume}
                onDiscard={handleDiscard}
              />
            ))}
          </section>
        </ErrorBoundary>
      )}

      <section className="home-page__section" aria-label="Available actions">
        <h2 className="home-page__section-title">Actions</h2>
        <div className="home-page__cards">

          <ErrorBoundary moduleName="Daily Check Card">
            <div className="module-card">
              <div className="module-card__icon" aria-hidden="true">✓</div>
              <div className="module-card__content">
                <div className="module-card__title">Daily Check</div>
                <div className="module-card__description">
                  {selectedStation
                    ? `Start a check at ${selectedStation.name}`
                    : 'Select a station above to start'}
                </div>
              </div>
              <button
                className="btn btn--primary"
                style={colors ? { background: colors.primary } : {}}
                onClick={handleStartNew}
                disabled={!selectedStation}
                type="button"
              >
                Start
              </button>
            </div>
          </ErrorBoundary>

          <ErrorBoundary moduleName="Vehicle Status Card">
            <div className="module-card">
              <div className="module-card__icon" aria-hidden="true">🚑</div>
              <div className="module-card__content">
                <div className="module-card__title">Vehicle &amp; Equipment Status</div>
                <div className="module-card__description">Report a repair or mark out of service</div>
              </div>
              <button
                className="btn btn--primary"
                style={colors ? { background: colors.primary } : {}}
                onClick={() => setActiveModule('vehicles')}
                disabled={!selectedStation}
                type="button"
              >
                Open
              </button>
            </div>
          </ErrorBoundary>

          <ErrorBoundary moduleName="Check History Card">
            <div className="module-card">
              <div className="module-card__icon" aria-hidden="true">📋</div>
              <div className="module-card__content">
                <div className="module-card__title">Check History</div>
                <div className="module-card__description">View past checks, acknowledge issues</div>
              </div>
              <button
                className="btn btn--primary"
                style={colors ? { background: colors.primary } : {}}
                onClick={() => setActiveModule('history')}
                disabled={!selectedStation}
                type="button"
              >
                Open
              </button>
            </div>
          </ErrorBoundary>

          {canAccess(user, 'supervisor') && (
            <ErrorBoundary moduleName="Dashboard Card">
              <div className="module-card module-card--disabled">
                <div className="module-card__icon" aria-hidden="true">📊</div>
                <div className="module-card__content">
                  <div className="module-card__title">Compliance Dashboard</div>
                  <div className="module-card__description">Today's status, calendar, check details</div>
                  <div className="module-card__badge">Coming in Phase 5F</div>
                </div>
              </div>
            </ErrorBoundary>
          )}

          <ErrorBoundary moduleName="Help Card">
            <div className="module-card module-card--disabled">
              <div className="module-card__icon" aria-hidden="true">?</div>
              <div className="module-card__content">
                <div className="module-card__title">Help &amp; Tutorial</div>
                <div className="module-card__description">How-to guide, FAQ, contextual help</div>
                <div className="module-card__badge">Coming in Phase 5C</div>
              </div>
            </div>
          </ErrorBoundary>

        </div>
      </section>
    </div>
  )
}

function StationBand({ station, colors, onChangeStation, showChange }) {
  return (
    <div
      className="station-band"
      style={{ background: colors?.primary ?? 'var(--color-brand)', color: colors?.text ?? '#ffffff' }}
      role="note"
      aria-label={`Current station: ${station.name}`}
    >
      <div className="station-band__info">
        <span className="station-band__icon" aria-hidden="true">📍</span>
        <div>
          <div className="station-band__name">{station.name}</div>
          {station.region && <div className="station-band__region">{station.region}</div>}
        </div>
      </div>
      {showChange && (
        <button
          className="station-band__change-btn"
          style={{ color: colors?.text ?? '#ffffff' }}
          onClick={onChangeStation}
          type="button"
          aria-label="Change station"
        >
          Change
        </button>
      )}
    </div>
  )
}

function StationPicker({ stations, currentStation, onSelect, onCancel }) {
  return (
    <div className="station-picker">
      <div className="station-picker__header">
        <h2 className="station-picker__title">
          {currentStation ? 'Change station' : 'Select your station'}
        </h2>
        {onCancel && (
          <button className="btn-text" onClick={onCancel} type="button">Cancel</button>
        )}
      </div>
      <div className="station-grid" role="radiogroup" aria-label="Select your station">
        {stations.map((s, idx) => {
          const sc = stationColor(s.name, idx)
          const isSelected = s.station_id === currentStation?.station_id
          return (
            <button
              key={s.station_id}
              role="radio"
              aria-checked={isSelected}
              className={`station-card ${isSelected ? 'station-card--selected' : ''}`}
              onClick={() => onSelect(s)}
              type="button"
              aria-label={`${s.name}${s.region ? `, ${s.region}` : ''}${isSelected ? ' — current' : ''}`}
            >
              <div className="station-card__color-bar" style={{ background: sc.primary }} aria-hidden="true" />
              <div className="station-card__body">
                <div className="station-card__name">{s.name}</div>
                {s.region && <div className="station-card__region">{s.region}</div>}
              </div>
              {isSelected && (
                <div className="station-card__check" style={{ color: sc.primary }} aria-hidden="true">✓</div>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function _timeOfDay() {
  const h = new Date().getHours()
  if (h < 12) return 'morning'
  if (h < 17) return 'afternoon'
  return 'evening'
}
