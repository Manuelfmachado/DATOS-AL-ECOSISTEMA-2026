import { useMemo } from 'react'
import { formatCOP } from '../utils/format'

export type Metrica =
  | 'desempleo'
  | 'ocupados'
  | 'ingreso'
  | 'formalidad'
  | 'mujeres'
  | 'dnp'
  | 'snies'

interface DeptoData {
  departamento: string
  tasa_desempleo?: number | null
  ocupados?: number | null
  ingreso_promedio?: number | null
  tasa_formalidad?: number | null
  mujeres_pct?: number | null
  dnp_desempeno?: number | null
  matriculados_snies?: number | null
}

interface Props {
  data: DeptoData[]
  metric?: Metrica
  width?: number
  height?: number
}

const deptos: { id: string; name: string; x: number; y: number }[] = [
  { id: 'Amazonas', name: 'Amazonas', x: 115, y: 215 },
  { id: 'Antioquia', name: 'Antioquia', x: 78, y: 55 },
  { id: 'Arauca', name: 'Arauca', x: 165, y: 55 },
  { id: 'Atlántico', name: 'Atlántico', x: 115, y: 20 },
  { id: 'Bolívar', name: 'Bolívar', x: 108, y: 38 },
  { id: 'Boyacá', name: 'Boyacá', x: 125, y: 70 },
  { id: 'Caldas', name: 'Caldas', x: 95, y: 75 },
  { id: 'Caquetá', name: 'Caquetá', x: 110, y: 160 },
  { id: 'Casanare', name: 'Casanare', x: 145, y: 75 },
  { id: 'Cauca', name: 'Cauca', x: 70, y: 120 },
  { id: 'Cesar', name: 'Cesar', x: 125, y: 35 },
  { id: 'Chocó', name: 'Chocó', x: 55, y: 85 },
  { id: 'Córdoba', name: 'Córdoba', x: 88, y: 42 },
  { id: 'Cundinamarca', name: 'Cundinamarca', x: 115, y: 82 },
  { id: 'Guainía', name: 'Guainía', x: 170, y: 150 },
  { id: 'Guaviare', name: 'Guaviare', x: 145, y: 150 },
  { id: 'Huila', name: 'Huila', x: 105, y: 108 },
  { id: 'La Guajira', name: 'La Guajira', x: 140, y: 10 },
  { id: 'Magdalena', name: 'Magdalena', x: 120, y: 25 },
  { id: 'Meta', name: 'Meta', x: 130, y: 105 },
  { id: 'Nariño', name: 'Nariño', x: 62, y: 175 },
  { id: 'Norte de Santander', name: 'Norte de Santander', x: 155, y: 45 },
  { id: 'Putumayo', name: 'Putumayo', x: 78, y: 185 },
  { id: 'Quindío', name: 'Quindío', x: 92, y: 80 },
  { id: 'Risaralda', name: 'Risaralda', x: 88, y: 72 },
  { id: 'San Andrés y Providencia', name: 'San Andrés', x: 55, y: 5 },
  { id: 'Santander', name: 'Santander', x: 130, y: 55 },
  { id: 'Sucre', name: 'Sucre', x: 100, y: 32 },
  { id: 'Tolima', name: 'Tolima', x: 100, y: 92 },
  { id: 'Valle del Cauca', name: 'Valle del Cauca', x: 78, y: 98 },
  { id: 'Vaupés', name: 'Vaupés', x: 155, y: 185 },
  { id: 'Vichada', name: 'Vichada', x: 180, y: 110 },
  { id: 'Bogotá D.C.', name: 'Bogotá', x: 117, y: 82 },
]

const colombiaPath = `
  M 152 5
  Q 145 6 138 8
  Q 130 10 125 14
  Q 118 18 112 22
  Q 104 26 98 32
  Q 90 38 82 44
  Q 74 50 68 58
  Q 60 66 55 75
  Q 48 86 42 100
  Q 38 112 38 125
  Q 38 138 42 150
  Q 46 162 50 170
  Q 56 185 62 195
  Q 68 205 75 212
  Q 84 220 95 224
  Q 108 228 120 227
  Q 130 225 140 220
  Q 150 213 158 205
  Q 166 195 172 182
  Q 178 168 182 152
  Q 186 135 188 118
  Q 190 102 189 86
  Q 188 70 184 56
  Q 180 42 174 30
  Q 168 20 162 14
  Q 157 9 152 5
  Z
`

// Mapeo: nombre mostrado en el mapa -> nombre que devuelve el backend (uppercase)
const NAME_MAP: Record<string, string> = {
  'Bogotá D.C.': 'BOGOTÁ',
  'San Andrés y Providencia': 'ARCHIPIÉLAGO DE SAN ANDRÉS',
}

