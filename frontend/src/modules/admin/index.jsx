/**
 * modules/admin/index.jsx
 * Station Administration screen — membership management (B-ACCESS1 Phase 3).
 *
 * Shows all stations the current user is assigned to.
 * For each station: lists current members and allows adding/removing members.
 *
 * Access: Supervisor+ only (enforced in HomePage and by the API).
 */
import React, { useState, useCallback } from 'react'
import { useAuth } from '../../shared/hooks/useAuth.jsx'
import { useApi } from '../../shared/hooks/useApi.js'
import Spinner from '../../shared/components/Spinner.jsx'
import ErrorBoundary from '../../shared/components/ErrorBoundary.jsx'
import MemberList from './components/MemberList.jsx'
import AddMemberForm from './components/AddMemberForm.jsx'
import ItemCatalog from './components/ItemCatalog.jsx'
import { adminApi } from './api/adminApi.js'
import './admin.css'

const TABS = [
  { id: 'members', label: '👥 Members'      },
  { id: 'catalog', label: '📦 Item Catalog'  },
]

export default function AdminScreen({ onBack }) {
  const { getToken } = useAuth()
  const [activeTab, setActiveTab]             = useState('members')
  const [selectedStationId, setSelectedStationId] = useState(null)
  const [showAddForm, setShowAddForm]             = useState(false)
  const [membersKey, setMembersKey]               = useState(0)

  // Load stations this user manages
  const {
    data: stations,
    isLoading: loadingStations,
    error: stationsError,
  } = useApi(() => adminApi.getMyStations(getToken), [])

  // Auto-select first station once loaded
  React.useEffect(() => {
    if (stations?.length && !selectedStationId) {
      setSelectedStationId(stations[0].station_id)
    }
  }, [stations, selectedStationId])

  // Load members for selected station — re-fetches when membersKey changes
  const {
    data: members,
    isLoading: loadingMembers,
    error: membersError,
  } = useApi(
    () => selectedStationId
      ? adminApi.getStationMembers(selectedStationId, getToken)
      : Promise.resolve([]),
    [selectedStationId, membersKey]
  )

  const refreshMembers = useCallback(() => {
    setMembersKey(k => k + 1)
    setShowAddForm(false)
  }, [])

  const selectedStation = stations?.find(s => s.station_id === selectedStationId)

  return (
    <div className="admin-screen">

      {/* Header */}
      <div className="admin-screen__header">
        <button className="admin-screen__back" onClick={onBack} type="button">
          ← Home
        </button>
        <div className="admin-screen__title-block">
          <h1 className="admin-screen__title">Station Administration</h1>
          <p className="admin-screen__subtitle">Manage station membership</p>
        </div>
      </div>

      {/* Station selector */}
      {loadingStations ? (
        <Spinner label="Loading stations…" size="sm" />
      ) : stationsError ? (
        <div className="admin-screen__error" role="alert">
          ⚠ Could not load stations — {stationsError.message}
        </div>
      ) : (stations?.length ?? 0) === 0 ? (
        <div className="admin-screen__error" role="alert">
          You are not assigned to any stations.
        </div>
      ) : (
        <>
      {/* Tab bar */}
      <div className="admin-tabs" role="tablist" aria-label="Admin sections">
        {TABS.map(tab => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`admin-tab ${activeTab === tab.id ? 'admin-tab--active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Item Catalog tab */}
      {activeTab === 'catalog' && (
        <ErrorBoundary moduleName="Item Catalog">
          <ItemCatalog stationId={selectedStationId} />
        </ErrorBoundary>
      )}

      {/* Members tab */}
      {activeTab === 'members' && (
        <>
          {/* Station selector — vertical list matching station-card style */}
          {stations.length > 1 && (
            <div className="admin-station-list">
              {stations.map(s => (
                <button
                  key={s.station_id}
                  className={`admin-station-btn ${s.station_id === selectedStationId ? 'admin-station-btn--active' : ''}`}
                  onClick={() => {
                    setSelectedStationId(s.station_id)
                    setShowAddForm(false)
                  }}
                  type="button"
                >
                  <div className="admin-station-btn__bar" />
                  <span>{s.name}</span>
                  {s.station_id === selectedStationId && (
                    <span className="admin-station-btn__check" aria-hidden="true">✓</span>
                  )}
                </button>
              ))}
            </div>
          )}

          {/* Station name when only one station */}
          {stations.length === 1 && (
            <div className="admin-screen__station-name">{stations[0].name}</div>
          )}

          {/* Members section */}
          <div className="admin-screen__section">
            <div className="admin-screen__section-header">
              <h2 className="admin-screen__section-title">Members</h2>
              {!showAddForm && (
                <button
                  className="btn btn--primary btn--sm"
                  onClick={() => setShowAddForm(true)}
                  type="button"
                >
                  + Add member
                </button>
              )}
            </div>

            {showAddForm && (
              <ErrorBoundary moduleName="Add Member Form">
                <AddMemberForm
                  stationId={selectedStationId}
                  onMembersChanged={refreshMembers}
                  onCancel={() => setShowAddForm(false)}
                />
              </ErrorBoundary>
            )}

            {loadingMembers ? (
              <Spinner label="Loading members…" size="sm" />
            ) : membersError ? (
              <div className="admin-screen__error" role="alert">
                ⚠ Could not load members — {membersError.message}
              </div>
            ) : (
              <ErrorBoundary moduleName="Member List">
                <MemberList
                  stationId={selectedStationId}
                  members={members ?? []}
                  onMembersChanged={refreshMembers}
                />
              </ErrorBoundary>
            )}
          </div>
        </>
      )}
        </>
      )}
    </div>
  )
}
