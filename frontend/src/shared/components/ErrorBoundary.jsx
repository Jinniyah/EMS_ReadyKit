/**
 * shared/components/ErrorBoundary.jsx
 * React class component error boundary — catches unhandled render errors.
 *
 * Wraps each feature module so a crash in one module cannot crash the app.
 * A medic must always be able to submit a check even if an unrelated module
 * (e.g. supervisor dashboard, data export) throws an error.
 *
 * Usage:
 *   <ErrorBoundary moduleName="Check Wizard">
 *     <CheckWizard />
 *   </ErrorBoundary>
 *
 * On error, renders an inline message with a "Try again" button that resets
 * the boundary state (re-renders the wrapped component from scratch).
 * Error details are logged to console in dev; suppressed in production.
 */

import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
    this._reset = this._reset.bind(this)
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    // In production this would ship to an error tracking service.
    // For now, log to console only in dev.
    if (import.meta.env.VITE_APP_ENV !== 'production') {
      console.error(
        `[ErrorBoundary] Caught in module "${this.props.moduleName ?? 'unknown'}":`,
        error,
        info.componentStack
      )
    }
  }

  _reset() {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (!this.state.hasError) return this.props.children

    const moduleName = this.props.moduleName ?? 'This section'
    const isDev = import.meta.env.VITE_APP_ENV !== 'production'

    return (
      <div className="error-boundary" role="alert" aria-live="assertive">
        <div className="error-boundary__icon" aria-hidden="true">⚠️</div>
        <h2 className="error-boundary__title">{moduleName} encountered an error</h2>
        <p className="error-boundary__message">
          Something went wrong. The rest of the app is still available.
        </p>
        {isDev && this.state.error && (
          <pre className="error-boundary__detail">
            {this.state.error.message}
          </pre>
        )}
        <button
          className="btn btn--secondary"
          onClick={this._reset}
          type="button"
        >
          Try again
        </button>
      </div>
    )
  }
}
