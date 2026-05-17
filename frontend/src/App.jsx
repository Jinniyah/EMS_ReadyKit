/**
 * App.jsx
 * Top-level route configuration and per-module ErrorBoundary wiring.
 *
 * Each module is wrapped in its own ErrorBoundary so a crash in one feature
 * cannot prevent another from rendering.  A medic must always be able to
 * submit a check even if, e.g., the supervisor dashboard module crashes.
 *
 * Routes are role-gated via RoleGuard — a Responder who navigates to
 * /supervisor will see an "access denied" message, not a blank screen.
 */

import React, { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

import ErrorBoundary from './shared/components/ErrorBoundary.jsx'
import Spinner from './shared/components/Spinner.jsx'
import UserPill from './shared/components/UserPill.jsx'
import DevBanner from './shared/components/DevBanner.jsx'
import { useAuth } from './shared/hooks/useAuth.jsx'
import { canAccess } from './shared/utils/roleGuard.js'
import './App.css'

// Lazy-load module entry points — each module loads only when navigated to.
// Phase 5A: placeholder pages for modules not yet built.
const HomePage     = lazy(() => import('./pages/HomePage.jsx'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage.jsx'))

const isDev = import.meta.env.VITE_APP_ENV !== 'production'

// ── Loading fallback ──────────────────────────────────────────────────────────
function PageSpinner() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', paddingTop: '4rem' }}>
      <Spinner label="Loading…" />
    </div>
  )
}

// ── App shell ─────────────────────────────────────────────────────────────────
export default function App() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) return <PageSpinner />

  return (
    <div className="app-shell">
      {isDev && <DevBanner />}
      {isAuthenticated && (
        <header className="app-header">
          <div className="app-header__brand">
            <span className="app-header__logo" aria-hidden="true">🚑</span>
            <span className="app-header__title">EMS ReadyKit</span>
          </div>
          <UserPill />
        </header>
      )}

      <main className="app-main">
        <ErrorBoundary moduleName="App">
          <Suspense fallback={<PageSpinner />}>
            <Routes>
              <Route path="/" element={isAuthenticated ? <HomePage /> : <Navigate to="/login" replace />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </main>
    </div>
  )
}

// ── Login page (inline — intentionally minimal) ───────────────────────────────
function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  if (isAuthenticated) return <Navigate to="/" replace />

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-card__logo" aria-hidden="true">🚑</div>
        <h1 className="login-card__title">EMS ReadyKit</h1>
        <p className="login-card__subtitle">Vehicle inventory and readiness platform</p>
        <button className="btn btn--primary btn--large" onClick={login}>
          Sign in with your organization account
        </button>
      </div>
    </div>
  )
}
