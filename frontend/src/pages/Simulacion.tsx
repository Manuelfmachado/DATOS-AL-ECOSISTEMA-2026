import { useEffect, useState, type ReactNode } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Cell,
} from 'recharts'
import AnalizarIAButton from '../components/AnalizarIAButton'
import api from '../services/api'
import { formatCOP, formatNumber } from '../utils/format'

type Tab = 'universidades' | 'gobierno' | 'estudiantes'

interface AlineacionResult {
  programa: string
  pensum_ingresado: string[]
  ocupaciones_afines: string[]
  indice_alineacion_curricular: number
  cobertura_esco_pct: number
  total_esenciales: number
  total_cubiertas: number
  total_faltantes: number
  coincidencia_vacantes_spe_pct: number
  competencias_cubiertas: string[]
  competencias_faltan: string[]
  cursos_sena_recomendados: {
    programa: string
    area: string
    duracion_horas: string
    costo_cop: string
    institucion: string
    departamento: string
  }[]
  metodologia: string
  fuentes: string[]
}

interface IntervencionResult {
  departamento: string
  objetivo: string
  objetivo_label: string
  beneficiarios: number
  periodo_empleo: string
  pesos_objetivo: Record<string, number>
  top_oportunidades: {
    rama_ciiu: number
    sector: string
    empleo_depto: number
    demanda_pct: number
    crecimiento_proyectado_pct: number
    deficit_talento_pct: number
    compatibilidad_economica_pct: number
    score: number
    beneficiarios_estimados: number
    justificacion: string
  }[]
  ranking_completo: any[]
  metodologia: string
  fuentes: string[]
}

interface ExploraResult {
  programa: string
  ocupaciones_afines: string[]
  habilidades_desarrollaras: { habilidad: string; frecuencia_en_ocupaciones: number }[]
  salidas_laborales: string[]
  demanda_laboral_sectores: { rama_ciiu: number; sector: string; empleo_nacional: number }[]
  salario_esperado: {
    rango_modal: string | null
    mediana_cop: number | null
    egresados_anuales_nacional: number
  }
  donde_estudiarla: {
    institucion: string
    programa: string
    departamento: string
    matriculados: number
  }[]
  fuentes: string[]
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
    icon: '🎓',
  },
]

const fieldClass = 'w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-base text-slate-200 outline-none transition focus:border-gold-400/60'
const textareaClass = 'w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-base text-slate-200 outline-none transition focus:border-gold-400/60 min-h-[100px] resize-y'

const tooltipStyle = {
  contentStyle: { background: '#0a0f1f', border: '1px solid rgba(212,175,55,0.35)', borderRadius: 10, color: '#e9ecf5' },
  labelStyle: { color: '#d4af37', fontWeight: 700 },
}

