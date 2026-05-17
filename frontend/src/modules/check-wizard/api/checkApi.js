/**
 * modules/check-wizard/api/checkApi.js
 * API calls for the check wizard module.
 * All calls go through the shared authenticated client.
 */
import { apiGet, apiPost } from '../../../shared/api/client.js'

export const checkApi = {
  /** Vehicles at a station the user can check */
  getVehicles: (stationId, getToken) =>
    apiGet(`/api/v1/stations/${stationId}/vehicles`, getToken),

  /** All stations (needed to derive stationId for responder) */
  getStations: (getToken) =>
    apiGet('/api/v1/stations', getToken),

  /** Inventory location for a vehicle (VEHICLE type) */
  getLocations: (getToken) =>
    apiGet('/api/v1/inventory/locations', getToken),

  /** Compartments at a location, sorted by sort_order */
  getCompartments: (locationId, getToken) =>
    apiGet(`/api/v1/inventory/locations/${locationId}/compartments`, getToken),

  /** Par levels at a location — gives quantity_needed per item */
  getParLevels: (locationId, getToken) =>
    apiGet(`/api/v1/inventory/locations/${locationId}/par-levels`, getToken),

  /** Stock lots at a location — for expiry data and lot_id */
  getStockLots: (locationId, getToken) =>
    apiGet(`/api/v1/inventory/locations/${locationId}/stock`, getToken),

  /** Item catalog — for check_type, measurement_minimum, recurrence_days */
  getItems: (getToken) =>
    apiGet('/api/v1/items', getToken),

  /** Submit a completed daily check */
  submitCheck: (payload, getToken) =>
    apiPost('/api/v1/checks/daily', payload, getToken),

  /** Existing checks for a vehicle (to detect duplicate) */
  getVehicleChecks: (vehicleId, getToken) =>
    apiGet(`/api/v1/checks/daily/vehicle/${vehicleId}`, getToken),
}
