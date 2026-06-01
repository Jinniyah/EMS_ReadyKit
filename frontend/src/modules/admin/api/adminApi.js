/**
 * modules/admin/api/adminApi.js
 * API calls for station membership, item catalog, par levels,
 * vehicle management, and station CRUD.
 */
import { apiGet, apiPost, apiPatch, apiDelete, apiUpload } from '../../../shared/api/client.js'

const ADMIN = '/api/v1/admin'

export const adminApi = {
  // ── Station membership ─────────────────────────────────────────────────

  getMyStations: (getToken) =>
    apiGet('/api/v1/stations/my', getToken),

  getStationMembers: (stationId, getToken) =>
    apiGet(`/api/v1/stations/${stationId}/members`, getToken),

  addMember: (stationId, payload, getToken) =>
    apiPost(`/api/v1/stations/${stationId}/members`, payload, getToken),

  updateMember: (stationId, userId, payload, getToken) =>
    apiPatch(`/api/v1/stations/${stationId}/members/${encodeURIComponent(userId)}`, payload, getToken),

  removeMember: (stationId, userId, getToken) =>
    apiDelete(`/api/v1/stations/${stationId}/members/${encodeURIComponent(userId)}`, getToken),

  // ── Station CRUD (ADMIN-B15) ───────────────────────────────────────────

  createStation: (payload, getToken) =>
    apiPost(`${ADMIN}/stations`, payload, getToken),

  /** Edit a station's name, address, region, call_sign, primary_color. Admin only. */
  updateStation: (stationId, payload, getToken) =>
    apiPatch(`/api/v1/stations/${stationId}`, payload, getToken),

  /** Soft-deactivate a station. Admin only. */
  deactivateStation: (stationId, getToken) =>
    apiDelete(`/api/v1/stations/${stationId}`, getToken),

  // ── Item catalog ──────────────────────────────────────────────────────────

  listItems: (getToken, { category, checkType, active = true } = {}) => {
    const params = new URLSearchParams()
    if (category  != null) params.set('category',   category)
    if (checkType != null) params.set('check_type', checkType)
    if (active    != null) params.set('active',      active)
    const qs = params.toString() ? `?${params}` : ''
    return apiGet(`${ADMIN}/items${qs}`, getToken)
  },

  searchItems: (q, getToken, { activeOnly = true, limit = 20 } = {}) => {
    const params = new URLSearchParams({ q, active_only: activeOnly, limit })
    return apiGet(`${ADMIN}/items/search?${params}`, getToken)
  },

  getItem: (itemId, getToken) =>
    apiGet(`${ADMIN}/items/${itemId}`, getToken),

  createItem: (payload, getToken) =>
    apiPost(`${ADMIN}/items`, payload, getToken),

  updateItem: (itemId, payload, getToken) =>
    apiPatch(`${ADMIN}/items/${itemId}`, payload, getToken),

  deactivateItem: (itemId, getToken) =>
    apiPatch(`${ADMIN}/items/${itemId}/deactivate`, {}, getToken),

  // ── Par level assignments ─────────────────────────────────────────────────

  getAssignmentCount: (itemId, getToken) =>
    apiGet(`${ADMIN}/items/${itemId}/assignments/count`, getToken),

  getItemAssignments: (itemId, getToken) =>
    apiGet(`${ADMIN}/items/${itemId}/assignments`, getToken),

  assignItem: (itemId, payload, getToken) =>
    apiPost(`${ADMIN}/items/${itemId}/assign`, payload, getToken),

  updateParLevel: (parId, payload, getToken) =>
    apiPatch(`${ADMIN}/par-levels/${parId}`, payload, getToken),

  deactivateParLevel: (parId, getToken) =>
    apiPatch(`${ADMIN}/par-levels/${parId}/deactivate`, {}, getToken),

  removeParLevel: (parId, getToken) =>
    apiDelete(`${ADMIN}/par-levels/${parId}`, getToken),

  getVehicleCompartments: (vehicleId, getToken) =>
    apiGet(`${ADMIN}/vehicles/${vehicleId}/compartments`, getToken),

  getCompartmentAssignments: (compartmentId, getToken) =>
    apiGet(`${ADMIN}/compartments/${compartmentId}/assignments`, getToken),

  // ── Vehicles ──────────────────────────────────────────────────────────────

  createVehicle: (payload, getToken) =>
    apiPost('/api/v1/vehicles', payload, getToken),

  updateVehicle: (vehicleId, payload, getToken) =>
    apiPatch(`/api/v1/vehicles/${vehicleId}`, payload, getToken),

  updateVehicleDetails: (vehicleId, payload, getToken) =>
    apiPatch(`${ADMIN}/vehicles/${vehicleId}/details`, payload, getToken),

  updateVehicleColor: (vehicleId, vehicleColor, getToken) =>
    apiPatch(`${ADMIN}/vehicles/${vehicleId}/color`, { vehicle_color: vehicleColor }, getToken),

  createCompartment: (locationId, payload, getToken) =>
    apiPost(`/api/v1/inventory/locations/${locationId}/compartments`, payload, getToken),

  updateCompartment: (compartmentId, payload, getToken) =>
    apiPatch(`/api/v1/inventory/compartments/${compartmentId}`, payload, getToken),

  getVehicleLocation: (stationId, getToken) =>
    apiGet(`/api/v1/inventory/locations?station_id=${stationId}`, getToken),

  // ── CSV import ────────────────────────────────────────────────────────────

  importItemsCsv: (formData, getToken) =>
    apiUpload(`${ADMIN}/items/import`, formData, getToken),
}
