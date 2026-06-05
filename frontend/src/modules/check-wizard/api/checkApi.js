/**
 * modules/check-wizard/api/checkApi.js
 * API calls for the check wizard module.
 * All calls go through the shared authenticated client.
 */
import { apiGet, apiPost } from '../../../shared/api/client.js'
import { getMyStations } from '../../../shared/api/stationsApi.js'

export const checkApi = {
  /**
   * Active vehicles at a station the user can check.
   * Passes active=true so inactive/out-of-service vehicles are excluded —
   * you cannot start a check on a vehicle that's out of service.
   */
  getVehicles: (stationId, getToken) =>
    apiGet(`/api/v1/stations/${stationId}/vehicles?active=true`, getToken),

  /** Stations the current user is assigned to (membership-scoped) */
  getStations: getMyStations,

  /**
   * Non-vehicle checkable locations at a station (JUMP_BAG, EQUIPMENT).
   * Returns InventoryLocationRead objects with location_id, location_type, label.
   */
  getStationLocations: (stationId, getToken) =>
    apiGet(`/api/v1/stations/${stationId}/locations`, getToken),

  /** Vehicle's inventory location — scoped to station to avoid 403 for non-Admins */
  getLocations: (stationId, getToken) =>
    apiGet(`/api/v1/inventory/locations?station_id=${stationId}`, getToken),

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

  /** Existing checks for a vehicle — used by LastCheckBanner */
  getVehicleChecks: (vehicleId, getToken) =>
    apiGet(`/api/v1/checks/daily/vehicle/${vehicleId}`, getToken),

  /** Existing checks for a portable location (jump bag) — used by LastCheckBanner */
  getLocationChecks: (locationId, getToken) =>
    apiGet(`/api/v1/checks/daily/location/${locationId}`, getToken),
}
