/**
 * modules/supply-room/index.jsx
 * Station supply inventory module.
 *
 * Landing: 2 large action cards (View Supplies, Count Supplies) +
 *          secondary text links (Receive New Stock, Transfer History).
 *
 * SR-F2: Replaced 4-section layout with 2-card layout.
 * SR-F6: Removed Restock Vehicle section and import.
 */
import React, { useEffect, useState } from 'react'
import { supplyApi } from './api/supplyApi.js'
import { useAuth } from '../../shared/hooks/useAuth.jsx'
import SupplyCatalogView from './components/SupplyCatalogView.jsx'
import ReceiveStockPanel  from './components/ReceiveStockPanel.jsx'
import TransferHistory    from './components/TransferHistory.jsx'
import UsageLogView       from './components/UsageLogView.jsx'
import './supply-room.css'

const PRIMARY_SECTIONS = [
  {
    key:   'VIEW',
    icon:  '📦',
    label: 'View Supplies',
    hint:  'Check what\'s on hand and correct any counts',
  },
  {
    key:   'COUNT',
    icon:  '✅',
    label: 'Count Supplies',
    hint:  'Walk through each shelf and record what you find',
  },
  {
    key:   'USAGE_LOG',
    icon:  '📋',
    label: 'Usage Log',
    hint:  'Items logged as used after calls',
  },
]

const SECONDARY_SECTIONS = [
  { key: 'RECEIVE', label: 'Receive New Stock' },
  { key: 'HISTORY', label: 'Transfer History' },
]