function useDepartamentos() {
  const [deptos, setDeptos] = useState(DEPTOS_FALLBACK)

  useEffect(() => {
    api.get('/simulacion/departamentos')
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
      api.get('/simulacion/programas', { params: { q: query, limit: 20 } })
        .then((r) => setProgramas(r.data?.programas.map((p: any) => p.programa) || []))
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
  const [programaQuery, setProgramaQuery] = useState('')
  const [programa, setPrograma] = useState('')
  const [pensumText, setPensumText] = useState('')
  const [result, setResult] = useState<AlineacionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { programas, setProgramas } = useProgramas(programaQuery)

  const run = async () => {
    if (!programa.trim()) {
      setError('Selecciona un programa académico.')
      return
    }
    const pensum = pensumText.split('\n').map(l => l.trim()).filter(l => l.length > 0)
    if (pensum.length === 0) {
      setError('Ingresa al menos una competencia del pensum actual.')
      return
    }
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const r = await api.post('/simulacion/alineacion-curricular', { programa: programa.trim(), pensum })
      setResult(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'No se pudo evaluar la alineación curricular.')
    } finally {
      setLoading(false)
    }
  }

  const chartData = result ? [
    { name: 'Cobertura ESCO', value: result.cobertura_esco_pct },
    { name: 'Coincidencia SPE', value: result.coincidencia_vacantes_spe_pct },
  ] : []

  return (
    <section className="space-y-4">
      <FormCard
        title="🏫 Universidades — Alineación curricular"
        description="Evalúa si el pensum de un programa cubre las habilidades esenciales que exige el mercado laboral (ESCO) y verifica la coincidencia con las vacantes del SPE/APE SENA."
      >
        <div className="md:col-span-2">
          <ProgramaInput query={programaQuery} setQuery={setProgramaQuery} setPrograma={setPrograma} programas={programas} setProgramas={setProgramas} />
        </div>
        <div className="md:col-span-2">
          <label className="text-sm text-slate-400 mb-1 block">Pensum actual (una competencia por línea)</label>
          <textarea 
            value={pensumText} 
            onChange={(e) => setPensumText(e.target.value)} 
            placeholder="Ej: Análisis de algoritmos&#10;Bases de datos SQL&#10;Desarrollo web" 
            className={textareaClass}
          />
        </div>
        <div className="md:col-span-4">
          <ActionButton onClick={run} loading={loading} label="Evaluar alineación" loadingLabel="Evaluando…" />
          {error && <p className="text-rose-400 text-sm mt-2">{error}</p>}
        </div>
      </FormCard>

      {result && (
        <>
          <div className="plate card p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-widest text-gold-400">Resultado curricular</p>
              <h3 className="text-2xl font-bold text-white mt-1">{result.programa}</h3>
              <p className="text-sm text-slate-300 mt-2 max-w-3xl">El programa cubre {result.total_cubiertas} de {result.total_esenciales} habilidades esenciales identificadas.</p>
            </div>
            <div className="text-center rounded-2xl border border-gold-400/40 bg-gold-400/10 px-6 py-4">
              <div className="text-5xl font-bold font-display text-gold-400">{result.indice_alineacion_curricular}%</div>
              <p className="text-xs text-slate-400 uppercase tracking-wider">índice de alineación</p>
            </div>
          </div>

          <KpiGrid items={[
            ['Habilidades esenciales', `${result.total_esenciales}`, 'ESCO', 'blue'],
            ['Cobertura del pensum', `${result.total_cubiertas}`, `Faltan ${result.total_faltantes}`, result.total_cubiertas >= result.total_esenciales / 2 ? 'green' : 'rose'],
            ['Match con SPE', `${result.coincidencia_vacantes_spe_pct}%`, 'demanda local', 'gold'],
            ['Ocupaciones afines', `${result.ocupaciones_afines.length}`, 'encontradas', 'gold'],
          ]} />

          <div className="plate card p-5 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <WidgetHeader title="Competencias Faltantes" dashboard="simulacion" data={result} />
              <ul className="list-disc pl-5 text-sm text-slate-300 space-y-1">
                {result.competencias_faltan.slice(0, 8).map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gold-400 mb-2">Cursos SENA Recomendados</h3>
              <ul className="space-y-2">
                {result.cursos_sena_recomendados.map((c, i) => (
                  <li key={i} className="text-sm text-slate-300 bg-white/5 p-2 rounded">
                    <strong>{c.programa}</strong> ({c.duracion_horas}h) - {c.departamento}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="plate card p-5">
            <WidgetHeader title="Resumen de Indicadores" dashboard="simulacion" data={result} />
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="name" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} domain={[0, 100]} />
                <Tooltip {...tooltipStyle} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={60}>
                  {chartData.map((_, i) => <Cell key={i} fill={i === 1 ? '#f59e0b' : '#d4af37'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <SourceLine fuentes={result.fuentes} />
          </div>
        </>
      )}
    </section>
  )
}

function Gobierno() {
  const deptos = useDepartamentos()
  const [departamento, setDepartamento] = useState('Bogotá D.C.')
  const [objetivo, setObjetivo] = useState('sectores_emergentes')
  const [beneficiarios, setBeneficiarios] = useState(500)
  const [result, setResult] = useState<IntervencionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const r = await api.post('/simulacion/intervencion-gobierno', { departamento, objetivo, beneficiarios })
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
        title="🏛️ Gobierno — Intervención por objetivo"
        description="Prioriza sectores en un departamento según tu objetivo (reducir desempleo, sectores emergentes, etc). Combina empleo GEIH, crecimiento Chronos, déficit SENA y base formal PILA."
      >
        <SelectField label="Departamento" value={departamento} onChange={setDepartamento} options={deptos} />
        <SelectField label="Objetivo principal" value={objetivo} onChange={setObjetivo} options={[
          { value: 'sectores_emergentes', label: 'Impulsar sectores emergentes' },
          { value: 'reducir_desempleo_juvenil', label: 'Reducir desempleo' },
          { value: 'emprendimiento', label: 'Fomentar emprendimiento' },
          { value: 'reducir_informalidad', label: 'Reducir informalidad' },
        ].map(o => o.value)} renderOptions={[
          { value: 'sectores_emergentes', label: 'Impulsar sectores emergentes' },
          { value: 'reducir_desempleo_juvenil', label: 'Reducir desempleo' },
          { value: 'emprendimiento', label: 'Fomentar emprendimiento' },
          { value: 'reducir_informalidad', label: 'Reducir informalidad' },
        ]} />
        <div>
          <label className="text-sm text-slate-400 mb-1 block">Beneficiarios estimados</label>
          <input type="number" min={10} step={10} value={beneficiarios} onChange={(e) => setBeneficiarios(Number(e.target.value))} className={fieldClass} />
        </div>
        <div className="md:col-span-1 flex items-end">
          <ActionButton onClick={run} loading={loading} label="Calcular intervención" loadingLabel="Calculando…" />
        </div>
        {error && <p className="text-rose-400 text-sm md:col-span-4">{error}</p>}
      </FormCard>

      {result && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {result.top_oportunidades?.slice(0, 2).map((rec, i) => (
              <div key={rec.sector} className="plate card p-4 border-gold-400/30 bg-gold-400/5">
                <p className="text-xs text-gold-400 font-bold uppercase">Prioridad #{i + 1}</p>
                <h3 className="text-xl font-bold text-white mt-1">{rec.sector}</h3>
                <p className="text-2xl font-display font-bold text-gold-400 mt-2">Score: {rec.score}</p>
                <p className="text-sm text-slate-300 mt-2">{rec.justificacion}</p>
              </div>
            ))}
          </div>

          <div className="plate card p-5 overflow-x-auto">
            <WidgetHeader title={`Top sectores para ${result.objetivo_label} en ${result.departamento}`} dashboard="simulacion" data={result} />
            <table className="w-full text-sm mt-3">
              <thead>
                <tr className="border-b border-white/10 text-left text-slate-300">
                  <th className="py-3 px-2">#</th>
                  <th className="py-3 px-2">Sector (CIIU)</th>
                  <th className="py-3 px-2 text-right">Score</th>
                  <th className="py-3 px-2 text-right">Empleo (GEIH)</th>
                  <th className="py-3 px-2 text-right">Crecimiento</th>
                  <th className="py-3 px-2 text-right">Déficit Talento</th>
                </tr>
              </thead>
              <tbody>
                {result.top_oportunidades.map((d, i) => (
                  <tr key={d.rama_ciiu} className="border-b border-white/5 text-slate-300">
                    <td className="py-3 px-2 text-slate-500">{i + 1}</td>
                    <td className="py-3 px-2 font-semibold text-white">{d.sector}</td>
                    <td className="py-3 px-2 text-right font-bold text-gold-400">{d.score}</td>
                    <td className="py-3 px-2 text-right">{formatNumber(d.empleo_depto)}</td>
                    <td className="py-3 px-2 text-right">{d.crecimiento_proyectado_pct > 0 ? '+' : ''}{d.crecimiento_proyectado_pct}%</td>
                    <td className="py-3 px-2 text-right">{d.deficit_talento_pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-xs text-slate-500 mt-3">{result.metodologia}</p>
            <SourceLine fuentes={result.fuentes} />
          </div>
        </>
      )}
    </section>
  )
}

function FuturosEstudiantes() {
  const [programaQuery, setProgramaQuery] = useState('')
  const [programa, setPrograma] = useState('')
  const [result, setResult] = useState<ExploraResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { programas, setProgramas } = useProgramas(programaQuery)

  const run = async () => {
    if (!programa.trim()) {
      setError('Selecciona una carrera o programa de la lista.')
      return
    }
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const r = await api.post('/simulacion/explora-carrera', { programa: programa.trim() })
      setResult(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'No se pudo explorar la carrera.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="space-y-4">
      <FormCard
        title="🎓 Futuros estudiantes — Explora carrera"
        description="Muestra datos reales de salarios, habilidades a desarrollar, salidas laborales y dónde estudiar un programa específico sin scores mágicos."
      >
        <div className="md:col-span-2">
          <ProgramaInput query={programaQuery} setQuery={setProgramaQuery} setPrograma={setPrograma} programas={programas} setProgramas={setProgramas} />
        </div>
        <div className="md:col-span-2 flex items-end">
          <ActionButton onClick={run} loading={loading} label="Explorar carrera" loadingLabel="Explorando…" />
        </div>
        {error && <p className="text-rose-400 text-sm md:col-span-4">{error}</p>}
      </FormCard>

      {result && (
        <>
          <KpiGrid items={[
            ['Salario esperado', result.salario_esperado.mediana_cop ? formatCOP(result.salario_esperado.mediana_cop) : result.salario_esperado.rango_modal || 'No info', '/mes', 'gold'],
            ['Egresados anuales', formatNumber(result.salario_esperado.egresados_anuales_nacional), 'a nivel nacional', 'blue'],
            ['Ocupaciones afines', `${result.ocupaciones_afines.length}`, 'identificadas', 'green'],
            ['Opciones de estudio', `${result.donde_estudiarla.length}`, 'universidades top', 'gold'],
          ]} />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="plate card p-5">
              <WidgetHeader title="Habilidades que desarrollarás" dashboard="simulacion" data={result} />
              <ul className="space-y-2 mt-3">
                {result.habilidades_desarrollaras.map((h, i) => (
                  <li key={i} className="text-sm text-slate-300 flex justify-between">
                    <span>{h.habilidad}</span>
                    <span className="text-slate-500">req. {h.frecuencia_en_ocupaciones}x</span>
                  </li>
                ))}
              </ul>
            </div>
            
            <div className="plate card p-5">
              <h3 className="text-lg font-semibold text-gold-400 mb-3">Principales salidas laborales</h3>
              <ul className="list-disc pl-5 space-y-1 text-sm text-slate-300">
                {result.salidas_laborales.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          </div>

          <div className="plate card p-5 overflow-x-auto">
            <h3 className="text-lg font-semibold text-gold-400 mb-3">¿Dónde estudiar este programa? (SNIES)</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-slate-300">
                  <th className="py-3 px-2">Institución</th>
                  <th className="py-3 px-2">Programa</th>
                  <th className="py-3 px-2">Departamento</th>
                  <th className="py-3 px-2 text-right">Matriculados</th>
                </tr>
              </thead>
              <tbody>
                {result.donde_estudiarla.map((d, i) => (
                  <tr key={i} className="border-b border-white/5 text-slate-300">
                    <td className="py-3 px-2 font-semibold text-white">{d.institucion}</td>
                    <td className="py-3 px-2">{d.programa}</td>
                    <td className="py-3 px-2">{d.departamento}</td>
                    <td className="py-3 px-2 text-right">{formatNumber(d.matriculados)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <SourceLine fuentes={result.fuentes} />
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
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-start">{children}</div>
    </div>
  )
}

function ProgramaInput({ query, setQuery, setPrograma, programas, setProgramas }: { query: string; setQuery: (v: string) => void; setPrograma: (v: string) => void; programas: string[]; setProgramas: (v: string[]) => void }) {
  return (
    <div className="relative">
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

function SelectField({ label, value, onChange, options, renderOptions }: { label: string; value: string; onChange: (v: string) => void; options: string[], renderOptions?: { value: string, label: string }[] }) {
  return (
    <div>
      <label className="text-sm text-slate-400 mb-1 block">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)} className={fieldClass}>
        {renderOptions 
          ? renderOptions.map((op) => <option key={op.value} value={op.value}>{op.label}</option>)
          : options.map((op) => <option key={op} value={op}>{op}</option>)
        }
      </select>
    </div>
  )
}

function ActionButton({ onClick, loading, label, loadingLabel }: { onClick: () => void; loading: boolean; label: string; loadingLabel: string }) {
  return <button onClick={onClick} disabled={loading} className="w-full rounded-lg bg-gold-400 px-5 py-2.5 font-semibold text-[#0a0f1f] transition hover:bg-gold-400/90 disabled:opacity-50">{loading ? loadingLabel : label}</button>
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