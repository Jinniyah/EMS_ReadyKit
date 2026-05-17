/**
 * shared/api/client.js
 * Authenticated HTTP client for all API calls.
 *
 * Responsibilities:
 *   - Attaches the Bearer token from useAuth to every request
 *   - Prefixes requests with VITE_API_BASE_URL (empty in dev — Vite proxies /api)
 *   - Parses JSON responses and surfaces structured errors
 *   - Throws ApiError with status, message, and detail for consistent handling
 *
 * Usage:
 *   import { apiGet, apiPost } from '../shared/api/client.js'
 *
 *   const vehicles = await apiGet('/api/v1/stations/1/vehicles', getToken)
 *   const check    = await apiPost('/api/v1/checks/daily', payload, getToken)
 *
 * The getToken parameter is the function returned by useAuth().getToken —
 * it silently acquires a fresh token from MSAL (or returns the dev fake token).
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

// ── Error type ────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  /**
   * @param {number} status     HTTP status code
   * @param {string} message    Human-readable message
   * @param {any}    detail     Raw FastAPI detail field (string | object | null)
   */
  constructor(status, message, detail = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function apiFetch(method, path, body, getToken) {
  const token = getToken ? await getToken() : null

  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const options = { method, headers }
  if (body !== undefined) {
    options.body = JSON.stringify(body)
  }

  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, options)
  } catch (networkError) {
    // Network failure (no connection, DNS error, etc.)
    throw new ApiError(0, 'Network error — check your connection and try again.', null)
  }

  // Parse response body regardless of status so error details are available.
  let data = null
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    try {
      data = await response.json()
    } catch {
      // Non-JSON body on an error response — treat as empty
    }
  }

  if (!response.ok) {
    const detail = data?.detail ?? null
    const message = _extractMessage(response.status, detail)
    throw new ApiError(response.status, message, detail)
  }

  return data
}

// ── Public helpers ────────────────────────────────────────────────────────────

export async function apiGet(path, getToken) {
  return apiFetch('GET', path, undefined, getToken)
}

export async function apiPost(path, body, getToken) {
  return apiFetch('POST', path, body, getToken)
}

export async function apiPatch(path, body, getToken) {
  return apiFetch('PATCH', path, body, getToken)
}

export async function apiPut(path, body, getToken) {
  return apiFetch('PUT', path, body, getToken)
}

export async function apiDelete(path, getToken) {
  return apiFetch('DELETE', path, undefined, getToken)
}

// ── Error message extraction ──────────────────────────────────────────────────

function _extractMessage(status, detail) {
  if (status === 0) return 'Network error — check your connection and try again.'
  if (status === 401 || status === 403) return 'You do not have permission to perform this action.'
  if (status === 404) return 'The requested resource was not found.'
  if (status === 409) return 'This record already exists.'
  if (status === 422) {
    // FastAPI validation errors — extract first message
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
