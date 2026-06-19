/**
 * modules/admin/components/MembersScreen.jsx
 *
 * Station Administration -> Members.
 *
 * Session AE (MERGE-1): consolidated from two places that previously did
 * overlapping, partially-broken member management:
 *   - Admin -> Members (this screen) used to be a simple flat list hitting
 *     adminApi.removeMember(stationId, userId) -- userId is an email string,
 *     but the backend route is /members/{member_id} (an integer primary key,
 *     per ACC-B7's multi-role redesign). Every removal here threw
 *     "Input should be a valid integer, unable to parse string as an integer".
 *   - Settings -> Team Members had the correct, fuller-featured
 *     implementation (multi-role grouping, edit name, CSV import) already
 *     calling the right member_id-based endpoints.
 *
 * Rather than fix the broken copy, member management now lives in exactly
 * one place: here. MemberManagementSection and EmailAlignmentSection were
 * moved over verbatim from modules/settings/. Settings no longer has any
 * member management UI -- it's reserved for admin-only configuration
 * (check workflow toggle, station/vehicle/location retirement).
 *
 * A Supervisor can manage their own station's members (add, edit name,
 * add additional roles, CSV import) without Administrator access -- the
 * underlying SUPERVISOR_PLUS endpoints already supported this; only the
 * UI was previously gating it oddly across two screens.
 */
import React from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { canAccess } from '../../../shared/utils/roleGuard.js'
import ErrorBoundary from '../../../shared/components/ErrorBoundary.jsx'
import MemberManagementSection from './MemberManagementSection.jsx'
import EmailAlignmentSection from './EmailAlignmentSection.jsx'

export default function MembersScreen({ station, onBack }) {
  const { user, getToken } = useAuth()
  const isAdmin = canAccess(user, 'administrator')

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

      <ErrorBoundary moduleName="Member Management">
        <MemberManagementSection station={station} getToken={getToken} />
      </ErrorBoundary>

      {isAdmin && (
        <ErrorBoundary moduleName="Email Alignment Check">
          <EmailAlignmentSection station={station} getToken={getToken} />
        </ErrorBoundary>
      )}
    </div>
  )
}
