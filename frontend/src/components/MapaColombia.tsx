import { useMemo, useState, useCallback, useRef, useEffect } from 'react'
import { ComposableMap, Geographies, Geography } from 'react-simple-maps'
import { formatCOP } from '../utils/format'

export type Metrica =
  | 'desempleo'
  | 'ocupados'
  | 'ingreso'
  | 'formalidad'
  | 'mujeres'
  | 'dnp'
  | 'snies'

export interface DeptoData {
  departamento: string
  tasa_desempleo?: number | null
  ocupados?: number | null
  no_ocupados?: number | null
  ingreso_promedio?: number | null
  tasa_formalidad?: number | null
  mujeres_pct?: number | null
  dnp_desempeno?: number | null
  matriculados_snies?: number | null
  mujeres_cabeza_hogar_pct?: number | null
  pct_educacion_superior?: number | null
  nivel_educativo_etiqueta?: string | null
}

export interface SectorLider {
  sector: string
  crecimiento_2035_pct: number
}

interface Props {
  data: DeptoData[]
  metric?: Metrica
  onSelectDepto?: (depto: DeptoData | null) => void
  onHoverDepto?: (depto: DeptoData | null) => void
  selectedDepto?: string | null
  sectorLiderNacional?: SectorLider | null
}

const GEO_URL = '/colombia-departments.geojson'

// Mapa de codigo DANE a nombre de departamento (como viene del backend)
// Mapeo de nombres normalizados del GeoJSON a nombres normalizados del backend
const BACKEND_NAME_FIX: Record<string, string> = {
  'BOGOTA DC': 'BOGOTA',
  'BOGOTA D.C.': 'BOGOTA',
  'SAN ANDRES Y PROVIDENCIA': 'ARCHIPIELAGO DE SAN ANDRES',
}

const nameMap: Record<string, string> = {
  '05': 'ANTIOQUIA',
  '08': 'ATLÁNTICO',
  '11': 'BOGOTÁ D.C.',
  '13': 'BOLÍVAR',
  '15': 'BOYACÁ',
  '17': 'CALDAS',
  '18': 'CAQUETÁ',
  '19': 'CAUCA',
  '20': 'CESAR',
  '23': 'CÓRDOBA',
  '25': 'CUNDINAMARCA',
  '27': 'CHOCÓ',
  '41': 'HUILA',
  '44': 'LA GUAJIRA',
  '47': 'MAGDALENA',
  '50': 'META',
  '52': 'NARIÑO',
  '54': 'NORTE DE SANTANDER',
  '63': 'QUINDÍO',
  '66': 'RISARALDA',
  '68': 'SANTANDER',
  '70': 'SUCRE',
  '73': 'TOLIMA',
  '76': 'VALLE DEL CAUCA',
  '81': 'ARAUCA',
  '85': 'CASANARE',
  '86': 'PUTUMAYO',
  '91': 'AMAZONAS',
  '94': 'GUAINÍA',
  '95': 'GUAVIARE',
  '97': 'VAUPÉS',
  '99': 'VICHADA',
  '88': 'SAN ANDRÉS Y PROVIDENCIA',
}

interface MetricConfig {
  label: string
  unit: string
  getter: (d: DeptoData) => number | null
  format: (v: number) => string
  // colores para interpolacion: [bajo, medio, alto]
  colors: [string, string, string]
  // Si true, valores bajos son malos (ej. desempleo). Si false, valores bajos son buenos.
  lowIsBad?: boolean
  // Umbres para clasificar en semaforo; si null se usa min/med/max automatico.
  thresholds?: number[]
  // Etiquetas para cada franja del semaforo
  bucketLabels?: string[]
}

const hexToRgb = (hex: string) => {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return [r, g, b]
}

const rgbToHex = (r: number, g: number, b: number) => {
  return `#${[r, g, b].map(x => Math.round(x).toString(16).padStart(2, '0')).join('')}`
}

const interpolateColor = (c1: string, c2: string, t: number) => {
  const [r1, g1, b1] = hexToRgb(c1)
  const [r2, g2, b2] = hexToRgb(c2)
  return rgbToHex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t)
}

