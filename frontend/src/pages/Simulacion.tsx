import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  BarChart, Bar, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Cell, Area, ComposedChart,
} from 'recharts'
import AnalizarIAButton from '../components/AnalizarIAButton'
import api from '../services/api'
import { formatCOP, formatCOPCompact } from '../utils/format'
import { formatCOP, formatCOPCompact, formatNumber } from '../utils/format'

type Tab = 'universidades' | 'gobierno' | 'estudiantes'

interface ViabilidadResult {
  programa: string
  departamento: string
  nivel: string
  score_viabilidad: number
  nivel_riesgo: string
  sin_oferta_local: boolean
  recomendacion: string
  indicadores: {
    salario_estimado_cop: number
    salario_mercado_cop: number
    demanda_score: number
    saturacion_oferta_pct: number
    crecimiento_proyectado_anual_pct: number
    matriculados_competencia: number
    sectores_demandantes?: { sector: string; empresas: number }[]
  }
  fuentes?: string[]
}

interface PriorizacionResult {
  presupuesto_cop: number
  total_departamentos: number
  ranking: {
    nombre: string
    score_prioridad: number
    nivel_urgencia: string
    tasa_desempleo: number | null
    tasa_informalidad: number | null
    dnp_desempeno: number | null
    accion_recomendada: string
  }[]
  recomendaciones_inversion: { departamento: string; inversion_sugerida_cop: number; accion: string }[]
  metodologia: string
  fuentes?: string[]
}

interface FuturoResult {
  programa: string
  departamento: string
  edad: number
  nivel_detectado: string
  escenarios: {
    label: string
    salario_inicial_cop: number
    crecimiento_anual_pct: number
    anos: number[]
    mediana: number[]
    p10: number[]
    p90: number[]
    ingreso_acumulado_10a: number
    descripcion: string
    profesion_chronos: string
  }[]
  veredicto: string
  alerta_saturacion?: { riesgo: string; mensaje: string; detalle: string }
}

const DEPTOS_FALLBACK = [
  'Amazonas', 'Antioquia', 'Arauca', 'Archipiélago de San Andrés', 'Atlántico',
  'Bogotá D.C.', 'Bolívar', 'Boyacá', 'Caldas', 'Caquetá', 'Casanare', 'Cauca',
  'Cesar', 'Chocó', 'Cundinamarca', 'Córdoba', 'Guainía', 'Guaviare', 'Huila',
  'La Guajira', 'Magdalena', 'Meta', 'Nariño', 'Norte de Santander', 'Putumayo',
  'Quindío', 'Risaralda', 'Santander', 'Sucre', 'Tolima', 'Valle del Cauca',
  'Vaupés', 'Vichada',
]

const TAB_CONFIG: { id: Tab; title: string; subtitle: string; description: string; icon: string }[] = [
  {
    id: 'universidades',
    title: 'Universidades',
    subtitle: 'Alineación curricular',
    description: 'Primero: evalúa apertura o actualización de programas con SNIES, OLE, SPE/APE, GEIH y crecimiento proyectado.',
    icon: '▦',
  },
  {
    id: 'gobierno',
    title: 'Gobierno',
    subtitle: 'Intervención por objetivo',
    description: 'Segundo: prioriza territorios según desempleo, informalidad, desempeño municipal y presupuesto público disponible.',
    icon: '▥',
  },
  {
  {
    id: 'universidades',
    title: 'Universidades',
    subtitle: 'Alineación curricular',
    description: 'Primero: evalúa apertura o actualización de programas con SNIES, OLE, SPE/APE, GEIH y crecimiento proyectado.',
    icon: '🏫',
  },
  {
    id: 'gobierno',
    title: 'Gobierno',
    subtitle: 'Intervención por objetivo',
    description: 'Segundo: prioriza territorios según desempleo, informalidad, desempeño municipal y presupuesto público disponible.',
    icon: '🏛️',
  },
  {
    id: 'estudiantes',
    title: 'Futuros estudiantes',
    subtitle: 'Explora carrera',
    description: 'Tercero: explora salarios, crecimiento y alertas de saturación con métricas observables y supuestos visibles.',
    icon: '◈',
    icon: '🎓',
  },
]

const fieldClass = 'w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-base text-slate-200 outline-none transition focus:border-gold-400/60'

const tooltipStyle = {
  contentStyle: { background: '#0a0f1f', border: '1px solid rgba(212,175,55,0.35)', borderRadius: 10, color: '#e9ecf5' },
  labelStyle: { color: '#d4af37', fontWeight: 700 },
}

function useDepartamentos() {
  const [deptos, setDeptos] = useState(DEPTOS_FALLBACK)

  useEffect(() => {
    api.get('/simulacion/trayectoria/departamentos')
      .then((r) => {
        const departamentos = r.data?.departamentos
        if (Array.isArray(departamentos) && departamentos.length > 0) setDeptos(departamentos)
      })
      .catch(() => setDeptos(DEPTOS_FALLBACK))
  }, [])

  return deptos
}

function useProgramas(query: string) {
  const [programas, setProgramas] = useState<string[]>([])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (query.trim().length < 2) {
        setProgramas([])
        return
      }
      api.get('/simulacion/trayectoria/programas', { params: { q: query, limit: 20 } })
        .then((r) => setProgramas(r.data?.programas || []))
        .catch(() => setProgramas([]))
    }, 250)

    return () => window.clearTimeout(timer)
  }, [query])

  return { programas, setProgramas }
}

