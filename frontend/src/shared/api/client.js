/**
 * shared/api/client.js
 * Authenticated HTTP client for all API calls.
 *
 * Error messages for 401/403 are written for frontline EMS users —
 * tired, stressed, possibly on a mobile device mid-shift. They tell the
 * user what happened and what to do, not what the HTTP status code means.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  constructor(status, message, detail = null) {
    super(message)
    this.name   = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function apiFetch(method, path, body, getToken) {
  const token = getToken ? await getToken() : null

  const headers = {
    'Content-Type': 'application/json',
    'Accept':       'application/json',
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const options = { method, headers }
  if (body !== undefined) options.body = JSON.stringify(body)

  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, options)
  } catch {
    throw new ApiError(
      0,
      'No connection — check your internet and try again.',
      null
    )
  }

  let data = null
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    try { data = await response.json() } catch { /* ignore */ }
  }

  if (!response.ok) {
    const detail = data?.detail ?? null
    throw new ApiError(response.status, _extractMessage(response.status, detail), detail)
  }

  return data
}

export const apiGet            = (path, getToken)       => apiFetch('GET',    path, undefined, getToken)
export const apiPost           = (path, body, getToken) => apiFetch('POST',   path, body,      getToken)
export const apiPatch          = (path, body, getToken) => apiFetch('PATCH',  path, body,      getToken)
export const apiPut            = (path, body, getToken) => apiFetch('PUT',    path, body,      getToken)
export const apiDelete         = (path, getToken)       => apiFetch('DELETE', path, undefined, getToken)
export const apiDeleteWithBody = (path, body, getToken) => apiFetch('DELETE', path, body,      getToken)

/**
 * Upload a file as multipart/form-data.
 * Omits Content-Type header so the browser sets it with the correct boundary.
 */
export async function apiUpload(path, formData, getToken) {
  const token = getToken ? await getToken() : null
  const headers = { 'Accept': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, { method: 'POST', headers, body: formData })
  } catch {
    throw new ApiError(0, 'No connection — check your internet and try again.', null)
  }

  let data = null
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    try { data = await response.json() } catch { /* ignore */ }
  }

  if (!response.ok) {
    const detail = data?.detail ?? null
    throw new ApiError(response.status, _extractMessage(response.status, detail), detail)
  }

  return data
}

function _extractMessage(status, detail) {
  // Network / no response
  if (status === 0) {
    return 'No connection — check your internet and try again.'
  }

  // Session expired
  if (status === 401) {
    return 'Your session expired. Sign out and sign back in.'
  }

  // Access denied — use the backend message when available (it's written
  // for EMS users), fall back to a clear generic message
  if (status === 403) {
    if (typeof detail === 'string' && detail.length > 0) return detail
    return "You don't have permission to do that. Ask your supervisor if something seems wrong."
  }

  if (status === 404) {
    return 'The requested record was not found.'
  }

  if (status === 409) {
    if (typeof detail === 'string' && detail.length > 0) return detail
    return 'This record already exists.'
  }

  if (status === 422) {
    if (Array.isArray(detail)) {
      const first = detail[0]
      if (first?.msg) return `Check your input: ${first.msg}`
    }
    if (typeof detail === 'string' && detail.length > 0) return detail
    return 'Invalid request — please check your input and try again.'
  }

  if (status >= 500) {
    return 'Something went wrong on our end. Please try again in a moment.'
  }

  if (typeof detail === 'string' && detail.length > 0) return detail
  return `Unexpected error (HTTP ${status}) — please try again.`
}