export const METRICAS: Record<Metrica, MetricConfig> = {
  desempleo: {
    label: 'Tasa de desempleo',
    unit: '%',
    getter: (d) => d.tasa_desempleo ?? null,
    format: (v) => `${v.toFixed(1)}%`,
    // Orden: [bajo=azul, medio=amarillo, alto=rojo]
    colors: ['#22d3ee', '#fbbf24', '#ef4444'],
    lowIsBad: true,
    thresholds: [8, 12],
    bucketLabels: ['Bajo desempleo', 'Medio', 'Alto desempleo'],
  },
  ocupados: {
    label: 'Ocupados',
    unit: '',
    getter: (d) => d.ocupados ?? null,
    format: (v) => v.toLocaleString(),
    colors: ['#1e3a5f', '#3b6ea8', '#fbbf24'],
    lowIsBad: false,
  },
  ingreso: {
    label: 'Ingreso promedio',
    unit: 'COP',
    getter: (d) => d.ingreso_promedio ?? null,
    format: (v) => formatCOP(v),
    colors: ['#7c2d12', '#fbbf24', '#22d3ee'],
    lowIsBad: false,
  },
  formalidad: {
    label: 'Tasa de formalidad',
    unit: '%',
    getter: (d) => d.tasa_formalidad ?? null,
    format: (v) => `${v.toFixed(1)}%`,
    colors: ['#ef4444', '#fbbf24', '#22d3ee'],
    lowIsBad: false,
    thresholds: [40, 60],
    bucketLabels: ['Baja (<40%)', 'Media (40-60%)', 'Alta (>60%)'],
  },
  mujeres: {
    label: '% Mujeres ocupadas',
    unit: '%',
    getter: (d) => d.mujeres_pct ?? null,
    format: (v) => `${v.toFixed(1)}%`,
    colors: ['#7c3aed', '#a78bfa', '#fbbf24'],
    lowIsBad: false,
  },
  dnp: {
    label: 'Desempeño municipal',
    unit: '/100',
    getter: (d) => d.dnp_desempeno ?? null,
    format: (v) => v.toFixed(1),
    colors: ['#7c2d12', '#fbbf24', '#22d3ee'],
    lowIsBad: false,
    thresholds: [50, 65],
    bucketLabels: ['Bajo (<50)', 'Medio (50-65)', 'Alto (>65)'],
  },
  snies: {
    label: 'Matriculados SNIES',
    unit: '',
    getter: (d) => d.matriculados_snies ?? null,
    format: (v) => Math.round(v).toLocaleString("es-CO"),
    colors: ['#1e3a5f', '#3b6ea8', '#fbbf24'],
    lowIsBad: false,
  },
}

function getBucketForValue(v: number, config: MetricConfig, min: number, max: number): 0 | 1 | 2 {
  if (config.thresholds && config.thresholds.length === 2) {
    const [t1, t2] = config.thresholds
    if (v <= t1) return 0
    if (v <= t2) return 1
    return 2
  }
  // Fallback a terciles automaticos
  if (min === max) return 1
  const t = (v - min) / (max - min)
  if (t <= 0.33) return 0
  if (t <= 0.66) return 1
  return 2
}

function getColorForValue(v: number, min: number, max: number, config: MetricConfig): string {
  const bucket = getBucketForValue(v, config, min, max)
  // Para desempleo (lowIsBad):
  //   bucket 0 = bajo desempleo (≤8%) -> color 0 (azul/verde bueno)
  //   bucket 2 = alto desempleo (>12%) -> color 2 (rojo malo)
  const idx = config.lowIsBad ? bucket : bucket
  return config.colors[idx]
}

// Constantes para calcular el scale que llena el viewBox
// Colombia: lon ~[-79.5, -66.5] (13°), lat ~[-4.5, 13.8] (18.3°)
const COL_LON_SPAN_RAD = 15 * Math.PI / 180
const mercY = (latDeg: number) => Math.log(Math.tan(Math.PI / 4 + (latDeg * Math.PI / 180) / 2))
const COL_LAT_SPAN_MERC = mercY(14.5) - mercY(-5.0)
const SCALE_PAD = 0.82

