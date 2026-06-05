/**
 * shared/hooks/useApi.js
 * Data-fetching hook with loading/error/data state.
 *
 * Usage:
 *   const { data, isLoading, error, refetch } = useApi(
 *     () => apiGet('/api/v1/stations/1/vehicles', getToken),
 *     [stationId]   // re-fetch when these change
 *   )
 *
 * Returns:
 *   data      — the response JSON (null while loading or on error)
 *   isLoading — true while the request is in flight
 *   error     — ApiError | null
 *   refetch   — call to manually trigger a re-fetch
 */

import { useState, useEffect, useCallback, useRef } from 'react'

export function useApi(fetchFn, deps = []) {
  const [data, setData]       = useState(null)
  const [isLoading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  const execute = useCallback(async () => {
    setLoading(true)
    setError(null)
    setData(null)
    try {
      const result = await fetchFn()
      if (mountedRef.current) {
        setData(result)
        setError(null)
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err)
        setData(null)
      }
    } finally {
      if (mountedRef.current) setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    execute()
  }, [execute])

  return { data, isLoading, error, refetch: execute }
}
