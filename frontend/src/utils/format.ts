// Utilidades de formato para ALBA

/**
 * Formatea un valor numérico en pesos colombianos (COP).
 * Ejemplos:
 *   2_194_000 -> $2.2M COP
 *   500_000   -> $500K COP
 *   800       -> $800 COP
 */
export function formatCOP(value: number | null | undefined): string {
  if (value == null) return 'N/D'
  const abs = Math.abs(value)
  if (abs >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(1).replace(/\.0$/, '')}M millones`
  }
  if (abs >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`
  }
  if (abs >= 1_000) {
    return `$${(value / 1_000).toFixed(0)}K`
  }
  return `$${value.toLocaleString('es-CO')}`
}

/**
 * Formatea COP con el valor completo (sin abreviar) y COP explícito.
 * Ejemplo: $2,194,000 COP
 */
export function formatCOPFull(value: number | null | undefined): string {
  if (value == null) return 'N/D'
  return `$${value.toLocaleString('es-CO')} COP`
}

/**
 * Formatea un porcentaje.
 */
export function formatPct(value: number | null | undefined, decimals = 1): string {
  if (value == null) return 'N/D'
  return `${value.toFixed(decimals)}%`
}

/**
 * Formatea un número grande con separadores de miles.
 */
export function formatNumber(value: number | null | undefined): string {
  if (value == null) return 'N/D'
  return value.toLocaleString('es-CO')
}
