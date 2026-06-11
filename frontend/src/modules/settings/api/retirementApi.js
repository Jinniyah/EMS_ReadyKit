import { apiGet, apiPatch } from '../../../shared/api/client.js'

export const retirementApi = {
  getStationVehicles: (stationId, getToken) =>
    apiGet(`/api/v1/stations/${stationId}/vehicles`, getToken),

  getStationLocations: (stationId, getToken) =>
    apiGet(`/api/v1/stations/${stationId}/locations`, getToken),

  retireVehicle: (vehicleId, reason, getToken) =>
    apiPatch(`/api/v1/vehicles/${vehicleId}/retire`, { retirement_reason: reason }, getToken),

  retireLocation: (locationId, reason, getToken) =>
    apiPatch(`/api/v1/inventory/locations/${locationId}/retire`, { retirement_reason: reason }, getToken),

  retireStation: (stationId, reason, getToken) =>
    apiPatch(`/api/v1/stations/${stationId}/retire`, { retirement_reason: reason }, getToken),

  getRetired: (type, stationId, getToken) =>
    apiGet(`/api/v1/admin/retired?type=${type}&station_id=${stationId}`, getToken),
}
