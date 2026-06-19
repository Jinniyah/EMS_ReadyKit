/**
 * modules/settings/index.jsx
 * S-F1/S-F3: Station settings — allow_check_modification toggle.
 * S-F6: Station management (Admin) — retire station (RET-F4).
 * S-F7: Vehicle management (Admin) — retire vehicle/location (RET-F1/F2).
 * RET-F5: Retired items list (Admin).
 * ACC-B6/B7/B8: Member management — add, edit, multi-role, CSV import.
 * LAUNCH-OPS9: Email alignment check (Admin only).
 * Visible to Supervisor+.
 */
import React, { useState } from 'react'
import { useAuth } from '../../shared/hooks/useAuth.jsx'
import { useApi } from '../../shared/hooks/useApi.js'
import { canAccess } from '../../shared/utils/roleGuard.js'
import { settingsApi } from './api/settingsApi.js'
import MemberManagementSection from './components/MemberManagementSection.jsx'
import EmailAlignmentSection from './components/EmailAlignmentSection.jsx'
import VehicleManagementSection from './components/VehicleManagementSection.jsx'
import StationManagementSection from './components/StationManagementSection.jsx'
import RetiredListSection from './components/RetiredListSection.jsx'
import Spinner from '../../shared/components/Spinner.jsx'
import './settings.css'

export default function SettingsScreen({ station, onBack }) {
  const { user, getToken } = useAuth()
  const isAdmin = canAccess(user, 'administrator')
  const [key, setKey]       = useState(0)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)

  const { data: settings, isLoading, error } = useApi(
    () => settingsApi.getSettings(station.station_id, getToken),
    [station.station_id, key]
  )

  async function handleToggle(newValue) {
    if (!isAdmin) return
    setSaving(true)
    setSaveError(null)
    try {
      await settingsApi.updateSettings(
        station.station_id,
        { allow_check_modification: newValue },
        getToken
      )
      setKey(k => k + 1)
    } catch (e) {
      setSaveError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="settings-screen">
      <div className="settings-screen__header">
        <button className="settings-screen__back" onClick={onBack} type="button">
          ← Back
        </button>
        <div className="settings-screen__title-block">
          <h1 className="settings-screen__title">Settings</h1>
          <p className="settings-screen__subtitle">{station.name}</p>
        </div>
      </div>

      {isLoading ? (
        <Spinner label="Loading settings…" />
      ) : error ? (
        <div className="settings-screen__error">Could not load settings.</div>
      ) : settings ? (
        <>
          <div className="settings-screen__body">
            {/* Check workflow toggle */}
            <div className="settings-section">
              <h2 className="settings-section__heading">Check Workflow</h2>
              <div className="settings-row">
                <div className="settings-row__content">
                  <div className="settings-row__label">Allow check modification</div>
                  <div className="settings-row__description">
                    When on, crew can edit a submitted check to add comments or correct errors.
                    Turn off to make all submitted checks fully locked.
                  </div>
                </div>
                <div className="settings-row__control">
                  {isAdmin ? (
                    <button
                      className={`settings-toggle ${settings.allow_check_modification ? 'settings-toggle--on' : 'settings-toggle--off'}`}
                      onClick={() => handleToggle(!settings.allow_check_modification)}
                      disabled={saving}
                      type="button"
                      aria-pressed={settings.allow_check_modification}
                      aria-label="Allow check modification"
                    >
                      {saving ? '…' : settings.allow_check_modification ? 'On' : 'Off'}
                    </button>
                  ) : (
                    <span className={`settings-value ${settings.allow_check_modification ? 'settings-value--on' : 'settings-value--off'}`}>
                      {settings.allow_check_modification ? 'On' : 'Off'}
                    </span>
                  )}
                </div>
              </div>
              {saveError && (
                <p className="settings-screen__error" role="alert">{saveError}</p>
              )}
            </div>

            {!isAdmin && (
              <p className="settings-screen__readonly-note">
                Contact your administrator to change these settings.
              </p>
            )}

            {/* Member management — Supervisor+ */}
            <MemberManagementSection
              station={station}
              getToken={getToken}
            />
          </div>

          {/* Admin-only sections */}
          {isAdmin && (
            <div className="settings-screen__body" style={{ paddingTop: 0 }}>
              <EmailAlignmentSection
                station={station}
                getToken={getToken}
              />
              <StationManagementSection
                station={station}
                getToken={getToken}
                onStationRetired={onBack}
              />
              <VehicleManagementSection
                station={station}
                getToken={getToken}
              />
              <RetiredListSection
                station={station}
                getToken={getToken}
              />
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}
