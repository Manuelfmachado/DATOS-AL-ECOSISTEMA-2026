import { useEffect, useMemo, useState, Fragment, type ReactNode } from 'react'
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, XAxis, YAxis,
  Tooltip, ResponsiveContainer, CartesianGrid, Cell, LabelList,
  ReferenceLine, Legend, ComposedChart,
} from 'recharts'
import api from '../services/api'
import { formatCOP, formatCOPFull, formatNumber } from '../utils/format'

// ===========================================================================
// Tipos
// ===========================================================================

interface SimulacionMeta {
  id: string
  nombre: string
  descripcion: string
  fuentes: string[]
}

interface TrayectoriaResult {
  programa: string
  departamento: string
  nivel_detectado: string
  salario_base_ole_cop: number
  salario_inicial_cop: number
  salario_inicial_rango: string
  calidad_saberpro: number | null
  ajuste_territorial: number
  profesion_chronos: string
  fuente_crecimiento: string
  anos: number[]
  mediana: number[]
  p10: number[]
  p90: number[]
  crecimiento_anual_pct: number
  salario_5a_cop: number
  salario_10a_cop: number
  recomendacion: string
  desglose: string
}

interface MigracionResult {
  origen: Record<string, any>
  destino: Record<string, any>
  delta: Record<string, number>
  score_atractivo: number
  veredicto: string
}

interface ReskillingResult {
  ocupacion_actual: string
  ocupacion_deseada: string
  habilidades_actuales: number
  habilidades_deseadas: number
  habilidades_coinciden: string[]
  habilidades_faltan: string[]
  habilidades_sobran: string[]
  overlap_pct: number
  faltan_criticas_wef: { habilidad: string; demanda_wef: number }[]
  programas_sena_recomendados: { habilidad_faltante: string; programa_sena: string; departamento: string; duracion_horas: number; costo: number }[]
  veredicto: string
}

interface DemandaResult {
  sector_ciiu: string
  sector_nombre: string
  empleo_actual: number
  empleo_proyectado_12m: number
  delta_empleo_pct: number
  salario_actual: number
  salario_proyectado_12m: number
  delta_salario_pct: number
  meses: number[]
  proyeccion_base: number[]
  proyeccion_escenario: number[]
  parametros: { crecimiento_pib_pct: number; inflacion_pct: number; inversion_pct: number }
  veredicto: string
}

interface DecisionResult {
  anos: number[]
  estudiar: { trayectoria: number[]; ingreso_acumulado_10a: number; anos_inversion: number; descripcion: string }
  trabajar: { trayectoria: number[]; ingreso_acumulado_10a: number; crecimiento_anual_pct: number; descripcion: string }
  emprender: { mediana: number[]; p10: number[]; p90: number[]; ingreso_acumulado_10a: number; prob_exito_pct: number; descripcion: string }
  mejor_opcion: string
  veredicto: string
  parametros: Record<string, any>
}

interface EscenarioResult {
  tipo: string
  label: string
  color: string
  salario_inicial_cop: number
  crecimiento_anual_pct: number
  anos_inversion: number
  anos: number[]
  mediana: number[]
  p10: number[]
  p90: number[]
  ingreso_acumulado_10a: number
  delta_vs_base_cop: number
  descripcion: string
  profesion_chronos: string
  costo_educacion_cop?: number
  anos_recuperacion?: number
}

interface QuePasaSiResponse {
  programa: string
  departamento: string
  edad: number
  nivel_detectado: string
  escenarios: EscenarioResult[]
  mejor_opcion: string
  veredicto: string
  alerta_saturacion?: {
    riesgo: string
    mensaje: string
    detalle: string
  }
}

// ===========================================================================
// Constantes
// ===========================================================================

const SIMULACIONES: SimulacionMeta[] = [
  {
    id: 'trayectoria',
    nombre: 'Trayectoria Profesional',
    descripcion: 'Proyecta tu salario a 10 años según tu programa académico y departamento',
    fuentes: ['OLE/MEN', 'Saber Pro', 'GEIH', 'Chronos T5'],
  },
  {
    id: 'migracion',
    nombre: 'Migración Territorial',
    descripcion: 'Compara condiciones laborales entre departamentos antes de mudarte',
    fuentes: ['GEIH', 'DNP/MDM'],
  },
  {
    id: 'reskilling',
    nombre: 'Reskilling / Transición',
    descripcion: 'Calcula la brecha de habilidades entre ocupaciones y recomienda formación SENA',
    fuentes: ['ESCO', 'SENA', 'WEF Future of Jobs'],
  },
  {
    id: 'demanda-sectorial',
    nombre: 'Demanda Sectorial',
    descripcion: 'Simula el impacto de escenarios macroeconómicos en el empleo sectorial',
    fuentes: ['GEIH mensual', 'Chronos T5', 'RUES'],
  },
  {
    id: 'decision',
    nombre: 'Estudiar vs Trabajar vs Emprender',
    descripcion: 'Compara 3 trayectorias a 10 años según tu perfil',
    fuentes: ['GEIH', 'RUES', 'Chronos T5', 'OLE/MEN'],
  },
]

const tooltipStyle = {
  contentStyle: { background: '#0a0f1f', border: '1px solid rgba(212,175,55,0.35)', borderRadius: '10px', color: '#e9ecf5', fontSize: '13px' },
  itemStyle: { color: '#e9ecf5' },
  labelStyle: { color: '#d4af37', fontWeight: 700 },
}

const NIVELES_EDUCATIVOS = ['Bachiller', 'Tecnico', 'Tecnologo', 'Universitario', 'Especializacion', 'Maestria', 'Doctorado']
const SECTORES_INTERES = ['Agricultura', 'Industria', 'Servicios']

// Lista de fallback si el backend no responde al cargar departamentos
const DEPTOS_FALLBACK = [
  'Amazonas', 'Antioquia', 'Arauca', 'Archipiélago de San Andrés', 'Atlántico',
  'Bogotá D.C.', 'Bolívar', 'Boyacá', 'Caldas', 'Caquetá', 'Casanare', 'Cauca',
  'Cesar', 'Chocó', 'Cundinamarca', 'Córdoba', 'Guainía', 'Guaviare', 'Huila',
  'La Guajira', 'Magdalena', 'Meta', 'Nariño', 'Norte de Santander', 'Putumayo',
  'Quindío', 'Risaralda', 'Santander', 'Sucre', 'Tolima', 'Valle del Cauca',
  'Vaupés', 'Vichada',
]

// Hook reutilizable para cargar departamentos con fallback
function useDepartamentos() {
  const [deptos, setDeptos] = useState<string[]>(DEPTOS_FALLBACK)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    api.get('/simulacion/trayectoria/departamentos')
      .then((r) => {
        if (r.data.departamentos?.length > 0) setDeptos(r.data.departamentos)
      })
      .catch(() => {/* fallback ya está cargado */})
      .finally(() => setCargando(false))
  }, [])

  return { deptos, cargando }
}

// ===========================================================================
// Componente principal — tabs Simulador unificado + Demanda Sectorial
// ===========================================================================