export default function SupplyRoomScreen({ station, onBack, onCountSupplies }) {
  const { getToken } = useAuth()
  const [activeSection, setActiveSection]   = useState(null)
  const [supplyRoom, setSupplyRoom]         = useState(null)
  const [roomLoading, setRoomLoading]       = useState(true)
  const [roomError, setRoomError]           = useState(null)
  const [roomMissing, setRoomMissing]       = useState(false)
  const [creating, setCreating]             = useState(false)
  const [createError, setCreateError]       = useState(null)
  const [catalogItems, setCatalogItems]     = useState([])
  const [catalogLoading, setCatalogLoading] = useState(false)
  const [catalogError, setCatalogError]     = useState(null)

  useEffect(() => {
    if (!station?.station_id) return
    setRoomLoading(true)
    setRoomMissing(false)
    setRoomError(null)
    supplyApi.getSupplyRoom(station.station_id, getToken)
      .then(loc => { setSupplyRoom(loc); setRoomLoading(false) })
      .catch(e  => {
        if (e.status === 404) {
          setRoomMissing(true)
        } else {
          setRoomError(e.message)
        }
        setRoomLoading(false)
      })
  }, [station, getToken])

  async function handleSetupSupplyRoom() {
    setCreating(true)
    setCreateError(null)
    try {
      const loc = await supplyApi.createSupplyRoom(station.station_id, getToken)
      setSupplyRoom(loc)
      setRoomMissing(false)
    } catch (e) {
      setCreateError(e.message)
    } finally {
      setCreating(false)
    }
  }

  useEffect(() => {
    if (!station?.station_id || !supplyRoom) return
    loadCatalog()
  }, [supplyRoom])

  function loadCatalog() {
    setCatalogLoading(true)
    setCatalogError(null)
    supplyApi.getCatalog(station.station_id, getToken)
      .then(items => { setCatalogItems(items); setCatalogLoading(false) })
      .catch(e    => { setCatalogError(e.message); setCatalogLoading(false) })
  }

  const lowCount = catalogItems.filter(i =>
    i.par_min != null && i.on_hand < i.par_min
  ).length
  const sectionLabel = [
    ...PRIMARY_SECTIONS,
    ...SECONDARY_SECTIONS,
  ].find(s => s.key === activeSection)?.label ?? null
  const onHeaderBack = activeSection ? () => setActiveSection(null) : onBack

  function handlePrimaryCard(key) {
    if (key === 'COUNT') {
      onCountSupplies?.(supplyRoom.location_id)
    } else {
      setActiveSection(key)
    }
  }

  // Header title — show section label or default
  const headerTitle = sectionLabel ?? (activeSection === 'VIEW' ? 'View Supplies' : 'Station Supplies')

  return (
    <div className="sr-screen">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="sr-header">
        <button
          className="sr-back-btn"
          onClick={onHeaderBack}
          type="button"
          aria-label={activeSection ? 'Back to Station Supplies menu' : 'Back to Home'}
        >
          {activeSection ? '← Back' : '← Home'}
        </button>
        <div className="sr-header__text">
          <h1 className="sr-header__title">{headerTitle}</h1>
          {station && !activeSection && (
            <p className="sr-header__station">{station.name}</p>
          )}
        </div>
        {lowCount > 0 && !activeSection && (
          <div className="sr-alert-badge" aria-live="polite">
            {lowCount} Low
          </div>
        )}
      </div>

      {/* ── Loading / error / not-set-up states ─────────────────────────────── */}
      {roomLoading && <div className="sr-center">Loading supply room…</div>}
      {roomError && (
        <div className="sr-error">
          <strong>Could not load supply room</strong>
          <p style={{ margin: '4px 0 0' }}>{roomError}</p>
        </div>
      )}
      {roomMissing && !roomLoading && (
        <div className="sr-setup">
          <p className="sr-setup__icon" aria-hidden="true">📦</p>
          <h2 className="sr-setup__title">Supply room not set up yet</h2>
          <p className="sr-setup__body">
            This station does not have a supply room configured.
            Tap the button below to create one, then use
            <strong> Receive New Stock</strong> to load your initial inventory.
          </p>
          {createError && (
            <p className="sr-setup__error" role="alert">{createError}</p>
          )}
          <button
            className="btn btn--primary btn--large sr-setup__btn"
            onClick={handleSetupSupplyRoom}
            disabled={creating}
            type="button"
          >
            {creating ? 'Setting up…' : 'Set Up Supply Room'}
          </button>
        </div>
      )}

      {/* ── Landing: 2 primary cards + secondary text links ─────────────────── */}
      {supplyRoom && !activeSection && (
        <div className="sr-body">
          <div className="sr-nav-cards">
            {PRIMARY_SECTIONS.map(s => {
              const badge = s.key === 'VIEW' && lowCount > 0
                ? `${lowCount} item${lowCount !== 1 ? 's' : ''} low or out of stock`
                : null
              return (
                <button
                  key={s.key}
                  className="sr-nav-card"
                  onClick={() => handlePrimaryCard(s.key)}
                  type="button"
                >
                  <span className="sr-nav-card__icon" aria-hidden="true">{s.icon}</span>
                  <div className="sr-nav-card__content">
                    <span className="sr-nav-card__label">{s.label}</span>
                    <span className="sr-nav-card__hint">{s.hint}</span>
                    {badge && (
                      <span className="sr-nav-card__badge">⚠ {badge}</span>
                    )}
                  </div>
                  <span className="sr-nav-card__arrow" aria-hidden="true">›</span>
                </button>
              )
            })}
          </div>

          <div className="sr-secondary-links">
            {SECONDARY_SECTIONS.map((s, idx) => (
              <React.Fragment key={s.key}>
                {idx > 0 && <span className="sr-secondary-link__sep" aria-hidden="true">·</span>}
                <button
                  className="sr-secondary-link"
                  onClick={() => setActiveSection(s.key)}
                  type="button"
                >
                  {s.label}
                </button>
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {/* ── Active section — full screen ────────────────────────────────────── */}
      {supplyRoom && activeSection && (
        <div className="sr-section">
          {activeSection === 'VIEW' && (
            <SupplyCatalogView
              stationId={station?.station_id}
              locationId={supplyRoom.location_id}
              items={catalogItems}
              loading={catalogLoading}
              error={catalogError}
              onRefresh={loadCatalog}
            />
          )}
          {activeSection === 'RECEIVE' && (
            <ReceiveStockPanel
              locationId={supplyRoom.location_id}
              stationId={station?.station_id}
              onStockAdded={loadCatalog}
            />
          )}
          {activeSection === 'HISTORY' && (
            <TransferHistory locationId={supplyRoom.location_id} />
          )}
          {activeSection === 'USAGE_LOG' && (
            <UsageLogView stationId={station?.station_id} />
          )}
        </div>
      )}

    </div>
  )
}
