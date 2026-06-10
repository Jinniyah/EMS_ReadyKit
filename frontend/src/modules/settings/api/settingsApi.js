import { apiGet, apiPatch } from '../../../shared/api/client.js'

export const settingsApi = {
  getSettings: (stationId, getToken) =>
    apiGet(`/api/v1/stations/${stationId}/settings`, getToken),

  updateSettings: (stationId, payload, getToken) =>
    apiPatch(`/api/v1/stations/${stationId}/settings`, payload, getToken),
}
