// Utilidades de formato para ALBA

/**
 * Formatea un valor numérico en pesos colombianos (COP) con valor completo.
 * Ejemplo: 2_194_000 -> $2.194.000
 */
export function formatCOP(value: number | null | undefined): string {
  if (value == null) return 'N/D'
  return `$${Math.round(value).toLocaleString('es-CO')}`
}

/**
 * Formatea COP con el valor completo y COP explícito.
 * Ejemplo: 2_194_000 -> $2.194.000 COP
 */
export function formatCOPFull(value: number | null | undefined): string {
  if (value == null) return 'N/D'
  return `$${Math.round(value).toLocaleString('es-CO')} COP`
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
