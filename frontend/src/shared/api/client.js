/**
 * shared/api/client.js
 * Authenticated HTTP client for all API calls.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  constructor(status, message, detail = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function apiFetch(method, path, body, getToken) {
  const token = getToken ? await getToken() : null

  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const options = { method, headers }
  if (body !== undefined) options.body = JSON.stringify(body)

  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, options)
  } catch {
    throw new ApiError(0, 'Network error — check your connection and try again.', null)
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

export const apiGet    = (path, getToken)        => apiFetch('GET',    path, undefined, getToken)
export const apiPost   = (path, body, getToken)  => apiFetch('POST',   path, body,      getToken)
export const apiPatch  = (path, body, getToken)  => apiFetch('PATCH',  path, body,      getToken)
export const apiPut    = (path, body, getToken)  => apiFetch('PUT',    path, body,      getToken)
export const apiDelete = (path, getToken)        => apiFetch('DELETE', path, undefined, getToken)

/** DELETE with a JSON body — needed for soft-delete endpoints that require a reason. */
export const apiDeleteWithBody = (path, body, getToken) => apiFetch('DELETE', path, body, getToken)

function _extractMessage(status, detail) {
  if (status === 0)   return 'Network error — check your connection and try again.'
  if (status === 401 || status === 403) return 'You do not have permission to perform this action.'
  if (status === 404) return 'The requested resource was not found.'
  if (status === 409) return 'This record already exists.'
  if (status === 422) {
    if (Array.isArray(detail)) {
      const first = detail[0]
      if (first?.msg) return `Validation error: ${first.msg}`
    }
    if (typeof detail === 'string') return detail
    return 'Invalid request — please check your input.'
  }
  if (status >= 500) return 'Server error — please try again in a moment.'
  if (typeof detail === 'string') return detail
  return `Unexpected error (HTTP ${status})`
}
