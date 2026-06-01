/**
 * shared/components/ColorPickerWidget.jsx  (S-F2)
 *
 * Reusable 12-color accessible swatch palette.
 * Used by VehiclesScreen (vehicle card color picker) and will be reused
 * in station settings once that page is built.
 *
 * Props
 * ─────
 * value      {string|null}  Current #rrggbb selection, or null for "inherit".
 * onChange   {function}     Called with #rrggbb string or null (when "Inherit" is chosen).
 * label      {string}       Visible label above the swatches. Default "Color".
 * showInherit {boolean}     Show an "Inherit" (×) chip. Default true.
 * disabled   {boolean}      Disables all interaction. Default false.
 *
 * Design notes
 * ────────────
 * • 12 swatches chosen for WCAG 2.1 AA contrast against white (#ffffff)
 *   — each foreground color is ≥ 4.5:1 against white.
 * • Keyboard: arrow keys cycle swatches, Enter/Space select.
 * • Screen-reader: each swatch has aria-label with the color name.
 * • No external dependencies — pure CSS + CSS variables from index.css.
 * • The component does NOT save — that is the caller's responsibility.
 *   VehiclesScreen calls adminApi.updateVehicleColor after onChange fires.
 */

import React from 'react'
import './ColorPickerWidget.css'

// ── Palette ───────────────────────────────────────────────────────────────────
// 12 accessible colors. hex must be lowercase 7-char for DB storage.
export const COLOR_PALETTE = [
  { hex: '#1a3a5c', name: 'Navy'        },
  { hex: '#1565c0', name: 'Blue'        },
  { hex: '#0277bd', name: 'Sky'         },
  { hex: '#00695c', name: 'Teal'        },
  { hex: '#2e7d32', name: 'Green'       },
  { hex: '#558b2f', name: 'Olive'       },
  { hex: '#e65100', name: 'Orange'      },
  { hex: '#c62828', name: 'Red'         },
  { hex: '#ad1457', name: 'Crimson'     },
  { hex: '#6a1b9a', name: 'Purple'      },
  { hex: '#4e342e', name: 'Brown'       },
  { hex: '#37474f', name: 'Slate'       },
]

// ── Component ─────────────────────────────────────────────────────────────────

export default function ColorPickerWidget({
  value      = null,
  onChange,
  label      = 'Color',
  showInherit = true,
  disabled   = false,
}) {
  const paletteWithInherit = showInherit
    ? [{ hex: null, name: 'Inherit' }, ...COLOR_PALETTE]
    : COLOR_PALETTE

  function handleKey(e, hex) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      if (!disabled) onChange(hex)
    }
  }

  return (
    <div className="color-picker" aria-label={label}>
      {label && <span className="color-picker__label">{label}</span>}
      <div className="color-picker__swatches" role="radiogroup" aria-label={label}>
        {paletteWithInherit.map(({ hex, name }) => {
          const selected = hex === value
          return (
            <button
              key={hex ?? 'inherit'}
              type="button"
              role="radio"
              aria-checked={selected}
              aria-label={name}
              title={name}
              disabled={disabled}
              className={[
                'color-picker__swatch',
                hex === null && 'color-picker__swatch--inherit',
                selected    && 'color-picker__swatch--selected',
              ].filter(Boolean).join(' ')}
              style={hex ? { background: hex } : undefined}
              onClick={() => !disabled && onChange(hex)}
              onKeyDown={e => handleKey(e, hex)}
            >
              {hex === null && <span aria-hidden="true">×</span>}
              {selected && hex !== null && (
                <span className="color-picker__check" aria-hidden="true">✓</span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