export default function MapaColombia({
  data,
  metric = 'desempleo',
  onSelectDepto,
  onHoverDepto,
  selectedDepto,
  sectorLiderNacional = null,
}: Props) {
  const [hovered, setHovered] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState<{ w: number; h: number }>({ w: 0, h: 0 })

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (width > 0 && height > 0) {
          setSize({ w: width, h: height })
        }
      }
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const scale = useMemo(() => {
    if (size.w < 20 || size.h < 20) return 1300
    // Aumentamos el factor para que San Andres y otros territorios pequenos se vean mejor
    return 1.15 * SCALE_PAD * Math.min(size.w / COL_LON_SPAN_RAD, size.h / COL_LAT_SPAN_MERC)
  }, [size.w, size.h])

  const config = METRICAS[metric]

  const lookup = useMemo(() => {
    const map = new Map<string, DeptoData>()
    const normalize = (s: string) =>
      s.trim().toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    data.forEach((d) => {
      map.set(normalize(d.departamento), d)
    })
    return { map, normalize }
  }, [data])

  const getData = useCallback((code: string, rawName: string): DeptoData | null => {
    let normalizedName = lookup.normalize(nameMap[code] || rawName)
    // Corregir casos especiales donde GeoJSON y backend usan nombres diferentes
    normalizedName = BACKEND_NAME_FIX[normalizedName] || normalizedName
    return lookup.map.get(normalizedName) || null
  }, [lookup])

  const getValue = useCallback((code: string, rawName: string): number | null => {
    const d = getData(code, rawName)
    return d ? config.getter(d) : null
  }, [getData, config])

  // Calcular min/max y promedio nacional para escala de colores y comparaciones
  const { min, max, promedioNacional } = useMemo(() => {
    const values = data.map(d => config.getter(d)).filter((v): v is number => v != null)
    if (values.length === 0) return { min: 0, max: 1, promedioNacional: 0 }
    const sum = values.reduce((a, b) => a + b, 0)
    return {
      min: Math.min(...values),
      max: Math.max(...values),
      promedioNacional: sum / values.length,
    }
  }, [data, config])

  // Determinar color del badge segun el valor
  const getBadgeColor = useCallback((v: number): { color: string; label: string } | null => {
    const bucket = getBucketForValue(v, config, min, max)
    const colors = config.colors
    const idx = bucket
    return { color: colors[idx], label: config.bucketLabels?.[idx] || '' }
  }, [config, min, max])

  // Formatear la diferencia vs promedio nacional
  const formatDiff = useCallback((v: number): { text: string; tipo: 'mejor' | 'peor' | 'igual' } | null => {
    if (promedioNacional === 0) return null
    const diff = v - promedioNacional
    const absDiff = Math.abs(diff)
    const formatted = config.format(absDiff)
    // Para desempleo, menos es mejor. Para otras, mas es mejor.
    if (config.lowIsBad) {
      if (diff < -0.1) return { text: `${formatted} por debajo del promedio`, tipo: 'mejor' }
      if (diff > 0.1) return { text: `${formatted} por encima del promedio`, tipo: 'peor' }
    } else {
      if (diff > 0.1) return { text: `${formatted} por encima del promedio`, tipo: 'mejor' }
      if (diff < -0.1) return { text: `${formatted} por debajo del promedio`, tipo: 'peor' }
    }
    return { text: 'Cerca del promedio', tipo: 'igual' }
  }, [promedioNacional, config])

  const getFill = useCallback((code: string, rawName: string) => {
    const v = getValue(code, rawName)
    if (v === null) return '#0e1730'
    return getColorForValue(v, min, max, config)
  }, [getValue, min, max, config])

  const handleClick = (code: string, rawName: string) => {
    const d = getData(code, rawName)
    if (onSelectDepto) {
      onSelectDepto(d)
    }
  }

  const handleMouseEnter = (code: string, rawName: string) => {
    setHovered(code)
    if (onHoverDepto) {
      const d = getData(code, rawName)
      onHoverDepto(d)
    }
  }

  const handleMouseLeave = () => {
    setHovered(null)
    if (onHoverDepto) {
      onHoverDepto(null)
    }
  }

  return (
    <div className="relative w-full h-full flex flex-row">
      <div className="flex-1 flex flex-col min-w-0">
        <div ref={containerRef} className="flex-1 relative overflow-hidden">
          <ComposableMap
            projection="geoMercator"
            projectionConfig={{
              scale,
              center: [-73, 3.5],
            }}
            width={size.w || 800}
            height={size.h || 600}
            style={{ width: '100%', height: '100%' }}
          >
          <defs>
            <filter id="deptGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="2" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <Geographies geography={GEO_URL}>
            {({ geographies }: { geographies: any[] }) =>
              geographies.map((geo) => {
                const code = geo.properties.DPTO
                const rawName = geo.properties.NOMBRE_DPT
                const displayName = nameMap[code] || rawName
                const value = getValue(code, rawName)
                const fill = getFill(code, rawName)
                const isHovered = hovered === code
                const isSelected = selectedDepto === displayName
                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill={fill}
                    stroke="#1a2040"
                    strokeWidth={isSelected ? 3 : isHovered ? 2.5 : 1.5}
                    style={{
                      default: {
                        opacity: value !== null ? 0.95 : 0.4,
                        transition: 'all 0.2s',
                        cursor: 'pointer',
                        strokeWidth: 1.5,
                      },
                      hover: {
                        opacity: 1,
                        stroke: '#d4af37',
                        strokeWidth: 2.2,
                        filter: 'url(#deptGlow)',
                      },
                      pressed: { opacity: 1 },
                    }}
                    onMouseEnter={() => handleMouseEnter(code, rawName)}
                    onMouseLeave={handleMouseLeave}
                    onClick={() => handleClick(code, rawName)}
                  />
                )
              })
            }
          </Geographies>
        </ComposableMap>
      </div>

      {/* Escala de colores tipo semaforo */}
      <div className="mt-3 px-1 shrink-0">
        <div className="text-base font-bold text-slate-200 mb-2">{config.label}</div>
        <div className="grid grid-cols-3 gap-2">
          {(() => {
            const labels = config.bucketLabels || ['Bajo', 'Medio', 'Alto']
            return config.colors.map((color, i) => {
              return (
                <div key={i} className="flex flex-col items-center">
                  <div
                    className="w-full h-3 rounded-md"
                    style={{ background: color, opacity: 0.95 }}
                  />
                  <span className="text-sm text-slate-300 mt-1.5 text-center leading-tight font-medium">{labels[i]}</span>
                </div>
              )
            })
          })()}
        </div>
      </div>
    </div>

    {/* Panel lateral fijo para informacion al hacer hover */}
    <div className={`w-[170px] md:w-[200px] shrink-0 h-full border-l px-3 py-2 text-[11px] z-20 overflow-y-auto transition-colors ${hovered ? 'border-gold-500/20 bg-[#0a0f1f]/95 backdrop-blur shadow-2xl' : 'border-transparent'}`}>
      {hovered && (
        <div>
            {(() => {
              const code = hovered
              const displayName = nameMap[code] || ''
              const d = getData(code, '')
              const v = d ? config.getter(d) : null
              const badge = v !== null ? getBadgeColor(v) : null
              const diff = v !== null ? formatDiff(v) : null
              const informalidad = d?.tasa_formalidad != null ? 100 - d.tasa_formalidad : null
              const total = data.length

              // Rankings: ordenar de mejor a peor
              const rankDesempleo = [...data].filter(x => x.tasa_desempleo != null).sort((a,b) => (a.tasa_desempleo ?? 0) - (b.tasa_desempleo ?? 0))
              const rankFormalidad = [...data].filter(x => x.tasa_formalidad != null).sort((a,b) => (b.tasa_formalidad ?? 0) - (a.tasa_formalidad ?? 0))
              const posDes = rankDesempleo.findIndex(x => x.departamento === d?.departamento) + 1
              const posFormal = rankFormalidad.findIndex(x => x.departamento === d?.departamento) + 1

              return (
                <>
                  <div className="flex items-center gap-2 mb-2">
                    {badge && (
                      <span
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ background: badge.color }}
                      />
                    )}
                    <span className="font-bold text-gold-400 text-base">{displayName}</span>
                    {informalidad != null && posFormal > 0 && (
                      <span className="text-[10px] text-rose-400 font-bold ml-auto">#{posFormal}</span>
                    )}
                  </div>
                  {v !== null && (
                    <>
                      <div className="text-slate-200 text-base">
                        <span className="text-slate-400 font-medium">{config.label}:</span>{' '}
                        <span className="font-bold text-lg">{config.format(v)}</span>
                      </div>
                      {/* Mini barra visual */}
                      <div className="mt-2 mb-2 h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${max > min ? ((v - min) / (max - min)) * 100 : 50}%`,
                            background: badge?.color || '#d4af37',
                          }}
                        />
                      </div>
                      {diff && diff.tipo !== 'igual' && (
                        <div className={`text-xs mb-1 ${
                          diff.tipo === 'mejor' ? 'text-cyan-400' : 'text-red-400'
                        }`}>
                          {diff.tipo === 'mejor' ? '↓' : '↑'} {diff.text}
                        </div>
                      )}
                    </>
                  )}
                  {/* Resumen rapido de indicadores clave */}
                  <div className="mt-2 pt-2 border-t border-white/[0.08] space-y-1.5">
                    {d?.ocupados != null && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400 font-medium">Ocupados</span>
                        <span className="text-slate-200 font-bold">{d.ocupados >= 1000000 ? `${(d.ocupados/1000000).toFixed(1)}M` : d.ocupados.toLocaleString('es-CO')}</span>
                      </div>
                    )}
                    {d?.no_ocupados != null && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400 font-medium">Sin empleo</span>
                        <span className="text-slate-200 font-bold">{d.no_ocupados >= 1000000 ? `${(d.no_ocupados/1000000).toFixed(1)}M` : Math.round(d.no_ocupados).toLocaleString('es-CO')}</span>
                      </div>
                    )}
                    {d?.ingreso_promedio != null && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400 font-medium">Salario promedio</span>
                        <span className="text-slate-200 font-bold">{formatCOP(d.ingreso_promedio)}</span>
                      </div>
                    )}
                    {d?.mujeres_pct != null && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400 font-medium">Mujeres ocupadas</span>
                        <span className="text-slate-200 font-bold">{d.mujeres_pct.toFixed(0)}%</span>
                      </div>
                    )}
                    {informalidad != null && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400 font-medium">Informalidad</span>
                        <span className="text-slate-200 font-bold">{informalidad.toFixed(1)}%</span>
                      </div>
                    )}
                    {d?.tasa_desempleo != null && metric !== 'desempleo' && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400 font-medium">Desempleo</span>
                        <span className="text-slate-200 font-bold">{d.tasa_desempleo.toFixed(1)}% {posDes > 0 && <span className="text-[10px] text-slate-500">#{posDes}</span>}</span>
                      </div>
                    )}
                    {d?.dnp_desempeno != null && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400 font-medium">Gestión pública</span>
                        <span className="text-slate-200 font-bold">{d.dnp_desempeno.toFixed(0)}/100</span>
                      </div>
                    )}
                    {d?.matriculados_snies != null && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400 font-medium">Universitarios</span>
                        <span className="text-slate-200 font-bold">{d.matriculados_snies >= 1000 ? `${(d.matriculados_snies/1000).toFixed(0)}K` : d.matriculados_snies.toLocaleString('es-CO')}</span>
                      </div>
                    )}
                    {d?.nivel_educativo_etiqueta != null && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400 font-medium">Nivel educativo</span>
                        <span className="text-slate-200 font-bold text-xs">{d.nivel_educativo_etiqueta}</span>
                      </div>
                    )}
                    {d?.mujeres_cabeza_hogar_pct != null && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400 font-medium">Mujeres cabeza hogar</span>
                        <span className="text-slate-200 font-bold">{d.mujeres_cabeza_hogar_pct.toFixed(1)}%</span>
                      </div>
                    )}
                    {d?.pct_educacion_superior != null && (
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400 font-medium">Educación superior</span>
                        <span className="text-slate-200 font-bold">{d.pct_educacion_superior.toFixed(1)}%</span>
                      </div>
                    )}
                  </div>
                </>
              )
            })()}
          </div>
        )}
      </div>
    </div>
  )
}