export default function Simulacion() {
  const [tab, setTab] = useState<'que-pasa-si' | 'viabilidad' | 'priorizacion'>('que-pasa-si')

  return (
    <div className="animate-fade-in space-y-5">
      <div>
        <h1 className="text-5xl font-bold text-gold-400 font-display">
          Simulación
        </h1>
        <p className="text-base text-white font-semibold mt-1">
          Explora escenarios laborales basados en datos reales del mercado colombiano.
        </p>
      </div>

      <div className="flex gap-1 bg-white/[0.03] rounded-xl p-1 border border-white/[0.06] w-fit">
        <button
          onClick={() => setTab('que-pasa-si')}
          className={`px-4 py-2 rounded-lg text-lg font-bold text-white transition-all ${
            tab === 'que-pasa-si'
              ? 'bg-[#d4af37]/20 text-white border border-[#d4af37]/50 shadow-[0_0_14px_rgba(212,175,55,0.25)]'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          ¿Y si...?
        </button>
        <button
          onClick={() => setTab('viabilidad')}
          className={`px-4 py-2 rounded-lg text-lg font-bold text-white transition-all ${
            tab === 'viabilidad'
              ? 'bg-[#d4af37]/20 text-white border border-[#d4af37]/50 shadow-[0_0_14px_rgba(212,175,55,0.25)]'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Viabilidad de Programa
        </button>
        <button
          onClick={() => setTab('priorizacion')}
          className={`px-4 py-2 rounded-lg text-lg font-bold text-white transition-all ${
            tab === 'priorizacion'
              ? 'bg-[#d4af37]/20 text-white border border-[#d4af37]/50 shadow-[0_0_14px_rgba(212,175,55,0.25)]'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Priorización Territorial
        </button>
      </div>

      {tab === 'que-pasa-si' && <SimQuePasaSi />}
      {tab === 'viabilidad' && <SimViabilidad />}
      {tab === 'priorizacion' && <SimPriorizacion />}

    </div>
  )
}


// ===========================================================================
// SIMULADOR UNIFICADO "¿Y si...?" — una pantalla, un gráfico, múltiples escenarios
// ===========================================================================

const OCUP_SUGERIDAS = [
  'CIENCIA DE DATOS', 'DESARROLLO DE SOFTWARE', 'MARKETING DIGITAL',
  'CIBERSEGURIDAD', 'FINANZAS', 'ENFERMERIA', 'CONTADURIA',
  'LOGISTICA', 'AGRONOMIA', 'INGENIERIA ELECTRICA', 'ELECTRONICA',
  'RECURSOS HUMANOS', 'EDUCACION', 'ENERGIAS RENOVABLES',
  'GESTION DE PROYECTOS', 'DISEÑO UX UI', 'INTELIGENCIA ARTIFICIAL',
]

function SimQuePasaSi() {
  const { deptos } = useDepartamentos()
  const [programas, setProgramas] = useState<string[]>([])
  const [programaQuery, setProgramaQuery] = useState('')
  const [programa, setPrograma] = useState('')
  const [departamento, setDepartamento] = useState('Bogotá D.C.')
  const [edad, setEdad] = useState(22)

  // Scenario toggles
  const [enabled, setEnabled] = useState<Set<string>>(new Set(['base']))
  const [migracionDest, setMigracionDest] = useState('Antioquia')
  const [posgradoNivel, setPosgradoNivel] = useState('Maestria')
  const [reskillingOcup, setReskillingOcup] = useState('CIENCIA DE DATOS')
  const [emprenderSector, setEmprenderSector] = useState('Servicios')
  const [emprenderCapital, setEmprenderCapital] = useState(20000000)
  const [trabajarNivel, setTrabajarNivel] = useState('Bachiller')

  const [result, setResult] = useState<QuePasaSiResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // program search
  useEffect(() => {
    const t = setTimeout(() => {
      if (programaQuery.length >= 2) {
        api.get('/simulacion/trayectoria/programas', { params: { q: programaQuery, limit: 20 } })
          .then((r) => setProgramas(r.data.programas))
          .catch(() => setProgramas([]))
      } else setProgramas([])
    }, 300)
    return () => clearTimeout(t)
  }, [programaQuery])

  const toggle = (tipo: string) => {
    setEnabled((prev) => {
      const next = new Set(prev)
      if (next.has(tipo)) {
        if (tipo === 'base') return prev // base always on
        next.delete(tipo)
      } else next.add(tipo)
      return next
    })
  }

  const run = async () => {
    if (!programa) { setError('Selecciona un programa académico'); return }
    setLoading(true); setError(''); setResult(null)
    const escenarios: any[] = []
    enabled.forEach((tipo) => {
      switch (tipo) {
        case 'migracion':
          escenarios.push({ tipo, departamento_destino: migracionDest }); break
        case 'posgrado':
          escenarios.push({ tipo, nivel: posgradoNivel }); break
        case 'reskilling':
          escenarios.push({ tipo, ocupacion_destino: reskillingOcup }); break
        case 'emprender':
          escenarios.push({ tipo, sector_interes: emprenderSector, capital_disponible_cop: emprenderCapital }); break
        case 'trabajar':
          escenarios.push({ tipo, nivel_actual: trabajarNivel }); break
        default:
          escenarios.push({ tipo: 'base' })
      }
    })
    try {
      const r = await api.post('/simulacion/que-pasa-si', { programa, departamento, edad, escenarios })
      setResult(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Error al simular')
    } finally { setLoading(false) }
  }

  const chartData = useMemo(() => {
    if (!result || result.escenarios.length === 0) return []
    return result.escenarios[0].anos.map((a, i) => {
      const row: Record<string, any> = { año: a }
      result.escenarios.forEach((e) => {
        row[e.tipo] = e.mediana[i] || 0
      })
      return row
    })
  }, [result])

  const toggleRow = (tipo: string, label: string, color: string, inline: ReactNode, alwaysOn = false) => (
    <label
      className={`flex items-center gap-3 px-4 py-3 rounded-lg border transition-all cursor-pointer ${
        enabled.has(tipo)
          ? `${color} border-${color}/30 bg-${color}/5`
          : 'border-transparent bg-white/[0.02] opacity-50 hover:opacity-80'
      }`}
    >
      <input
        type="checkbox"
        checked={enabled.has(tipo)}
        onChange={() => toggle(tipo)}
        disabled={alwaysOn}
        className="accent-amber-500 w-4 h-4 rounded"
        style={{ accentColor: color }}
      />
      <span className="text-base text-slate-300 font-medium min-w-[160px]">{label}</span>
      {inline}
    </label>
  )

  const selectStyles = "bg-white/[0.03] border border-white/0.08 rounded-lg px-2 py-1.5 text-base text-slate-300 focus:border-amber-500/40 outline-none"

  return (
    <div className="space-y-4">
      {/* Perfil */}
      <div className="plate card p-5">
        <h3 className="text-base font-semibold text-gold-400 uppercase tracking-wider mb-4">Perfil</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="text-base text-slate-400 mb-1 block">Programa</label>
            <input
              type="text"
              value={programaQuery}
              onChange={(e) => { setProgramaQuery(e.target.value); setPrograma('') }}
              placeholder="Busca tu programa..."
              className={`${selectStyles} w-full`}
            />
            {programas.length > 0 && !programa && (
              <div className="plate card mt-1 max-h-48 overflow-y-auto border-amber-500/20">
                {programas.map((p) => (
                  <button
                    key={p}
                    onClick={() => { setPrograma(p); setProgramaQuery(p); setProgramas([]) }}
                    className="block w-full text-left px-3 py-2 text-base text-slate-300 hover:bg-amber-500/10 hover:text-gold-400 transition-colors"
                  >
                    {p}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div>
            <label className="text-base text-slate-400 mb-1 block">Departamento</label>
            <select value={departamento} onChange={(e) => setDepartamento(e.target.value)} className={`${selectStyles} w-full`}>
              {deptos.map((d) => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="text-base text-slate-400 mb-1 block">Edad</label>
            <input type="number" value={edad} onChange={(e) => setEdad(Number(e.target.value))} min={16} max={70} className={`${selectStyles} w-full`} />
          </div>
        </div>
      </div>

      {/* Escenarios */}
      <div className="plate card p-5">
        <h3 className="text-base font-semibold text-gold-400 uppercase tracking-wider mb-4">¿Y si...?</h3>
        <div className="space-y-2">
          {toggleRow('base', 'Sigo mi plan actual', 'border-amber-500/40', <span className="text-xs text-slate-500">Tu trayectoria base</span>, true)}
          {toggleRow('migracion', 'Me mudo a...', 'border-blue-500/40',
            <select value={migracionDest} onChange={(e) => setMigracionDest(e.target.value)} className={selectStyles} disabled={!enabled.has('migracion')}>
              {deptos.filter((d) => d !== departamento).map((d) => <option key={d}>{d}</option>)}
            </select>
          )}
          {toggleRow('posgrado', 'Estudio un...', 'border-green-500/40',
            <select value={posgradoNivel} onChange={(e) => setPosgradoNivel(e.target.value)} className={selectStyles} disabled={!enabled.has('posgrado')}>
              <option>Especializacion</option>
              <option>Maestria</option>
              <option>Doctorado</option>
            </select>
          )}
          {toggleRow('reskilling', 'Hago reskilling a...', 'border-purple-500/40',
            <div className="flex-1">
              <select
                value={reskillingOcup}
                onChange={(e) => setReskillingOcup(e.target.value)}
                disabled={!enabled.has('reskilling')}
                className={`${selectStyles} w-full`}
              >
                {OCUP_SUGERIDAS.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          )}
          {toggleRow('emprender', 'Emprendo un negocio', 'border-orange-500/40',
            <div className="flex items-center gap-2">
              <select value={emprenderSector} onChange={(e) => setEmprenderSector(e.target.value)} className={selectStyles} disabled={!enabled.has('emprender')}>
                {SECTORES_INTERES.map((s) => <option key={s}>{s}</option>)}
              </select>
              <span className="text-xs text-slate-500">Capital:</span>
              <input
                type="number"
                value={emprenderCapital / 1_000_000}
                onChange={(e) => setEmprenderCapital(Number(e.target.value) * 1_000_000)}
                min={0} max={500} step={1}
                className={selectStyles} style={{ width: 80 }}
                disabled={!enabled.has('emprender')}
              />
              <span className="text-xs text-slate-500">M COP</span>
            </div>
          )}
          {toggleRow('trabajar', 'Solo trabajo ya', 'border-slate-500/40',
            <select value={trabajarNivel} onChange={(e) => setTrabajarNivel(e.target.value)} className={selectStyles} disabled={!enabled.has('trabajar')}>
              {NIVELES_EDUCATIVOS.map((n) => <option key={n}>{n}</option>)}
            </select>
          )}
        </div>

        <div className="mt-5">
          <button
            onClick={run}
            disabled={loading || !programa}
            className="px-6 py-2.5 rounded-lg font-semibold text-base transition-all bg-gold-400 text-[#0a0f1f] hover:bg-gold-400/90 disabled:opacity-40"
          >
            {loading ? 'Simulando...' : 'Simular'}
          </button>
          {error && <p className="text-rose-400 text-sm mt-3">{error}</p>}
        </div>
      </div>

      {/* Resultados */}
      {result && (
        <>
          {/* Veredicto prominente */}
          <div className="plate card p-5 border-amber-500/30 bg-gradient-to-r from-amber-500/10 to-transparent">
            <div className="flex items-start gap-3">
              <span className="text-2xl">🏆</span>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs uppercase tracking-wider text-amber-400 font-bold">Mejor opción</span>
                  <span className="px-2 py-0.5 rounded text-xs font-bold bg-amber-500/20 text-amber-300">
                    {result.escenarios.find((e: any) => e.tipo === result.mejor_opcion)?.label || result.mejor_opcion}
                  </span>
                </div>
                <p className="text-base text-slate-200 font-medium leading-relaxed">{result.veredicto}</p>
                <p className="text-xs text-slate-500 mt-1.5">
                  Nivel detectado: {result.nivel_detectado}. Proyecciones basadas en OLE, GEIH, Saber Pro y Chronos T5.
                </p>
              </div>
            </div>
          </div>

          {/* Gráfico con bandas de riesgo */}
          <div className="plate card p-5">
            <h3 className="text-base font-semibold text-gold-400 uppercase tracking-wider mb-4">Trayectoria a 10 años</h3>
            <ResponsiveContainer width="100%" height={380}>
              <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="año" stroke="#64748b" tick={{ fontSize: 12 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 12 }} tickFormatter={(v: number) => `$${(v / 1_000_000).toFixed(0)}M`} />
                <Tooltip contentStyle={{ background: '#0a0f1f', border: '1px solid rgba(212,175,55,0.35)', borderRadius: '10px', color: '#e9ecf5' }} formatter={(v: any, name: string) => { const e = result.escenarios.find((x: any) => x.tipo === name); return [`$${Math.round(Number(v)).toLocaleString("es-CO")}`, e?.label || name] }} />
                <Legend formatter={(val: string) => { const e = result.escenarios.find((x: any) => x.tipo === val); return e?.label || val }} />
                {result.escenarios.map((e: any) => (
                  <>
                    {e.p10 && e.p90 && (
                      <Area type="monotone" dataKey="año" fill={e.color} fillOpacity={0.08} stroke="none" isAnimationActive={false} />
                    )}
                    <Line type="monotone" dataKey={e.tipo} stroke={e.color} strokeWidth={e.tipo === 'base' ? 3 : 2} dot={false} activeDot={{ r: 4 }} />
                  </>
                ))}
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {result.escenarios.map((e: any) => {
              const isBest = e.tipo === result.mejor_opcion
              const deltaColor = e.delta_vs_base_cop > 0 ? 'text-green-400' : e.delta_vs_base_cop < 0 ? 'text-rose-400' : 'text-slate-500'
              const deltaSign = e.delta_vs_base_cop > 0 ? '+' : ''
              return (
                <div key={e.tipo} className={`plate card p-4 text-center ${isBest ? 'ring-2 ring-amber-500/60 bg-amber-500/5' : ''}`}>
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: e.color }} />
                    <span className="text-xs text-slate-300 font-medium truncate">{e.label}</span>
                    {isBest && <span className="text-xs text-amber-400">★</span>}
                  </div>
                  <p className="text-lg font-bold font-display text-white">{formatCOP(e.ingreso_acumulado_10a)}</p>
                  <p className="text-xs text-slate-500">acumulado 10 años</p>
                  {e.tipo !== 'base' && (
                    <p className={`text-xs mt-1 ${deltaColor} font-semibold`}>
                      {deltaSign}{formatCOP(Math.abs(e.delta_vs_base_cop))} vs base
                    </p>
                  )}
                  {e.tipo !== 'base' && (
                    <p className="text-xs text-slate-500 mt-0.5">Crecimiento: {e.crecimiento_anual_pct > 0 ? '+' : ''}{e.crecimiento_anual_pct}% anual</p>
                  )}
                  {e.costo_educacion_cop > 0 && (
                    <div className="mt-2 pt-2 border-t border-white/[0.06]">
                      <p className="text-base text-slate-400">Inversión: {formatCOP(e.costo_educacion_cop)}</p>
                      {e.anos_recuperacion > 0 && (
                        <p className="text-xs text-amber-400 mt-0.5">Recuperas en {e.anos_recuperacion} años</p>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Alerta de saturación */}
          {result.alerta_saturacion && (
            <div className={`plate card p-4 border ${result.alerta_saturacion.riesgo === 'alto' ? 'border-rose-500/30 bg-rose-500/5' : 'border-amber-500/20 bg-amber-500/5'}`}>
              <div className="flex items-center gap-2">
                <span className="text-lg">{result.alerta_saturacion.riesgo === 'alto' ? '⚠️' : '📊'}</span>
                <div>
                  <p className="text-base text-slate-200 font-medium">{result.alerta_saturacion.mensaje}</p>
                  <p className="text-base text-slate-400 mt-1">{result.alerta_saturacion.detalle}</p>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ===========================================================================
// 1. Trayectoria Profesional
// ===========================================================================

function SimTrayectoria() {
  const { deptos, cargando: deptosCargando } = useDepartamentos()
  const [programas, setProgramas] = useState<string[]>([])
  const [programaQuery, setProgramaQuery] = useState('')
  const [programa, setPrograma] = useState('')
  const [departamento, setDepartamento] = useState('Bogotá D.C.')
  const [result, setResult] = useState<TrayectoriaResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const t = setTimeout(() => {
      if (programaQuery.length >= 2) {
        api.get('/simulacion/trayectoria/programas', { params: { q: programaQuery, limit: 30 } })
          .then((r) => setProgramas(r.data.programas))
          .catch(() => setProgramas([]))
      } else {
        setProgramas([])
      }
    }, 300)
    return () => clearTimeout(t)
  }, [programaQuery])

  const run = async () => {
    if (!programa) { setError('Selecciona un programa académico'); return }
    setLoading(true); setError(''); setResult(null)
    try {
      const r = await api.post('/simulacion/trayectoria', { programa, departamento })
      setResult(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Error al simular')
    } finally { setLoading(false) }
  }

  const chartData = useMemo(() => {
    if (!result) return []
    return result.anos.map((a, i) => ({
      año: a,
      mediana: result.mediana[i],
      p10: result.p10[i],
      p90: result.p90[i],
    }))
  }, [result])

  return (
    <div className="space-y-5">
      {/* Formulario */}
      <div className="plate card p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="relative">
            <label className="block text-base text-slate-400 mb-1.5">Programa académico</label>
            <input
              type="text"
              value={programaQuery}
              onChange={(e) => { setProgramaQuery(e.target.value); setPrograma('') }}
              placeholder="Escribe: ingeniería, derecho, enfermería..."
              className="w-full bg-[#0a0f1f] text-slate-200 text-base border border-amber-500/20 rounded-lg px-3 py-2.5 focus:outline-none focus:border-amber-500/50"
            />
            {programaQuery.length > 0 && programaQuery.length < 2 && !programa && (
              <p className="text-xs text-slate-500 mt-1">Escribe al menos 2 caracteres para buscar</p>
            )}
            {programaQuery.length >= 2 && programas.length === 0 && !programa && (
              <p className="text-xs text-slate-500 mt-1">Buscando programas...</p>
            )}
            {programaQuery.length >= 2 && programas.length > 0 && !programa && (
              <div className="mt-1 max-h-56 overflow-y-auto bg-[#0a0f1f] border border-amber-500/20 rounded-lg shadow-xl absolute z-50 left-0 right-0">
                <div className="px-3 py-1 text-xs text-slate-500 border-b border-white/[0.04]">{programas.length} programas encontrados</div>
                {programas.slice(0, 20).map((p) => (
                  <button
                    key={p}
                    onClick={() => { setPrograma(p); setProgramaQuery(p); setProgramas([]) }}
                    className="block w-full text-left px-3 py-2 text-base text-slate-300 hover:bg-amber-500/10 hover:text-gold-400 transition-colors"
                  >
                    {p}
                  </button>
                ))}
              </div>
            )}
            {programa && (
              <div className="mt-1 text-xs text-green-400">
                {programa}
              </div>
            )}
          </div>
          <div>
            <label className="block text-base text-slate-400 mb-1.5">
              Departamento {deptosCargando && <span className="text-slate-600">(cargando...)</span>}
            </label>
            <select
              value={departamento}
              onChange={(e) => setDepartamento(e.target.value)}
              className="w-full bg-[#0a0f1f] text-slate-200 text-base border border-amber-500/20 rounded-lg px-3 py-2.5 focus:outline-none focus:border-amber-500/50"
            >
              {deptos.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
        </div>
        <button
          onClick={run}
          disabled={loading || !programa}
          className="w-full md:w-auto px-6 py-2.5 bg-[#d4af37] text-[#0a0f1f] font-bold text-base rounded-lg hover:shadow-lg hover:shadow-[#d4af37]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? <>Simulando...</> : <>Simular trayectoria</>}
        </button>
      </div>

      {error && <div className="plate card rounded-xl p-4 text-rose-400 text-sm">{error}</div>}

      {result && (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KpiCard label="Salario inicial" value={formatCOP(result.salario_inicial_cop)} sub={result.salario_inicial_rango} />
            <KpiCard label="Salario año 5" value={formatCOP(result.salario_5a_cop)} sub={`${result.crecimiento_anual_pct}% anual`} accent="gold" />
            <KpiCard label="Salario año 10" value={formatCOP(result.salario_10a_cop)} sub="Proyección mediana" accent="green" />
            <KpiCard
              label="Nivel detectado"
              value={result.nivel_detectado}
              sub={`Crecimiento: ${result.crecimiento_anual_pct}% anual`}
            />
          </div>

          {/* Gráfico */}
          <div className="plate card p-5">
            <div className="mb-4 pb-3 border-b border-gold-500/20">
              <h3 className="text-lg font-bold text-gold-400 font-display mb-1">
                Tu salario estimado año a año
              </h3>
              <p className="text-base text-slate-400">
                {result.programa} · {result.departamento}
              </p>
            </div>

            <p className="text-base text-slate-400 mb-4">
              <strong className="text-gold-400">Línea dorada:</strong> lo que ganarías. Las grises son el rango posible (mínimo y máximo realista).
            </p>

            <ResponsiveContainer width="100%" height={360}>
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#141b2a" />
                <XAxis
                  dataKey="año"
                  stroke="#475569"
                  fontSize={13}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => (v === 0 ? 'Hoy' : v === 5 ? 'Año 5' : v === 10 ? 'Año 10' : '')}
                />
                <YAxis
                  stroke="#475569"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => `$${Math.round(v).toLocaleString("es-CO")}`}
                  width={80}
                />
                <Tooltip
                  {...tooltipStyle}
                  formatter={(v: number, name: string) => {
                    const labels: Record<string, string> = { mediana: 'Salario esperado', p10: 'Rango mínimo', p90: 'Rango máximo' }
                    return [formatCOPFull(v), labels[name] || name]
                  }}
                  labelFormatter={(l: number) => (l === 0 ? 'Hoy' : `Año ${l}`)}
                />
                <Line type="monotone" dataKey="p10" stroke="#334155" strokeWidth={1.5} strokeDasharray="4 4" dot={false} name="p10" />
                <Line type="monotone" dataKey="p90" stroke="#334155" strokeWidth={1.5} strokeDasharray="4 4" dot={false} name="p90" />
                <Line type="monotone" dataKey="mediana" stroke="#d4af37" strokeWidth={3} dot={false} activeDot={{ r: 5, strokeWidth: 0, fill: '#d4af37' }} name="mediana">
                  <LabelList
                    dataKey="mediana"
                    content={(props: any) => {
                      const { x, y, value, index } = props
                      const data = chartData[index ?? 0]
                      if (!data || ![0, 5, 10].includes(data.año)) return null
                      return (
                        <g>
                          <circle cx={x} cy={y} r={5} fill="#d4af37" />
                          <text x={x} y={y - 14} textAnchor="middle" fill="#d4af37" fontSize={13} fontWeight={700}>
                            $${Math.round(value as number).toLocaleString("es-CO")}
                          </text>
                        </g>
                      )
                    }}
                  />
                </Line>
              </LineChart>
            </ResponsiveContainer>
          </div>

          {result.recomendacion && (
            <div className="plate card p-5 border-amber-500/20">
              <p className="text-base text-slate-300">{result.recomendacion}</p>
              {result.profesion_chronos && result.profesion_chronos !== 'Baseline general' && (
                <p className="text-xs text-amber-400/80 mt-2">
                  Profesión equivalente (Chronos T5): {result.profesion_chronos}
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ===========================================================================
// 2. Migración Territorial
// ===========================================================================

function SimMigracion() {
  const { deptos, cargando: deptosCargando } = useDepartamentos()
  const [origen, setOrigen] = useState('Bogotá D.C.')
  const [destino, setDestino] = useState('Antioquia')
  const [result, setResult] = useState<MigracionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    if (origen === destino) { setError('Selecciona departamentos diferentes'); return }
    setLoading(true); setError(''); setResult(null)
    try {
      const r = await api.post('/simulacion/migracion', { departamento_origen: origen, departamento_destino: destino })
      setResult(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Error al simular')
    } finally { setLoading(false) }
  }

  return (
    <div className="space-y-5">
      <div className="plate card p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
          <div>
            <label className="block text-base text-slate-400 mb-1.5">Departamento origen</label>
            <select value={origen} onChange={(e) => setOrigen(e.target.value)} disabled={deptosCargando} className="w-full bg-[#0a0f1f] text-slate-200 text-base border border-amber-500/20 rounded-lg px-3 py-2.5 focus:outline-none focus:border-amber-500/50 disabled:opacity-50">
              {deptos.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-base text-slate-400 mb-1.5">Departamento destino</label>
            <select value={destino} onChange={(e) => setDestino(e.target.value)} disabled={deptosCargando} className="w-full bg-[#0a0f1f] text-slate-200 text-base border border-amber-500/20 rounded-lg px-3 py-2.5 focus:outline-none focus:border-amber-500/50 disabled:opacity-50">
              {deptos.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="w-full md:w-auto px-6 py-2.5 bg-[#d4af37] text-[#0a0f1f] font-bold text-base rounded-lg hover:shadow-lg hover:shadow-[#d4af37]/30 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? <>Comparando...</> : <>Comparar departamentos</>}
        </button>
      </div>

      {error && <div className="plate card rounded-xl p-4 text-rose-400 text-sm">{error}</div>}

      {result && (
        <>
          {/* Score */}
          <div className="plate card p-5 text-center">
            <p className="text-base text-slate-400 uppercase tracking-wider mb-2">Score de atractivo territorial</p>
            <div className="relative inline-block">
              <p className={`text-5xl font-bold font-display ${result.score_atractivo >= 65 ? 'text-green-400' : result.score_atractivo >= 45 ? 'text-amber-400' : 'text-rose-400'}`}>
                {result.score_atractivo.toFixed(0)}
              </p>
              <span className="text-xl text-slate-500">/100</span>
            </div>
            <p className="text-base text-slate-300 mt-3 max-w-xl mx-auto">{result.veredicto}</p>
          </div>

          {/* Comparación lado a lado */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <DeptoCard titulo="Origen" data={result.origen} color="slate" />
            <DeptoCard titulo="Destino" data={result.destino} color="gold" />
          </div>

          {/* Deltas */}
          <div className="plate card p-5">
            <h3 className="text-lg font-bold text-gold-400 font-display mb-4">Diferencia (destino - origen)</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <DeltaCard label="Salario promedio" value={`${result.delta.salario_pct > 0 ? '+' : ''}${result.delta.salario_pct}%`} cop={result.delta.salario_cop} positive={result.delta.salario_pct > 0} />
              <DeltaCard label="Formalidad" value={`${result.delta.formalidad_pct > 0 ? '+' : ''}${result.delta.formalidad_pct} pts`} positive={result.delta.formalidad_pct > 0} />
              <DeltaCard label="Educación superior" value={`${result.delta.educacion_pct > 0 ? '+' : ''}${result.delta.educacion_pct} pts`} positive={result.delta.educacion_pct > 0} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function DeptoCard({ titulo, data, color }: { titulo: string; data: Record<string, any>; color: string }) {
  const accent = color === 'gold' ? 'text-gold-400 border-amber-500/30' : 'text-slate-300 border-slate-600/30'
  return (
    <div className={`plate card p-5 border ${accent}`}>
      <div className="flex items-center gap-2 mb-4 pb-2 border-b border-white/[0.06]">
        <span className={`text-sm uppercase tracking-wider font-semibold ${color === 'gold' ? 'text-gold-400' : 'text-slate-400'}`}>{titulo}</span>
        <span className="ml-auto text-white font-display font-bold">{data.departamento}</span>
      </div>
      <div className="space-y-2">
        <Row label="Ingreso promedio" value={formatCOP(data.ingreso_promedio)} />
        <Row label="Ingreso mediano" value={formatCOP(data.ingreso_mediano)} />
        <Row label="Formalidad" value={`${data.tasa_formalidad_pct}%`} />
        <Row label="Educación superior" value={`${data.pct_educacion_superior}%`} />
        <Row label="Ocupados" value={formatNumber(data.ocupados)} />
        <Row label="Nivel educativo" value={data.nivel_educativo} />
      </div>
    </div>
  )
}

function DeltaCard({ label, value, cop, positive }: { label: string; value: string; cop?: number; positive: boolean }) {
  return (
    <div className="plate card p-4 text-center">
      <p className="text-base text-slate-400 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-bold font-display ${positive ? 'text-green-400' : 'text-rose-400'}`}>{value}</p>
      {cop != null && <p className={`text-xs mt-1 ${positive ? 'text-green-400/70' : 'text-rose-400/70'}`}>{cop > 0 ? '+' : ''}{formatCOP(cop)}</p>}
    </div>
  )
}

// ===========================================================================
// 3. Reskilling / Transición
// ===========================================================================

function SimReskilling() {
  const [ocupaciones, setOcupaciones] = useState<string[]>([])
  const [actualQuery, setActualQuery] = useState('')
  const [deseadaQuery, setDeseadaQuery] = useState('')
  const [actual, setActual] = useState('')
  const [deseada, setDeseada] = useState('')
  const [result, setResult] = useState<ReskillingResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const buscarOcupaciones = (q: string, setter: (v: string[]) => void) => {
    if (q.length < 2) { setter([]); return }
    api.get('/simulacion/reskilling/ocupaciones', { params: { q, limit: 20 } })
      .then((r) => setter(r.data.ocupaciones))
      .catch(() => setter([]))
  }

  const run = async () => {
    if (!actual || !deseada) { setError('Selecciona ambas ocupaciones'); return }
    if (actual === deseada) { setError('Selecciona ocupaciones diferentes'); return }
    setLoading(true); setError(''); setResult(null)
    try {
      const r = await api.post('/simulacion/reskilling', { ocupacion_actual: actual, ocupacion_deseada: deseada })
      setResult(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Error al simular')
    } finally { setLoading(false) }
  }

  const overlapData = [
    { name: 'Coinciden', value: result?.habilidades_coinciden.length || 0, color: '#4ade80' },
    { name: 'Faltan', value: result?.habilidades_faltan.length || 0, color: '#ff6b6b' },
  ]

  return (
    <div className="space-y-5">
      <div className="plate card p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <OcupacionInput
            label="Ocupación actual"
            query={actualQuery}
            setQuery={(v) => { setActualQuery(v); setActual(''); buscarOcupaciones(v, setOcupaciones) }}
            seleccionado={actual}
            opciones={ocupaciones}
            onSelect={(o) => { setActual(o); setActualQuery(o); setOcupaciones([]) }}
          />
          <OcupacionInput
            label="Ocupación deseada"
            query={deseadaQuery}
            setQuery={(v) => { setDeseadaQuery(v); setDeseada(''); buscarOcupaciones(v, setOcupaciones) }}
            seleccionado={deseada}
            opciones={ocupaciones}
            onSelect={(o) => { setDeseada(o); setDeseadaQuery(o); setOcupaciones([]) }}
          />
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="w-full md:w-auto px-6 py-2.5 bg-[#d4af37] text-[#0a0f1f] font-bold text-base rounded-lg hover:shadow-lg hover:shadow-[#d4af37]/30 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? <>Analizando...</> : <>Calcular brecha de habilidades</>}
        </button>
      </div>

      {error && <div className="plate card rounded-xl p-4 text-rose-400 text-sm">{error}</div>}

      {result && (
        <>
          {/* Overlap */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="plate card p-5 text-center">
              <p className="text-base text-slate-400 uppercase tracking-wider mb-2">Overlap de habilidades</p>
              <p className={`text-5xl font-bold font-display ${result.overlap_pct >= 70 ? 'text-green-400' : result.overlap_pct >= 40 ? 'text-amber-400' : 'text-rose-400'}`}>
                {result.overlap_pct.toFixed(0)}%
              </p>
              <div className="flex justify-center gap-4 mt-3 text-xs">
                <span className="text-green-400">{result.habilidades_coinciden.length} coinciden</span>
                <span className="text-rose-400">{result.habilidades_faltan.length} faltan</span>
              </div>
            </div>
            <div className="plate card p-5 md:col-span-2 flex items-center">
              <div className="flex-1">
                <p className="text-base text-slate-400 uppercase tracking-wider mb-1">Veredicto</p>
                <p className="text-base text-slate-300">{result.veredicto}</p>
              </div>
            </div>
          </div>

          {/* Habilidades que faltan */}
          {result.habilidades_faltan.length > 0 && (
            <div className="plate card p-5">
              <h3 className="text-lg font-bold text-gold-400 font-display mb-4">
                Habilidades que necesitas desarrollar ({result.habilidades_faltan.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.habilidades_faltan.map((h) => (
                  <span key={h} className="px-3 py-1.5 text-xs bg-rose-500/10 text-rose-300 border border-rose-500/20 rounded-lg">{h}</span>
                ))}
              </div>
            </div>
          )}

          {/* Habilidades críticas WEF */}
          {result.faltan_criticas_wef.length > 0 && (
            <div className="plate card p-5 border-amber-500/20">
              <h3 className="text-lg font-bold text-gold-400 font-display mb-4">
                Habilidades críticas para el futuro (WEF)
              </h3>
              <ResponsiveContainer width="100%" height={Math.max(120, result.faltan_criticas_wef.length * 40)}>
                <BarChart data={result.faltan_criticas_wef.map((h) => ({ habilidad: h.habilidad, demanda: h.demanda_wef }))} layout="vertical" margin={{ left: 10, right: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e2329" horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} stroke="#475569" fontSize={11} />
                  <YAxis type="category" dataKey="habilidad" stroke="#c8d0de" fontSize={11} width={200} tickLine={false} axisLine={false} />
                  <Tooltip {...tooltipStyle} formatter={(v: number) => [`${v}/100`, 'Demanda WEF']} cursor={{ fill: '#1e232980' }} />
                  <Bar dataKey="demanda" radius={[0, 6, 6, 0]} fill="#d4af37">
                    <LabelList dataKey="demanda" position="right" fill="#d4af37" fontSize={12} fontWeight={700} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Programas SENA */}
          {result.programas_sena_recomendados.length > 0 && (
            <div className="plate card p-5">
              <h3 className="text-lg font-bold text-gold-400 font-display mb-4">
                Programas SENA recomendados
              </h3>
              <div className="space-y-2">
                {result.programas_sena_recomendados.map((p, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 bg-white/[0.02] rounded-lg">
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-slate-200">{p.programa_sena}</p>
                      <p className="text-xs text-slate-500">{p.departamento} · {p.duracion_horas > 0 ? `${p.duracion_horas}h` : 'N/D'} · {p.costo > 0 ? formatCOP(p.costo) : 'Gratuito'}</p>
                    </div>
                    <span className="text-xs text-amber-400 bg-amber-500/10 px-2 py-1 rounded-full border border-amber-500/20">{p.habilidad_faltante}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function OcupacionInput({ label, query, setQuery, seleccionado, opciones, onSelect }: {
  label: string; query: string; setQuery: (v: string) => void; seleccionado: string; opciones: string[]; onSelect: (v: string) => void
}) {
  return (
    <div className="relative">
      <label className="block text-base text-slate-400 mb-1.5">{label}</label>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Escribe: developer, nurse, accountant..."
        className="w-full bg-[#0a0f1f] text-slate-200 text-base border border-amber-500/20 rounded-lg px-3 py-2.5 focus:outline-none focus:border-amber-500/50"
      />
      {query.length > 0 && query.length < 2 && !seleccionado && (
        <p className="text-xs text-slate-500 mt-1">Escribe al menos 2 caracteres</p>
      )}
      {query.length >= 2 && opciones.length === 0 && !seleccionado && (
        <p className="text-xs text-slate-500 mt-1">Buscando ocupaciones...</p>
      )}
      {opciones.length > 0 && !seleccionado && (
        <div className="mt-1 max-h-48 overflow-y-auto bg-[#0a0f1f] border border-amber-500/20 rounded-lg shadow-xl absolute z-50 left-0 right-0">
          <div className="px-3 py-1 text-xs text-slate-500 border-b border-white/[0.04]">{opciones.length} ocupaciones encontradas</div>
          {opciones.slice(0, 15).map((o) => (
            <button key={o} onClick={() => onSelect(o)} className="block w-full text-left px-3 py-2 text-base text-slate-300 hover:bg-amber-500/10 hover:text-gold-400 transition-colors">
              {o}
            </button>
          ))}
        </div>
      )}
      {seleccionado && <div className="mt-1 text-xs text-green-400">{seleccionado}</div>}
    </div>
  )
}

// ===========================================================================
// 4. Demanda Sectorial
// ===========================================================================

function SimDemanda() {
  const [sectores, setSectores] = useState<{ codigo: string; nombre: string }[]>([])
  const [sector, setSector] = useState('47')
  const [pib, setPib] = useState(3.0)
  const [inflacion, setInflacion] = useState(5.0)
  const [inversion, setInversion] = useState(0)
  const [result, setResult] = useState<DemandaResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/simulacion/demanda-sectorial/sectores').then((r) => {
      setSectores(r.data.sectores)
      if (r.data.sectores.length > 0) setSector(r.data.sectores[0].codigo)
    }).catch(() => {})
  }, [])

  const run = async () => {
    setLoading(true); setError(''); setResult(null)
    try {
      const r = await api.post('/simulacion/demanda-sectorial', {
        sector_ciiu: sector, crecimiento_pib_pct: pib, inflacion_pct: inflacion, inversion_pct: inversion,
      })
      setResult(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Error al simular')
    } finally { setLoading(false) }
  }

  const chartData = useMemo(() => {
    if (!result) return []
    return result.meses.map((m, i) => ({
      mes: `M${m}`,
      base: result.proyeccion_base[i],
      escenario: result.proyeccion_escenario[i],
    }))
  }, [result])

  return (
    <div className="space-y-5">
      <div className="plate card p-5 space-y-5">
        <div>
          <label className="block text-base text-slate-400 mb-1.5">Sector</label>
          <select value={sector} onChange={(e) => setSector(e.target.value)} className="w-full bg-[#0a0f1f] text-slate-200 text-base border border-amber-500/20 rounded-lg px-3 py-2.5 focus:outline-none focus:border-amber-500/50">
            {sectores.map((s) => <option key={s.codigo} value={s.codigo}>{s.nombre}</option>)}
          </select>
        </div>

        <Slider label="Crecimiento del PIB" value={pib} min={-5} max={10} step={0.5} suffix="%" onChange={setPib} color="#4ade80" />
        <Slider label="Inflación" value={inflacion} min={0} max={15} step={0.5} suffix="%" onChange={setInflacion} color="#f97316" />
        <Slider label="Shock de inversión" value={inversion} min={-20} max={20} step={1} suffix="%" onChange={setInversion} color="#d4af37" />

        <button
          onClick={run}
          disabled={loading}
          className="w-full md:w-auto px-6 py-2.5 bg-[#d4af37] text-[#0a0f1f] font-bold text-base rounded-lg hover:shadow-lg hover:shadow-[#d4af37]/30 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? <>Simulando...</> : <>Simular escenario</>}
        </button>
      </div>

      {error && <div className="plate card rounded-xl p-4 text-rose-400 text-sm">{error}</div>}

      {result && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KpiCard label="Empleo actual" value={formatNumber(result.empleo_actual)} sub={result.sector_nombre} />
            <KpiCard label="Empleo proyectado (12m)" value={formatNumber(result.empleo_proyectado_12m)} sub="Con escenario" accent={result.delta_empleo_pct >= 0 ? 'green' : 'rose'} />
            <KpiCard label="Delta empleo" value={`${result.delta_empleo_pct > 0 ? '+' : ''}${result.delta_empleo_pct}%`} accent={result.delta_empleo_pct >= 0 ? 'green' : 'rose'} />
            <KpiCard label="Delta salario" value={`${result.delta_salario_pct > 0 ? '+' : ''}${result.delta_salario_pct}%`} accent={result.delta_salario_pct >= 0 ? 'green' : 'rose'} />
          </div>

          <div className="plate card p-5">
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
              <h3 className="text-lg font-bold text-gold-400 font-display">
                Empleo proyectado a 12 meses
              </h3>
              <span className="text-sm text-gold-400 uppercase tracking-wider font-semibold">{result.sector_nombre}</span>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2329" />
                <XAxis dataKey="mes" stroke="#475569" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#475569" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => Math.round(v).toLocaleString("es-CO")} width={80} />
                <Tooltip {...tooltipStyle} formatter={(v: number, name: string) => {
                  const labels: Record<string, string> = { base: 'Predicción base', escenario: 'Con escenario' }
                  return [formatNumber(Math.round(v)), labels[name] || name]
                }} />
                <Legend wrapperStyle={{ fontSize: '12px', color: '#c8d0de' }} />
                <Line type="monotone" dataKey="base" stroke="#475569" strokeWidth={2} strokeDasharray="5 5" dot={false} name="base" />
                <Line type="monotone" dataKey="escenario" stroke="#d4af37" strokeWidth={2.5} dot={false} name="escenario" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="plate card p-5 border-amber-500/20">
            <p className="text-base text-slate-300">{result.veredicto}</p>
          </div>
        </>
      )}
    </div>
  )
}

function Slider({ label, value, min, max, step, suffix, onChange, color }: {
  label: string; value: number; min: number; max: number; step: number; suffix: string; onChange: (v: number) => void; color: string
}) {
  return (
    <div>
      <div className="flex justify-between items-baseline mb-2">
        <label className="text-base text-slate-400">{label}</label>
        <span className="text-lg font-bold font-display" style={{ color }}>{value > 0 ? '+' : ''}{value}{suffix}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-amber-500"
        style={{ accentColor: color }}
      />
      <div className="flex justify-between text-xs text-slate-600 mt-1">
        <span>{min}{suffix}</span>
        <span>{max}{suffix}</span>
      </div>
    </div>
  )
}

// ===========================================================================
// 5. Estudiar vs Trabajar vs Emprender
// ===========================================================================

function SimDecision() {
  const { deptos, cargando: deptosCargando } = useDepartamentos()
  const [edad, setEdad] = useState(20)
  const [nivel, setNivel] = useState('Bachiller')
  const [departamento, setDepartamento] = useState('Bogotá D.C.')
  const [sector, setSector] = useState('Servicios')
  const [capital, setCapital] = useState(0)
  const [result, setResult] = useState<DecisionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    setLoading(true); setError(''); setResult(null)
    try {
      const r = await api.post('/simulacion/decision', {
        edad, nivel_educativo_actual: nivel, departamento, sector_interes: sector, capital_disponible_cop: capital,
      })
      setResult(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Error al simular')
    } finally { setLoading(false) }
  }

  const chartData = useMemo(() => {
    if (!result) return []
    return result.anos.map((a, i) => ({
      año: a,
      Estudiar: result.estudiar.trayectoria[i],
      Trabajar: result.trabajar.trayectoria[i],
      Emprender: result.emprender.mediana[i],
      EmprenderP10: result.emprender.p10[i],
      EmprenderP90: result.emprender.p90[i],
    }))
  }, [result])

  const opcionesOrden = [
    { key: 'estudiar', label: 'Estudiar', color: '#2563eb' },
    { key: 'trabajar', label: 'Trabajar', color: '#4ade80' },
    { key: 'emprender', label: 'Emprender', color: '#d4af37' },
  ]

  return (
    <div className="space-y-5">
      <div className="plate card p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-base text-slate-400 mb-1.5">Edad</label>
            <input type="number" value={edad} onChange={(e) => setEdad(parseInt(e.target.value) || 18)} min={16} max={60}
              className="w-full bg-[#0a0f1f] text-slate-200 text-base border border-amber-500/20 rounded-lg px-3 py-2.5 focus:outline-none focus:border-amber-500/50" />
          </div>
          <div>
            <label className="block text-base text-slate-400 mb-1.5">Nivel educativo actual</label>
            <select value={nivel} onChange={(e) => setNivel(e.target.value)} className="w-full bg-[#0a0f1f] text-slate-200 text-base border border-amber-500/20 rounded-lg px-3 py-2.5 focus:outline-none focus:border-amber-500/50">
              {['Bachiller', 'Tecnico', 'Tecnologo', 'Universitario'].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-base text-slate-400 mb-1.5">Departamento</label>
            <select value={departamento} onChange={(e) => setDepartamento(e.target.value)} disabled={deptosCargando} className="w-full bg-[#0a0f1f] text-slate-200 text-base border border-amber-500/20 rounded-lg px-3 py-2.5 focus:outline-none focus:border-amber-500/50 disabled:opacity-50">
              {deptos.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-base text-slate-400 mb-1.5">Sector de interés</label>
            <select value={sector} onChange={(e) => setSector(e.target.value)} className="w-full bg-[#0a0f1f] text-slate-200 text-base border border-amber-500/20 rounded-lg px-3 py-2.5 focus:outline-none focus:border-amber-500/50">
              {SECTORES_INTERES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="block text-base text-slate-400 mb-1.5">Capital disponible para emprender (COP)</label>
          <input type="number" value={capital} onChange={(e) => setCapital(parseInt(e.target.value) || 0)} min={0} step={500000}
            placeholder="0"
            className="w-full md:w-1/2 bg-[#0a0f1f] text-slate-200 text-base border border-amber-500/20 rounded-lg px-3 py-2.5 focus:outline-none focus:border-amber-500/50" />
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="w-full md:w-auto px-6 py-2.5 bg-[#d4af37] text-[#0a0f1f] font-bold text-base rounded-lg hover:shadow-lg hover:shadow-[#d4af37]/30 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? <>Simulando...</> : <>Comparar trayectorias</>}
        </button>
      </div>

      {error && <div className="plate card rounded-xl p-4 text-rose-400 text-sm">{error}</div>}

      {result && (
        <>
          {/* Mejor opción */}
          <div className="plate card p-5 text-center border-amber-500/30">
            <p className="text-base text-slate-400 uppercase tracking-wider mb-2">Mejor opción según ingreso acumulado a 10 años</p>
            <div className="flex items-center justify-center gap-3">
              <p className="text-3xl font-bold font-display" style={{ color: opcionesOrden.find((o) => o.key === result.mejor_opcion)?.color }}>
                {opcionesOrden.find((o) => o.key === result.mejor_opcion)?.label}
              </p>
            </div>
            <p className="text-base text-slate-300 mt-3 max-w-xl mx-auto">{result.veredicto}</p>
          </div>

          {/* Comparación de ingreso acumulado */}
          <div className="grid grid-cols-3 gap-3">
            {opcionesOrden.map((o) => {
              const val = result[o.key as 'estudiar' | 'trabajar' | 'emprender'].ingreso_acumulado_10a
              const isMejor = result.mejor_opcion === o.key
              return (
                <div key={o.key} className={`plate card p-4 text-center ${isMejor ? 'border-2' : ''}`} style={isMejor ? { borderColor: o.color + '60' } : {}}>
                  <p className="text-base text-slate-400 uppercase tracking-wider">{o.label}</p>
                  <p className="text-xl font-bold font-display mt-1" style={{ color: o.color }}>{formatCOP(val)}</p>
                  <p className="text-xs text-slate-500 mt-1">Ingreso acumulado 10 años</p>
                </div>
              )
            })}
          </div>

          {/* Gráfico comparativo */}
          <div className="plate card p-5">
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
              <h3 className="text-lg font-bold text-gold-400 font-display">
                Ingreso mensual proyectado a 10 años
              </h3>
              <span className="text-sm text-gold-400 uppercase tracking-wider font-semibold">Monte Carlo · 500 sim.</span>
            </div>
            <ResponsiveContainer width="100%" height={350}>
              <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
                <defs>
                  <linearGradient id="empBand" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#d4af37" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="#d4af37" stopOpacity={0.03} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2329" />
                <XAxis dataKey="año" stroke="#475569" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `Año ${v}`} />
                <YAxis stroke="#475569" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v / 1_000_000).toFixed(1)}M`} width={60} />
                <Tooltip {...tooltipStyle} formatter={(v: number, name: string) => {
                  const labels: Record<string, string> = { Estudiar: 'Estudiar', Trabajar: 'Trabajar', Emprender: 'Emprender (mediana)', EmprenderP10: 'Emprender (pesimista)', EmprenderP90: 'Emprender (optimista)' }
                  return [formatCOPFull(v), labels[name] || name]
                }} />
                <Legend wrapperStyle={{ fontSize: '12px', color: '#c8d0de' }} />
                {/* Banda emprendimiento */}
                <Area type="monotone" dataKey="EmprenderP90" stroke="none" fill="url(#empBand)" name="EmprenderP90" />
                <Area type="monotone" dataKey="EmprenderP10" stroke="none" fill="#0a1226" name="EmprenderP10" />
                <Line type="monotone" dataKey="Estudiar" stroke="#2563eb" strokeWidth={2.5} dot={false} name="Estudiar" />
                <Line type="monotone" dataKey="Trabajar" stroke="#4ade80" strokeWidth={2.5} dot={false} name="Trabajar" />
                <Line type="monotone" dataKey="Emprender" stroke="#d4af37" strokeWidth={2.5} dot={false} name="Emprender" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Detalles por opción */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {opcionesOrden.map((o) => {
              const data = result[o.key as 'estudiar' | 'trabajar' | 'emprender'] as any
              return (
                <div key={o.key} className="plate card p-4">
                  <div className="flex items-center gap-2 mb-2" style={{ color: o.color }}>
                    <span className="font-bold text-sm" style={{ color: o.color }}>{o.label}</span>
                  </div>
                  <p className="text-base text-slate-400">{data.descripcion}</p>
                  {o.key === 'estudiar' && <p className="text-xs text-slate-500 mt-2">Años de inversión: {data.anos_inversion}</p>}
                  {o.key === 'trabajar' && <p className="text-xs text-slate-500 mt-2">Crecimiento: {data.crecimiento_anual_pct}% anual</p>}
                  {o.key === 'emprender' && <p className="text-xs text-slate-500 mt-2">Prob. de éxito: {data.prob_exito_pct}%</p>}
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

// ===========================================================================
// SIMULADOR VIABILIDAD DE PROGRAMA (Universidades)
// ===========================================================================

function SimViabilidad() {
  const { deptos } = useDepartamentos()
  const [programaQuery, setProgramaQuery] = useState('')
  const [programa, setPrograma] = useState('')
  const [programas, setProgramas] = useState<string[]>([])
  const [departamento, setDepartamento] = useState('Bogotá D.C.')
  const [nivel, setNivel] = useState('Profesional')
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const t = setTimeout(() => {
      if (programaQuery.length >= 2) {
        api.get('/simulacion/trayectoria/programas', { params: { q: programaQuery, limit: 20 } })
          .then((r) => setProgramas(r.data.programas))
          .catch(() => setProgramas([]))
      } else setProgramas([])
    }, 300)
    return () => clearTimeout(t)
  }, [programaQuery])

  const run = async () => {
    if (!programa.trim()) { setError('Selecciona un programa académico'); return }
    setLoading(true); setError(''); setResult(null)
    try {
      const r = await api.post('/simulacion/viabilidad-programa', { programa: programa.trim(), departamento, nivel })
      setResult(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Error al evaluar viabilidad')
    } finally { setLoading(false) }
  }

  const scoreColor = (s: number) => s >= 70 ? 'text-green-400' : s >= 45 ? 'text-amber-400' : 'text-rose-400'
  const scoreBg = (s: number) => s >= 70 ? 'bg-green-500/20 border-green-500/40' : s >= 45 ? 'bg-amber-500/20 border-amber-500/40' : 'bg-rose-500/20 border-rose-500/40'

  return (
    <div className="space-y-4">
      <div className="plate card p-5">
        <h3 className="text-base font-semibold text-gold-400 uppercase tracking-wider mb-4">Evaluar viabilidad de un programa académico</h3>
        <p className="text-base text-slate-400 mb-4">Cruza oferta educativa (SNIES) con demanda laboral (SPE/APE) e ingresos de graduados (OLE) para calcular un score de viabilidad 0-100.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative">
            <label className="text-base text-slate-400 mb-1 block">Programa académico</label>
            <input type="text" value={programaQuery} onChange={(e) => { setProgramaQuery(e.target.value); setPrograma('') }} placeholder="Busca tu programa..." className="bg-white/[0.03] border border-white/0.08 rounded-lg px-3 py-2 text-base text-slate-300 focus:border-amber-500/40 outline-none w-full" />
            {programas.length > 0 && !programa && (
              <div className="plate card mt-1 max-h-48 overflow-y-auto border-amber-500/20 absolute z-50 w-full">
                {programas.map((p) => (
                  <button key={p} onClick={() => { setPrograma(p); setProgramaQuery(p); setProgramas([]) }} className="block w-full text-left px-3 py-2 text-base text-slate-300 hover:bg-amber-500/10 hover:text-gold-400 transition-colors">
                    {p}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div>
            <label className="text-base text-slate-400 mb-1 block">Departamento</label>
            <select value={departamento} onChange={(e) => setDepartamento(e.target.value)} className="bg-white/[0.03] border border-white/0.08 rounded-lg px-2 py-1.5 text-base text-slate-300 focus:border-amber-500/40 outline-none w-full">
              {deptos.map((d) => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="text-base text-slate-400 mb-1 block">Nivel</label>
            <select value={nivel} onChange={(e) => setNivel(e.target.value)} className="bg-white/[0.03] border border-white/0.08 rounded-lg px-2 py-1.5 text-base text-slate-300 focus:border-amber-500/40 outline-none w-full">
              <option>Técnico</option>
              <option>Profesional</option>
              <option>Especialización</option>
              <option>Maestría</option>
            </select>
          </div>
        </div>
        <button onClick={run} disabled={loading} className="mt-4 px-6 py-2.5 rounded-lg font-semibold text-base transition-all bg-gold-400 text-[#0a0f1f] hover:bg-gold-400/90 disabled:opacity-40">
          {loading ? 'Evaluando...' : 'Evaluar viabilidad'}
        </button>
        {error && <p className="text-rose-400 text-sm mt-3">{error}</p>}
      </div>

      {result && (
        <>
          <div className={`plate card p-6 border ${scoreBg(result.score_viabilidad)}`}>
            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className={`text-4xl font-bold font-display ${scoreColor(result.score_viabilidad)}`}>{result.score_viabilidad}</div>
                <div className="text-base text-slate-400 mt-1">/ 100</div>
              </div>
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
                    result.nivel_riesgo === 'bajo' ? 'bg-green-500/20 text-green-400' :
                    result.nivel_riesgo === 'medio' ? 'bg-amber-500/20 text-amber-400' :
                    'bg-rose-500/20 text-rose-400'
                  }`}>{result.nivel_riesgo === 'bajo' ? '✔ Viable' : result.nivel_riesgo === 'medio' ? '⚠ Moderado' : '✘ Riesgo'}</span>
                </div>
                <p className="text-base text-slate-200 leading-relaxed">{result.recomendacion}</p>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <KpiCard label="Salario estimado" value={formatCOP(result.indicadores.salario_estimado_cop)} sub="/mes" accent="gold" />
            <KpiCard label="Salario mercado" value={formatCOP(result.indicadores.salario_mercado_cop)} sub="/mes" />
            <KpiCard label="Demanda laboral" value={`${result.indicadores.demanda_score}%`} sub="score SPE/APE" accent="green" />
            <KpiCard label="Saturación oferta" value={`${result.indicadores.saturacion_oferta_pct}%`} sub="matriculados vs vacantes" accent={result.indicadores.saturacion_oferta_pct > 60 ? 'rose' : 'green'} />
            <KpiCard label="Crecimiento proyectado" value={`${result.indicadores.crecimiento_proyectado_anual_pct > 0 ? '+' : ''}${result.indicadores.crecimiento_proyectado_anual_pct}%`} sub="anual (Chronos T5)" accent="gold" />
            <KpiCard label="Competencia" value={result.indicadores.matriculados_competencia.toLocaleString()} sub="matriculados en el depto" />
          </div>
          {result.indicadores.sectores_demandantes?.length > 0 && (
            <div className="plate card p-5">
              <h3 className="text-base font-semibold text-gold-400 uppercase tracking-wider mb-3">Sectores demandantes</h3>
              <div className="flex flex-wrap gap-2">
                {result.indicadores.sectores_demandantes.map((s: any) => (
                  <span key={s.sector} className="px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-slate-300">
                    {s.sector} <span className="text-amber-400 font-semibold ml-1">{s.empresas.toLocaleString()}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
          <div className="text-xs text-slate-500 text-right">Fuentes: {result.fuentes?.join(', ') || 'SNIES, OLE, SPE, GEIH'}</div>
        </>
      )}
    </div>
  )
}

// ===========================================================================
// SIMULADOR PRIORIZACIÓN TERRITORIAL (Gobiernos)
// ===========================================================================

function SimPriorizacion() {
  const [presupuesto, setPresupuesto] = useState(1000)
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    setLoading(true); setError(''); setResult(null)
    try {
      const r = await api.post('/simulacion/priorizacion-territorial', { presupuesto_cop: presupuesto * 1_000_000 })
      setResult(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Error al calcular priorización')
    } finally { setLoading(false) }
  }

  return (
    <div className="space-y-4">
      <div className="plate card p-5">
        <h3 className="text-base font-semibold text-gold-400 uppercase tracking-wider mb-4">Priorización territorial de inversión</h3>
        <p className="text-base text-slate-400 mb-4">Ranking de departamentos por urgencia de intervención laboral. Score compuesto: desempleo, informalidad, desempeño DNP, ingreso y proyecciones.</p>
        <div className="flex items-end gap-4">
          <div>
            <label className="text-base text-slate-400 mb-1 block">Presupuesto disponible (millones COP)</label>
            <input type="number" value={presupuesto} onChange={(e) => setPresupuesto(Number(e.target.value))} min={100} max={100000} step={100} className="bg-white/[0.03] border border-white/0.08 rounded-lg px-3 py-2 text-base text-slate-300 focus:border-amber-500/40 outline-none w-40" />
          </div>
          <button onClick={run} disabled={loading} className="px-6 py-2.5 rounded-lg font-semibold text-base transition-all bg-gold-400 text-[#0a0f1f] hover:bg-gold-400/90 disabled:opacity-40">
            {loading ? 'Calculando...' : 'Calcular priorización'}
          </button>
        </div>
        {error && <p className="text-rose-400 text-sm mt-3">{error}</p>}
      </div>

      {result && (
        <>
          {result.recomendaciones_inversion?.length > 0 && (
            <div className="plate card p-5 border-amber-500/20">
              <h3 className="text-base font-semibold text-gold-400 uppercase tracking-wider mb-3">Top 3 — Recomendaciones de inversión</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {result.recomendaciones_inversion.map((rec: any, i: number) => (
                  <div key={i} className="plate card p-4 border-amber-500/30 bg-amber-500/5">
                    <div className="text-xs text-amber-400 font-bold uppercase mb-1">#{i + 1} — {rec.departamento}</div>
                    <div className="text-lg font-bold text-gold-400 font-display mb-2">{formatCOP(rec.inversion_sugerida_cop)}</div>
                    <p className="text-xs text-slate-300 leading-relaxed">{rec.accion}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="plate card p-5">
            <h3 className="text-base font-semibold text-gold-400 uppercase tracking-wider mb-3">Ranking completo — {result.total_departamentos} departamentos</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/[0.08] text-left">
                    <th className="py-2 px-3 text-base text-slate-400 font-medium">#</th>
                    <th className="py-2 px-3 text-base text-slate-400 font-medium">Departamento</th>
                    <th className="py-2 px-3 text-base text-slate-400 font-medium text-right">Score</th>
                    <th className="py-2 px-3 text-base text-slate-400 font-medium">Urgencia</th>
                    <th className="py-2 px-3 text-base text-slate-400 font-medium text-right">Desempleo</th>
                    <th className="py-2 px-3 text-base text-slate-400 font-medium text-right">Informalidad</th>
                    <th className="py-2 px-3 text-base text-slate-400 font-medium text-right">DNP</th>
                  </tr>
                </thead>
                <tbody>
                  {result.ranking?.slice(0, 15).map((d: any, i: number) => (
                    <tr key={i} className={`border-b border-white/[0.04] hover:bg-white/[0.02] ${i < 3 ? 'bg-amber-500/5' : ''}`}>
                      <td className="py-2.5 px-3 text-slate-400">{i + 1}</td>
                      <td className="py-2.5 px-3 text-slate-200 font-medium">{d.nombre}</td>
                      <td className="py-2.5 px-3 text-right font-bold text-gold-400">{d.score_prioridad}</td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          d.nivel_urgencia === 'Crítico' ? 'bg-rose-500/20 text-rose-400' :
                          d.nivel_urgencia === 'Alta' ? 'bg-amber-500/20 text-amber-400' :
                          d.nivel_urgencia === 'Media' ? 'bg-blue-500/20 text-blue-400' :
                          'bg-green-500/20 text-green-400'
                        }`}>{d.nivel_urgencia}</span>
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-300">{d.tasa_desempleo?.toFixed(1)}%</td>
                      <td className="py-2.5 px-3 text-right text-slate-300">{d.tasa_informalidad?.toFixed(0)}%</td>
                      <td className="py-2.5 px-3 text-right text-slate-300">{d.dnp_desempeno?.toFixed(0) || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="text-xs text-slate-500">{result.metodologia}</div>
          <div className="text-xs text-slate-500 text-right">Fuentes: {result.fuentes?.join(', ') || 'GEIH, DNP, SNIES'}</div>
        </>
      )}
    </div>
  )
}

// ===========================================================================
// Componentes UI compartidos
// ===========================================================================

function KpiCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: 'gold' | 'green' | 'rose' }) {
  const color = accent === 'gold' ? 'text-gold-400' : accent === 'green' ? 'text-green-400' : accent === 'rose' ? 'text-rose-400' : 'text-white'
  return (
    <div className="plate card p-4 text-center">
      <p className="text-base text-slate-400 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-xl font-bold font-display ${color}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-baseline">
      <span className="text-base text-slate-400">{label}</span>
      <span className="text-sm font-semibold text-slate-200">{value}</span>
    </div>
  )
}