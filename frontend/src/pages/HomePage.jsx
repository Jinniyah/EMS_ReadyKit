/**
 * pages/HomePage.jsx
 * Application home screen.
 *
 * Bug fix (post-Block-6):
 *   Station colors now use station.primary_color (DB value) when set,
 *   falling back to stationColor() palette. Previously the palette was
 *   always used regardless of what was saved in the DB.
 *
 *   Also: selectedStation is re-hydrated from the stations API response
 *   on every load rather than trusting the stale localStorage copy, so
 *   color changes made in admin are immediately reflected here.
 */
import React, { useState, useEffect, useCallback, lazy, Suspense } from 'react'
import { useAuth } from '../shared/hooks/useAuth.jsx'
import { useApi } from '../shared/hooks/useApi.js'
import { useDraftIndex } from '../shared/hooks/useDraft.js'
import { canAccess } from '../shared/utils/roleGuard.js'
import { useRoleMode } from '../shared/hooks/useRoleMode.jsx'
import { stationColor } from '../shared/utils/stationColors.js'
import ErrorBoundary from '../shared/components/ErrorBoundary.jsx'
import DraftBanner from '../modules/check-wizard/components/DraftBanner.jsx'
import Spinner from '../shared/components/Spinner.jsx'
import PendingAssignmentScreen from '../modules/admin/components/PendingAssignmentScreen.jsx'
import { checkApi } from '../modules/check-wizard/api/checkApi.js'
import { vehicleApi } from '../modules/vehicles/api/vehicleApi.js'

const CheckWizard          = lazy(() => import('../modules/check-wizard/index.jsx'))
const VehicleStatusScreen  = lazy(() => import('../modules/vehicles/index.jsx'))
const CheckHistoryScreen   = lazy(() => import('../modules/check-history/index.jsx'))
const SupervisorDashboard  = lazy(() => import('../modules/supervisor/index.jsx'))
const AdminScreen          = lazy(() => import('../modules/admin/index.jsx'))
const SupplyRoomScreen     = lazy(() => import('../modules/supply-room/index.jsx'))

const STATION_STORAGE_KEY = 'ems_selected_station_id'  // store ID only, not full object

/**
 * Resolve the effective color set for a station.
 * Priority: station.primary_color (DB) → stationColor() palette fallback.
 */
function resolveStationColors(station, index) {
  if (!station) return null
  const palette = stationColor(station.name, index)
  const primary = station.primary_color ?? palette.primary
  return { primary, text: palette.text, light: palette.light }
}

/**
 * VE-F5: Check all vehicles at the selected station for open repair requests.
 */
function useStationIssues(stationId, getToken) {
  const [issueState, setIssueState] = useState(null)

  const compute = useCallback(async () => {
    if (!stationId) { setIssueState(null); return }
    try {
      const vehicles = await vehicleApi.getStationVehicles(stationId, getToken)
      if (!vehicles?.length) { setIssueState(null); return }

      const allRepairs = await Promise.all(
        vehicles.map(v => vehicleApi.getRepairRequests(v.vehicle_id, getToken))
      )

      const active = allRepairs.flat().filter(
        r => r.status === 'OPEN' || r.status === 'IN_PROGRESS'
      )

      if (active.length === 0) { setIssueState(null); return }

      const hasOpen = active.some(r => r.status === 'OPEN')
      setIssueState(hasOpen ? 'issue' : 'needs-review')
    } catch {
      setIssueState(null)
    }
  }, [stationId, getToken])

  useEffect(() => { compute() }, [compute])

  useEffect(() => {
    window.addEventListener('focus', compute)
    return () => window.removeEventListener('focus', compute)
  }, [compute])

  return issueState
}

/** Persist only the station ID — re-hydrate from the API on load. */
function loadSavedStationId() {
  try {
    // Support old format (full object) and new format (ID only)
    const raw = localStorage.getItem(STATION_STORAGE_KEY)
    if (!raw) {
      // Try old key
      const old = localStorage.getItem('ems_selected_station')
      if (old) {
        const parsed = JSON.parse(old)
        return parsed?.station_id ?? null
      }
      return null
    }
    const parsed = JSON.parse(raw)
    // Handle both {station_id: N} and plain N
    return typeof parsed === 'number' ? parsed : (parsed?.station_id ?? null)
  } catch { return null }
}

