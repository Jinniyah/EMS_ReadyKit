/**
 * modules/admin/components/MembersScreen.jsx
 *
 * Full-screen members management — extracted from the old AdminScreen tab.
 * Logic unchanged; now a standalone screen with Back navigation.
 */

import React, { useState, useCallback } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { useApi } from '../../../shared/hooks/useApi.js'
import Spinner from '../../../shared/components/Spinner.jsx'
import ErrorBoundary from '../../../shared/components/ErrorBoundary.jsx'
import MemberList from './MemberList.jsx'
import AddMemberForm from './AddMemberForm.jsx'
import { adminApi } from '../api/adminApi.js'

export default function MembersScreen({ station, onBack }) {
  const { getToken } = useAuth()
  const [showAddForm, setShowAddForm] = useState(false)
  const [membersKey, setMembersKey]   = useState(0)

  const {
    data: members,
    isLoading,
    error,
  } = useApi(
    () => adminApi.getStationMembers(station.station_id, getToken),
    [station.station_id, membersKey]
  )

  const refreshMembers = useCallback(() => {
    setMembersKey(k => k + 1)
    setShowAddForm(false)
  }, [])

  return (
    <div className="admin-subscreen">
      <div className="admin-subscreen__header">
        <button className="admin-screen__back" onClick={onBack} type="button">
          ← Back
        </button>
        <div>
          <h2 className="admin-subscreen__title">Members</h2>
          <p className="admin-subscreen__station">{station.name}</p>
        </div>
      </div>

      <div className="admin-screen__section">
        <div className="admin-screen__section-header">
          <h3 className="admin-screen__section-title">
            {members ? `${members.length} member${members.length !== 1 ? 's' : ''}` : 'Members'}
          </h3>
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
              stationId={station.station_id}
              onMembersChanged={refreshMembers}
              onCancel={() => setShowAddForm(false)}
            />
          </ErrorBoundary>
        )}

        {isLoading ? (
          <Spinner label="Loading members…" size="sm" />
        ) : error ? (
          <div className="admin-screen__error" role="alert">
            ⚠ Could not load members — {error.message}
          </div>
        ) : (
          <ErrorBoundary moduleName="Member List">
            <MemberList
              stationId={station.station_id}
              members={members ?? []}
              onMembersChanged={refreshMembers}
            />
          </ErrorBoundary>
        )}
      </div>
    </div>
  )
}
