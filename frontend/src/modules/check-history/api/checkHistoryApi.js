/**
 * modules/check-history/api/checkHistoryApi.js
 * API calls for the Check History module.
 */

import { apiDelete, apiGet, apiPatch, apiDeleteWithBody, ApiError } from '../../../shared/api/client.js'

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
   * Supervisor "All Checks" tab -- checks for a station within a date range.
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

  /** CH-B2: Full check detail -- Responders own only, Supervisor+ any */
  getCheckDetail: (checkId, getToken) =>
    apiGet(`${BASE}/checks/daily/${checkId}/detail`, getToken),

  /** B-E2: Supervisor acknowledges a check with corrective action */
  acknowledgeCheck: (checkId, correctiveAction, getToken) =>
    apiPatch(`${BASE}/checks/daily/${checkId}/acknowledge`, { corrective_action: correctiveAction }, getToken),

  /** CH-B3: Supervisor+ soft-deletes a check with mandatory reason */
  softDeleteCheck: (checkId, deletionReason, getToken) =>
    apiDeleteWithBody(`${BASE}/checks/daily/${checkId}`, { deletion_reason: deletionReason }, getToken),

  /** CH-B5: List soft-deleted checks for a station (Supervisor+) */
  getDeletedChecks: (stationId, getToken) =>
    apiGet(`${BASE}/checks/daily/deleted?station_id=${stationId}`, getToken),

  /** CH-B6: Restore a soft-deleted check (Supervisor+) */
  restoreCheck: (checkId, getToken) =>
    apiPatch(`${BASE}/checks/daily/${checkId}/restore`, {}, getToken),

  /** CH-B4: Permanently hard-delete a soft-deleted check (Admin only) */
  forceDeleteCheck: (checkId, getToken) =>
    apiDelete(`${BASE}/checks/daily/${checkId}/force`, getToken),

  /** F-5G3a: Active vehicles + jump bags + supply room, for the export filter panel */
  getStationVehicles: (stationId, getToken) =>
    apiGet(`${BASE}/stations/${stationId}/vehicles`, getToken),

  getStationLocations: (stationId, getToken) =>
    apiGet(`${BASE}/stations/${stationId}/locations`, getToken),

  getSupplyRoom: (stationId, getToken) =>
    apiGet(`${BASE}/stations/${stationId}/supply-room`, getToken).catch(() => null),

  /**
   * F-5G3a: Download a compliance CSV export. Raw fetch (not apiGet, which
   * is JSON-only) -- same deliberate exception supplyApi.js already uses for
   * its template download. Unlike that existing pattern, this DOES check
   * res.ok before treating the body as a blob, so a non-2xx response (e.g.
   * the 422 for an out-of-range date pick, or picking nothing to export)
   * surfaces the server's real message instead of silently downloading a
   * broken "CSV" of the JSON error body.
   */
  exportChecks: async (
    stationId,
    getToken,
    { from, to, format, wholeStation, vehicleIds = [], locationIds = [] }
  ) => {
    const token = getToken ? await getToken() : null
    const headers = { Accept: 'text/csv' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    const params = new URLSearchParams()
    params.set('from', from)
    params.set('to', to)
    params.set('format', format)
    if (wholeStation) {
      params.set('whole_station', 'true')
    } else {
      vehicleIds.forEach(id => params.append('vehicle_ids', id))
      locationIds.forEach(id => params.append('location_ids', id))
    }

    let res
    try {
      res = await fetch(`${BASE}/checks/daily/station/${stationId}/export?${params}`, { headers })
    } catch {
      throw new ApiError(0, 'No connection — check your internet and try again.', null)
    }

    if (!res.ok) {
      let detail = null
      try { detail = (await res.json()).detail } catch { /* body wasn't JSON */ }
      const message = typeof detail === 'string' && detail
        ? detail
        : `Export failed (HTTP ${res.status}). Please try again.`
      throw new ApiError(res.status, message, detail)
    }

    const blob = await res.blob()
    const disposition = res.headers.get('Content-Disposition') || ''
    const match = disposition.match(/filename="?([^"]+)"?/)
    const filename = match ? match[1] : `compliance_${format}_${from}_to_${to}.csv`
    return { blob, filename }
  },
}
