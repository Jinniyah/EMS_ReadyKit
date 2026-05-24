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
    const vehicles = await apiGet(
      `${BASE}/stations/${stationId}/vehicles`,
      getToken
    )

    const today = todayStr()
    const checkResults = await Promise.allSettled(
      vehicles.map(v =>
        apiGet(`${BASE}/checks/daily/vehicle/${v.vehicle_id}`, getToken)
          .then(checks => ({
            vehicle_id: v.vehicle_id,
            checks: checks.filter(c => c.check_date === today && !c.deleted_at),
          }))
      )
    )

    const checksByVehicle = {}
    checkResults.forEach((result, i) => {
      checksByVehicle[vehicles[i].vehicle_id] =
        result.status === 'fulfilled' ? result.value.checks : []
    })

    const activeVehicles = vehicles.filter(v => v.active)
    let passCount = 0, failCount = 0, restockCount = 0, uncheckedCount = 0

    activeVehicles.forEach(v => {
      const checks = checksByVehicle[v.vehicle_id] ?? []
      if (checks.length === 0) {
        uncheckedCount++
      } else {
        const latest = checks[0]
        if (latest.status === 'FAIL')               failCount++
        else if (latest.status === 'NEEDS_RESTOCK') restockCount++
        else                                        passCount++
      }
    })

    return {
      vehicles,
      checksByVehicle,
      summary: { total: activeVehicles.length, pass: passCount, fail: failCount, restock: restockCount, unchecked: uncheckedCount },
    }
  },

  getCheckDetail: (checkId, getToken) =>
    checkHistoryApi.getCheckDetail(checkId, getToken),

  acknowledgeCheck: (checkId, correctiveAction, getToken) =>
    checkHistoryApi.acknowledgeCheck(checkId, correctiveAction, getToken),

  /**
   * "I fixed this" — supervisor resolves failed items on a check.
   * Creates a repair request and immediately marks it RESOLVED.
   * Also acknowledges the check with the corrective action note.
   * All three calls run in parallel for speed.
   *
   * @param {number} checkId
   * @param {number} vehicleId
   * @param {string} resolutionNote — what the supervisor did to fix it
   * @param {Function} getToken
   */
  resolveFailedItems: async (checkId, vehicleId, resolutionNote, getToken) => {
    // 1. File a repair request (documents the issue)
    const repair = await apiPost(
      `${BASE}/vehicles/${vehicleId}/repair-requests`,
      {
        severity: 'ROUTINE',
        description: `Supervisor fix — resolved during check review. Check #${checkId}. ${resolutionNote}`,
      },
      getToken
    )

    // 2. Immediately resolve it (supervisor confirmed fix on the spot)
    // 3. Acknowledge the check with the corrective action
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
