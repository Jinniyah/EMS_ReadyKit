/**
 * modules/settings/api/membersApi.js
 * Station membership API calls (ACC-B6, ACC-B7, ACC-B8, LAUNCH-OPS9).
 */
import { apiGet, apiPost, apiPatch, apiDelete, apiUpload } from '../../../shared/api/client.js'

export const membersApi = {
  /** List all active members at a station. */
  listMembers: (stationId, getToken) =>
    apiGet(`/api/v1/stations/${stationId}/members`, getToken),

  /** Add a member with a specific role. */
  addMember: (stationId, payload, getToken) =>
    apiPost(`/api/v1/stations/${stationId}/members`, payload, getToken),

  /** Update a member's preferred name (by member_id). */
  updateMember: (stationId, memberId, payload, getToken) =>
    apiPatch(`/api/v1/stations/${stationId}/members/${memberId}`, payload, getToken),

  /** Remove a specific role row from a member (soft delete by member_id). */
  removeMember: (stationId, memberId, getToken) =>
    apiDelete(`/api/v1/stations/${stationId}/members/${memberId}`, getToken),

  /** Download CSV import template. */
  templateUrl: (stationId) =>
    `/api/v1/stations/${stationId}/members/import/template`,

  /** Bulk import members from a CSV file. */
  importCsv: (stationId, file, getToken) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiUpload(`/api/v1/stations/${stationId}/members/import`, formData, getToken)
  },

  /**
   * LAUNCH-OPS9: Run the email alignment diagnostic for a station.
   * Flags StationMember rows whose user_id doesn't look like a valid email.
   * Read-only — Admin only.
   */
  checkEmailAlignment: (stationId, getToken) =>
    apiGet(`/api/v1/admin/email-alignment-check?station_id=${stationId}`, getToken),
}
