/**
 * shared/components/StatusBadge.jsx
 * Color+label status chip — always shows both color and text (never color alone).
 *
 * @param {{ status: string, level?: 'check' | 'item', size?: 'sm' | 'md' }} props
 *   status — API status string (PASS, FAIL, NEEDS_RESTOCK, OK, SHORT, etc.)
 *   level  — 'check' for overall check status, 'item' for line item status
 */
import React from 'react'
import { checkStatus, lineItemStatus } from '../utils/statusCalc.js'

export default function StatusBadge({ status, level = 'check', size = 'md' }) {
  const fn = level === 'item' ? lineItemStatus : checkStatus
  const { label, icon, color } = fn(status)

  return (
    <span
      className={`status-badge status-badge--${size} status-badge--${fn(status).severity}`}
      style={{ color }}
      aria-label={`Status: ${label}`}
    >
      <span aria-hidden="true">{icon}</span>
      {' '}{label}
    </span>
  )
}
