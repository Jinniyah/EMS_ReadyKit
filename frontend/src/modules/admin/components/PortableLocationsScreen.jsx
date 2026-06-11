/**
 * modules/admin/components/PortableLocationsScreen.jsx
 * ADMIN-F7: Full CRUD for portable locations (Jump Bags / JUMP_BAG type).
 * List → create → rename + compartment + par level management.
 * Admin only.
 */
import React, { useState, useCallback } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import { adminApi } from '../api/adminApi.js'
import CompartmentParLevels from './CompartmentParLevels.jsx'
import Spinner from '../../../shared/components/Spinner.jsx'

// ── ShelfManager — compartments + par levels for one portable location ────────

function ShelfManager({ location, getToken }) {
  const [key, setKey]                   = useState(0)
  const [addingComp, setAddingComp]     = useState(false)
  const [compName, setCompName]         = useState('')
  const [compError, setCompError]       = useState(null)
  const [compSaving, setCompSaving]     = useState(false)
  const [renamingId, setRenamingId]     = useState(null)
  const [renameLabel, setRenameLabel]   = useState('')
  const [renameError, setRenameError]   = useState(null)
  const [renameSaving, setRenameSaving] = useState(false)

  const { data: compartments, isLoading, error } = useApi(
    () => adminApi.getLocationCompartments(location.location_id, getToken),
    [location.location_id, key]
  )

  const refresh = useCallback(() => setKey(k => k + 1), [])

  async function handleAddComp() {
    const name = compName.trim()
    if (!name) { setCompError('Compartment name is required.'); return }
    setCompSaving(true); setCompError(null)
    try {
      await adminApi.createCompartment(location.location_id, {
        location_id: location.location_id,
        name,
        sort_order: (compartments?.length ?? 0) + 1,
        active: true,
      }, getToken)
      setCompName('')
      setAddingComp(false)
      refresh()
    } catch (e) {
      setCompError(e.message)
    } finally {
      setCompSaving(false)
    }
  }

  async function handleRename() {
    const label = renameLabel.trim()
    if (!label) { setRenameError('Name is required.'); return }
    setRenameSaving(true); setRenameError(null)
    try {
      await adminApi.updateCompartment(renamingId, { name: label }, getToken)
      setRenamingId(null)
      refresh()
    } catch (e) {
      setRenameError(e.message)
    } finally {
      setRenameSaving(false)
    }
  }

  if (isLoading) return <Spinner label="Loading compartments…" />
  if (error) return <p className="assignment-error">Could not load compartments.</p>

  return (
    <div style={{ marginTop: '0.5rem' }}>
      {(compartments ?? []).map(comp => (
        <div key={comp.compartment_id} className="supply-shelf-section">
          <div className="supply-shelf-section__header">
            {renamingId === comp.compartment_id ? (
              <div className="supply-shelf-section__rename-row">
                <input
                  className="assignment-edit-input assignment-edit-input--wide"
                  value={renameLabel}
                  onChange={e => setRenameLabel(e.target.value)}
                  maxLength={100}
                  autoFocus
                  disabled={renameSaving}
                  aria-label="New compartment name"
                />
                {renameError && <p className="assignment-error">{renameError}</p>}
                <div className="assignment-edit-actions">
                  <button className="btn btn--primary btn--sm" onClick={handleRename} type="button" disabled={renameSaving}>
                    {renameSaving ? 'Saving…' : 'Save'}
                  </button>
                  <button className="btn btn--secondary btn--sm" onClick={() => setRenamingId(null)} type="button" disabled={renameSaving}>
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <span className="supply-shelf-section__name">{comp.name}</span>
                <button
                  className="btn btn--secondary btn--sm"
                  type="button"
                  onClick={() => { setRenamingId(comp.compartment_id); setRenameLabel(comp.name); setRenameError(null) }}
                >
                  Rename
                </button>
              </>
            )}
          </div>
          <CompartmentParLevels
            compartmentId={comp.compartment_id}
            locationId={location.location_id}
          />
        </div>
      ))}

      {addingComp ? (
        <div className="supply-shelf-section supply-shelf-section--add">
          <label className="assignment-edit-label">
            Compartment name
            <input
              className="assignment-edit-input assignment-edit-input--wide"
              value={compName}
              onChange={e => setCompName(e.target.value)}
              maxLength={100}
              autoFocus
              disabled={compSaving}
              aria-label="New compartment name"
            />
          </label>
          {compError && <p className="assignment-error">{compError}</p>}
          <div className="assignment-edit-actions">
            <button className="btn btn--primary btn--sm" onClick={handleAddComp} type="button" disabled={compSaving}>
              {compSaving ? 'Adding…' : 'Add Compartment'}
            </button>
            <button className="btn btn--secondary btn--sm" onClick={() => { setAddingComp(false); setCompError(null) }} type="button" disabled={compSaving}>
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          className="btn btn--secondary btn--sm"
          style={{ marginTop: '0.5rem' }}
          onClick={() => { setAddingComp(true); setCompName('') }}
          type="button"
        >
          + Add Compartment
        </button>
      )}
    </div>
  )
}

// ── PortableLocationsScreen ───────────────────────────────────────────────────

