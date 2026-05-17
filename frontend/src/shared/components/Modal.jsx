/**
 * shared/components/Modal.jsx
 * Accessible confirmation dialog.
 * Traps focus within the dialog while open.
 * Closes on Escape or the cancel button.
 *
 * @param {{
 *   open: boolean
 *   title: string
 *   children: React.ReactNode
 *   confirmLabel?: string
 *   cancelLabel?: string
 *   onConfirm: () => void
 *   onCancel: () => void
 *   danger?: boolean       — red confirm button for destructive actions
 * }} props
 */
import React, { useEffect, useRef } from 'react'

export default function Modal({
  open,
  title,
  children,
  confirmLabel = 'Confirm',
  cancelLabel  = 'Cancel',
  onConfirm,
  onCancel,
  danger = false,
}) {
  const dialogRef = useRef(null)

  useEffect(() => {
    if (open) dialogRef.current?.focus()
  }, [open])

  useEffect(() => {
    if (!open) return
    const handler = (e) => { if (e.key === 'Escape') onCancel() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onCancel])

  if (!open) return null

  return (
    <div className="modal-overlay" role="presentation" onClick={onCancel}>
      <div
        ref={dialogRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
        onClick={e => e.stopPropagation()}
      >
        <h2 id="modal-title" className="modal__title">{title}</h2>
        <div className="modal__body">{children}</div>
        <div className="modal__actions">
          <button
            className="btn btn--secondary"
            onClick={onCancel}
            type="button"
          >
            {cancelLabel}
          </button>
          <button
            className={`btn ${danger ? 'btn--danger' : 'btn--primary'}`}
            onClick={onConfirm}
            type="button"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
