/**
 * modules/admin/index.jsx
 * Station Administration — Option B redesign (ADMIN-UX1).
 *
 * Post-Block-6 additions:
 *   - Each station button has an "Edit" gear (⚙) that opens an inline edit form
 *   - Edit form: name, address, region, call sign, color — same fields as Add
 *   - Deactivate button with a one-tap confirm — soft-deletes the station
 *   - Station list auto-reloads and selects next station after deactivate
 *
 * Bug fixes:
 *   - create_station now auto-adds admin as member (backend fix)
 *   - Station bars always show a color (stationColor fallback)
 *   - Selection border now wraps the ENTIRE button+gear row (not just left half)
 */
import React, { useState } from 'react'
import { useAuth } from '../../shared/hooks/useAuth.jsx'
import { useApi } from '../../shared/hooks/useApi.js'
import { canAccess } from '../../shared/utils/roleGuard.js'
import { stationColor } from '../../shared/utils/stationColors.js'
import Spinner from '../../shared/components/Spinner.jsx'
import ErrorBoundary from '../../shared/components/ErrorBoundary.jsx'
import ColorPickerWidget from '../../shared/components/ColorPickerWidget.jsx'
import MembersScreen from './components/MembersScreen.jsx'
import ItemCatalog from './components/ItemCatalog.jsx'
import VehiclesScreen from './components/VehiclesScreen.jsx'
import StationSuppliesScreen from './components/StationSuppliesScreen.jsx'
import PortableLocationsScreen from './components/PortableLocationsScreen.jsx'
import { adminApi } from './api/adminApi.js'
import './admin.css'

// ── StationForm — shared by Add and Edit ──────────────────────────────────────