export default function Simulacion() {
  const [tab, setTab] = useState<Tab>('universidades')

  return (
    <div className="animate-fade-in space-y-5">
      <header>
        <p className="text-sm uppercase tracking-[0.3em] text-gold-400/80">Módulo depurado</p>
        <h1 className="text-5xl font-bold text-gold-400 font-display">Simulación</h1>
        <p className="text-lg text-slate-300 mt-2 max-w-4xl">
          Tres simulaciones sólidas, accionables y sustentadas en datos reales: alineación curricular, intervención territorial y exploración de carrera.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {TAB_CONFIG.map((item) => (
          <button
            key={item.id}
            onClick={() => setTab(item.id)}
            className={`plate card p-5 text-left transition-all ${tab === item.id ? 'border-[#d4af37]/80 shadow-[0_0_18px_rgba(212,175,55,0.20)]' : 'hover:border-white/[0.12]'}`}
          >
            <div className="flex items-start gap-3">
              <span className="text-3xl text-gold-400 leading-none">{item.icon}</span>
              <span className="text-3xl">{item.icon}</span>
              <div>
                <h2 className={`text-lg font-bold ${tab === item.id ? 'text-[#d4af37]' : 'text-white'}`}>{item.title}</h2>
                <p className="text-sm font-semibold text-slate-300">{item.subtitle}</p>
              </div>
            </div>
            <p className="text-sm text-slate-400 mt-3 leading-relaxed">{item.description}</p>
          </button>
        ))}
      </div>

      {tab === 'universidades' && <Universidades />}
      {tab === 'gobierno' && <Gobierno />}
      {tab === 'estudiantes' && <FuturosEstudiantes />}
    </div>
  )
}

