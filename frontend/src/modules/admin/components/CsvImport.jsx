/**
 * modules/admin/components/CsvImport.jsx
 *
 * CSV bulk import panel for the Item Catalog.
 * Lets supervisors and administrators load the full inventory list
 * from a spreadsheet rather than entering items one by one.
 *
 * Flow:
 *   1. Download template (pre-filled example rows, opens in Excel correctly)
 *   2. Fill out the spreadsheet offline
 *   3. Upload — results shown inline: added / skipped / errors
 *
 * UX notes:
 *   - Panel is collapsed by default — it's a rare action, not a daily one
 *   - Template download works even before a file is chosen
 *   - Results are plain English, not HTTP jargon
 *   - Error rows show row number so the user can find them in the spreadsheet
 *   - On success the catalog refreshes automatically (via onImported callback)
 */

import React, { useState, useRef } from 'react'
import { useAuth } from '../../../shared/hooks/useAuth.jsx'
import { apiUpload } from '../../../shared/api/client.js'

const TEMPLATE_URL = '/api/v1/admin/items/import/template'
const IMPORT_URL   = '/api/v1/admin/items/import'

export default function CsvImport({ onImported }) {
  const { getToken } = useAuth()
  const fileRef = useRef(null)

  const [expanded, setExpanded]     = useState(false)
  const [file, setFile]             = useState(null)
  const [uploading, setUploading]   = useState(false)
  const [result, setResult]         = useState(null)   // { created, skipped, errors }
  const [uploadError, setUploadError] = useState(null)
  const [showErrors, setShowErrors] = useState(false)

  // ── Template download ─────────────────────────────────────────────────────

  async function handleTemplateDownload(e) {
    e.preventDefault()
    const token = await getToken()
    const res   = await fetch(TEMPLATE_URL, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) { alert('Could not download template. Please try again.'); return }
    const blob = await res.blob()
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = 'ems_readykit_items_template.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  // ── File selection ────────────────────────────────────────────────────────

  function handleFileChange(e) {
    const selected = e.target.files?.[0] ?? null
    setFile(selected)
    setResult(null)
    setUploadError(null)
    setShowErrors(false)
  }

  // ── Upload ────────────────────────────────────────────────────────────────

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) return

    setUploading(true)
    setResult(null)
    setUploadError(null)
    setShowErrors(false)

    try {
      const form = new FormData()
      form.append('file', file)
      const data = await apiUpload(IMPORT_URL, form, getToken)
      setResult(data)
      setFile(null)
      if (fileRef.current) fileRef.current.value = ''
      if (data.created > 0) onImported?.()
    } catch (err) {
      setUploadError(err.message ?? 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="csv-import">
      <button
        type="button"
        className="csv-import__toggle"
        onClick={() => setExpanded(v => !v)}
        aria-expanded={expanded}
      >
        <span>↑ Import from CSV</span>
        <span className="csv-import__toggle-hint" aria-hidden="true">
          {expanded ? 'Hide' : 'Bulk load items from a spreadsheet'}
        </span>
        <span aria-hidden="true">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="csv-import__panel">

          {/* Step 1 — Template */}
          <div className="csv-import__step">
            <p className="csv-import__step-label">Step 1 — Download the template</p>
            <p className="csv-import__hint">
              Fill it out in Excel or Google Sheets, then come back and upload it.
              Don't change the column headers.
            </p>
            <button
              type="button"
              className="btn btn--secondary btn--full"
              onClick={handleTemplateDownload}
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
            {file && (
              <p className="csv-import__filename">
                📄 {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>

          {/* Step 3 — Upload */}
          <div className="csv-import__step">
            <p className="csv-import__step-label">Step 3 — Upload</p>
            <button
              type="button"
              className="btn btn--primary btn--full"
              onClick={handleUpload}
              disabled={!file || uploading}
            >
              {uploading ? 'Uploading…' : '↑ Upload and Import'}
            </button>
          </div>

          {/* Upload error */}
          {uploadError && (
            <div className="csv-import__error" role="alert">
              ⚠ {uploadError}
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="csv-import__results">
              {result.created > 0 && (
                <div className="csv-import__result csv-import__result--success">
                  ✓ {result.created} item{result.created !== 1 ? 's' : ''} added to the catalog
                </div>
              )}
              {result.skipped > 0 && (
                <div className="csv-import__result csv-import__result--warning">
                  ⚠ {result.skipped} item{result.skipped !== 1 ? 's' : ''} skipped — already exist in the catalog
                </div>
              )}
              {result.errors?.length > 0 && (
                <div className="csv-import__result csv-import__result--error">
                  <div className="csv-import__result-header">
                    <span>✗ {result.errors.length} row{result.errors.length !== 1 ? 's' : ''} had errors</span>
                    <button
                      type="button"
                      className="csv-import__show-errors"
                      onClick={() => setShowErrors(v => !v)}
                    >
                      {showErrors ? 'Hide details' : 'Show details'}
                    </button>
                  </div>
                  {showErrors && (
                    <ul className="csv-import__error-list">
                      {result.errors.map((e, i) => (
                        <li key={i} className="csv-import__error-row">
                          <span className="csv-import__error-row-num">Row {e.row}</span>
                          {e.name && <span className="csv-import__error-name">{e.name}</span>}
                          <span className="csv-import__error-msg">{e.error}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
              {result.created === 0 && result.skipped === 0 && result.errors?.length === 0 && (
                <div className="csv-import__result csv-import__result--warning">
                  The file was processed but contained no data rows.
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
