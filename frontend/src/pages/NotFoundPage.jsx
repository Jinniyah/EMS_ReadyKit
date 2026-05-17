/**
 * pages/NotFoundPage.jsx
 */
import React from 'react'
import { useNavigate } from 'react-router-dom'

export default function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <div className="not-found-page">
      <div className="not-found-page__icon" aria-hidden="true">🔍</div>
      <h1 className="not-found-page__title">Page not found</h1>
      <p className="not-found-page__message">
        The page you're looking for doesn't exist.
      </p>
      <button className="btn btn--primary" onClick={() => navigate('/')} type="button">
        Go home
      </button>
    </div>
  )
}