function Universidades() {
  const deptos = useDepartamentos()
  const [programaQuery, setProgramaQuery] = useState('')
  const [programa, setPrograma] = useState('')
  const [departamento, setDepartamento] = useState('Bogotá D.C.')
  const [nivel, setNivel] = useState('Profesional')
  const [result, setResult] = useState<ViabilidadResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { programas, setProgramas } = useProgramas(programaQuery)

  const run = async () => {
    if (!programa.trim()) {
      setError('Selecciona un programa académico de la lista.')
      return
    }
    setProgramas([])
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const r = await api.post('/simulacion/viabilidad-programa', { programa: programa.trim(), departamento, nivel })
      setResult(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'No se pudo evaluar la alineación curricular.')
    } finally {
      setLoading(false)
    }
  }

  const chartData = result ? [
    { name: 'Demanda laboral', value: result.indicadores.demanda_score },
    { name: 'Saturación oferta', value: result.sin_oferta_local ? 0 : result.indicadores.saturacion_oferta_pct },
    { name: 'Crecimiento anual', value: Math.max(0, result.indicadores.crecimiento_proyectado_anual_pct * 10) },
  ] : []

  return (
    <section className="space-y-4">
      <FormCard
        title="Universidades — Alineación curricular"
        description="Evalúa si un programa está alineado con la demanda territorial. La decisión combina oferta educativa local, ingresos de egresados, demanda SPE/APE, tejido empresarial y crecimiento sectorial."
      >
        <ProgramaInput query={programaQuery} selectedPrograma={programa} setQuery={setProgramaQuery} setPrograma={setPrograma} programas={programas} setProgramas={setProgramas} />
        title="🏫 Universidades — Alineación curricular"
        description="Evalúa si un programa está alineado con la demanda territorial. La decisión combina oferta educativa local, ingresos de egresados, demanda SPE/APE, tejido empresarial y crecimiento sectorial."
      >
        <ProgramaInput query={programaQuery} setQuery={setProgramaQuery} setPrograma={setPrograma} programas={programas} setProgramas={setProgramas} />
        <SelectField label="Departamento" value={departamento} onChange={setDepartamento} options={deptos} />
        <SelectField label="Nivel" value={nivel} onChange={setNivel} options={['Técnico', 'Profesional', 'Especialización', 'Maestría']} />
        <ActionButton onClick={run} loading={loading} label="Evaluar alineación" loadingLabel="Evaluando…" />
        {error && <p className="text-rose-400 text-sm md:col-span-4">{error}</p>}
      </FormCard>

      {result && (
        <>
          <div className="plate card p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-widest text-gold-400">Resultado curricular</p>
              <h3 className="text-2xl font-bold text-white mt-1">{result.programa}</h3>
              <p className="text-sm text-slate-300 mt-2 max-w-3xl">{result.recomendacion}</p>
            </div>
            <div className="text-center rounded-2xl border border-gold-400/40 bg-gold-400/10 px-6 py-4">
              <div className="text-5xl font-bold font-display text-gold-400">{result.score_viabilidad}</div>
              <p className="text-xs text-slate-400 uppercase tracking-wider">índice de viabilidad</p>
            </div>
          </div>

          <KpiGrid items={[
            ['Salario estimado', formatCOP(result.indicadores.salario_estimado_cop), '/mes', 'gold'],
            ['Demanda laboral', `${result.indicadores.demanda_score}%`, 'SPE/APE', 'green'],
            ['Oferta local', result.sin_oferta_local ? 'Sin oferta' : `${result.indicadores.matriculados_competencia.toLocaleString('es-CO')} matriculados`, result.sin_oferta_local ? 'oportunidad' : 'competencia', result.sin_oferta_local ? 'gold' : 'blue'],
            ['Crecimiento', `${result.indicadores.crecimiento_proyectado_anual_pct > 0 ? '+' : ''}${result.indicadores.crecimiento_proyectado_anual_pct}%`, 'anual', 'gold'],
          ]} />

          <div className="plate card p-5">
            <WidgetHeader title="Variables que explican la decisión" dashboard="simulacion" data={result} />
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="name" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip {...tooltipStyle} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {chartData.map((_, i) => <Cell key={i} fill={i === 1 ? '#f59e0b' : '#d4af37'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <SourceLine fuentes={result.fuentes || ['SNIES', 'OLE/MEN', 'SPE/APE SENA', 'GEIH', 'RUES']} />
          </div>
        </>
      )}
    </section>
  )
}

function Gobierno() {
  const [presupuesto, setPresupuesto] = useState(1000)
  const [result, setResult] = useState<PriorizacionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const dashboard = await fetch('/dashboard.json')
        .then((res) => res.ok ? res.json() : Promise.reject(new Error('dashboard estático no disponible')))
        .catch(() => api.get('/observatorio/dashboard').then((res) => res.data))
      const departamentos = dashboard?.prioridad?.departamentos || []
      const ranking = departamentos.map((d: any) => {
        const score = Number(d.indice_prioridad ?? 0)
        const informalidad = d.tasa_formalidad != null ? Math.max(0, 100 - Number(d.tasa_formalidad)) : null
        return {
          nombre: d.departamento,
          score_prioridad: score,
          nivel_urgencia: score >= 70 ? 'Urgente' : score >= 50 ? 'Atención' : 'Estable',
          tasa_desempleo: d.tasa_desempleo ?? null,
          tasa_informalidad: informalidad,
          dnp_desempeno: d.dnp_desempeno ?? null,
          accion_recomendada: score >= 70
            ? 'Priorizar programas integrales de empleo, formación pertinente y formalización.'
            : score >= 50
              ? 'Hacer seguimiento e intervenciones focalizadas por brechas laborales.'
              : 'Mantener monitoreo preventivo y reforzar sectores con potencial.',
        }
      })
      const top3 = ranking.slice(0, 3).map((d: any) => ({
        departamento: d.nombre,
        inversion_sugerida_cop: Math.round((presupuesto * 1_000_000 / 3) / 1_000_000) * 1_000_000,
        accion: d.accion_recomendada,
      }))
      setResult({
        presupuesto_cop: presupuesto * 1_000_000,
        total_departamentos: ranking.length,
        ranking,
        recomendaciones_inversion: top3,
        metodologia: dashboard?.prioridad?.nota || 'Índice compuesto del Observatorio: ≥70 urgente, 50-69 atención, <50 estable.',
        fuentes: ['GEIH', 'DNP/MDM', 'RUES', 'Observatorio ALBA'],
      })
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'No se pudo calcular la intervención territorial.')
      const r = await api.post('/simulacion/priorizacion-territorial', { presupuesto_cop: presupuesto * 1_000_000 })
      setResult(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'No se pudo calcular la intervención territorial.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="space-y-4">
      <FormCard
        title="Gobierno — Intervención por objetivo"
        title="🏛️ Gobierno — Intervención por objetivo"
        description="Convierte indicadores territoriales en una lista priorizada de intervención: desempleo, informalidad, DNP/MDM, acción recomendada e inversión sugerida."
      >
        <div>
          <label className="text-sm text-slate-400 mb-1 block">Presupuesto disponible (millones COP)</label>
          <input type="number" min={100} step={100} value={presupuesto} onChange={(e) => setPresupuesto(Number(e.target.value))} className={fieldClass} />
        </div>
        <ActionButton onClick={run} loading={loading} label="Calcular intervención" loadingLabel="Calculando…" />
        {error && <p className="text-rose-400 text-sm md:col-span-4">{error}</p>}
      </FormCard>

      {result && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {result.recomendaciones_inversion?.slice(0, 3).map((rec, i) => (
              <div key={rec.departamento} className="plate card p-4 border-gold-400/30 bg-gold-400/5">
                <p className="text-xs text-gold-400 font-bold uppercase">Prioridad #{i + 1}</p>
                <h3 className="text-xl font-bold text-white mt-1">{rec.departamento}</h3>
                <p className="text-2xl font-display font-bold text-gold-400 mt-2">{formatCOPCompact(rec.inversion_sugerida_cop)}</p>
                <p className="text-sm text-slate-300 mt-2">{rec.accion}</p>
              </div>
            ))}
          </div>

          <div className="plate card p-5">
            <WidgetHeader title="Prioridad de intervención por departamento" dashboard="simulacion" data={result} />
            <WidgetHeader title="Ranking de intervención territorial" dashboard="simulacion" data={result} />
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={result.ranking.slice(0, 10)} layout="vertical" margin={{ left: 28, right: 28 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis dataKey="nombre" type="category" width={145} tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                <Tooltip {...tooltipStyle} />
                <Bar dataKey="score_prioridad" fill="#d4af37" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="plate card p-5 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-slate-300">
                  <th className="py-3 px-2">#</th><th className="py-3 px-2">Departamento</th><th className="py-3 px-2">Score</th><th className="py-3 px-2">Nivel</th><th className="py-3 px-2 text-right">Desempleo</th><th className="py-3 px-2 text-right">Informalidad</th><th className="py-3 px-2 text-right">DNP</th><th className="py-3 px-2">Acción</th>
                  <th className="py-3 px-2">#</th><th className="py-3 px-2">Departamento</th><th className="py-3 px-2">Urgencia</th><th className="py-3 px-2 text-right">Desempleo</th><th className="py-3 px-2 text-right">Informalidad</th><th className="py-3 px-2 text-right">DNP</th><th className="py-3 px-2">Acción</th>
                </tr>
              </thead>
              <tbody>
                {result.ranking.slice(0, 20).map((d, i) => (
                  <tr key={d.nombre} className="border-b border-white/5 text-slate-300">
                    <td className="py-3 px-2 text-slate-500">{i + 1}</td>
                    <td className="py-3 px-2 font-semibold text-white">{d.nombre}</td>
                    <td className="py-3 px-2 font-bold text-gold-400">{d.score_prioridad}</td>
                    <td className="py-3 px-2"><span className="rounded bg-gold-400/10 px-2 py-1 text-gold-400 font-semibold">{d.nivel_urgencia}</span></td>
                    <td className="py-3 px-2 text-right">{d.tasa_desempleo != null ? `${d.tasa_desempleo.toFixed(1)}%` : '—'}</td>
                    <td className="py-3 px-2 text-right">{d.tasa_informalidad != null ? `${d.tasa_informalidad.toFixed(0)}%` : '—'}</td>
                    <td className="py-3 px-2 text-right">{d.dnp_desempeno != null ? d.dnp_desempeno.toFixed(0) : '—'}</td>
                    <td className="py-3 px-2 max-w-md">{d.accion_recomendada}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-xs text-slate-500 mt-3">{result.metodologia}</p>
            <SourceLine fuentes={result.fuentes || ['GEIH', 'DNP/MDM', 'SNIES']} />
          </div>
        </>
      )}
    </section>
  )
}

function FuturosEstudiantes() {
  const deptos = useDepartamentos()
  const [programaQuery, setProgramaQuery] = useState('')
  const [programa, setPrograma] = useState('')
  const [departamento, setDepartamento] = useState('Bogotá D.C.')
  const [result, setResult] = useState<FuturoResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { programas, setProgramas } = useProgramas(programaQuery)

  const run = async () => {
    if (!programa.trim()) {
      setError('Selecciona una carrera o programa de la lista.')
      return
    }
    setProgramas([])
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const r = await api.post('/simulacion/que-pasa-si', { programa: programa.trim(), departamento, edad: 22, escenarios: [{ tipo: 'base' }] })
      setResult(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'No se pudo explorar la carrera.')
    } finally {
      setLoading(false)
    }
  }

  const base = result?.escenarios?.[0]
  const chartData = useMemo(() => {
    if (!base) return []
    return base.anos.map((ano, i) => ({ ano, mediana: base.mediana[i], p10: base.p10[i], p90: base.p90[i] }))
  }, [base])

  return (
    <section className="space-y-4">
      <FormCard
        title="Futuros estudiantes — Explora carrera"
        description="Muestra datos comprensibles de salario y crecimiento para una carrera en un territorio. La decisión queda explicada con fuentes, salarios, crecimiento y alertas; no se muestran marcadores sintéticos."
      >
        <ProgramaInput query={programaQuery} selectedPrograma={programa} setQuery={setProgramaQuery} setPrograma={setPrograma} programas={programas} setProgramas={setProgramas} />
        title="🎓 Futuros estudiantes — Explora carrera"
        description="Muestra datos comprensibles de salario y crecimiento para una carrera en un territorio. La decisión queda explicada con fuentes, salarios, crecimiento y alertas; no se muestran marcadores sintéticos."
      >
        <ProgramaInput query={programaQuery} setQuery={setProgramaQuery} setPrograma={setPrograma} programas={programas} setProgramas={setProgramas} />
        <SelectField label="Departamento donde quieres trabajar" value={departamento} onChange={setDepartamento} options={deptos} />
        <ActionButton onClick={run} loading={loading} label="Explorar carrera" loadingLabel="Explorando…" />
        {error && <p className="text-rose-400 text-sm md:col-span-4">{error}</p>}
      </FormCard>

      {result && base && (
        <>
          <KpiGrid items={[
            ['Salario inicial', formatCOP(base.salario_inicial_cop), '/mes', 'gold'],
            ['Salario a 5 años', formatCOP(base.mediana[4] || 0), '/mes', 'gold'],
            ['Crecimiento anual', `${base.crecimiento_anual_pct > 0 ? '+' : ''}${base.crecimiento_anual_pct}%`, 'proyectado', base.crecimiento_anual_pct >= 0 ? 'green' : 'rose'],
            ['Acumulado 10 años', formatCOP(base.ingreso_acumulado_10a), 'ingreso total', 'blue'],
          ]} />

          <div className="plate card p-5">
            <WidgetHeader title={`Proyección para ${result.programa} en ${result.departamento}`} dashboard="simulacion" data={result} />
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={chartData} margin={{ top: 8, right: 28, left: 16, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="ano" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={(v) => `$${(Number(v) / 1_000_000).toFixed(1)}M`} />
                <Tooltip {...tooltipStyle} formatter={(v: any) => [formatCOP(Number(v)), 'Salario mensual']} />
                <Area type="monotone" dataKey="p90" fill="#d4af37" fillOpacity={0.06} stroke="none" />
                <Area type="monotone" dataKey="p10" fill="#d4af37" fillOpacity={0.06} stroke="none" />
                <Line type="monotone" dataKey="mediana" stroke="#d4af37" strokeWidth={3} dot={{ r: 4 }} />
              </ComposedChart>
            </ResponsiveContainer>
            <p className="text-sm text-slate-400 mt-3">{result.veredicto}</p>
            {result.alerta_saturacion && <p className="text-sm text-amber-300 mt-2">{result.alerta_saturacion.mensaje}: {result.alerta_saturacion.detalle}</p>}
            <SourceLine fuentes={['OLE/MEN', 'GEIH', 'Chronos T5', 'SNIES']} />
          </div>
        </>
      )}
    </section>
  )
}

function FormCard({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <div className="plate card p-5">
      <h2 className="text-xl font-bold text-white">{title}</h2>
      <p className="text-sm text-slate-400 mt-1 mb-4 max-w-4xl">{description}</p>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">{children}</div>
    </div>
  )
}

function ProgramaInput({ query, selectedPrograma, setQuery, setPrograma, programas, setProgramas }: { query: string; selectedPrograma: string; setQuery: (v: string) => void; setPrograma: (v: string) => void; programas: string[]; setProgramas: (v: string[]) => void }) {
  return (
    <div className="relative md:col-span-2">
      <label className="text-sm text-slate-400 mb-1 block">Programa académico</label>
      <input value={query} onChange={(e) => { setQuery(e.target.value); setPrograma('') }} onBlur={() => window.setTimeout(() => setProgramas([]), 150)} placeholder="Busca por nombre del programa…" className={fieldClass} />
      {programas.length > 0 && query !== selectedPrograma && (
function ProgramaInput({ query, setQuery, setPrograma, programas, setProgramas }: { query: string; setQuery: (v: string) => void; setPrograma: (v: string) => void; programas: string[]; setProgramas: (v: string[]) => void }) {
  return (
    <div className="relative md:col-span-2">
      <label className="text-sm text-slate-400 mb-1 block">Programa académico</label>
      <input value={query} onChange={(e) => { setQuery(e.target.value); setPrograma('') }} placeholder="Busca por nombre del programa…" className={fieldClass} />
      {programas.length > 0 && (
        <div className="absolute z-50 mt-1 max-h-56 w-full overflow-y-auto rounded-lg border border-gold-400/30 bg-[#0a0f1f] shadow-2xl">
          {programas.map((p) => (
            <button key={p} type="button" onClick={() => { setPrograma(p); setQuery(p); setProgramas([]) }} className="block w-full px-3 py-2 text-left text-sm text-slate-300 hover:bg-gold-400/10 hover:text-gold-400">
              {p}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function SelectField({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <div>
      <label className="text-sm text-slate-400 mb-1 block">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)} className={fieldClass}>
        {options.map((op) => <option key={op} value={op}>{op}</option>)}
      </select>
    </div>
  )
}

function ActionButton({ onClick, loading, label, loadingLabel }: { onClick: () => void; loading: boolean; label: string; loadingLabel: string }) {
  return <button onClick={onClick} disabled={loading} className="rounded-lg bg-gold-400 px-5 py-2.5 font-semibold text-[#0a0f1f] transition hover:bg-gold-400/90 disabled:opacity-50">{loading ? loadingLabel : label}</button>
}

function KpiGrid({ items }: { items: [string, string, string, string][] }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {items.map(([label, value, sub, accent]) => <KpiCard key={label} label={label} value={value} sub={sub} accent={accent} />)}
    </div>
  )
}

function KpiCard({ label, value, sub, accent = 'gold' }: { label: string; value: string; sub?: string; accent?: string }) {
  const color = accent === 'green' ? 'text-emerald-400' : accent === 'rose' ? 'text-rose-400' : accent === 'blue' ? 'text-sky-400' : 'text-gold-400'
  return (
    <div className="plate card p-4">
      <p className="text-xs uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`text-2xl font-bold font-display mt-1 ${color}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  )
}

function WidgetHeader({ title, dashboard, data }: { title: string; dashboard: string; data: unknown }) {
  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h3 className="text-lg font-semibold text-gold-400">{title}</h3>
        <p className="text-sm text-slate-500">Usa el cuadro de IA para preguntar por la simulación generada.</p>
      </div>
      <AnalizarIAButton dashboard={dashboard} widgetTitle={title} widgetType="grafico" data={data} />
    </div>
  )
}

function SourceLine({ fuentes }: { fuentes: string[] }) {
  return <p className="mt-3 text-right text-xs text-slate-500">Fuentes: {fuentes.join(', ')}</p>
}
