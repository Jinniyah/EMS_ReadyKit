/**
 * modules/supervisor/api/supervisorApi.js
 * API calls for the Supervisor Dashboard.
 */

import { apiGet, apiPost, apiPatch } from '../../../shared/api/client.js'
import { checkHistoryApi } from '../../check-history/api/checkHistoryApi.js'
import { vehicleApi } from '../../vehicles/api/vehicleApi.js'

const BASE = '/api/v1'

const todayStr = () => new Date().toISOString().slice(0, 10)

export const supervisorApi = {
  /**
   * F-5F1: Build today's compliance summary for a station.
   */
  getTodayCompliance: async (stationId, getToken) => {
    const today = todayStr()

    // Fetch vehicles + portable locations in parallel.
    // GET /stations/{id}/vehicles returns ALL vehicles (active and retired)
    // when no `active` query param is passed -- retired vehicles must be
    // excluded here explicitly via `!v.retired_at`, never inferred from
    // `active` alone (see CODEBASE_INDEX.md "active vs retired_at", BUG-AD1).
    // This is the single source feeding the dashboard list, the summary
    // tiles, and the calendar, so filtering once here keeps all three in sync.
    // GET /stations/{id}/locations (jump bags/equipment) already excludes
    // retired_at server-side (see stations.py list_station_locations), so no
    // frontend filter is needed for `portables`.
    const [vehiclesRaw, portables] = await Promise.all([
      apiGet(`${BASE}/stations/${stationId}/vehicles`, getToken),
      apiGet(`${BASE}/stations/${stationId}/locations`, getToken).catch(() => []),
    ])
    const vehicles = vehiclesRaw.filter(v => !v.retired_at)

    // Fetch today's checks + open repair requests in parallel
    const [vehicleCheckResults, portableCheckResults, repairResults] = await Promise.all([
      Promise.allSettled(
        vehicles.map(v =>
          apiGet(`${BASE}/checks/daily/vehicle/${v.vehicle_id}`, getToken)
            .then(checks => ({
              vehicle_id: v.vehicle_id,
              checks: checks.filter(c => c.check_date === today && !c.deleted_at),
            }))
        )
      ),
      Promise.allSettled(
        portables.map(loc =>
          apiGet(`${BASE}/checks/daily/location/${loc.location_id}`, getToken)
            .then(checks => ({
              location_id: loc.location_id,
              checks: checks.filter(c => c.check_date === today && !c.deleted_at),
            }))
        )
      ),
      Promise.allSettled(
        vehicles.filter(v => v.active).map(v =>
          vehicleApi.getRepairRequests(v.vehicle_id, getToken)
            .then(reqs => ({
              vehicle_id: v.vehicle_id,
              openCount: reqs.filter(r => r.status === 'OPEN' || r.status === 'IN_PROGRESS').length,
              hasResolved: reqs.some(r => r.status === 'RESOLVED'),
            }))
            .catch(() => ({ vehicle_id: v.vehicle_id, openCount: 0, hasResolved: false }))
        )
      ),
    ])

    const checksByVehicle = {}
    vehicleCheckResults.forEach((result, i) => {
      checksByVehicle[vehicles[i].vehicle_id] =
        result.status === 'fulfilled' ? result.value.checks : []
    })

    const checksByLocation = {}
    portableCheckResults.forEach((result, i) => {
      checksByLocation[portables[i].location_id] =
        result.status === 'fulfilled' ? result.value.checks : []
    })

    // Build repairStateByVehicle first so we can use it for unresolvedFailCount
    const repairStateByVehicleTemp = {}
    repairResults.forEach((result, i) => {
      const vid = vehicles.filter(v => v.active)[i]?.vehicle_id
      if (vid) {
        repairStateByVehicleTemp[vid] = result.status === 'fulfilled'
          ? { openCount: result.value.openCount, hasResolved: result.value.hasResolved }
          : { openCount: 0, hasResolved: false }
      }
    })

    const activeVehicles = vehicles.filter(v => v.active)
    let passCount = 0, failCount = 0, restockCount = 0, uncheckedCount = 0
    let unresolvedFailCount = 0

    activeVehicles.forEach(v => {
      const checks = checksByVehicle[v.vehicle_id] ?? []
      if (checks.length === 0)                      uncheckedCount++
      else if (checks[0].status === 'FAIL') {
        failCount++
        // A FAIL is resolved when all repair requests are closed and at least one was resolved
        const rs = repairStateByVehicleTemp[v.vehicle_id]
        const isResolved = rs && rs.openCount === 0 && rs.hasResolved
        if (!isResolved) unresolvedFailCount++
      }
      else if (checks[0].status === 'NEEDS_RESTOCK') restockCount++
      else                                           passCount++
    })

    portables.forEach(loc => {
      const checks = checksByLocation[loc.location_id] ?? []
      if (checks.length === 0)                      uncheckedCount++
      else if (checks[0].status === 'FAIL') {
        failCount++
        unresolvedFailCount++ // portables don't have repair state; always show
      }
      else if (checks[0].status === 'NEEDS_RESTOCK') restockCount++
      else                                           passCount++
    })

    const openRepairCount = repairResults.reduce((sum, r) =>
      sum + (r.status === 'fulfilled' ? r.value.openCount : 0), 0
    )

    // Per-vehicle repair state — used by VehicleComplianceCard to show
    // 'Fixed' when issues were resolved via V&E Status (not just via
    // the supervisor dashboard "I fixed this" flow).
    const repairStateByVehicle = repairStateByVehicleTemp

    return {
      vehicles,
      checksByVehicle,
      portables,
      checksByLocation,
      openRepairCount,
      repairStateByVehicle,
      summary: {
        total:          activeVehicles.length + portables.length,
        pass:           passCount,
        fail:           failCount,
        restock:        restockCount,
        unchecked:      uncheckedCount,
        unresolvedFail: unresolvedFailCount,
      },
    }
  },

  /**
   * F-5F2: Load checks for a station over a date range (B-E3).
   * Returns flat array; caller aggregates by vehicle and date.
   */
  getComplianceRange: async (stationId, fromDate, toDate, getToken) => {
    const params = new URLSearchParams({ from: fromDate, to: toDate })
    return apiGet(`${BASE}/checks/daily/station/${stationId}?${params}`, getToken)
  },

  getCheckDateRange: (stationId, getToken) =>
    apiGet(`${BASE}/checks/daily/station/${stationId}/date-range`, getToken),

  getExpiringSoon: (stationId, getToken, days = 30) =>
    apiGet(`${BASE}/stations/${stationId}/expiring-soon?days=${days}`, getToken).catch(() => []),

  getSupplyAlerts: (stationId, getToken) =>
    apiGet(`${BASE}/stations/${stationId}/supply-alerts`, getToken).catch(() => []),

  getDamagedItems: (stationId, getToken) =>
    apiGet(`${BASE}/stations/${stationId}/damaged-items`, getToken).catch(() => []),

  /**
   * F-5F2 (calendar) + Compliance Dashboard reminder row.
   * The station's Station Supply Room is not returned by GET /locations
   * (that endpoint is scoped to JUMP_BAG/EQUIPMENT only) and is not a
   * vehicle, so it has its own fetch. Returns null if no supply room has
   * been set up yet, or if it has been retired (GET /supply-room does not
   * filter retired_at server-side, since RET-B2 allows retiring any
   * InventoryLocation including STATION_SUPPLY_ROOM) -- callers should
   * treat null as "nothing to show", not an error.
   */
  getSupplyRoomLocation: (stationId, getToken) =>
    apiGet(`${BASE}/stations/${stationId}/supply-room`, getToken)
      .then(loc => (loc && !loc.retired_at) ? loc : null)
      .catch(() => null),

  getCheckDetail: (checkId, getToken) =>
    checkHistoryApi.getCheckDetail(checkId, getToken),

  acknowledgeCheck: (checkId, correctiveAction, getToken) =>
    checkHistoryApi.acknowledgeCheck(checkId, correctiveAction, getToken),

  /**
   * "I fixed this" — supervisor resolves failed items on a check.
   */
  resolveFailedItems: async (checkId, vehicleId, resolutionNote, getToken) => {
    const repair = await apiPost(
      `${BASE}/vehicles/${vehicleId}/repair-requests`,
      {
        severity: 'ROUTINE',
        description: `Supervisor fix — resolved during check review. Check #${checkId}. ${resolutionNote}`,
      },
      getToken
    )

    await Promise.all([
      apiPatch(
        `${BASE}/vehicles/${vehicleId}/repair-requests/${repair.repair_id}`,
        { status: 'RESOLVED', resolution_notes: resolutionNote },
        getToken
      ),
      checkHistoryApi.acknowledgeCheck(checkId, `Items fixed by supervisor: ${resolutionNote}`, getToken),
    ])

    return repair
  },
}
