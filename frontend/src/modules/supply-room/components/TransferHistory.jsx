/**
 * supply-room/components/TransferHistory.jsx
 * SUPPLY-F4 — Transfer history for the supply room.
 *
 * Shows inbound (received) and outbound (restocked to vehicle) transfers.
 */
import React, { useEffect, useState } from 'react'
import { supplyApi } from '../api/supplyApi.js'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'

export default function TransferHistory({ locationId }) {
  const { getToken } = useAuth()
  const [transfers, setTransfers] = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)

  useEffect(() => {
    if (!locationId) return
    setLoading(true)
    supplyApi.getTransferHistory(locationId, getToken)
      .then(data => { setTransfers(data); setLoading(false) })
      .catch(e  => { setError(e.message); setLoading(false) })
  }, [locationId, getToken])

  if (loading) return <div style={styles.center}>Loading history…</div>
  if (error)   return <div style={styles.error}>{error}</div>
  if (!transfers.length) {
    return (
      <div style={styles.empty}>
        <p style={styles.emptyText}>No transfers recorded yet.</p>
        <p style={{ color: '#888', fontSize: 14 }}>
          Transfers appear here after stock is restocked to vehicles or received into the supply room.
        </p>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      <p style={styles.count}>{transfers.length} transfer{transfers.length !== 1 ? 's' : ''}</p>
      {transfers.map(t => {
        const isOutbound = t.from_location_id === locationId
        return (
          <div key={t.transfer_id} style={{ ...styles.row, borderLeft: `5px solid ${isOutbound ? '#ffc107' : '#28a745'}` }}>
            <div style={styles.directionBadge(isOutbound)}>
              {isOutbound ? '↑ Out' : '↓ In'}
            </div>
            <div style={styles.main}>
              <div style={styles.itemName}>{t.item_name}</div>
              <div style={styles.detail}>
                <span style={styles.qty}>{t.quantity} units</span>
                {isOutbound
                  ? <span style={{ color: '#555' }}>→ {t.to_location_label}</span>
                  : t.from_location_label
                    ? <span style={{ color: '#555' }}>← {t.from_location_label}</span>
                    : <span style={{ color: '#198754' }}>← Received (external)</span>
                }
              </div>
              {t.lot_number && (
                <div style={styles.lot}>
                  Lot: {t.lot_number}
                  {t.lot_expiration_date && ` · Exp: ${t.lot_expiration_date}`}
                </div>
              )}
              {t.notes && <div style={styles.notes}>{t.notes}</div>}
            </div>
            <div style={styles.meta}>
              <div style={styles.date}>{_formatDate(t.transferred_at)}</div>
              <div style={styles.user}>{_shortEmail(t.transferred_by)}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function _formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

function _shortEmail(email) {
  if (!email) return ''
  return email.split('@')[0]
}

const styles = {
  container:    { padding: 12 },
  center:       { padding: 40, textAlign: 'center', color: '#666' },
  error:        { padding: 16, background: '#f8d7da', color: '#721c24', margin: 12, borderRadius: 8 },
  empty:        { padding: 40, textAlign: 'center' },
  emptyText:    { fontSize: 18, fontWeight: 600, color: '#333' },
  count:        { color: '#888', fontSize: 13, margin: '0 0 8px' },
  row:          { display: 'flex', gap: 12, background: '#fff', borderRadius: 8, padding: '14px 16px', marginBottom: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.06)', alignItems: 'flex-start' },
  directionBadge: isOut => ({
    fontSize: 12, fontWeight: 700, padding: '4px 10px', borderRadius: 12,
    background: isOut ? '#fff3cd' : '#d4edda',
    color: isOut ? '#856404' : '#155724',
    whiteSpace: 'nowrap', marginTop: 2,
  }),
  main:         { flex: 1, minWidth: 0 },
  itemName:     { fontSize: 16, fontWeight: 600, color: '#1a1a1a', marginBottom: 4 },
  detail:       { display: 'flex', gap: 10, fontSize: 14, flexWrap: 'wrap', marginBottom: 2 },
  qty:          { fontWeight: 700, color: '#333' },
  lot:          { fontSize: 13, color: '#666', fontFamily: 'monospace' },
  notes:        { fontSize: 13, color: '#555', marginTop: 4, fontStyle: 'italic' },
  meta:         { textAlign: 'right', flexShrink: 0 },
  date:         { fontSize: 13, color: '#888' },
  user:         { fontSize: 12, color: '#aaa', marginTop: 2 },
}
