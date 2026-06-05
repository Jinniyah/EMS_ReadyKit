/**
 * modules/supply-room/index.jsx
 * Supply Room & Restocking module.
 *
 * Navigation model: vertical nav cards (one per section) → full-screen
 * section view with ← Back, matching the admin module's card pattern.
 * No horizontal tab bar — bad tap targets for tired users on phones.
 *
 * Sections:
 *   Stock Levels    — view all items and quantities (SUPPLY-F1)
 *   Restock Vehicle — move stock from supply room to a unit (SUPPLY-F2)
 *   Receive Stock   — add new stock, manual or CSV upload (SUPPLY-F3)
 *   History         — transfer log (SUPPLY-F4)
 */
import React, { useEffect, useState } from 'react'
import { supplyApi } from './api/supplyApi.js'
import { useAuth } from '../../shared/hooks/useAuth.jsx'
import StockSummaryView    from './components/StockSummaryView.jsx'
import RestockVehiclePanel from './components/RestockVehiclePanel.jsx'
import ReceiveStockPanel   from './components/ReceiveStockPanel.jsx'
import TransferHistory     from './components/TransferHistory.jsx'
import './supply-room.css'

const SECTIONS = [
  {
    key:   'STOCK',
    icon:  '📦',
    label: 'Stock Levels',
    hint:  'Check current inventory — quantities, lots, and low-stock alerts',
  },
  {
    key:   'RESTOCK',
    icon:  '🚑',
    label: 'Restock a Vehicle',
    hint:  'Move supplies from the supply room to a unit',
  },
  {
    key:   'RECEIVE',
    icon:  '📥',
    label: 'Receive New Stock',
    hint:  'Log incoming shipments by hand or CSV upload',
  },
  {
    key:   'HISTORY',
    icon:  '📋',
    label: 'Transfer History',
    hint:  'View all inbound and outbound transfers',
  },
]

export default function SupplyRoomScreen({ station, onBack }) {
  const { getToken } = useAuth()
  const [activeSection, setActiveSection] = useState(null)
  const [supplyRoom, setSupplyRoom]       = useState(null)
  const [roomLoading, setRoomLoading]     = useState(true)
  const [roomError, setRoomError]         = useState(null)
  const [stockItems, setStockItems]       = useState([])
  const [stockLoading, setStockLoading]   = useState(false)
  const [stockError, setStockError]       = useState(null)

  useEffect(() => {
    if (!station?.station_id) return
    setRoomLoading(true)
    supplyApi.getSupplyRoom(station.station_id, getToken)
      .then(loc => { setSupplyRoom(loc); setRoomLoading(false) })
      .catch(e  => { setRoomError(e.message); setRoomLoading(false) })
  }, [station, getToken])

  useEffect(() => {
    if (!supplyRoom?.location_id) return
    loadStock()
  }, [supplyRoom])

  function loadStock() {
    setStockLoading(true)
    setStockError(null)
    supplyApi.getStockSummary(supplyRoom.location_id, getToken)
      .then(items => { setStockItems(items); setStockLoading(false) })
      .catch(e    => { setStockError(e.message); setStockLoading(false) })
  }

  const lowCount    = stockItems.filter(i => i.status === 'LOW' || i.status === 'OUT').length
  const activeData  = SECTIONS.find(s => s.key === activeSection)
  const onHeaderBack = activeSection ? () => setActiveSection(null) : onBack

  return (
    <div className="sr-screen">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="sr-header">
        <button
          className="sr-back-btn"
          onClick={onHeaderBack}
          type="button"
          aria-label={activeSection ? 'Back to Supply Room menu' : 'Back to Home'}
        >
          {activeSection ? '← Back' : '← Home'}
        </button>
        <div className="sr-header__text">
          <h1 className="sr-header__title">
            {activeSection ? activeData.label : 'Supply Room'}
          </h1>
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

      {/* ── Loading / error for room itself ────────────────────────────────── */}
      {roomLoading && <div className="sr-center">Loading supply room…</div>}
      {roomError && (
        <div className="sr-error">
          <strong>Could not load supply room</strong>
          <p style={{ margin: '4px 0 0' }}>{roomError}</p>
        </div>
      )}

      {/* ── Landing: nav cards ─────────────────────────────────────────────── */}
      {supplyRoom && !activeSection && (
        <div className="sr-body">
          <div className="sr-nav-cards">
            {SECTIONS.map(s => {
              const badge = s.key === 'STOCK' && lowCount > 0
                ? `${lowCount} item${lowCount !== 1 ? 's' : ''} low or out of stock`
                : null
              return (
                <button
                  key={s.key}
                  className="sr-nav-card"
                  onClick={() => setActiveSection(s.key)}
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
        </div>
      )}

      {/* ── Active section — full screen ────────────────────────────────────── */}
      {supplyRoom && activeSection && (
        <div className="sr-section">
          {activeSection === 'STOCK' && (
            <StockSummaryView
              items={stockItems}
              loading={stockLoading}
              error={stockError}
              onRefresh={loadStock}
            />
          )}
          {activeSection === 'RESTOCK' && (
            <RestockVehiclePanel
              station={station}
              supplyRoomLocationId={supplyRoom.location_id}
              onDone={() => { setActiveSection(null); loadStock() }}
            />
          )}
          {activeSection === 'RECEIVE' && (
            <ReceiveStockPanel
              locationId={supplyRoom.location_id}
              onStockAdded={loadStock}
            />
          )}
          {activeSection === 'HISTORY' && (
            <TransferHistory locationId={supplyRoom.location_id} />
          )}
        </div>
      )}

    </div>
  )
}
