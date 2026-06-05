/**
 * modules/supply-room/api/supplyApi.js
 * API calls for the Supply Room & Restocking module.
 */

import { apiGet, apiPost, apiUpload } from '../../../shared/api/client.js'

const BASE = '/api/v1'

export const supplyApi = {
  /** Get the STATION_SUPPLY_ROOM location for a station */
  getSupplyRoom: (stationId, getToken) =>
    apiGet(`${BASE}/stations/${stationId}/supply-room`, getToken),

  /** Aggregate stock summary for a location (items, quantities, par status) */
  getStockSummary: (locationId, getToken) =>
    apiGet(`${BASE}/inventory/locations/${locationId}/stock-summary`, getToken),

  /** Move quantity from one location to another */
  transfer: (payload, getToken) =>
    apiPost(`${BASE}/inventory/transfer`, payload, getToken),

  /** Transfer history for a location (both inbound and outbound) */
  getTransferHistory: (locationId, getToken) =>
    apiGet(`${BASE}/inventory/locations/${locationId}/transfers`, getToken),

  /** Add a single stock lot to a location (GUI receive flow) */
  receiveLot: (payload, getToken) =>
    apiPost(`${BASE}/inventory/lots`, payload, getToken),

  /** Bulk receive via CSV upload */
  receiveCsv: (locationId, file, getToken) => {
    const fd = new FormData()
    fd.append('file', file)
    return apiUpload(`${BASE}/inventory/locations/${locationId}/receive-stock/csv`, fd, getToken)
  },

  /** Download the CSV receive template as a blob URL */
  getTemplateBlobUrl: async (getToken) => {
    const token = getToken ? await getToken() : null
    const headers = { Accept: 'text/csv' }
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`${BASE}/inventory/receive-stock/template`, { headers })
    const blob = await res.blob()
    return URL.createObjectURL(blob)
  },

  /** List all compartments for a location */
  getCompartments: (locationId, getToken) =>
    apiGet(`${BASE}/inventory/locations/${locationId}/compartments`, getToken),

  /** All inventory locations for a station — used to resolve vehicle location_id */
  getStationLocations: (stationId, getToken) =>
    apiGet(`${BASE}/inventory/locations?station_id=${stationId}`, getToken),
}
