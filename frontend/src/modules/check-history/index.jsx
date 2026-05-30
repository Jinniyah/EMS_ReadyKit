/**
 * modules/check-history/index.jsx
 * Check History screen.
 *
 * CH-F1: "My Checks" — responder's own submitted checks grouped by date
 * CH-F2: Check detail view (read-only for Responders)
 * CH-F3: Supervisor acknowledgement shown on detail
 * CH-F4: Supervisor history list — all checks at station, filterable
 * CH-F5: Soft-delete from detail view (Supervisor+)
 *
 * NOTE — "All Checks" tab (CH-F4):
 * The station-scoped history endpoint (B-E3) is not yet built.
 * Until it is, the All Checks tab calls GET /checks/daily/station/{id}/today
 * which returns all checks for the station for today only.
 * Full date-range history will be available once B-E3 is complete.
 */

import React, { useState } from 'react'
import { useAuth } from '../../shared/hooks/useAuth.jsx'
import { useApi } from '../../shared/hooks/useApi.js'
import { canAccess } from '../../shared/utils/roleGuard.js'
import Spinner from '../../shared/components/Spinner.jsx'
import ErrorBoundary from '../../shared/components/ErrorBoundary.jsx'
import CheckList from './components/CheckList.jsx'
import CheckDetail from './components/CheckDetail.jsx'
import { checkHistoryApi } from './api/checkHistoryApi.js'
import './check-history.css'

const STATUS_FILTERS = ['ALL', 'PASS', 'NEEDS_RESTOCK', 'FAIL']

export default function CheckHistoryScreen({ station, onBack, onNavigateToVehicles }) {
  const { user, getToken } = useAuth()
  const isSupervisor = canAccess(user, 'supervisor')

  const [activeTab, setActiveTab]         = useState(isSupervisor ? 'all' : 'mine')
  const [selectedCheck, setSelectedCheck] = useState(null)
  const [statusFilter, setStatusFilter]   = useState(isSupervisor ? 'FAIL' : 'ALL')
  const [deletedIds, setDeletedIds]       = useState(new Set())

  // My checks (all roles) — scoped to current user's own submissions
  const {
    data: myChecks,
    isLoading: loadingMine,
    error: errorMine,
    refetch: refetchMine,
  } = useApi(
    () => checkHistoryApi.getMyHistory(getToken),
    []
  )

  // All checks at station within a rolling 7-day window (Supervisor+ only).
  // Uses B-E3 date-range endpoint. Default (no params) returns today;
  // the compliance calendar (F-5F2) will add a date picker to this tab.
  const {
    data: allChecks,
    isLoading: loadingAll,
    error: errorAll,
    refetch: refetchAll,
  } = useApi(
    () => isSupervisor && activeTab === 'all'
      ? checkHistoryApi.getStationChecks(station.station_id, getToken)
      : Promise.resolve(null),
    [activeTab, isSupervisor]
  )

  // If a check is selected, show detail view
  if (selectedCheck) {
    return (
      <ErrorBoundary moduleName="Check Detail">
        <CheckDetail
          check={selectedCheck}
          onNavigateToVehicles={onNavigateToVehicles}
          onBack={() => {
            setSelectedCheck(null)
            refetchMine()
            refetchAll()
          }}
          onDeleted={() => {
            setDeletedIds(prev => new Set([...prev, selectedCheck.check_id]))
            setSelectedCheck(null)
            refetchMine()
            refetchAll()
          }}
        />
      </ErrorBoundary>
    )
  }

  const displayMine = (myChecks ?? []).filter(c => !deletedIds.has(c.check_id))
  const displayAll  = (allChecks ?? []).filter(c =>
    !deletedIds.has(c.check_id) &&
    (statusFilter === 'ALL' || c.status === statusFilter)
  )

  return (
    <div className="check-history-screen">

      {/* Header */}
      <div className="check-history-screen__header">
        <button className="btn-text check-history-screen__back" onClick={onBack} type="button">
          ← Back
        </button>
        <div className="check-history-screen__title-block">
          <h1 className="check-history-screen__title">Check History</h1>
          <p className="check-history-screen__subtitle">{station.name}</p>
        </div>
      </div>

      {/* Tab bar — only show "All Checks" tab to Supervisors */}
      {isSupervisor && (
        <div className="check-history-tabs" role="tablist">
          <button
            role="tab"
            aria-selected={activeTab === 'mine'}
            className={`check-history-tab ${activeTab === 'mine' ? 'check-history-tab--active' : ''}`}
            onClick={() => setActiveTab('mine')}
            type="button"
          >
            My Checks
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'all'}
            className={`check-history-tab ${activeTab === 'all' ? 'check-history-tab--active' : ''}`}
            onClick={() => setActiveTab('all')}
            type="button"
          >
            All Checks
          </button>
        </div>
      )}

      {/* My Checks tab */}
      {activeTab === 'mine' && (
        loadingMine ? <Spinner label="Loading your checks…" /> :
        errorMine   ? <ErrorCard message={errorMine.message} onRetry={refetchMine} /> :
        <CheckList
          checks={displayMine}
          onSelectCheck={setSelectedCheck}
          showPerformedBy={false}
        />
      )}

      {/* All Checks tab (Supervisor+) */}
      {activeTab === 'all' && (
        <div className="check-history-screen__all">
          {/* Status filter */}
          <div className="check-history-filters">
            {STATUS_FILTERS.map(f => (
              <button
                key={f}
                className={`check-filter-tab ${statusFilter === f ? 'check-filter-tab--active' : ''}`}
                onClick={() => setStatusFilter(f)}
                type="button"
              >
                {f === 'ALL' ? 'All' : f === 'NEEDS_RESTOCK' ? 'Restock' : f.charAt(0) + f.slice(1).toLowerCase()}
              </button>
            ))}
          </div>

          {loadingAll ? <Spinner label="Loading checks…" /> :
           errorAll   ? <ErrorCard message={errorAll.message} onRetry={refetchAll} /> :
           <CheckList
             checks={displayAll}
             onSelectCheck={setSelectedCheck}
             showPerformedBy={true}
           />}
        </div>
      )}
    </div>
  )
}

function ErrorCard({ message, onRetry }) {
  return (
    <div className="check-history-error" role="alert">
      <p>⚠ {message}</p>
      <button className="btn btn--secondary" onClick={onRetry} type="button">Try again</button>
    </div>
  )
}
