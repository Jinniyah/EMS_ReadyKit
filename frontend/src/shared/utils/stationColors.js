/**
 * shared/utils/stationColors.js
 * Assigns a consistent brand color to each station.
 *
 * Named stations get their specific color; others cycle through the palette.
 * Colors are deterministic: same station name always gets same color.
 *
 * Each color object:
 *   primary — main color (header background, selected card border)
 *   light   — pale tint (selected card background, row highlights)
 *   text    — text color on primary background (always #ffffff here)
 */

const NAMED_COLORS = {
  // Newberg Township — dark navy blue (their actual uniform shirt color)
  'newberg': { primary: '#1a2f5a', light: '#e8edf5', text: '#ffffff' },

  // Marcellus Township — forest green (distinct from Newberg navy)
  'marcellus': { primary: '#1b4d3e', light: '#e4f0ec', text: '#ffffff' },
}

// Fallback palette for stations without a named color
const PALETTE = [
  { primary: '#1a2f5a', light: '#e8edf5', text: '#ffffff' }, // 0 navy
  { primary: '#1b4d3e', light: '#e4f0ec', text: '#ffffff' }, // 1 forest green
  { primary: '#7b3f00', light: '#f5ece4', text: '#ffffff' }, // 2 brown
  { primary: '#4a0072', light: '#f0e8f5', text: '#ffffff' }, // 3 purple
  { primary: '#b5451b', light: '#f7ece8', text: '#ffffff' }, // 4 burnt orange
  { primary: '#1a3a6b', light: '#e4ecf5', text: '#ffffff' }, // 5 royal blue
  { primary: '#2d5a27', light: '#e8f0e7', text: '#ffffff' }, // 6 deep green
  { primary: '#5a1a3a', light: '#f5e4ec', text: '#ffffff' }, // 7 burgundy
]

/**
 * Returns the color set for a given station.
 * @param {string} stationName
 * @param {number} index  — position in the stations list (palette fallback)
 * @returns {{ primary: string, light: string, text: string }}
 */
export function stationColor(stationName, index = 0) {
  if (!stationName) return PALETTE[0]
  const lower = stationName.toLowerCase()
  for (const [key, color] of Object.entries(NAMED_COLORS)) {
    if (lower.includes(key)) return color
  }
  return PALETTE[index % PALETTE.length]
}

/**
 * Returns CSS custom properties for a station color.
 * @param {string} stationName
 * @param {number} index
 * @returns {React.CSSProperties}
 */
export function stationStyle(stationName, index = 0) {
  const { primary, light, text } = stationColor(stationName, index)
  return { '--sc-primary': primary, '--sc-light': light, '--sc-text': text }
}
