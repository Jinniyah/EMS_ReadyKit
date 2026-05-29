/**
 * shared/components/ResolutionTag.jsx
 * Displays the resolution state of a non-PASS check.
 *
 * States:
 *   'fixed'      — supervisor used "I Fixed This"
 *   'noted'      — supervisor added a note only
 *   'unresolved' — not yet acknowledged
 *
 * Used by CheckDetail and CheckList (check-history module).
 * CSS classes are defined in check-history.css.
 */

import React from 'react'

/**
 * Derive the resolution state of a check object.
 * A check is "fixed" when the supervisor used "I Fixed This", which
 * prefixes the corrective_action with a known sentinel string.
 *
 * @param {{ reviewed_at: string|null, corrective_action: string|null }} check
 * @returns {'fixed' | 'noted' | 'unresolved'}
 */
export function getResolutionState(check) {
  if (!check?.reviewed_at) return 'unresolved'
  if (check.corrective_action?.startsWith('Items fixed by supervisor:')) return 'fixed'
  return 'noted'
}

/**
 * ResolutionTag — pill showing fix/note/unresolved state.
 * Renders nothing for PASS checks.
 *
 * @param {{ resolution: 'fixed'|'noted'|'unresolved', status: string }} props
 */
export default function ResolutionTag({ resolution, status }) {
  if (status === 'PASS') return null

  if (resolution === 'fixed') {
    return <span className="resolution-tag resolution-tag--fixed">✓ Fixed</span>
  }
  if (resolution === 'noted') {
    return <span className="resolution-tag resolution-tag--noted">✎ Noted</span>
  }
  return <span className="resolution-tag resolution-tag--unresolved">✗ Not Fixed</span>
}