function saveStationId(station) {
  try {
    localStorage.setItem(STATION_STORAGE_KEY, JSON.stringify(station.station_id))
  } catch { /* ignore */ }
}

export default function HomePage() {
  const { user, getToken } = useAuth()
  const { isCrewMode } = useRoleMode()

  const [activeWizard, setActiveWizard]       = useState(null)
  const [activeDraftKey, setActiveDraftKey]   = useState(null)
  const [activeModule, setActiveModule]       = useState(null)
  const [selectedStationId, setSelectedStationId] = useState(loadSavedStationId)
  const [pickingStation, setPickingStation]   = useState(false)

  const {
    data: stations,
    isLoading: loadingStations,
    error: stationsError,
  } = useApi(() => checkApi.getStations(getToken), [])

  // Re-hydrate selectedStation from the fresh API response every load.
  // This ensures primary_color changes made in admin are reflected immediately
  // without requiring a manual station re-selection.
  const selectedStation = stations?.find(s => s.station_id === selectedStationId) ?? null

  // Auto-select the only station when there's exactly one
  useEffect(() => {
    if (!selectedStationId && stations?.length === 1) {
      setSelectedStationId(stations[0].station_id)
      saveStationId(stations[0])
    }
  }, [stations, selectedStationId])

  const stationIdx = stations?.findIndex(s => s.station_id === selectedStationId) ?? 0
  const colors = resolveStationColors(selectedStation, stationIdx >= 0 ? stationIdx : 0)

  // Apply station color as CSS custom property on body
  useEffect(() => {
    if (colors) {
      document.body.style.setProperty('--station-primary', colors.primary)
      document.body.style.setProperty('--station-text',    colors.text)
    } else {
      document.body.style.setProperty('--station-primary', 'var(--color-brand)')
      document.body.style.setProperty('--station-text',    '#ffffff')
    }
    return () => {
      document.body.style.removeProperty('--station-primary')
      document.body.style.removeProperty('--station-text')
    }
  }, [colors])

  const draftGroups = useDraftIndex(selectedStationId ?? null)
  const issueState  = useStationIssues(selectedStationId ?? null, getToken)

  function handleSelectStation(station) {
    setSelectedStationId(station.station_id)
    saveStationId(station)
    setPickingStation(false)
  }

  function handleStartNew() {
    setActiveDraftKey(null)
    setActiveWizard('new')
  }

  function handleResume(key, draft) {
    if (draft.station_id && stations) {
      const draftStation = stations.find(s => s.station_id === draft.station_id)
      if (draftStation) {
        setSelectedStationId(draftStation.station_id)
        saveStationId(draftStation)
      }
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

  // ── Active modules ────────────────────────────────────────────────────────
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

  if (activeModule === 'history') {
    return (
      <ErrorBoundary moduleName="Check History">
        <Suspense fallback={<Spinner label="Loading…" />}>
          <CheckHistoryScreen
            station={selectedStation}
            onBack={() => setActiveModule(null)}
            onNavigateToVehicles={() => setActiveModule('vehicles')}
          />
        </Suspense>
      </ErrorBoundary>
    )
  }

  if (activeModule === 'admin') {
    return (
      <ErrorBoundary moduleName="Station Administration">
        <Suspense fallback={<Spinner label="Loading…" />}>
          <AdminScreen onBack={() => setActiveModule(null)} />
        </Suspense>
      </ErrorBoundary>
    )
  }

  if (activeModule === 'supervisor') {
    return (
      <ErrorBoundary moduleName="Supervisor Dashboard">
        <Suspense fallback={<Spinner label="Loading…" />}>
          <SupervisorDashboard
            station={selectedStation}
            onBack={() => setActiveModule(null)}
            onNavigateToVehicles={() => setActiveModule('vehicles')}
          />
        </Suspense>
      </ErrorBoundary>
    )
  }

  if (activeModule === 'supply-room') {
    return (
      <ErrorBoundary moduleName="Supply Room">
        <Suspense fallback={<Spinner label="Loading…" />}>
          <SupplyRoomScreen
            station={selectedStation}
            onBack={() => setActiveModule(null)}
          />
        </Suspense>
      </ErrorBoundary>
    )
  }

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
          stations?.length === 0 ? (
            <PendingAssignmentScreen />
          ) : (
            <StationPicker
              stations={stations ?? []}
              currentStationId={selectedStationId}
              onSelect={handleSelectStation}
              onCancel={selectedStation ? () => setPickingStation(false) : null}
            />
          )
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
                {issueState === 'issue' && (
                  <div className="module-card__issue-badge module-card__issue-badge--issue" role="status">
                    ⚠ Unresolved Issue
                  </div>
                )}
                {issueState === 'needs-review' && (
                  <div className="module-card__issue-badge module-card__issue-badge--needs-review" role="status">
                    ✓ Acknowledged
                  </div>
                )}
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

          {canAccess(user, 'supervisor') && !isCrewMode && (
            <ErrorBoundary moduleName="Admin Card">
              <div className="module-card">
                <div className="module-card__icon" aria-hidden="true">👥</div>
                <div className="module-card__content">
                  <div className="module-card__title">Station Administration</div>
                  <div className="module-card__description">Manage station members and access</div>
                </div>
                <button
                  className="btn btn--primary"
                  style={colors ? { background: colors.primary } : {}}
                  onClick={() => setActiveModule('admin')}
                  type="button"
                >
                  Open
                </button>
              </div>
            </ErrorBoundary>
          )}

          {canAccess(user, 'supervisor') && !isCrewMode && (
            <ErrorBoundary moduleName="Dashboard Card">
              <div className="module-card">
                <div className="module-card__icon" aria-hidden="true">📊</div>
                <div className="module-card__content">
                  <div className="module-card__title">Compliance Dashboard</div>
                  <div className="module-card__description">Today's status, FAIL alerts, check details</div>
                </div>
                <button
                  className="btn btn--primary"
                  style={colors ? { background: colors.primary } : {}}
                  onClick={() => setActiveModule('supervisor')}
                  disabled={!selectedStation}
                  type="button"
                >
                  Open
                </button>
              </div>
            </ErrorBoundary>
          )}

          {canAccess(user, 'supervisor') && !isCrewMode && (
            <ErrorBoundary moduleName="Supply Room Card">
              <div className="module-card">
                <div className="module-card__icon" aria-hidden="true">🏪</div>
                <div className="module-card__content">
                  <div className="module-card__title">Supply Room</div>
                  <div className="module-card__description">Stock levels, restock vehicles, receive shipments</div>
                </div>
                <button
                  className="btn btn--primary"
                  style={colors ? { background: colors.primary } : {}}
                  onClick={() => setActiveModule('supply-room')}
                  disabled={!selectedStation}
                  type="button"
                >
                  Open
                </button>
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

function StationPicker({ stations, currentStationId, onSelect, onCancel }) {
  return (
    <div className="station-picker">
      <div className="station-picker__header">
        <h2 className="station-picker__title">
          {currentStationId ? 'Change station' : 'Select your station'}
        </h2>
        {onCancel && (
          <button className="btn-text" onClick={onCancel} type="button">Cancel</button>
        )}
      </div>
      <div className="station-grid" role="radiogroup" aria-label="Select your station">
        {stations.map((s, idx) => {
          // Use DB primary_color if set, fall back to palette
          const palette    = stationColor(s.name, idx)
          const barColor   = s.primary_color ?? palette.primary
          const isSelected = s.station_id === currentStationId
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
              <div className="station-card__color-bar" style={{ background: barColor }} aria-hidden="true" />
              <div className="station-card__body">
                <div className="station-card__name">{s.name}</div>
                {s.region && <div className="station-card__region">{s.region}</div>}
              </div>
              {isSelected && (
                <div className="station-card__check" style={{ color: barColor }} aria-hidden="true">✓</div>
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
