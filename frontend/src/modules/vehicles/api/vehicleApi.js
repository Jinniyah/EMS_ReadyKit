/**
 * modules/vehicles/api/vehicleApi.js
 * API calls for Vehicle & Equipment Status module.
 */

import { apiGet, apiPost, apiPatch } from '../../../shared/api/client.js'

const BASE = '/api/v1'

export const vehicleApi = {
  /**
   * List all vehicles for a station (active AND inactive).
   * Used by the V&E Status screen so out-of-service vehicles are visible
   * and can be returned to service.
   */
  getStationVehicles: (stationId, getToken) =>
    apiGet(`${BASE}/stations/${stationId}/vehicles`, getToken),

  /**
   * List only active vehicles for a station.
   * Used by the check wizard — you can't start a check on an inactive vehicle.
   */
  getActiveStationVehicles: (stationId, getToken) =>
    apiGet(`${BASE}/stations/${stationId}/vehicles?active=true`, getToken),

  /** Mark a vehicle active or inactive (Supervisor+) */
  updateVehicleStatus: (vehicleId, payload, getToken) =>
    apiPatch(`${BASE}/vehicles/${vehicleId}`, payload, getToken),

  /** File a new repair request (all roles) */
  createRepairRequest: (vehicleId, payload, getToken) =>
    apiPost(`${BASE}/vehicles/${vehicleId}/repair-requests`, payload, getToken),

  /** Update repair request status (Supervisor+) */
  updateRepairRequest: (vehicleId, repairId, payload, getToken) =>
    apiPatch(`${BASE}/vehicles/${vehicleId}/repair-requests/${repairId}`, payload, getToken),

  /** List repair requests for a vehicle, optionally filtered by status */
  getRepairRequests: (vehicleId, getToken, statusFilter = null) => {
    const qs = statusFilter ? `?status=${statusFilter}` : ''
    return apiGet(`${BASE}/vehicles/${vehicleId}/repair-requests${qs}`, getToken)
  },
}
