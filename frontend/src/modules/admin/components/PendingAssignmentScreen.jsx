/**
 * modules/admin/components/PendingAssignmentScreen.jsx
 * Shown to authenticated users who have no station assignments yet.
 * Friendly, non-technical — no error codes or technical jargon.
 */
import React from 'react'

export default function PendingAssignmentScreen() {
  return (
    <div className="pending-screen">
      <div className="pending-screen__icon" aria-hidden="true">🚑</div>
      <h1 className="pending-screen__title">Welcome to EMS ReadyKit</h1>
      <p className="pending-screen__message">
        Your account is being set up. An administrator needs to assign you
        to a station before you can get started.
      </p>
      <p className="pending-screen__contact">
        Contact your station administrator or supervisor to get access.
      </p>
    </div>
  )
}
