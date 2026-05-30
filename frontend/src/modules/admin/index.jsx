/**
 * modules/admin/index.jsx
 * Station Administration — Option B redesign (ADMIN-UX1).
 *
 * Layout: station header → three large nav cards → dedicated sub-screens.
 * Mirrors the home screen module card pattern — zero new mental model.
 *
 * Sub-screens:
 *   members  → MembersScreen  (extracted from previous AdminScreen)
 *   catalog  → ItemCatalog    (full screen)
 *   vehicles → VehiclesScreen (new — replaces seed script)
 *
 * UX principles:
 *   - 60px minimum tap targets throughout
 *   - One task at a time — each section is a full screen
 *   - Station selector: plain header (1 station), stacked cards (2-3), search (4+)
 *   - "+ Add Station" at bottom, Admin only, low-prominence
 */
import React, { useState } from 'react'
import { useAuth } from '../../shared/hooks/useAuth.jsx'
import { useApi } from '../../shared/hooks/useApi.js'
import { canAccess } from '../../shared/utils/roleGuard.js'
import Spinner from '../../shared/components/Spinner.jsx'
import ErrorBoundary from '../../shared/components/ErrorBoundary.jsx'
import MembersScreen from './components/MembersScreen.jsx'
import ItemCatalog from './components/ItemCatalog.jsx'
import VehiclesScreen from './components/VehiclesScreen.jsx'
import { adminApi } from './api/adminApi.js'
import './admin.css'

// ── Admin home — station selector + nav cards ─────────────────────────────────

