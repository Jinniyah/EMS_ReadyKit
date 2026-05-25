/**
 * modules/admin/api/adminApi.js
 * API calls for station membership management (B-ACCESS1 Phase 3).
 */
import { apiGet, apiPost, apiPatch, apiDelete } from '../../../shared/api/client.js'

export const adminApi = {
  /** Stations the current user is assigned to */
  getMyStations: (getToken) =>
    apiGet('/api/v1/stations/my', getToken),

  /** List members of a station (Supervisor+) */
  getStationMembers: (stationId, getToken) =>
    apiGet(`/api/v1/stations/${stationId}/members`, getToken),

  /** Add a user to a station */
  addMember: (stationId, payload, getToken) =>
    apiPost(`/api/v1/stations/${stationId}/members`, payload, getToken),

  /** Update a member's role or preferred name */
  updateMember: (stationId, userId, payload, getToken) =>
    apiPatch(`/api/v1/stations/${stationId}/members/${encodeURIComponent(userId)}`, payload, getToken),

  /** Remove a member from a station (soft delete) */
  removeMember: (stationId, userId, getToken) =>
    apiDelete(`/api/v1/stations/${stationId}/members/${encodeURIComponent(userId)}`, getToken),
}
