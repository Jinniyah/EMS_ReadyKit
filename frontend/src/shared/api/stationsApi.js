/**
 * shared/api/stationsApi.js
 * Shared station API calls used by multiple modules.
 * Import from here rather than duplicating across module api files.
 */
import { apiGet } from './client.js'

/** Stations the current user is assigned to (membership-scoped) */
export const getMyStations = (getToken) =>
  apiGet('/api/v1/stations/my', getToken)
