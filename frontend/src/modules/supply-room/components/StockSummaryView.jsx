/**
 * supply-room/components/StockSummaryView.jsx
 * SUPPLY-F1 — Supply room stock view.
 *
 * Shows all items with stock at the supply room, color-coded by par status.
 * Each card is tappable to expand lot detail.
 */
import React, { useState } from 'react'

const STATUS_COLOR = {
  OK:     { bg: '#d4edda', border: '#28a745', text: '#155724' },
  LOW:    { bg: '#fff3cd', border: '#ffc107', text: '#856404' },
  OUT:    { bg: '#f8d7da', border: '#dc3545', text: '#721c24' },
  NO_PAR: { bg: '#e9ecef', border: '#6c757d', text: '#495057' },
}

const STATUS_LABEL = {
  OK:     'In Stock',
  LOW:    'Low Stock',
  OUT:    'Out of Stock',
  NO_PAR: 'No Par Set',
}

export default function StockSummaryView({ items, loading, error, onRefresh }) {
  const [expandedId, setExpandedId] = useState(null)
  const [filter, setFilter] = useState('ALL')

  if (loading) {
    return <div style={styles.center}>Loading stock…</div>
  }
  if (error) {
    return (
      <div style={styles.errorBox}>
        <p>{error}</p>
        <button style={styles.btnSecondary} onClick={onRefresh} type="button">Retry</button>
      </div>
    )
  }
  if (!items?.length) {
    return (
      <div style={styles.emptyState}>
        <p style={styles.emptyText}>No items in stock.</p>
        <p style={{ color: '#666', fontSize: 15 }}>
          Use the <strong>Receive Stock</strong> tab to add inventory.
        </p>
      </div>
    )
  }

  const filtered = filter === 'ALL'
    ? items
    : items.filter(i => i.status === filter)

  const counts = {
    ALL:    items.length,
    OK:     items.filter(i => i.status === 'OK').length,
    LOW:    items.filter(i => i.status === 'LOW').length,
    OUT:    items.filter(i => i.status === 'OUT').length,
    NO_PAR: items.filter(i => i.status === 'NO_PAR').length,
  }

  return (
    <div>
      {/* Filter bar */}
      <div style={styles.filterBar} role="group" aria-label="Filter by stock status">
        {['ALL', 'LOW', 'OUT', 'OK', 'NO_PAR'].map(s => (
          <button
            key={s}
            style={{
              ...styles.filterBtn,
              background: filter === s ? '#0d6efd' : '#fff',
              color:      filter === s ? '#fff' : '#333',
            }}
            onClick={() => setFilter(s)}
            type="button"
            aria-pressed={filter === s}
          >
            {s === 'ALL' ? 'All' : STATUS_LABEL[s]}
            <span style={styles.filterCount}>{counts[s]}</span>
          </button>
        ))}
      </div>

      {/* Items */}
      <div>
        {filtered.map(item => {
          const colors   = STATUS_COLOR[item.status] ?? STATUS_COLOR.NO_PAR
          const expanded = expandedId === item.item_id

          return (
            <div
              key={item.item_id}
              style={{ ...styles.itemCard, borderLeft: `5px solid ${colors.border}` }}
              onClick={() => setExpandedId(expanded ? null : item.item_id)}
              role="button"
              tabIndex={0}
              onKeyDown={e => e.key === 'Enter' && setExpandedId(expanded ? null : item.item_id)}
              aria-expanded={expanded}
            >
              <div style={styles.itemRow}>
                <div style={styles.itemName}>{item.item_name}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {(item.is_any_expired || item.is_any_expiring) && (
                    <span style={styles.expiryWarn} title={item.is_any_expired ? 'Expired lot present' : 'Lot expiring soon'}>
                      {item.is_any_expired ? '⚠ Expired' : '⏰ Expiring'}
                    </span>
                  )}
                  <div style={{ ...styles.qtyBadge, background: colors.bg, color: colors.text, border: `1px solid ${colors.border}` }}>
                    {item.total_quantity}
                  </div>
                </div>
              </div>

              {item.par_min != null && (
                <div style={styles.parInfo}>
                  Par: {item.par_min}–{item.par_max} &nbsp;|&nbsp; {STATUS_LABEL[item.status]}
                </div>
              )}

              {expanded && item.lots.length > 0 && (
                <div style={styles.lotList} onClick={e => e.stopPropagation()}>
                  <div style={styles.lotHeader}>Lot Details</div>
                  {item.lots.map(lot => (
                    <div key={lot.lot_id} style={{ ...styles.lotRow, opacity: lot.quantity === 0 ? 0.5 : 1 }}>
                      <span style={styles.lotQty}>{lot.quantity} units</span>
                      <span style={styles.lotNum}>{lot.lot_number ?? 'No lot #'}</span>
                      <span style={{ ...styles.lotExp, color: lot.is_expired ? '#dc3545' : '#555' }}>
                        {lot.expiration_date ? `Exp: ${lot.expiration_date}` : 'No expiry'}
                        {lot.is_expired && ' ⚠'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

const styles = {
  center:       { padding: 40, textAlign: 'center', color: '#666' },
  errorBox:     { padding: 20, background: '#fff3cd', borderRadius: 8, margin: 12 },
  emptyState:   { padding: 40, textAlign: 'center' },
  emptyText:    { fontSize: 18, fontWeight: 600, color: '#333' },
  filterBar:    { display: 'flex', gap: 8, padding: '12px 12px 4px', flexWrap: 'wrap' },
  filterBtn:    { padding: '8px 14px', borderRadius: 20, border: '1px solid #dee2e6', fontSize: 14, fontWeight: 600, cursor: 'pointer', display: 'flex', gap: 6, alignItems: 'center', minHeight: 44 },
  filterCount:  { background: 'rgba(0,0,0,0.1)', borderRadius: 10, padding: '0 7px', fontSize: 12 },
  itemCard:     { background: '#fff', margin: '8px 12px', borderRadius: 8, padding: '14px 16px', cursor: 'pointer', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' },
  itemRow:      { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  itemName:     { fontSize: 17, fontWeight: 600, color: '#1a1a1a', flex: 1 },
  qtyBadge:     { fontSize: 20, fontWeight: 700, borderRadius: 8, padding: '4px 14px', minWidth: 48, textAlign: 'center' },
  parInfo:      { fontSize: 13, color: '#666', marginTop: 4 },
  expiryWarn:   { fontSize: 12, fontWeight: 600, color: '#856404', background: '#fff3cd', padding: '2px 8px', borderRadius: 10 },
  lotList:      { marginTop: 12, borderTop: '1px solid #eee', paddingTop: 10 },
  lotHeader:    { fontSize: 12, fontWeight: 700, color: '#666', textTransform: 'uppercase', marginBottom: 6 },
  lotRow:       { display: 'flex', gap: 12, alignItems: 'center', padding: '4px 0', flexWrap: 'wrap' },
  lotQty:       { fontWeight: 700, fontSize: 15, minWidth: 70 },
  lotNum:       { fontSize: 13, color: '#444', flex: 1 },
  lotExp:       { fontSize: 13 },
  btnSecondary: { padding: '10px 20px', background: '#6c757d', color: '#fff', border: 'none', borderRadius: 8, fontSize: 15, cursor: 'pointer', minHeight: 44 },
}
