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

  const [result, setResult] = useState<QuePasaSiResponse | null>(null)
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
    if (!programa) { setError('Selecciona un programa académico'); return }
    setLoading(true); setError(''); setResult(null)
    try {
      const r = await api.post('/simulacion/que-pasa-si', { programa, departamento, edad: 22, escenarios: [{ tipo: 'base' }] })
      setResult(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Error al proyectar')
    } finally { setLoading(false) }
  }

  const chartData = useMemo(() => {
    if (!result || result.escenarios.length === 0) return []
    const base = result.escenarios[0]
    return base.anos.map((a, i) => ({
      año: a,
      mediana: base.mediana[i] || 0,
      p10: base.p10[i] || 0,
      p90: base.p90[i] || 0,
    }))
  }, [result])

  const selectStyles = "bg-white/[0.03] border border-white/0.08 rounded-lg px-2 py-1.5 text-base text-slate-300 focus:border-amber-500/40 outline-none"

  return (
    <div className="space-y-4">
      <div className="plate card p-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="relative">
            <label className="text-lg text-slate-300 mb-1 block font-medium">Quiero estudiar</label>
            <input type="text" value={programaQuery} onChange={(e) => { setProgramaQuery(e.target.value); setPrograma('') }} placeholder="Busca tu carrera..." className={`${selectStyles} w-full`} />
            {programas.length > 0 && !programa && (
              <div className="bg-[#0a0f1f] border border-amber-500/40 rounded-lg mt-1 max-h-48 overflow-y-auto absolute z-50 w-full shadow-2xl">
                {programas.map((p) => (
                  <button key={p} onClick={() => { setPrograma(p); setProgramaQuery(p); setProgramas([]) }} className="block w-full text-left px-3 py-2 text-base text-slate-300 hover:bg-amber-500/10 hover:text-gold-400 transition-colors">{p}</button>
                ))}
              </div>
            )}
          </div>
          <div>
            <label className="text-lg text-slate-300 mb-1 block font-medium">y quiero trabajar en</label>
            <select value={departamento} onChange={(e) => setDepartamento(e.target.value)} className={`${selectStyles} w-full`}>
              {deptos.map((d) => <option key={d}>{d}</option>)}
            </select>
          </div>
        </div>
        <div className="mt-5">
          <button onClick={run} disabled={loading || !programa} className="px-6 py-2.5 rounded-lg font-semibold text-base transition-all bg-gold-400 text-[#0a0f1f] hover:bg-gold-400/90 disabled:opacity-40">
            {loading ? 'Proyectando...' : 'Proyectar mi carrera'}
          </button>
          {error && <p className="text-rose-400 text-sm mt-3">{error}</p>}
        </div>
      </div>

      {result && (() => {
        const base = result.escenarios[0]
        const salarioInicial = base.salario_inicial_cop
        const salario5 = base.mediana[4] || 0
        const crecAnual = base.crecimiento_anual_pct
        const acum10 = base.ingreso_acumulado_10a
        return (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KpiCard label="Salario inicial" value={formatCOP(salarioInicial)} sub="/mes" accent="gold" />
            <KpiCard label="Salario a 5 años" value={formatCOP(salario5)} sub="/mes" accent="gold" />
            <KpiCard label="Crecimiento anual" value={`${crecAnual > 0 ? '+' : ''}${crecAnual}%`} sub="proyectado" accent={crecAnual > 0 ? 'green' : 'rose'} />
            <KpiCard label="Acumulado 10 años" value={formatCOP(acum10)} sub="total" accent="gold" />
          </div>

          <div className="plate card p-5">
            <h3 className="text-lg font-semibold text-gold-400 mb-4">Proyección salarial — {programa} en {departamento}</h3>
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="año" stroke="#64748b" tick={{ fontSize: 12 }} label={{ value: 'Años', position: 'insideBottom', offset: -5, fill: '#64748b' }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 12 }} tickFormatter={(v: number) => `$${(v / 1_000_000).toFixed(0)}M`} />
                <Tooltip contentStyle={{ background: '#0a0f1f', border: '1px solid rgba(212,175,55,0.35)', borderRadius: '10px', color: '#e9ecf5' }} formatter={(v: any) => [`$${Math.round(Number(v)).toLocaleString("es-CO")}`, 'Salario']} />
                <Area type="monotone" dataKey="p90" fill="#d4af37" fillOpacity={0.06} stroke="none" />
                <Area type="monotone" dataKey="p10" fill="#d4af37" fillOpacity={0.06} stroke="none" />
                <Line type="monotone" dataKey="mediana" stroke="#d4af37" strokeWidth={3} dot={{ r: 4 }} name="Salario proyectado" />
              </ComposedChart>
            </ResponsiveContainer>
            <p className="text-sm text-slate-500 mt-3 text-center">Banda sombreada: rango p10-p90. Proyección basada en OLE, GEIH y Chronos T5.</p>
          </div>

          {result.alerta_saturacion && (
            <div className={`plate card p-4 border ${result.alerta_saturacion.riesgo === 'alto' ? 'border-rose-500/30 bg-rose-500/5' : 'border-amber-500/20 bg-amber-500/5'}`}>
              <div className="flex items-center gap-2">
                <span className="text-lg">{result.alerta_saturacion.riesgo === 'alto' ? '⚠️' : '📊'}</span>
                <div>
                  <p className="text-base text-slate-200 font-medium">{result.alerta_saturacion.mensaje}</p>
                  <p className="text-sm text-slate-400 mt-1">{result.alerta_saturacion.detalle}</p>
                </div>
              </div>
            </div>
          )}
        </>
        )
      })()}
    </div>
  )
}
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
              <div className="bg-[#0a0f1f] border border-amber-500/40 rounded-lg mt-1 max-h-48 overflow-y-auto absolute z-50 w-full shadow-2xl">
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
              <table className="w-full text-base">
                <thead>
                  <tr className="border-b border-white/[0.08] text-left">
                    <th className="py-3 px-3 text-base text-slate-300 font-semibold">#</th>
                    <th className="py-3 px-3 text-base text-slate-300 font-semibold">Departamento</th>
                    <th className="py-3 px-3 text-base text-slate-300 font-semibold">Score</th>
                    <th className="py-3 px-3 text-base text-slate-300 font-semibold">Urgencia</th>
                    <th className="py-3 px-3 text-base text-slate-300 font-semibold text-right">Desempleo</th>
                    <th className="py-3 px-3 text-base text-slate-300 font-semibold text-right">Informalidad</th>
                    <th className="py-3 px-3 text-base text-slate-300 font-semibold text-right">DNP</th>
                  </tr>
                </thead>
                <tbody>
                  {result.ranking?.slice(0, 20).map((d: any, i: number) => {
                    const urgColor = d.nivel_urgencia === 'Crítico' ? '#ef4444' : d.nivel_urgencia === 'Alta' ? '#f59e0b' : d.nivel_urgencia === 'Media' ? '#3b82f6' : '#22c55e'
                    return (
                    <tr key={i} className={`border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors ${i < 3 ? 'bg-amber-500/5' : ''}`}>
                      <td className="py-3 px-3 text-slate-400 font-mono">{i + 1}</td>
                      <td className="py-3 px-3 text-slate-200 font-medium">{d.nombre}</td>
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-20 h-2.5 bg-white/[0.06] rounded-full overflow-hidden">
                            <div className="h-full rounded-full" style={{ width: `${d.score_prioridad}%`, backgroundColor: urgColor }} />
                          </div>
                          <span className="font-bold text-gold-400 text-sm">{d.score_prioridad}</span>
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <span className="px-2.5 py-1 rounded text-sm font-bold" style={{ backgroundColor: `${urgColor}25`, color: urgColor }}>
                          {d.nivel_urgencia}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right text-slate-300 font-semibold">{d.tasa_desempleo != null ? `${d.tasa_desempleo.toFixed(1)}%` : '—'}</td>
                      <td className="py-3 px-3 text-right text-slate-300 font-semibold">{d.tasa_informalidad != null ? `${d.tasa_informalidad.toFixed(0)}%` : '—'}</td>
                      <td className="py-3 px-3 text-right text-slate-300 font-semibold">{d.dnp_desempeno != null ? d.dnp_desempeno.toFixed(0) : '—'}</td>
                    </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            {result.ranking?.length > 20 && (
              <p className="text-base text-slate-500 mt-3 text-center">Mostrando 20 de {result.total_departamentos} departamentos</p>
            )}
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
