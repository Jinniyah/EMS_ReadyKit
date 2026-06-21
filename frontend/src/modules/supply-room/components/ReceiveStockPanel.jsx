/**
 * supply-room/components/ReceiveStockPanel.jsx
 * SUPPLY-F3 — Receive stock into the supply room.
 *
 * Layout mirrors Item Catalog exactly:
 *   - Manual "Add Stock" form is always visible (primary action)
 *   - "Upload CSV" is a collapsible disclosure below the form (rare action)
 *   - Collapsed by default — same pattern as CsvImport in admin/ItemCatalog
 *
 * Style: CSS classes only (.rsp-* namespace in supply-room.css).
 * No inline styles. All values use design tokens from index.css :root.
 */
import React, { useState, useRef } from 'react'
import ItemSearchCombobox from '../../../shared/components/ItemSearchCombobox.jsx'
import { supplyApi } from '../api/supplyApi.js'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'

export default function ReceiveStockPanel({ locationId, stationId, onStockAdded }) {
  const { getToken } = useAuth()

  // Manual form state
  const [selectedItem, setSelectedItem] = useState(null)
  const [lotNumber, setLotNumber]       = useState('')
  const [expiryDate, setExpiryDate]     = useState('')
  const [quantity, setQuantity]         = useState('')
  const [saving, setSaving]             = useState(false)
  const [saveMsg, setSaveMsg]           = useState(null)
  const [saveError, setSaveError]       = useState(null)

  // CSV disclosure state — collapsed by default, same as CsvImport
  const [csvExpanded, setCsvExpanded]   = useState(false)
  const fileRef                         = useRef(null)
  const [csvFile, setCsvFile]           = useState(null)
  const [uploading, setUploading]       = useState(false)
  const [csvResult, setCsvResult]       = useState(null)
  const [csvError, setCsvError]         = useState(null)
  const [showCsvErrors, setShowCsvErrors] = useState(false)

  // ── Manual add ─────────────────────────────────────────────────────────────

  async function handleAdd() {
    if (!selectedItem) { setSaveError('Select an item first.'); return }
    const qty = parseInt(quantity, 10)
    if (!qty || qty < 1) { setSaveError('Enter a quantity of at least 1.'); return }
    setSaveError(null)
    setSaving(true)
    try {
      await supplyApi.receiveLot({
        item_id:         selectedItem.item_id,
        location_id:     locationId,
        quantity:        qty,
        lot_number:      lotNumber.trim() || null,
        expiration_date: expiryDate || null,
      }, getToken)
      setSaveMsg('Added ' + qty + ' x ' + selectedItem.name)
      setSelectedItem(null)
      setLotNumber('')
      setExpiryDate('')
      setQuantity('')
      onStockAdded?.()
    } catch (e) {
      setSaveError(e.message)
    } finally {
      setSaving(false)
    }
  }

  // ── CSV upload ─────────────────────────────────────────────────────────────

  function handleFileChange(e) {
    setCsvFile(e.target.files?.[0] ?? null)
    setCsvResult(null)
    setCsvError(null)
    setShowCsvErrors(false)
  }

  async function handleDownloadTemplate() {
    try {
      const url = await supplyApi.getTemplateBlobUrl(getToken)
      const a = document.createElement('a')
      a.href = url
      a.download = 'supply_room_receive_template.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      /* ignore */
    }
  }

  async function handleCsvUpload(e) {
    e.preventDefault()
    if (!csvFile) return
    setCsvError(null)
    setCsvResult(null)
    setShowCsvErrors(false)
    setUploading(true)
    try {
      const result = await supplyApi.receiveCsv(locationId, csvFile, getToken)
      setCsvResult(result)
      setCsvFile(null)
      if (fileRef.current) fileRef.current.value = ''
      if (result.rows_imported > 0) onStockAdded?.()
    } catch (err) {
      setCsvError(err.message)
    } finally {
      setUploading(false)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="rsp">

      {/* ── CSV disclosure — top, collapsed by default, same pattern as Item Catalog ── */}
      <div className="csv-import">

        <button
          type="button"
          className="csv-import__toggle"
          onClick={() => setCsvExpanded(v => !v)}
          aria-expanded={csvExpanded}
        >
          <span>↑ Receive from CSV</span>
          <span className="csv-import__toggle-hint" aria-hidden="true">
            {csvExpanded ? 'Hide' : 'Bulk load stock from a spreadsheet'}
          </span>
          <span aria-hidden="true">{csvExpanded ? '▲' : '▼'}</span>
        </button>

        {csvExpanded && (
          <div className="csv-import__panel">

            {/* Step 1 — Template */}
            <div className="csv-import__step">
              <p className="csv-import__step-label">Step 1 — Download the template</p>
              <p className="csv-import__hint">
                Fill it out in Excel or Google Sheets, then come back and upload it.
                Columns: item name, lot number, expiration date (YYYY-MM-DD), quantity.
                Item names must match the item catalog exactly.
              </p>
              <button
                type="button"
                className="btn btn--secondary btn--full"
                onClick={handleDownloadTemplate}
              >
                ↓ Download Template (CSV)
              </button>
            </div>

            {/* Step 2 — Pick file */}
            <div className="csv-import__step">
              <p className="csv-import__step-label">Step 2 — Choose your completed file</p>
              <input
                ref={fileRef}
                type="file"
                accept=".csv,text/csv"
                className="csv-import__file-input"
                onChange={handleFileChange}
                disabled={uploading}
                aria-label="Choose CSV file to upload"
              />
              {csvFile && (
                <p className="csv-import__filename">
                  {csvFile.name} ({(csvFile.size / 1024).toFixed(1)} KB)
                </p>
              )}
            </div>

            {/* Step 3 — Upload */}
            <div className="csv-import__step">
              <p className="csv-import__step-label">Step 3 — Upload</p>
              <button
                type="button"
                className="btn btn--primary btn--full"
                onClick={handleCsvUpload}
                disabled={!csvFile || uploading}
              >
                {uploading ? 'Uploading...' : '↑ Upload and Receive Stock'}
              </button>
            </div>

            {/* Upload error */}
            {csvError && (
              <div className="csv-import__error" role="alert">
                {csvError}
              </div>
            )}

            {/* Results */}
            {csvResult && (
              <div className="csv-import__results">
                {csvResult.rows_imported > 0 && (
                  <div className="csv-import__result csv-import__result--success">
                    {csvResult.rows_imported} lot{csvResult.rows_imported !== 1 ? 's' : ''} received into supply room
                  </div>
                )}
                {csvResult.rows_skipped > 0 && (
                  <div className="csv-import__result csv-import__result--warning">
                    {csvResult.rows_skipped} row{csvResult.rows_skipped !== 1 ? 's' : ''} skipped — item name not found in catalog
                  </div>
                )}
                {csvResult.errors?.length > 0 && (
                  <div className="csv-import__result csv-import__result--error">
                    <div className="csv-import__result-header">
                      <span>{csvResult.errors.length} row{csvResult.errors.length !== 1 ? 's' : ''} had errors</span>
                      <button
                        type="button"
                        className="csv-import__show-errors"
                        onClick={() => setShowCsvErrors(v => !v)}
                      >
                        {showCsvErrors ? 'Hide details' : 'Show details'}
                      </button>
                    </div>
                    {showCsvErrors && (
                      <ul className="csv-import__error-list">
                        {csvResult.errors.map((e, i) => (
                          <li key={i} className="csv-import__error-row">
                            <span className="csv-import__error-row-num">Row {e.row}</span>
                            {e.item_name && (
                              <span className="csv-import__error-name">{e.item_name}</span>
                            )}
                            <span className="csv-import__error-msg">{e.error}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
                {csvResult.rows_imported === 0 && csvResult.rows_skipped === 0 && !csvResult.errors?.length && (
                  <div className="csv-import__result csv-import__result--warning">
                    The file was processed but contained no data rows.
                  </div>
                )}
              </div>
            )}

          </div>
        )}
      </div>

      {/* ── Manual form — below CSV disclosure, primary daily action ── */}
      <div className="rsp__form">

        <h3 className="rsp__form-title">Add Stock to Supply Room</h3>

        {saveMsg && (
          <div className="rsp__success" role="status">{saveMsg}</div>
        )}
        {saveError && (
          <div className="rsp__error" role="alert">{saveError}</div>
        )}

        <div className="rsp__field">
          <label className="rsp__label">Item *</label>
          <ItemSearchCombobox
            onSelect={setSelectedItem}
            initialItem={selectedItem}
            placeholder="Type to search items..."
            stationId={stationId}
          />
        </div>

        <div className="rsp__row-2">
          <div className="rsp__field">
            <label className="rsp__label" htmlFor="rsp-lot">Lot Number</label>
            <input
              id="rsp-lot"
              className="rsp__input"
              type="text"
              placeholder="e.g. LOT-2026-001"
              value={lotNumber}
              onChange={e => setLotNumber(e.target.value)}
            />
          </div>
          <div className="rsp__field">
            <label className="rsp__label" htmlFor="rsp-expiry">Expiry Date</label>
            <input
              id="rsp-expiry"
              className="rsp__input"
              type="date"
              value={expiryDate}
              onChange={e => setExpiryDate(e.target.value)}
            />
          </div>
        </div>

        <div className="rsp__field">
          <label className="rsp__label" htmlFor="rsp-qty">Quantity *</label>
          <input
            id="rsp-qty"
            className="rsp__input rsp__input--qty"
            type="number"
            min="1"
            placeholder="0"
            value={quantity}
            onChange={e => setQuantity(e.target.value)}
          />
        </div>

        <button
          className="btn btn--primary btn--large"
          onClick={handleAdd}
          disabled={saving}
          type="button"
        >
          {saving ? 'Adding...' : 'Add to Supply Room'}
        </button>

      </div>

    </div>
  )
}
