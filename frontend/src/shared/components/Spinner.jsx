/**
 * shared/components/Spinner.jsx
 * Accessible loading indicator.
 * @param {{ label?: string, size?: 'sm' | 'md' | 'lg' }} props
 */
import React from 'react'

export default function Spinner({ label = 'Loading…', size = 'md' }) {
  return (
    <div className={`spinner spinner--${size}`} role="status" aria-label={label}>
      <div className="spinner__ring" aria-hidden="true" />
      <span className="spinner__label">{label}</span>
    </div>
  )
}
