/**
 * modules/admin/api/adminApi.js
 * API calls for item catalog, par levels, vehicle management, station CRUD,
 * and portable locations. Member CRUD lives in ./membersApi.js (Session AE).
 */
import { apiGet, apiPost, apiPatch, apiDelete, apiUpload } from '../../../shared/api/client.js'
import { getMyStations } from '../../../shared/api/stationsApi.js'

const ADMIN = '/api/v1/admin'

export const adminApi = {
  // ── Station membership ─────────────────────────────────────────────────
  // Member CRUD (add/edit/remove/CSV) lives in ./membersApi.js (Session AE,
  // MERGE-1) -- it's member_id-based, matching the backend's ACC-B7 routes.
  // The old getStationMembers/addMember/updateMember/removeMember here used
  // a user_id (email) where the backend expects an integer member_id, which
  // is why member removal in Station Administration used to fail with
  // "unable to parse string as an integer". Don't re-add member endpoints
  // here -- use membersApi.

  getMyStations,

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

  /** Update AI identification fields only — Admin only (AI-B1). */
  updateAiFields: (itemId, payload, getToken) =>
    apiPatch(`${ADMIN}/items/${itemId}/ai-fields`, payload, getToken),

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

  /** Soft-deactivate a par level with optional reason — hits B-E9 inventory endpoint. */
  deactivateParLevelFull: (parId, reason, getToken) =>
    apiPatch(`/api/v1/inventory/par-levels/${parId}`, { reason: reason || null }, getToken),

  getVehicleCompartments: (vehicleId, getToken) =>
    apiGet(`${ADMIN}/vehicles/${vehicleId}/compartments`, getToken),

  getCompartmentAssignments: (compartmentId, getToken) =>
    apiGet(`${ADMIN}/compartments/${compartmentId}/assignments`, getToken),

  // ── Vehicles ──────────────────────────────────────────────────────────────

  createVehicle: (payload, getToken) =>
    apiPost('/api/v1/vehicles', payload, getToken),

  /** OOS/RTS status toggle — sends {active, inactive_reason}. PATCH /api/v1/vehicles/{id} */
  patchVehicleStatus: (vehicleId, payload, getToken) =>
    apiPatch(`/api/v1/vehicles/${vehicleId}`, payload, getToken),

  /** Edit vehicle number + type. PATCH /admin/vehicles/{id}/details — Admin only */
  updateVehicleDetails: (vehicleId, payload, getToken) =>
    apiPatch(`${ADMIN}/vehicles/${vehicleId}/details`, payload, getToken),

  /** Set vehicle color hex. PATCH /admin/vehicles/{id}/color — Supervisor+ */
  updateVehicleColor: (vehicleId, vehicleColor, getToken) =>
    apiPatch(`${ADMIN}/vehicles/${vehicleId}/color`, { vehicle_color: vehicleColor }, getToken),

  createCompartment: (locationId, payload, getToken) =>
    apiPost(`/api/v1/inventory/locations/${locationId}/compartments`, payload, getToken),

  updateCompartment: (compartmentId, payload, getToken) =>
    apiPatch(`/api/v1/inventory/compartments/${compartmentId}`, payload, getToken),

  getVehicleLocation: (stationId, getToken) =>
    apiGet(`/api/v1/inventory/locations?station_id=${stationId}`, getToken),

  // ── Portable locations (Jump Bags / ADMIN-F7) ─────────────────────────────

  /** List all inventory locations for a station (filter JUMP_BAG on client). */
  getStationLocations: (stationId, getToken) =>
    apiGet(`/api/v1/inventory/locations?station_id=${stationId}`, getToken),

  /** Create a new JUMP_BAG portable location. */
  createPortableLocation: (payload, getToken) =>
    apiPost('/api/v1/inventory/locations', payload, getToken),

  /** Rename an inventory location label (SS-B1, Admin only). */
  renameLocation: (locationId, label, getToken) =>
    apiPatch(`${ADMIN}/locations/${locationId}`, { label }, getToken),

  /** List compartments for any inventory location (portable or vehicle). */
  getLocationCompartments: (locationId, getToken) =>
    apiGet(`/api/v1/inventory/locations/${locationId}/compartments`, getToken),

  // ── CSV import ────────────────────────────────────────────────────────────

  importItemsCsv: (formData, getToken) =>
    apiUpload(`${ADMIN}/items/import`, formData, getToken),
}
