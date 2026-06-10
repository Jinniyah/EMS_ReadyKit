import { apiGet, apiPost } from '../../../shared/api/client.js'

const BASE = '/api/v1'

export const usageApi = {
  logUsage: (payload, getToken) =>
    apiPost(`${BASE}/checks/usage`, payload, getToken),

  getHistory: (stationId, getToken) =>
    apiGet(`${BASE}/checks/usage/station/${stationId}`, getToken),

  getFrequentItems: (stationId, getToken) =>
    apiGet(`${BASE}/checks/usage/station/${stationId}/frequent`, getToken),
}