export default function PortableLocationsScreen({ station, onBack }) {
  const { getToken }                      = useAuth()
  const [locKey, setLocKey]               = useState(0)
  const [expandedId, setExpandedId]       = useState(null)
  const [addingLoc, setAddingLoc]         = useState(false)
  const [newLocLabel, setNewLocLabel]     = useState('')
  const [locError, setLocError]           = useState(null)
  const [locSaving, setLocSaving]         = useState(false)
  const [renamingLocId, setRenamingLocId] = useState(null)
  const [renameLocLabel, setRenameLocLabel] = useState('')
  const [renameLocError, setRenameLocError] = useState(null)
  const [renameLocSaving, setRenameLocSaving] = useState(false)

  const { data: allLocations, isLoading, error } = useApi(
    () => adminApi.getStationLocations(station.station_id, getToken),
    [station.station_id, locKey]
  )

  const portableLocations = (allLocations ?? []).filter(
    l => (l.location_type === 'JUMP_BAG' || l.location_type === 'EQUIPMENT') && !l.retired_at
  )

  const refresh = useCallback(() => setLocKey(k => k + 1), [])

  async function handleAddLocation() {
    const label = newLocLabel.trim()
    if (!label) { setLocError('Name is required.'); return }
    setLocSaving(true); setLocError(null)
    try {
      await adminApi.createPortableLocation({
        location_type: 'JUMP_BAG',
        station_id: station.station_id,
        label,
      }, getToken)
      setNewLocLabel('')
      setAddingLoc(false)
      refresh()
    } catch (e) {
      setLocError(e.message)
    } finally {
      setLocSaving(false)
    }
  }

  async function handleRenameLocation() {
    const label = renameLocLabel.trim()
    if (!label) { setRenameLocError('Name is required.'); return }
    setRenameLocSaving(true); setRenameLocError(null)
    try {
      await adminApi.renameLocation(renamingLocId, label, getToken)
      setRenamingLocId(null)
      refresh()
    } catch (e) {
      setRenameLocError(e.message)
    } finally {
      setRenameLocSaving(false)
    }
  }

  return (
    <div className="admin-screen">
      <div className="admin-screen__header">
        <button className="admin-screen__back" onClick={onBack} type="button">← Back</button>
        <div className="admin-screen__title-block">
          <h1 className="admin-screen__title">Portable Locations</h1>
          <p className="admin-screen__subtitle">{station.name}</p>
        </div>
      </div>

      {isLoading ? (
        <Spinner label="Loading locations…" />
      ) : error ? (
        <div className="admin-screen__error">Could not load locations.</div>
      ) : (
        <div style={{ padding: '0 1rem 2rem' }}>
          {portableLocations.length === 0 && !addingLoc && (
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '1rem' }}>
              No portable locations configured. Add a Jump Bag below.
            </p>
          )}

          {portableLocations.map(loc => (
            <div key={loc.location_id} className="supply-shelf-section" style={{ marginBottom: '1rem' }}>
              <div className="supply-shelf-section__header">
                {renamingLocId === loc.location_id ? (
                  <div className="supply-shelf-section__rename-row">
                    <input
                      className="assignment-edit-input assignment-edit-input--wide"
                      value={renameLocLabel}
                      onChange={e => setRenameLocLabel(e.target.value)}
                      maxLength={150}
                      autoFocus
                      disabled={renameLocSaving}
                      aria-label="New location name"
                    />
                    {renameLocError && <p className="assignment-error">{renameLocError}</p>}
                    <div className="assignment-edit-actions">
                      <button className="btn btn--primary btn--sm" onClick={handleRenameLocation} type="button" disabled={renameLocSaving}>
                        {renameLocSaving ? 'Saving…' : 'Save'}
                      </button>
                      <button className="btn btn--secondary btn--sm" onClick={() => setRenamingLocId(null)} type="button" disabled={renameLocSaving}>
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <button
                      className="supply-shelf-section__name supply-shelf-section__toggle"
                      type="button"
                      onClick={() => setExpandedId(v => v === loc.location_id ? null : loc.location_id)}
                      aria-expanded={expandedId === loc.location_id}
                    >
                      {loc.label}
                      <span aria-hidden="true" style={{ marginLeft: '0.5rem' }}>
                        {expandedId === loc.location_id ? '▲' : '▼'}
                      </span>
                    </button>
                    <button
                      className="btn btn--secondary btn--sm"
                      type="button"
                      onClick={() => { setRenamingLocId(loc.location_id); setRenameLocLabel(loc.label); setRenameLocError(null) }}
                    >
                      Rename
                    </button>
                  </>
                )}
              </div>

              {expandedId === loc.location_id && (
                <ShelfManager location={loc} getToken={getToken} />
              )}
            </div>
          ))}

          {addingLoc ? (
            <div className="supply-shelf-section supply-shelf-section--add">
              <label className="assignment-edit-label">
                Location name (e.g. "Unit 712 Jump Bag")
                <input
                  className="assignment-edit-input assignment-edit-input--wide"
                  value={newLocLabel}
                  onChange={e => setNewLocLabel(e.target.value)}
                  maxLength={150}
                  autoFocus
                  disabled={locSaving}
                  aria-label="New portable location name"
                />
              </label>
              {locError && <p className="assignment-error">{locError}</p>}
              <div className="assignment-edit-actions">
                <button className="btn btn--primary btn--sm" onClick={handleAddLocation} type="button" disabled={locSaving}>
                  {locSaving ? 'Adding…' : 'Add Location'}
                </button>
                <button className="btn btn--secondary btn--sm" onClick={() => { setAddingLoc(false); setLocError(null) }} type="button" disabled={locSaving}>
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              className="btn btn--secondary"
              style={{ marginTop: '0.5rem' }}
              onClick={() => { setAddingLoc(true); setNewLocLabel('') }}
              type="button"
            >
              + Add Jump Bag / Portable Location
            </button>
          )}
        </div>
      )}
    </div>
  )
}
