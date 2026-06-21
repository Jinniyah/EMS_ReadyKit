/**
 * modules/admin/components/StationSuppliesScreen.jsx
 * SS-F1: Station Supplies admin screen — manage supply room shelves and their
 * par levels. Uses CompartmentParLevels per shelf. Admin only entry point;
 * reached from the "Station Supplies" nav card in AdminHome.
 */
import React, { useState, useCallback } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import { adminApi } from '../api/adminApi.js'
import { supplyApi } from '../../supply-room/api/supplyApi.js'
import CompartmentParLevels from './CompartmentParLevels.jsx'
import Spinner from '../../../shared/components/Spinner.jsx'

export default function StationSuppliesScreen({ station, onBack }) {
  const { getToken }                    = useAuth()
  const [compartmentsKey, setKey]       = useState(0)
  const [addingShelf, setAddingShelf]   = useState(false)
  const [newShelfName, setNewShelfName] = useState('')
  const [shelfError, setShelfError]     = useState(null)
  const [shelfSaving, setShelfSaving]   = useState(false)
  const [renamingId, setRenamingId]     = useState(null)
  const [renameLabel, setRenameLabel]   = useState('')
  const [renameError, setRenameError]   = useState(null)
  const [renameSaving, setRenameSaving] = useState(false)

  const { data: supplyRoom, isLoading: loadingRoom, error: roomError } = useApi(
    () => supplyApi.getSupplyRoom(station.station_id, getToken),
    [station.station_id]
  )

  const { data: compartments, isLoading: loadingComps, error: compsError } = useApi(
    () => supplyRoom ? adminApi.getLocationCompartments(supplyRoom.location_id, getToken) : Promise.resolve(null),
    [supplyRoom?.location_id, compartmentsKey]
  )

  const refresh = useCallback(() => setKey(k => k + 1), [])

  async function handleAddShelf() {
    const name = newShelfName.trim()
    if (!name) { setShelfError('Shelf name is required.'); return }
    setShelfSaving(true); setShelfError(null)
    try {
      await adminApi.createCompartment(supplyRoom.location_id, {
        location_id: supplyRoom.location_id,
        name,
        sort_order: (compartments?.length ?? 0) + 1,
        active: true,
      }, getToken)
      setNewShelfName('')
      setAddingShelf(false)
      refresh()
    } catch (e) {
      setShelfError(e.message)
    } finally {
      setShelfSaving(false)
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

  if (loadingRoom) return <Spinner label="Loading supply room…" />
  if (roomError) {
    return (
      <div className="admin-screen">
        <div className="admin-screen__header">
          <button className="admin-screen__back" onClick={onBack} type="button">← Back</button>
          <div className="admin-screen__title-block">
            <h1 className="admin-screen__title">Station Supplies</h1>
            <p className="admin-screen__subtitle">{station.name}</p>
          </div>
        </div>
        <div className="admin-screen__error">Supply room not set up. Go to Supply Room and set it up first.</div>
      </div>
    )
  }

  return (
    <div className="admin-screen">
      <div className="admin-screen__header">
        <button className="admin-screen__back" onClick={onBack} type="button">← Back</button>
        <div className="admin-screen__title-block">
          <h1 className="admin-screen__title">Station Supplies</h1>
          <p className="admin-screen__subtitle">{station.name}</p>
        </div>
      </div>

      {loadingComps ? (
        <Spinner label="Loading shelves…" />
      ) : compsError ? (
        <div className="admin-screen__error">Could not load shelves.</div>
      ) : (
        <div style={{ padding: '0 1rem 2rem' }}>
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
                      aria-label="New shelf name"
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
                locationId={supplyRoom.location_id}
                stationId={station.station_id}
              />
            </div>
          ))}

          {addingShelf ? (
            <div className="supply-shelf-section supply-shelf-section--add">
              <label className="assignment-edit-label">
                New shelf name
                <input
                  className="assignment-edit-input assignment-edit-input--wide"
                  value={newShelfName}
                  onChange={e => setNewShelfName(e.target.value)}
                  maxLength={100}
                  autoFocus
                  disabled={shelfSaving}
                  aria-label="New shelf name"
                />
              </label>
              {shelfError && <p className="assignment-error">{shelfError}</p>}
              <div className="assignment-edit-actions">
                <button className="btn btn--primary btn--sm" onClick={handleAddShelf} type="button" disabled={shelfSaving}>
                  {shelfSaving ? 'Adding…' : 'Add Shelf'}
                </button>
                <button className="btn btn--secondary btn--sm" onClick={() => { setAddingShelf(false); setShelfError(null) }} type="button" disabled={shelfSaving}>
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              className="btn btn--secondary"
              style={{ marginTop: '1rem' }}
              onClick={() => { setAddingShelf(true); setNewShelfName('') }}
              type="button"
            >
              + Add Shelf
            </button>
          )}
        </div>
      )}
    </div>
  )
}
