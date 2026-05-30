/**
 * modules/admin/api/adminApi.js
 * API calls for station membership management (B-ACCESS1 Phase 3)
 * and item catalog management (ADMIN-B1 through ADMIN-B4).
 */
import { apiGet, apiPost, apiPatch, apiDelete } from '../../../shared/api/client.js'

const ADMIN    = '/api/v1/admin'
const BASE_API = '/api/v1'

export const adminApi = {
  // ── Station membership ─────────────────────────────────────────────────

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

  // ── Item catalog (ADMIN-B1 through ADMIN-B4) ──────────────────────────────

  /** List all items. Pass { category, checkType, active } to filter. */
  listItems: (getToken, { category, checkType, active = true } = {}) => {
    const params = new URLSearchParams()
    if (category  != null) params.set('category',   category)
    if (checkType != null) params.set('check_type', checkType)
    if (active    != null) params.set('active',      active)
    const qs = params.toString() ? `?${params}` : ''
    return apiGet(`${ADMIN}/items${qs}`, getToken)
  },

  /**
   * Typeahead search — used by ItemSearchCombobox.
   * Searches name, alternate_names, and ai_tags (case-insensitive).
   * Returns up to `limit` active items by default.
   */
  searchItems: (q, getToken, { activeOnly = true, limit = 20 } = {}) => {
    const params = new URLSearchParams({ q, active_only: activeOnly, limit })
    return apiGet(`${ADMIN}/items/search?${params}`, getToken)
  },

  /** Get a single item by ID */
  getItem: (itemId, getToken) =>
    apiGet(`${ADMIN}/items/${itemId}`, getToken),

  /** Create a new item (Supervisor+) */
  createItem: (payload, getToken) =>
    apiPost(`${ADMIN}/items`, payload, getToken),

  /** Edit an existing item (Supervisor+) */
  updateItem: (itemId, payload, getToken) =>
    apiPatch(`${ADMIN}/items/${itemId}`, payload, getToken),

  /** Soft-deactivate an item (Administrator only) */
  deactivateItem: (itemId, getToken) =>
    apiPatch(`${ADMIN}/items/${itemId}/deactivate`, {}, getToken),

  // ── Par level assignments (ADMIN-F4) ─────────────────────────────────

  /** All vehicle/compartment assignments for an item (enriched) */
  getItemAssignments: (itemId, getToken) =>
    apiGet(`${ADMIN}/items/${itemId}/assignments`, getToken),

  /** Assign an item to a vehicle compartment */
  assignItem: (itemId, payload, getToken) =>
    apiPost(`${ADMIN}/items/${itemId}/assign`, payload, getToken),

  /** Edit min/max on an existing assignment */
  updateParLevel: (parId, payload, getToken) =>
    apiPatch(`${ADMIN}/par-levels/${parId}`, payload, getToken),

  /** Remove an item from a compartment (soft-deactivate) */
  removeParLevel: (parId, getToken) =>
    apiDelete(`${ADMIN}/par-levels/${parId}`, getToken),

  /** List compartments for a vehicle — used by assignment form cascade */
  getVehicleCompartments: (vehicleId, getToken) =>
    apiGet(`${ADMIN}/vehicles/${vehicleId}/compartments`, getToken),}
