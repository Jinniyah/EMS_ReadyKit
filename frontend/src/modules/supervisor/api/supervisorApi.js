/**
 * modules/supervisor/api/supervisorApi.js
 * API calls for the Supervisor Dashboard.
 */

import { apiGet, apiPost, apiPatch } from '../../../shared/api/client.js'
import { checkHistoryApi } from '../../check-history/api/checkHistoryApi.js'

const BASE = '/api/v1'

const todayStr = () => new Date().toISOString().slice(0, 10)

export const supervisorApi = {
  /**
   * F-5F1: Build today's compliance summary for a station.
   */
  getTodayCompliance: async (stationId, getToken) => {
    const today = todayStr()

    // Fetch vehicles + portable locations in parallel
    const [vehicles, portables] = await Promise.all([
      apiGet(`${BASE}/stations/${stationId}/vehicles`, getToken),
      apiGet(`${BASE}/stations/${stationId}/locations`, getToken).catch(() => []),
    ])

    // Fetch today's checks for vehicles and portable locations in parallel
    const [vehicleCheckResults, portableCheckResults] = await Promise.all([
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

    const activeVehicles = vehicles.filter(v => v.active)
    let passCount = 0, failCount = 0, restockCount = 0, uncheckedCount = 0

    activeVehicles.forEach(v => {
      const checks = checksByVehicle[v.vehicle_id] ?? []
      if (checks.length === 0)                      uncheckedCount++
      else if (checks[0].status === 'FAIL')          failCount++
      else if (checks[0].status === 'NEEDS_RESTOCK') restockCount++
      else                                           passCount++
    })

    portables.forEach(loc => {
      const checks = checksByLocation[loc.location_id] ?? []
      if (checks.length === 0)                      uncheckedCount++
      else if (checks[0].status === 'FAIL')          failCount++
      else if (checks[0].status === 'NEEDS_RESTOCK') restockCount++
      else                                           passCount++
    })

    return {
      vehicles,
      checksByVehicle,
      portables,
      checksByLocation,
      summary: {
        total:     activeVehicles.length + portables.length,
        pass:      passCount,
        fail:      failCount,
        restock:   restockCount,
        unchecked: uncheckedCount,
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