// Definicion de paletas y cortes para cada metrica
const METRICAS: Record<Metrica, {
  label: string
  unit: string
  getter: (d: DeptoData) => number | null
  format: (v: number) => string
  // Umbrales [bajo, medio, alto] - cada uno define el color del rango
  stops: [number, number, number, number]
  // Paleta de 4 colores: bajo -> alto
  palette: [string, string, string, string]
  inverse?: boolean  // si true, mayor valor = peor (rojo). Si false, mayor valor = mejor (cyan)
}> = {
  desempleo: {
    label: 'Tasa de desempleo',
    unit: '%',
    getter: (d) => d.tasa_desempleo ?? null,
    format: (v) => v.toFixed(1) + '%',
    stops: [8, 12, 18, 30],
    palette: ['#22d3ee', '#fbbf24', '#f59e0b', '#ef4444'],
    inverse: true,
  },
  ocupados: {
    label: 'Ocupados',
    unit: '',
    getter: (d) => d.ocupados ?? null,
    format: (v) => v.toLocaleString(),
    stops: [200, 500, 1000, 3000],
    palette: ['#1e3a5f', '#3b6ea8', '#7da3d6', '#fbbf24'],
    inverse: false,
  },
  ingreso: {
    label: 'Ingreso promedio',
    unit: 'COP',
    getter: (d) => d.ingreso_promedio ?? null,
    format: (v) => formatCOP(v),
    stops: [1500000, 2000000, 2500000, 3000000],
    palette: ['#7c2d12', '#c2410c', '#fbbf24', '#22d3ee'],
    inverse: false,
  },
  formalidad: {
    label: 'Tasa de formalidad',
    unit: '%',
    getter: (d) => d.tasa_formalidad ?? null,
    format: (v) => v.toFixed(1) + '%',
    stops: [20, 30, 40, 50],
    palette: ['#ef4444', '#f59e0b', '#fbbf24', '#22d3ee'],
    inverse: false,
  },
  mujeres: {
    label: '% Mujeres ocupadas',
    unit: '%',
    getter: (d) => d.mujeres_pct ?? null,
    format: (v) => v.toFixed(1) + '%',
    stops: [30, 40, 45, 50],
    palette: ['#7c3aed', '#a78bfa', '#c4b5fd', '#fbbf24'],
    inverse: false,
  },
  dnp: {
    label: 'Desempeño municipal (DNP)',
    unit: '/100',
    getter: (d) => d.dnp_desempeno ?? null,
    format: (v) => v.toFixed(1),
    stops: [40, 50, 60, 70],
    palette: ['#7c2d12', '#c2410c', '#fbbf24', '#22d3ee'],
    inverse: false,
  },
  snies: {
    label: 'Matriculados educación superior',
    unit: '',
    getter: (d) => d.matriculados_snies ?? null,
    format: (v) => Math.round(v).toLocaleString("es-CO"),
    stops: [100000, 500000, 1500000, 5000000],
    palette: ['#1e3a5f', '#3b6ea8', '#7da3d6', '#fbbf24'],
    inverse: false,
  },
}

function pickColor(value: number, m: typeof METRICAS[Metrica]): string {
  if (m.inverse) {
    if (value <= m.stops[0]) return m.palette[0]
    if (value <= m.stops[1]) return m.palette[1]
    if (value <= m.stops[2]) return m.palette[2]
    return m.palette[3]
  } else {
    if (value <= m.stops[0]) return m.palette[0]
    if (value <= m.stops[1]) return m.palette[1]
    if (value <= m.stops[2]) return m.palette[2]
    return m.palette[3]
  }
}

export default function MapaColombiaReal({ data, metric = 'desempleo', width = 260, height = 320 }: Props) {
  const m = METRICAS[metric]

  const lookup = useMemo(() => {
    const norm = (s: string) => s.trim().toUpperCase()
    const map = new Map<string, DeptoData>()
    data.forEach((d) => {
      const key = norm(d.departamento)
      if (!map.has(key)) map.set(key, d)
    })
    return map
  }, [data])

  const getValue = (name: string): number | null => {
    const backendName = NAME_MAP[name] || name
    return m.getter(lookup.get(backendName.toUpperCase()) || ({} as DeptoData))
  }

  const getColor = (name: string) => {
    const v = getValue(name)
    if (v === null) return '#475569'
    return pickColor(v, m)
  }

  const getRadius = (name: string) => {
    const v = getValue(name)
    if (v === null) return 1.8
    // Normalizar radio segun el valor relativo a los stops
    const s = m.stops
    const ratio = Math.min(1, Math.max(0, (v - s[0]) / (s[3] - s[0])))
    return 2 + ratio * 2
  }

  return (
    <div className="relative w-full h-full flex items-center justify-center">
      <svg viewBox="0 0 200 250" className="w-full h-full drop-shadow-[0_0_25px_rgba(245,158,11,0.2)]">
        <defs>
          <radialGradient id="colombiaGlow" cx="50%" cy="50%" r="55%">
            <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.08" />
            <stop offset="100%" stopColor="#f59e0b" stopOpacity="0" />
          </radialGradient>
          <filter id="goldGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="1.5" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <ellipse cx="100" cy="125" rx="95" ry="120" fill="url(#colombiaGlow)" />

        <path
          d={colombiaPath}
          fill="rgba(20, 26, 40, 0.85)"
          stroke="rgba(245, 158, 11, 0.35)"
          strokeWidth="1"
          strokeLinejoin="round"
        />

        {deptos.map((d) => {
          const value = getValue(d.name)
          const color = getColor(d.name)
          const r = getRadius(d.name)
          const hasData = value !== null
          return (
            <g key={d.id} className="cursor-pointer">
              {hasData && (
                <circle cx={d.x} cy={d.y} r={r * 2.8} fill={color} fillOpacity={0.18} />
              )}
              <circle
                cx={d.x}
                cy={d.y}
                r={r}
                fill={color}
                filter={hasData ? 'url(#goldGlow)' : undefined}
              />
              <circle cx={d.x} cy={d.y} r={r * 0.45} fill="white" fillOpacity={0.9} />
              <title>{`${d.name} - ${m.label}: ${value !== null ? m.format(value) : 'sin datos'}`}</title>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
