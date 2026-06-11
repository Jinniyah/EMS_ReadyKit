/**
 * settings/components/StationManagementSection.jsx
 * S-F6: Station management in Settings — retire station action (RET-F4).
 * Admin only.
 */
import React, { useState } from 'react'
import { retirementApi } from '../api/retirementApi.js'

function RetireConfirmSheet({ name, onConfirm, onCancel, saving, error }) {
  const [reason, setReason] = useState('')
  return (
    <div className="ems-confirm-overlay" role="dialog" aria-modal="true">
      <div className="ems-confirm-sheet">
        <p className="ems-confirm-sheet__title">Retire {name}?</p>
        <p className="ems-confirm-sheet__desc">
          This permanently retires the station. It will be deactivated and hidden from
          operational views. All data is preserved for audit history.
          This action cannot be undone.
        </p>
        <textarea
          placeholder="Reason for retirement (required)"
          value={reason}
          onChange={e => setReason(e.target.value)}
          maxLength={500}
        />
        {error && <p className="ems-confirm-sheet__error">{error}</p>}
        <div className="ems-confirm-sheet__actions">
          <button className="ems-confirm-sheet__cancel" onClick={onCancel} type="button">
            Cancel
          </button>
          <button
            className="ems-confirm-sheet__confirm"
            onClick={() => onConfirm(reason)}
            disabled={!reason.trim() || saving}
            type="button"
          >
            {saving ? 'Retiring…' : 'Retire Station'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function StationManagementSection({ station, getToken, onStationRetired }) {
  const [confirming, setConfirming] = useState(false)
  const [retiring, setRetiring]     = useState(false)
  const [error, setError]           = useState(null)

  if (station.retired_at) {
    return (
      <div className="settings-section">
        <h2 className="settings-section__heading">Station</h2>
        <div className="settings-row">
          <div className="settings-row__content">
            <div className="settings-row__label">{station.name}</div>
            <div className="settings-row__description">
              <span className="settings-retired-badge">Retired</span>
              {station.retirement_reason && ` — ${station.retirement_reason}`}
            </div>
          </div>
        </div>
      </div>
    )
  }

  async function handleRetire(reason) {
    if (!reason.trim()) return
    setRetiring(true)
    setError(null)
    try {
      await retirementApi.retireStation(station.station_id, reason, getToken)
      setConfirming(false)
      if (onStationRetired) onStationRetired()
    } catch (e) {
      setError(e.message)
    } finally {
      setRetiring(false)
    }
  }

  return (
    <>
      {confirming && (
        <RetireConfirmSheet
          name={station.name}
          onConfirm={handleRetire}
          onCancel={() => { setConfirming(false); setError(null) }}
          saving={retiring}
          error={error}
        />
      )}

      <div className="settings-section">
        <h2 className="settings-section__heading">Station</h2>
        <div className="settings-row">
          <div className="settings-row__content">
            <div className="settings-row__label">{station.name}</div>
            <div className="settings-row__description">
              {station.address}
              {station.call_sign ? ` · ${station.call_sign}` : ''}
            </div>
          </div>
          <div className="settings-row__control">
            <button
              className="settings-retire-btn"
              onClick={() => setConfirming(true)}
              type="button"
            >
              Retire Station
            </button>
          </div>
        </div>
        {error && <p className="settings-screen__error" role="alert">{error}</p>}
      </div>
    </>
  )
}
