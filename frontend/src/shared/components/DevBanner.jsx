/**
 * shared/components/DevBanner.jsx
 * Development-only banner — visible only when VITE_APP_ENV !== 'production'.
 * Shows current auth role and a quick role switcher.
 * Styled in a distinct amber color so it's never confused with production UI.
 */
import React from 'react'
import { useAuth } from '../hooks/useAuth.jsx'

export default function DevBanner() {
  const auth = useAuth()
  if (!auth._isDev) return null

  return (
    <div className="dev-banner" role="note" aria-label="Development mode">
      <span className="dev-banner__label">DEV</span>
      <span className="dev-banner__role">
        Signed in as: <strong>{auth.user?.role ?? 'none'}</strong>
        {' '}({auth.user?.name})
      </span>
      <div className="dev-banner__switches">
        {Object.entries(auth._devUsers ?? {}).map(([key, u]) => (
          <button
            key={key}
            className={`dev-banner__btn ${auth._devRoleKey === key ? 'dev-banner__btn--active' : ''}`}
            onClick={() => auth._switchRole(key)}
            type="button"
          >
            {u.role}
          </button>
        ))}
      </div>
    </div>
  )
}