function StationForm({ initial, onSaved, onCancel, onDeactivate }) {
  const { getToken } = useAuth()
  const isEdit = !!initial

  const [form, setForm] = useState({
    name:          initial?.name          ?? '',
    address:       initial?.address       ?? '',
    region:        initial?.region        ?? '',
    call_sign:     initial?.call_sign     ?? '',
    primary_color: initial?.primary_color ?? null,
  })
  const [errors, setErrors]               = useState({})
  const [saving, setSaving]               = useState(false)
  const [serverError, setServerError]     = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting]           = useState(false)

  function set(field, value) {
    setForm(f => ({ ...f, [field]: value }))
    setErrors(e => ({ ...e, [field]: null }))
  }

  function validate() {
    const e = {}
    if (!form.name.trim())    e.name    = 'Station name is required.'
    if (!form.address.trim()) e.address = 'Address is required.'
    if (!form.region.trim())  e.region  = 'Region is required.'
    return e
  }

  async function handleSubmit(ev) {
    ev.preventDefault()
    const e = validate()
    if (Object.keys(e).length) { setErrors(e); return }
    setSaving(true); setServerError(null)
    try {
      const payload = {
        name:          form.name.trim(),
        address:       form.address.trim(),
        region:        form.region.trim(),
        call_sign:     form.call_sign.trim() || null,
        primary_color: form.primary_color || null,
        active:        true,
      }
      const station = isEdit
        ? await adminApi.updateStation(initial.station_id, payload, getToken)
        : await adminApi.createStation(payload, getToken)
      onSaved(station)
    } catch (err) {
      setServerError(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleDeactivate() {
    setDeleting(true)
    try {
      await adminApi.deactivateStation(initial.station_id, getToken)
      onDeactivate()
    } catch (err) {
      setServerError(err.message)
      setDeleting(false)
      setConfirmDelete(false)
    }
  }

  return (
    <div className="add-station-form">
      <h3 className="add-station-form__title">
        {isEdit ? `Edit — ${initial.name}` : 'New Station'}
      </h3>

      {serverError && (
        <p className="add-station-form__error" role="alert">{serverError}</p>
      )}

      <div className="vehicle-form__field">
        <label className="vehicle-form__label">
          Station name <span aria-hidden="true">*</span>
        </label>
        <input
          className={`vehicle-form__input ${errors.name ? 'vehicle-form__input--error' : ''}`}
          value={form.name}
          onChange={e => set('name', e.target.value)}
          placeholder="e.g. Newberg Township Station 1"
          maxLength={100}
          autoFocus
          disabled={saving || deleting}
        />
        {errors.name && <p className="vehicle-form__error">{errors.name}</p>}
      </div>

      <div className="vehicle-form__field">
        <label className="vehicle-form__label">
          Address <span aria-hidden="true">*</span>
        </label>
        <input
          className={`vehicle-form__input ${errors.address ? 'vehicle-form__input--error' : ''}`}
          value={form.address}
          onChange={e => set('address', e.target.value)}
          placeholder="e.g. 100 Fire Station Dr, Newberg Township, MI 48183"
          maxLength={255}
          disabled={saving || deleting}
        />
        {errors.address && <p className="vehicle-form__error">{errors.address}</p>}
      </div>

      <div className="vehicle-form__row">
        <div className="vehicle-form__field">
          <label className="vehicle-form__label">
            Region <span aria-hidden="true">*</span>
          </label>
          <input
            className={`vehicle-form__input ${errors.region ? 'vehicle-form__input--error' : ''}`}
            value={form.region}
            onChange={e => set('region', e.target.value)}
            placeholder="e.g. Downriver"
            maxLength={100}
            disabled={saving || deleting}
          />
          {errors.region && <p className="vehicle-form__error">{errors.region}</p>}
        </div>

        <div className="vehicle-form__field">
          <label className="vehicle-form__label">
            Call sign <span className="vehicle-form__hint-inline">(optional)</span>
          </label>
          <input
            className="vehicle-form__input"
            value={form.call_sign}
            onChange={e => set('call_sign', e.target.value)}
            placeholder="e.g. DFD"
            maxLength={20}
            disabled={saving || deleting}
          />
        </div>
      </div>

      <div className="add-station-form__color-row">
        <ColorPickerWidget
          value={form.primary_color}
          onChange={hex => set('primary_color', hex)}
          label="Station color (optional)"
          showInherit={false}
          disabled={saving || deleting}
        />
        <p className="add-station-form__color-hint">
          Sets the header and button color.
        </p>
      </div>

      <div className="vehicle-form__actions">
        <button
          type="button"
          className="btn btn--primary btn--full"
          onClick={handleSubmit}
          disabled={saving || deleting}
        >
          {saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Station'}
        </button>
        <button
          type="button"
          className="btn btn--secondary btn--full"
          onClick={onCancel}
          disabled={saving || deleting}
        >
          Cancel
        </button>
      </div>

      {/* Deactivate — edit mode only */}
      {isEdit && onDeactivate && (
        <div className="station-form__deactivate">
          {confirmDelete ? (
            <div className="station-form__deactivate-confirm">
              <p className="station-form__deactivate-warn">
                This will hide the station and all its data from the UI.
                This action can be reversed by contacting an administrator.
              </p>
              <div className="vehicle-form__row">
                <button
                  type="button"
                  className="btn btn--danger btn--full"
                  onClick={handleDeactivate}
                  disabled={deleting}
                >
                  {deleting ? 'Deactivating…' : 'Yes, deactivate station'}
                </button>
                <button
                  type="button"
                  className="btn btn--secondary btn--full"
                  onClick={() => setConfirmDelete(false)}
                  disabled={deleting}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              className="station-form__deactivate-btn"
              onClick={() => setConfirmDelete(true)}
            >
              Deactivate this station…
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ── StationButton ─────────────────────────────────────────────────────────────

function stationBarColor(station, index) {
  return station.primary_color ?? stationColor(station.name, index).primary
}

/**
 * The selection border lives on the WRAP element so it goes all the way around
 * both the station name button and the ⚙ gear button.
 *
 * --sel-color is set as an inline CSS variable on the wrap so each station
 * can have its own color without a separate CSS class per station.
 */
function StationButton({ station, index, isSelected, onClick, onEdit }) {
  const barColor = stationBarColor(station, index)
  return (
    <div
      className={`admin-station-btn-wrap ${isSelected ? 'admin-station-btn-wrap--selected' : ''}`}
      style={isSelected ? { '--sel-color': barColor } : undefined}
    >
      <button
        className={`admin-station-btn ${isSelected ? 'admin-station-btn--active' : ''}`}
        onClick={onClick}
        type="button"
      >
        <div className="admin-station-btn__bar" style={{ background: barColor }} />
        <span>{station.name}</span>
        {station.call_sign && (
          <span className="admin-station-btn__call-sign">{station.call_sign}</span>
        )}
        {isSelected && (
          <span className="admin-station-btn__check" style={{ color: barColor }} aria-hidden="true">✓</span>
        )}
      </button>
      <button
        type="button"
        className="admin-station-btn__edit"
        onClick={e => { e.stopPropagation(); onEdit() }}
        aria-label={`Edit ${station.name}`}
        title="Edit station"
      >
        ⚙
      </button>
    </div>
  )
}

// ── AdminHome ─────────────────────────────────────────────────────────────────

function AdminHome({ stations, selectedId, onSelectStation, onBack, onNavigate, onStationsChanged }) {
  const { user } = useAuth()
  const isAdmin  = canAccess(user, 'administrator')

  const [search, setSearch]                 = useState('')
  const [showAddForm, setShowAddForm]       = useState(false)
  const [editingStation, setEditingStation] = useState(null)

  const station    = stations.find(s => s.station_id === selectedId)
  const showSearch = stations.length >= 4
  const showCards  = stations.length >= 2 && stations.length < 4
  const showHeader = stations.length === 1

  const filteredStations = showSearch
    ? stations.filter(s => s.name.toLowerCase().includes(search.toLowerCase()))
    : stations

  const NAV_CARDS = [
    { id: 'members',   icon: '👥', label: 'Members',            hint: 'Manage crew access' },
    { id: 'catalog',   icon: '📦', label: 'Item Catalog',       hint: 'Add and manage inventory items' },
    { id: 'vehicles',  icon: '🚑', label: 'Vehicles',           hint: 'Add vehicles and compartments' },
    { id: 'portable',  icon: '🎒', label: 'Jump Bags',          hint: 'Manage portable locations and compartments' },
    { id: 'supplies',  icon: '🏪', label: 'Station Supplies',   hint: 'Manage supply room shelves and items' },
  ]

  function handleSaved(s) {
    setShowAddForm(false)
    setEditingStation(null)
    onStationsChanged(s)
  }

  function handleDeactivated() {
    setEditingStation(null)
    onStationsChanged(null)
  }

  // ── Edit form ─────────────────────────────────────────────────────────────
  if (editingStation) {
    return (
      <div className="admin-screen">
        <div className="admin-screen__header">
          <button className="admin-screen__back" onClick={() => setEditingStation(null)} type="button">
            ← Back
          </button>
          <div className="admin-screen__title-block">
            <h1 className="admin-screen__title">Station Administration</h1>
          </div>
        </div>
        <ErrorBoundary moduleName="Edit Station">
          <StationForm
            initial={editingStation}
            onSaved={handleSaved}
            onCancel={() => setEditingStation(null)}
            onDeactivate={handleDeactivated}
          />
        </ErrorBoundary>
      </div>
    )
  }

  // ── Add form ──────────────────────────────────────────────────────────────
  if (showAddForm) {
    return (
      <div className="admin-screen">
        <div className="admin-screen__header">
          <button className="admin-screen__back" onClick={() => setShowAddForm(false)} type="button">
            ← Back
          </button>
          <div className="admin-screen__title-block">
            <h1 className="admin-screen__title">Station Administration</h1>
          </div>
        </div>
        <ErrorBoundary moduleName="Add Station">
          <StationForm
            initial={null}
            onSaved={handleSaved}
            onCancel={() => setShowAddForm(false)}
            onDeactivate={null}
          />
        </ErrorBoundary>
      </div>
    )
  }

  return (
    <div className="admin-screen">
      <div className="admin-screen__header">
        <button className="admin-screen__back" onClick={onBack} type="button">← Home</button>
        <div className="admin-screen__title-block">
          <h1 className="admin-screen__title">Station Administration</h1>
        </div>
      </div>

      {/* Single station header */}
      {showHeader && (
        <div className="admin-station-header">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <span className="admin-station-header__label">Managing</span>
              <span className="admin-station-header__name">{stations[0].name}</span>
            </div>
            {isAdmin && (
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={() => setEditingStation(stations[0])}
              >
                ⚙ Edit
              </button>
            )}
          </div>
        </div>
      )}

      {/* 2–3 stations: card list */}
      {showCards && (
        <div className="admin-station-list">
          {stations.map((s, idx) => (
            <StationButton
              key={s.station_id}
              station={s}
              index={idx}
              isSelected={s.station_id === selectedId}
              onClick={() => onSelectStation(s.station_id)}
              onEdit={() => isAdmin && setEditingStation(s)}
            />
          ))}
        </div>
      )}

      {/* 4+ stations: search + card list */}
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
            {filteredStations.map((s) => (
              <StationButton
                key={s.station_id}
                station={s}
                index={stations.indexOf(s)}
                isSelected={s.station_id === selectedId}
                onClick={() => onSelectStation(s.station_id)}
                onEdit={() => isAdmin && setEditingStation(s)}
              />
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

      {/* Add Station — Admin only */}
      {isAdmin && (
        <div className="admin-add-station-wrap">
          <button
            type="button"
            className="admin-add-station-btn"
            onClick={() => setShowAddForm(true)}
          >
            + Add Station
          </button>
        </div>
      )}
    </div>
  )
}

// ── AdminScreen — top-level router ────────────────────────────────────────────

export default function AdminScreen({ onBack }) {
  const { getToken } = useAuth()
  const [activeSection, setActiveSection]         = useState(null)
  const [activeStation, setActiveStation]         = useState(null)
  const [selectedStationId, setSelectedStationId] = useState(null)
  const [stationsKey, setStationsKey]             = useState(0)

  const { data: stations, isLoading, error } = useApi(
    () => adminApi.getMyStations(getToken),
    [stationsKey]
  )

  React.useEffect(() => {
    if (stations?.length && !selectedStationId) {
      setSelectedStationId(stations[0].station_id)
    }
  }, [stations, selectedStationId])

  function handleNavigate(section, station) {
    setActiveSection(section)
    setActiveStation(station)
  }

  function handleBack() {
    setActiveSection(null)
    setActiveStation(null)
  }

  function handleStationsChanged(station) {
    setSelectedStationId(station ? station.station_id : null)
    setStationsKey(k => k + 1)
  }

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

  if (error) {
    return (
      <div className="admin-screen">
        <div className="admin-screen__header">
          <button className="admin-screen__back" onClick={onBack} type="button">← Home</button>
          <div className="admin-screen__title-block">
            <h1 className="admin-screen__title">Station Administration</h1>
          </div>
        </div>
        <div className="admin-screen__error" role="alert">⚠ {error.message}</div>
      </div>
    )
  }

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
          <button className="admin-screen__back" onClick={handleBack} type="button">← Back</button>
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

  if (activeSection === 'supplies' && activeStation) {
    return (
      <ErrorBoundary moduleName="Station Supplies">
        <StationSuppliesScreen station={activeStation} onBack={handleBack} />
      </ErrorBoundary>
    )
  }

  if (activeSection === 'portable' && activeStation) {
    return (
      <ErrorBoundary moduleName="Portable Locations">
        <PortableLocationsScreen station={activeStation} onBack={handleBack} />
      </ErrorBoundary>
    )
  }

  if (!stations?.length) {
    return (
      <div className="admin-screen">
        <div className="admin-screen__header">
          <button className="admin-screen__back" onClick={onBack} type="button">← Home</button>
          <div className="admin-screen__title-block">
            <h1 className="admin-screen__title">Station Administration</h1>
          </div>
        </div>
        <div className="admin-screen__error" role="alert">
          You are not assigned to any stations.
        </div>
        <div className="admin-add-station-wrap">
          <ErrorBoundary moduleName="Add Station">
            <StationForm
              initial={null}
              onSaved={s => handleStationsChanged(s)}
              onCancel={onBack}
              onDeactivate={null}
            />
          </ErrorBoundary>
        </div>
      </div>
    )
  }

  return (
    <AdminHome
      stations={stations}
      selectedId={selectedStationId}
      onSelectStation={setSelectedStationId}
      onBack={onBack}
      onNavigate={handleNavigate}
      onStationsChanged={handleStationsChanged}
    />
  )
}