function AdminHome({ stations, selectedId, onSelectStation, onBack, onNavigate }) {
  const { user }    = useAuth()
  const isAdmin     = canAccess(user, 'administrator')
  const [search, setSearch] = useState('')

  const station = stations.find(s => s.station_id === selectedId)

  // Station selector display mode
  const showSearch  = stations.length >= 4
  const showCards   = stations.length >= 2 && stations.length < 4
  const showHeader  = stations.length === 1

  const filteredStations = showSearch
    ? stations.filter(s => s.name.toLowerCase().includes(search.toLowerCase()))
    : stations

  const NAV_CARDS = [
    { id: 'members',  icon: '👥', label: 'Members',      hint: 'Manage crew access' },
    { id: 'catalog',  icon: '📦', label: 'Item Catalog', hint: 'Add and manage inventory items' },
    { id: 'vehicles', icon: '🚑', label: 'Vehicles',     hint: 'Add vehicles and compartments' },
  ]

  return (
    <div className="admin-screen">
      {/* Header */}
      <div className="admin-screen__header">
        <button className="admin-screen__back" onClick={onBack} type="button">
          ← Home
        </button>
        <div className="admin-screen__title-block">
          <h1 className="admin-screen__title">Station Administration</h1>
        </div>
      </div>

      {/* Station selector */}
      {showHeader && (
        <div className="admin-station-header">
          <span className="admin-station-header__label">Managing</span>
          <span className="admin-station-header__name">{stations[0].name}</span>
        </div>
      )}

      {showCards && (
        <div className="admin-station-list">
          {stations.map(s => (
            <button
              key={s.station_id}
              className={`admin-station-btn ${s.station_id === selectedId ? 'admin-station-btn--active' : ''}`}
              onClick={() => onSelectStation(s.station_id)}
              type="button"
            >
              <div className="admin-station-btn__bar" />
              <span>{s.name}</span>
              {s.station_id === selectedId && (
                <span className="admin-station-btn__check" aria-hidden="true">✓</span>
              )}
            </button>
          ))}
        </div>
      )}

      {showSearch && (
        <div className="admin-station-search-wrap">
          <input
            className="admin-station-search"
            type="search"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search stations…"
            aria-label="Search stations"
          />
          <div className="admin-station-list">
            {filteredStations.map(s => (
              <button
                key={s.station_id}
                className={`admin-station-btn ${s.station_id === selectedId ? 'admin-station-btn--active' : ''}`}
                onClick={() => onSelectStation(s.station_id)}
                type="button"
              >
                <div className="admin-station-btn__bar" />
                <span>{s.name}</span>
                {s.station_id === selectedId && (
                  <span className="admin-station-btn__check" aria-hidden="true">✓</span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Nav cards */}
      {station && (
        <div className="admin-nav-cards">
          {NAV_CARDS.map(card => (
            <button
              key={card.id}
              type="button"
              className="admin-nav-card"
              onClick={() => onNavigate(card.id, station)}
            >
              <span className="admin-nav-card__icon" aria-hidden="true">{card.icon}</span>
              <div className="admin-nav-card__content">
                <span className="admin-nav-card__label">{card.label}</span>
                <span className="admin-nav-card__hint">{card.hint}</span>
              </div>
              <span className="admin-nav-card__arrow" aria-hidden="true">›</span>
            </button>
          ))}
        </div>
      )}

      {/* Add Station — Admin only, low-prominence */}
      {isAdmin && (
        <div className="admin-add-station-wrap">
          <button type="button" className="admin-add-station-btn">
            + Add Station
          </button>
        </div>
      )}
    </div>
  )
}

// ── AdminScreen — router ──────────────────────────────────────────────────────

export default function AdminScreen({ onBack }) {
  const { getToken } = useAuth()
  const [activeSection, setActiveSection]       = useState(null)
  const [activeStation, setActiveStation]       = useState(null)
  const [selectedStationId, setSelectedStationId] = useState(null)

  const {
    data: stations,
    isLoading,
    error,
  } = useApi(() => adminApi.getMyStations(getToken), [])

  // Auto-select first station on load — only if nothing selected yet
  React.useEffect(() => {
    if (stations?.length && !selectedStationId) {
      setSelectedStationId(stations[0].station_id)
    }
  }, [stations, selectedStationId])

  function handleNavigate(section, station) {
    setActiveSection(section)
    setActiveStation(station)
  }

  // Back preserves selectedStationId — user returns to the station they were on
  function handleBack() {
    setActiveSection(null)
    setActiveStation(null)
  }

  // ── Loading / error ────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="admin-screen">
        <div className="admin-screen__header">
          <button className="admin-screen__back" onClick={onBack} type="button">← Home</button>
          <div className="admin-screen__title-block">
            <h1 className="admin-screen__title">Station Administration</h1>
          </div>
        </div>
        <Spinner label="Loading stations…" />
      </div>
    )
  }

  if (error || !stations?.length) {
    return (
      <div className="admin-screen">
        <div className="admin-screen__header">
          <button className="admin-screen__back" onClick={onBack} type="button">← Home</button>
          <div className="admin-screen__title-block">
            <h1 className="admin-screen__title">Station Administration</h1>
          </div>
        </div>
        <div className="admin-screen__error" role="alert">
          {error ? `⚠ ${error.message}` : 'You are not assigned to any stations.'}
        </div>
      </div>
    )
  }

  // ── Sub-screens ────────────────────────────────────────────────────────────

  if (activeSection === 'members' && activeStation) {
    return (
      <ErrorBoundary moduleName="Members">
        <MembersScreen station={activeStation} onBack={handleBack} />
      </ErrorBoundary>
    )
  }

  if (activeSection === 'catalog' && activeStation) {
    return (
      <div className="admin-subscreen">
        <div className="admin-subscreen__header">
          <button className="admin-screen__back" onClick={handleBack} type="button">
            ← Back
          </button>
          <div>
            <h2 className="admin-subscreen__title">Item Catalog</h2>
            <p className="admin-subscreen__station">{activeStation.name}</p>
          </div>
        </div>
        <ErrorBoundary moduleName="Item Catalog">
          <ItemCatalog stationId={activeStation.station_id} />
        </ErrorBoundary>
      </div>
    )
  }

  if (activeSection === 'vehicles' && activeStation) {
    return (
      <ErrorBoundary moduleName="Vehicles">
        <VehiclesScreen station={activeStation} onBack={handleBack} />
      </ErrorBoundary>
    )
  }

  // ── Home ───────────────────────────────────────────────────────────────────

  return (
    <AdminHome
      stations={stations}
      selectedId={selectedStationId}
      onSelectStation={setSelectedStationId}
      onBack={onBack}
      onNavigate={handleNavigate}
    />
  )
}
