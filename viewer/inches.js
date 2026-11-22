// Inches and fractions: the shop's units. Nearest 1/32 in., reduced (28/32 -> 7/8).
export const MM = 25.4

export function split32(mm) {                      // -> { whole, n, d } with n/d reduced, rounded to the nearest 1/32
  const t = Math.round(Math.abs(mm) / MM * 32); let whole = Math.floor(t / 32), n = t % 32, d = 32
  while (n && n % 2 === 0) { n /= 2; d /= 2 }
  return { whole, n, d, neg: mm < 0 }
}
export function inch(mm, { mark = true } = {}) {
  const { whole, n, d, neg } = split32(mm)
  const s = n ? (whole ? `${whole} ${n}/${d}` : `${n}/${d}`) : `${whole}`
  return `${neg ? '−' : ''}${s}${mark ? '″' : ''}`
}
export const mmText = (mm) => `${mm >= 100 ? Math.round(mm) : (Math.round(mm * 10) / 10).toString()} mm`

// Typed sizes: 1 7/8 · 1-7/8 · 1 7/8" · 7/8 · 1.875 · 1.875in · 47mm · 47 mm · 4.7 cm. Returns mm or null.
export function parse(text) {
  let s = String(text || '').trim().toLowerCase().replace(/[″"”]|inches|inch|in\.?$/g, ' ').replace(/\s+/g, ' ').trim()
  if (!s) return null
  let m = s.match(/^(\d+(?:\.\d+)?)\s*(mm|cm|m)$/)
  if (m) return +m[1] * { mm: 1, cm: 10, m: 1000 }[m[2]]
  m = s.match(/^(\d+)(?:\s+|-)(\d+)\s*\/\s*(\d+)$/)                       // 1 7/8, 1-7/8
  if (m && +m[3]) return (+m[1] + +m[2] / +m[3]) * MM
  m = s.match(/^(\d+)\s*\/\s*(\d+)$/)                                       // 7/8
  if (m && +m[2]) return (+m[1] / +m[2]) * MM
  m = s.match(/^(\d*\.?\d+)$/)                                              // 1.875 (inches)
  if (m) return +m[1] * MM
  return null
}
