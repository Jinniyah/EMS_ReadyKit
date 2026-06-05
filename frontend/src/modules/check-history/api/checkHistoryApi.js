/**
 * modules/check-history/api/checkHistoryApi.js
 * API calls for the Check History module.
 */

import { apiGet, apiPatch, apiDeleteWithBody } from '../../../shared/api/client.js'

const BASE = '/api/v1'

export const checkHistoryApi = {
  /** CH-B1: Current user's submitted checks, most recent first, scoped to station */
  getMyHistory: (getToken, { stationId, from, to } = {}) => {
    const params = new URLSearchParams()
    if (stationId) params.set('station_id', stationId)
    if (from)      params.set('from', from)
    if (to)        params.set('to', to)
    const qs = params.toString() ? `?${params}` : ''
    return apiGet(`${BASE}/checks/daily/my-history${qs}`, getToken)
  },

  /**
   * Supervisor "All Checks" tab — checks for a station within a date range.
   * B-E3: GET /checks/daily/station/{id}?from=&to=
   * If from/to are omitted, backend defaults to today.
   */
  getStationChecks: (stationId, getToken, { from, to } = {}) => {
    const params = new URLSearchParams()
    if (from) params.set('from', from)
    if (to)   params.set('to', to)
    const qs = params.toString() ? `?${params}` : ''
    return apiGet(`${BASE}/checks/daily/station/${stationId}${qs}`, getToken)
  },

  /**
   * @deprecated Use getStationChecks() — kept for any callers still on the
   * today-only path until the compliance calendar is built (F-5F2).
   */
  getStationChecksToday: (stationId, getToken) =>
    apiGet(`${BASE}/checks/daily/station/${stationId}/today`, getToken),

  /** CH-B2: Full check detail — Responders own only, Supervisor+ any */
  getCheckDetail: (checkId, getToken) =>
    apiGet(`${BASE}/checks/daily/${checkId}/detail`, getToken),

  /** B-E2: Supervisor acknowledges a check with corrective action */
  acknowledgeCheck: (checkId, correctiveAction, getToken) =>
    apiPatch(`${BASE}/checks/daily/${checkId}/acknowledge`, { corrective_action: correctiveAction }, getToken),

  /** CH-B3: Supervisor+ soft-deletes a check with mandatory reason */
  softDeleteCheck: (checkId, deletionReason, getToken) =>
    apiDeleteWithBody(`${BASE}/checks/daily/${checkId}`, { deletion_reason: deletionReason }, getToken),
}
