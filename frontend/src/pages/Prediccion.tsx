import { useEffect, useState, type ReactNode } from 'react'
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, XAxis, YAxis,
  Tooltip, ResponsiveContainer, CartesianGrid, Cell, LabelList,
  ReferenceLine, Legend
} from 'recharts'
import Icon from '../components/Icon'
import api from '../services/api'
import FuentesBadge from '../components/FuentesBadge'
import { formatCOP } from '../utils/format'

function compactNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`
  return n.toLocaleString()
}

interface SeriePrediccion {
  años: number[]
  mediana: number[]
  bajo_10: number[]
  alto_90: number[]
}

interface SerieHistorico {
  años: number[]
  valores: number[]
}

interface SectorData {
  historico: SerieHistorico
  prediccion: SeriePrediccion
}

interface Profesion {
  profesion: string
  sector: string
  demanda: 'alta' | 'media' | 'baja'
  salario_mensual_cop: number
  salario_5a_cop: number
  salario_10a_cop: number
  crecimiento_anual_pct: number
  crecimiento_5a_pct: number
  crecimiento_10a_pct: number
}

interface Habilidad {
  habilidad: string
  demanda: number
}

interface SalarioData {
  metrica: string
  fuente: string
  crecimiento_anual_pct: number
  observacion: string
  salario_minimo_2026_cop: number
  salario_minimo_2030_cop: number
  salario_minimo_2035_cop: number
}

interface PrediccionData {
  modelo: string
  pais: string
  fuente: string
  ultimo_año_historico: number
  horizontes: { '5a': number; '10a': number }
  sectores: Record<string, SectorData>
  sectores_cagr_5a: Record<string, number>
  otros_indicadores?: Record<string, SectorData>
  profesiones: Profesion[]
  habilidades: Habilidad[]
  salarios: SalarioData
  insights: {
    sectores: {
      principal_empleador: string
      mas_estable: string
      mensaje: string
    }
    profesiones: {
      top_1: string
      top_3: string[]
      mensaje: string
    }
  }
}



interface GeihPunto {
  periodo: string
  valor?: number
  mediana?: number
  p10?: number
  p90?: number
}

interface GeihSerie {
  historico: GeihPunto[]
  prediccion_1ano: GeihPunto[]
  prediccion_5anos: GeihPunto[]
}

interface GeihData {
  modelo: string
  fuente: string
  ultimo_periodo_historico: string
  horizontes: string[]
  desempleo_nacional: GeihSerie
  informalidad_nacional: GeihSerie
  salario_promedio_nacional: GeihSerie
  sectores: Record<string, GeihSerie>
}

const COLORS: Record<string, string> = {
  Servicios: '#2563eb',
  Industria: '#0891b2',
  Agricultura: '#65a30d',
  alta: '#4ade80',
  media: '#fbbf24',
  baja: '#ff6b6b',
}

const CIIU_SECTORES: Record<string, string> = {
  '1': 'Agricultura',
  '47': 'Comercio al por menor',
  '56': 'Restaurantes y bebidas',
  '49': 'Transporte terrestre',
  '41': 'Construcción de edificios',
}

const GEIH_INDICADORES: { key: string; label: string; suffix: string; color: string }[] = [
  { key: 'desempleo_nacional', label: 'Desempleo', suffix: '%', color: '#d4af37' },
  { key: 'informalidad_nacional', label: 'Informalidad', suffix: '%', color: '#f97316' },
  { key: 'salario_promedio_nacional', label: 'Salario promedio', suffix: '', color: '#4ade80' },
]

const TABS: { key: string; label: string; icon: ReactNode }[] = [
  { key: 'sectores', label: 'Sectores', icon: <Icon.Prediccion size={16} /> },
  { key: 'profesiones', label: 'Profesiones', icon: <Icon.Match size={16} /> },
  { key: 'habilidades', label: 'Habilidades', icon: <Icon.PrediccionExito size={16} /> },
  { key: 'salarios', label: 'Salarios', icon: <Icon.EmprendeDinero size={16} /> },
  { key: 'mensual', label: 'Predicción mensual', icon: <Icon.ObservatorioLinea size={16} /> },
]

const pctFmt = (n: number) => `${n > 0 ? '+' : ''}${n.toFixed(1)}%`

const tooltipStyle = {
  contentStyle: { background: '#0a0f1f', border: '1px solid rgba(212,175,55,0.35)', borderRadius: '10px', color: '#e9ecf5', fontSize: '13px' },
  itemStyle: { color: '#e9ecf5' },
  labelStyle: { color: '#d4af37', fontWeight: 700 },
}

export default function Prediccion() {
  const [tab, setTab] = useState('sectores')
  const [data, setData] = useState<PrediccionData | null>(null)
  const [geihData, setGeihData] = useState<GeihData | null>(null)
  const [todosSectores, setTodosSectores] = useState<any[] | null>(null)
  const [todosSectoresMeta, setTodosSectoresMeta] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const load = async () => {
      try {
        const [resumen, sectores, profesiones, habilidades, salarios, geih, todosSec] = await Promise.all([
          api.get('/prediccion/resumen'),
          api.get('/prediccion/sectores'),
          api.get('/prediccion/profesiones'),
          api.get('/prediccion/habilidades'),
          api.get('/prediccion/salarios'),
          api.get('/prediccion/geih').catch(() => null),
          api.get('/prediccion/todos-los-sectores'),
        ])
        setData({
          ...resumen.data,
          sectores: sectores.data,
          otros_indicadores: resumen.data.otros_indicadores || {},
          profesiones: profesiones.data.profesiones,
          habilidades: habilidades.data.habilidades,
          salarios: salarios.data,
        })
        if (geih?.data) setGeihData(geih.data)
        if (todosSec?.data?.sectores) {
          setTodosSectores(todosSec.data.sectores)
          setTodosSectoresMeta({
            periodoHistorico: todosSec.data.periodo_historico,
            anioBaseProyeccion: todosSec.data.anio_base_proyeccion,
            ultimoPeriodo: todosSec.data.ultimo_periodo,
            anioActualIncompleto: todosSec.data.anio_actual_incompleto,
            metodologia: todosSec.data.metodologia,
            baselineEmpleoPct: todosSec.data.baseline_empleo_pct,
          })
        }
      } catch (e) {
        setError('No se pudieron cargar las predicciones. Verifica que el backend esté corriendo.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div className="animate-fade-in space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display flex items-center gap-3">
          <span style={{ color: '#d4af37' }}><Icon.Prediccion size={28} /></span>
          Predicción IA
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Proyecciones del mercado laboral colombiano a 5 y 10 años. Basadas en datos del Banco Mundial con Chronos T5.
        </p>
      </div>

      {loading && (
        <div className="plate card rounded-2xl h-64 flex items-center justify-center">
          <div className="text-slate-500 text-sm flex items-center gap-2">
            <span className="animate-spin inline-block"><Icon.Accion.Buscar size={16} /></span>
            Cargando predicciones...
          </div>
        </div>
      )}

      {error && (
        <div className="plate card rounded-xl p-4 text-rose-400 text-sm border-rose-900/40">
          {error}
        </div>
      )}

      {!loading && !error && data && (
        <>
          {/* Tabs */}
          <div className="plate p-1.5 flex gap-1.5">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-semibold rounded-lg transition-all ${
                  tab === t.key
                    ? 'bg-gradient-to-b from-amber-300/20 to-amber-700/10 text-gold-400 border border-amber-500/50'
                    : 'text-slate-400 hover:text-gold-400 hover:bg-white/[0.04] border border-transparent'
                }`}
              >
                {t.icon}
                {t.label}
              </button>
            ))}
          </div>

          {/* ================= SECTORES (10 macrosectores colombianos) ================= */}
          {tab === 'sectores' && todosSectores && todosSectores.length > 0 && (
            <div className="space-y-5">
              {(() => {
                const COLORS = ['#d4af37', '#3b82f6', '#22c55e', '#a855f7', '#f97316', '#ec4899', '#06b6d4', '#84cc16', '#f59e0b', '#6366f1']

                const barData = [...todosSectores]
                  .sort((a, b) => b.variacion_10y_pct - a.variacion_10y_pct)

                const topEmpleo = [...todosSectores]
                  .sort((a, b) => b.empleo_actual - a.empleo_actual)
                  .slice(0, 6)

                // Construir un solo dataset para el LineChart: cada sector es una columna.
                // Así recharts alinea correctamente las líneas y calcula el dominio del eje Y.
                const allYears = new Set<number>()
                const lineSeries: Record<string, Record<number, number | null>> = {}
                topEmpleo.forEach((s) => {
                  lineSeries[s.sector] = {}
                  s.serie.forEach((p: any) => {
                    allYears.add(p.ano)
                    lineSeries[s.sector][p.ano] = p.empleo
                  })
                })
                const yearsSorted = Array.from(allYears).sort((a, b) => a - b)
                const lineData = yearsSorted.map((y) => {
                  const row: any = { año: y }
                  topEmpleo.forEach((s) => { row[s.sector] = lineSeries[s.sector]?.[y] ?? null })
                  return row
                })

                const anioBase = todosSectoresMeta?.anioBaseProyeccion ?? yearsSorted[yearsSorted.length - 11]
                const ultimoPeriodo = todosSectoresMeta?.ultimoPeriodo
                const periodoHistorico = todosSectoresMeta?.periodoHistorico ?? `${yearsSorted[0]}-${anioBase}`
                const anioInicioHistorico = periodoHistorico.split('-')[0]
                const periodoNota = ultimoPeriodo
                  ? `Último dato GEIH: ${ultimoPeriodo}.`
                  : ''

                return (
                  <>
                    {/* Nota metodológica */}
                    <div className="plate card p-4">
                      <div className="flex items-start gap-3">
                        <span className="mt-0.5 text-gold-400"><Icon.Accion.Info size={18} /></span>
                        <div>
                          <p className="text-sm text-slate-200 font-semibold mb-1">¿Qué muestran estas cifras?</p>
                          <p className="text-xs text-slate-400 leading-relaxed">
                            {periodoNota} Los números son el empleo promedio mensual por macrosector según la GEIH del DANE,
                            agrupado en 10 grandes categorías (89 ramas CIIU). El porcentaje es una proyección conservadora a 10 años
                            desde {anioBase}: 80% crecimiento base del empleo en Colombia (~{todosSectoresMeta?.baselineEmpleoPct ?? 1.8}% anual) más
                            20% de la tendencia sectorial reciente. No es una predicción exacta, es una estimación de dirección y magnitud.
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Crecimiento proyectado */}
                    <div className="plate card p-5">
                      <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
                        <h2 className="text-xl font-bold text-white font-display">Crecimiento proyectado a 10 años</h2>
                        <span className="text-sm text-gold-400 uppercase tracking-wider">GEIH + Chronos T5</span>
                      </div>
                      <p className="text-xs text-slate-500 mb-4">
                        10 macrosectores colombianos. Ordenados por crecimiento esperado {anioBase}-2035.
                      </p>
                      <ResponsiveContainer width="100%" height={380}>
                        <BarChart data={barData} layout="vertical" margin={{ left: 10, right: 60 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                          <XAxis type="number" stroke="#64748b" fontSize={11} tickFormatter={(v) => `+${v}%`} />
                          <YAxis type="category" dataKey="sector" stroke="#94a3b8" fontSize={11} width={180} />
                          <Tooltip
                            contentStyle={{ background: '#0a0f1f', border: '1px solid rgba(212,175,55,0.3)', borderRadius: '10px', color: '#e9ecf5', fontSize: 13 }}
                            formatter={(v: any, name: string, props: any) => {
                              const s = barData.find((x) => x.sector === props.payload.sector)
                              return [`+${v}% → ${compactNum(s?.empleo_10y || 0)} empleos`, 'Proyección 10 años']
                            }}
                          />
                          <Bar dataKey="variacion_10y_pct" radius={[0, 4, 4, 0]}>
                            {barData.map((_, i) => (
                              <Cell key={i} fill={COLORS[i % COLORS.length]} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Tarjetas de todos los sectores */}
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                      {todosSectores.map((s: any, i: number) => (
                        <div key={s.sector} className="plate card p-4 text-center group relative">
                          <p className="text-xs text-slate-400 uppercase tracking-wider mb-3 font-semibold">{s.sector}</p>
                          <div className="space-y-2">
                            <div>
                              <p className="text-xs text-slate-500 mb-1">Empleados en {anioBase}</p>
                              <p className="text-xl font-bold text-white font-display">{s.empleo_actual.toLocaleString('es-CO')}</p>
                            </div>
                            <div>
                              <p className="text-xs text-slate-500 mb-1">Proyección 2035</p>
                              <p className="text-xl font-bold text-white font-display">{s.empleo_10y.toLocaleString('es-CO')}</p>
                            </div>
                            <div className="pt-2 border-t border-gold-500/20">
                              <p className="text-xs text-slate-500 mb-1">Crecimiento</p>
                              <p className="text-lg font-bold" style={{ color: COLORS[i % COLORS.length] }}>
                                +{s.variacion_10y_pct}%
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Evolución temporal top 6 */}
                    <div className="plate card p-5">
                      <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
                        <h2 className="text-xl font-bold text-white font-display">Evolución del empleo (histórico + proyección)</h2>
                        <span className="text-sm text-slate-500">{anioInicioHistorico}-2035</span>
                      </div>
                      <p className="text-xs text-slate-500 mb-4">
                        Línea sólida: histórico GEIH ({periodoHistorico}). Línea punteada después de {anioBase}: proyección. Top 6 sectores por empleo.
                      </p>
                      <ResponsiveContainer width="100%" height={380}>
                        <LineChart data={lineData} margin={{ top: 10, right: 30, left: 10, bottom: 45 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                          <XAxis
                            dataKey="año"
                            stroke="#64748b"
                            fontSize={12}
                            tickMargin={10}
                            interval={1}
                            angle={0}
                          />
                          <YAxis
                            stroke="#64748b"
                            fontSize={12}
                            tickFormatter={(v) => `${(v / 1_000_000).toFixed(1)}M`}
                            width={55}
                          />
                          <Tooltip
                            contentStyle={{ background: '#0a0f1f', border: '1px solid rgba(212,175,55,0.3)', borderRadius: '10px', color: '#e9ecf5', fontSize: 13 }}
                            formatter={(v: number, name: string, props: any) => {
                              const esProyeccion = props?.payload?.año > anioBase
                              return [compactNum(v), `${name}${esProyeccion ? ' (proy.)' : ''}`]
                            }}
                            labelFormatter={(label) => `${label}${Number(label) > anioBase ? ' — proyección' : ''}`}
                          />
                          <ReferenceLine x={anioBase} stroke="#d4af37" strokeDasharray="5 5" label={{ value: 'Proyección →', position: 'insideTopRight', fill: '#d4af37', fontSize: 11 }} />
                          <Legend formatter={(v: string) => <span style={{ color: '#e9ecf5', fontSize: 12 }}>{v}</span>} />
                          {topEmpleo.map((s: any, i: number) => (
                            <Line
                              key={s.sector}
                              type="monotone"
                              dataKey={s.sector}
                              name={s.sector}
                              stroke={COLORS[i]}
                              strokeWidth={2}
                              dot={false}
                              connectNulls
                            />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </>
                )
              })()}
            </div>
          )}

          {/* ================= PROFESIONES ================= */}
          {tab === 'profesiones' && (
            <div className="space-y-5">
              {/* Top 3 destacadas */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {data.profesiones.slice(0, 3).map((p, i) => (
                  <div key={i} className="plate card p-5 relative overflow-hidden">
                    <div className="absolute top-0 right-0 bg-gradient-to-b from-amber-300 to-amber-600 text-[#0a0f1f] text-xs font-bold px-3 py-1 rounded-bl-lg">
                      #{i + 1}
                    </div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-8 h-8 rounded-lg border border-amber-500/40 bg-amber-500/10 flex items-center justify-center text-gold-400">
                        {i === 0 ? <Icon.PrediccionExito size={16} /> : i === 1 ? <Icon.PrediccionUp size={16} /> : <Icon.Match size={16} />}
                      </span>
                      <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">{p.sector}</span>
                    </div>
                    <h3 className="font-bold text-white text-lg mb-3 pr-10">{p.profesion}</h3>
                    <div className="flex items-baseline gap-2 mb-2">
                      <span className="text-3xl font-bold text-green-400 font-display">+{p.crecimiento_10a_pct}%</span>
                      <span className="text-xs text-slate-500">demanda en 10 años</span>
                    </div>
                    <p className="text-sm text-slate-400">Salario hoy: <strong className="text-gold-400">{formatCOP(p.salario_mensual_cop)}</strong></p>
                  </div>
                ))}
              </div>

              {/* Ranking completo */}
              <div className="plate card p-5">
                <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
                  <h2 className="text-xl font-bold text-white font-display flex items-center gap-2">
                    <Icon.Match size={20} /> Ranking completo de profesiones
                  </h2>
                  <span className="text-sm text-gold-400 uppercase tracking-wider font-semibold">{data.profesiones.length} profesiones</span>
                </div>
                <p className="text-sm text-slate-500 mb-4">
                  Crecimiento de <strong className="text-slate-300">demanda laboral</strong> proyectado, no salarial.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead>
                      <tr className="text-xs text-slate-400 uppercase tracking-wider border-b border-white/[0.08]">
                        <th className="px-3 py-3">Profesión</th>
                        <th className="px-3 py-3">Demanda</th>
                        <th className="px-3 py-3 text-right">Crec. 10 años</th>
                        <th className="px-3 py-3 text-right">Salario hoy</th>
                        <th className="px-3 py-3 text-right">Salario 2035</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04]">
                      {data.profesiones.map((p, i) => (
                        <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                          <td className="px-3 py-3">
                            <div className="font-semibold text-slate-200">{p.profesion}</div>
                            <div className="text-xs text-slate-500">{p.sector}</div>
                          </td>
                          <td className="px-3 py-3">
                            <span
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                                p.demanda === 'alta'
                                  ? 'bg-green-500/15 text-green-400 border border-green-500/30'
                                  : p.demanda === 'media'
                                  ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                                  : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                              }`}
                            >
                              {p.demanda === 'alta' ? <Icon.Accion.Arriba size={12} /> : p.demanda === 'baja' ? <Icon.Accion.Abajo size={12} /> : '—'}
                              {p.demanda}
                            </span>
                          </td>
                          <td className={`px-3 py-3 text-right font-bold ${p.crecimiento_10a_pct >= 0 ? 'text-green-400' : 'text-rose-400'}`}>
                            {pctFmt(p.crecimiento_10a_pct)}
                          </td>
                          <td className="px-3 py-3 text-right text-slate-300">{formatCOP(p.salario_mensual_cop)}</td>
                          <td className="px-3 py-3 text-right font-semibold text-white">{formatCOP(p.salario_10a_cop)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ================= HABILIDADES ================= */}
          {tab === 'habilidades' && (
            <div className="space-y-5">
              <div className="plate card p-5">
                <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
                  <h2 className="text-xl font-bold text-white font-display flex items-center gap-2">
                    <Icon.PrediccionExito size={20} /> Top 10 habilidades más demandadas
                  </h2>
                  <span className="text-sm text-gold-400 uppercase tracking-wider font-semibold">WEF</span>
                </div>
                <p className="text-sm text-slate-500 mb-4">
                  Puntuación 0–100. Más alta = más importante para el futuro laboral. Fuente: Future of Jobs del Foro Económico Mundial, adaptado al contexto colombiano.
                </p>
                <ResponsiveContainer width="100%" height={420}>
                  <BarChart
                    data={data.habilidades.slice(0, 10)}
                    layout="vertical"
                    margin={{ left: 10, right: 40, top: 5, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2329" horizontal={false} />
                    <XAxis type="number" domain={[0, 100]} stroke="#475569" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis
                      type="category"
                      dataKey="habilidad"
                      stroke="#c8d0de"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                      width={170}
                    />
                    <Tooltip {...tooltipStyle} formatter={(v: number) => [`${v}/100`, 'Demanda']} cursor={{ fill: '#1e232980' }} />
                    <Bar dataKey="demanda" radius={[0, 6, 6, 0]}>
                      {data.habilidades.slice(0, 10).map((h, i) => (
                        <Cell key={i} fill={h.demanda >= 85 ? COLORS.alta : h.demanda >= 70 ? COLORS.media : COLORS.baja} />
                      ))}
                      <LabelList dataKey="demanda" position="right" fill="#d4af37" fontSize={12} fontWeight={700} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Leyenda de niveles */}
              <div className="grid grid-cols-3 gap-3">
                <div className="plate card p-3 text-center">
                  <div className="w-3 h-3 rounded-full mx-auto mb-1" style={{ backgroundColor: COLORS.alta }} />
                  <p className="text-sm font-bold text-green-400">Alta (85+)</p>
                  <p className="text-xs text-slate-500">Crítico para el futuro</p>
                </div>
                <div className="plate card p-3 text-center">
                  <div className="w-3 h-3 rounded-full mx-auto mb-1" style={{ backgroundColor: COLORS.media }} />
                  <p className="text-sm font-bold text-amber-400">Media (70–84)</p>
                  <p className="text-xs text-slate-500">Muy relevante</p>
                </div>
                <div className="plate card p-3 text-center">
                  <div className="w-3 h-3 rounded-full mx-auto mb-1" style={{ backgroundColor: COLORS.baja }} />
                  <p className="text-sm font-bold text-rose-400">Baja (&lt;70)</p>
                  <p className="text-xs text-slate-500">Importante de reforzar</p>
                </div>
              </div>
            </div>
          )}

          {/* ================= SALARIOS ================= */}
          {tab === 'salarios' && (
            <div className="space-y-4">
              {/* Tabla salarios por profesión */}
              <div className="plate card p-5">
                <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
                  <h2 className="text-xl font-bold text-white font-display flex items-center gap-2">
                    <Icon.EmprendeDinero size={20} /> Proyección salarial por profesión
                  </h2>
                  <span className="text-sm text-gold-400 uppercase tracking-wider font-semibold">Ordenado por salario actual</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead>
                      <tr className="text-xs text-slate-400 uppercase tracking-wider border-b border-white/[0.08]">
                        <th className="px-3 py-3">Profesión</th>
                        <th className="px-3 py-3 text-right">Hoy</th>
                        <th className="px-3 py-3 text-right">2030</th>
                        <th className="px-3 py-3 text-right">2035</th>
                        <th className="px-3 py-3 text-right">Crec. 10 años</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04]">
                      {data.profesiones
                        .slice()
                        .sort((a, b) => b.salario_mensual_cop - a.salario_mensual_cop)
                        .map((p, i) => {
                          const crecSalarial10 = ((p.salario_10a_cop / p.salario_mensual_cop) - 1) * 100
                          return (
                            <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                              <td className="px-3 py-3">
                                <div className="font-semibold text-slate-200">{p.profesion}</div>
                                <div className="text-xs text-slate-500">{p.sector}</div>
                              </td>
                              <td className="px-3 py-3 text-right text-slate-300">{formatCOP(p.salario_mensual_cop)}</td>
                              <td className="px-3 py-3 text-right text-slate-300">{formatCOP(p.salario_5a_cop)}</td>
                              <td className="px-3 py-3 text-right font-semibold text-white">{formatCOP(p.salario_10a_cop)}</td>
                              <td className="px-3 py-3 text-right font-bold text-green-400">+{crecSalarial10.toFixed(1)}%</td>
                            </tr>
                          )
                        })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ================= MENSUAL GEIH ================= */}
          {tab === 'mensual' && (
            <GeihMensual geihData={geihData} />
          )}
        </>
      )}

      <FuentesBadge fuentes={['World Bank Open Data', 'Chronos T5 Small', 'GEIH DANE mensual', 'O*NET', 'ESCO', 'WEF Future of Jobs']} />
    </div>
  )
}

// ===========================================================================
// Componente: GeihMensual — Predicción mensual con Chronos T5 sobre GEIH
// ===========================================================================

type HorizonteKey = 'prediccion_1ano' | 'prediccion_5anos'

function GeihMensual({ geihData }: { geihData: GeihData | null }) {
  const [indicador, setIndicador] = useState('desempleo_nacional')
  const [horizonte, setHorizonte] = useState<HorizonteKey>('prediccion_1ano')
  const [vista, setVista] = useState<'nacional' | 'sector'>('nacional')
  const [sectorSel, setSectorSel] = useState('1')

  if (!geihData) {
    return (
      <div className="plate card rounded-2xl p-8 text-center">
        <div className="text-slate-500 text-sm">
          No hay predicciones mensuales GEIH disponibles. Ejecuta el script de Chronos GEIH para generarlas.
        </div>
      </div>
    )
  }

  const indicadorMeta = GEIH_INDICADORES.find((i) => i.key === indicador)!
  const serie: GeihSerie | undefined =
    vista === 'nacional'
      ? (geihData as any)[indicador] as GeihSerie
      : geihData.sectores[sectorSel]

  if (!serie) {
    return (
      <div className="plate card rounded-2xl p-8 text-center text-slate-500 text-sm">
        Sin datos para esta selección.
      </div>
    )
  }

  const predArr = serie[horizonte]
  const ultimoHist = serie.historico[serie.historico.length - 1]
  const ultimoPred = predArr[predArr.length - 1]
  const primerPred = predArr[0]

  const chartData = [
    ...serie.historico.map((h) => ({
      periodo: h.periodo,
      valor: h.valor ?? null,
      mediana: null as number | null,
      p10: null as number | null,
      p90: null as number | null,
      esPrediccion: false,
    })),
    ...predArr.map((p) => ({
      periodo: p.periodo,
      valor: null as number | null,
      mediana: p.mediana ?? null,
      p10: p.p10 ?? null,
      p90: p.p90 ?? null,
      esPrediccion: true,
    })),
  ]

  const ultimoValor = ultimoHist.valor ?? null
  const valorFinal = ultimoPred.mediana ?? null
  const valorInicialPred = primerPred.mediana ?? null

  const deltaPct = valorFinal != null && valorInicialPred != null && valorInicialPred !== 0
    ? ((valorFinal - valorInicialPred) / Math.abs(valorInicialPred)) * 100
    : null

  const suffix = vista === 'nacional' ? indicadorMeta.suffix : ''
  const colorLinea = vista === 'nacional' ? indicadorMeta.color : '#d4af37'

  const fmtValor = (v: number | null | undefined) => {
    if (v == null) return '—'
    if (vista === 'nacional' && indicador === 'salario_promedio_nacional') return formatCOP(v)
    if (vista === 'sector') return `${Math.round(v).toLocaleString('es-CO')}`
    return `${v.toFixed(1)}${suffix}`
  }

  const tituloIndicador =
    vista === 'nacional'
      ? indicadorMeta.label
      : CIIU_SECTORES[sectorSel] || `Sector CIIU ${sectorSel}`

  const unidadDescripcion =
    vista === 'nacional'
      ? indicador === 'salario_promedio_nacional'
        ? 'salario promedio mensual (COP)'
        : `tasa de ${indicadorMeta.label.toLowerCase()} (%)`
      : 'empleo total (personas)'

  const nomHorizonte = horizonte === 'prediccion_1ano' ? '1 año (12 meses)' : '5 años (60 meses)'

  return (
    <div className="space-y-5">
      {/* Selectores */}
      <div className="plate p-4 flex flex-wrap items-center gap-4">
        <div className="flex gap-1.5">
          <button
            onClick={() => setVista('nacional')}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition-all ${
              vista === 'nacional'
                ? 'bg-gradient-to-b from-amber-300/20 to-amber-700/10 text-gold-400 border border-amber-500/50'
                : 'text-slate-400 hover:text-gold-400 border border-transparent'
            }`}
          >
            Nacional
          </button>
          <button
            onClick={() => setVista('sector')}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition-all ${
              vista === 'sector'
                ? 'bg-gradient-to-b from-amber-300/20 to-amber-700/10 text-gold-400 border border-amber-500/50'
                : 'text-slate-400 hover:text-gold-400 border border-transparent'
            }`}
          >
            Por sector CIIU
          </button>
        </div>

        {vista === 'nacional' ? (
          <div className="flex gap-1.5">
            {GEIH_INDICADORES.map((ind) => (
              <button
                key={ind.key}
                onClick={() => setIndicador(ind.key)}
                className={`px-3 py-2 text-sm font-semibold rounded-lg transition-all ${
                  indicador === ind.key
                    ? 'bg-gradient-to-b from-amber-300/20 to-amber-700/10 text-gold-400 border border-amber-500/50'
                    : 'text-slate-400 hover:text-gold-400 border border-transparent'
                }`}
              >
                {ind.label}
              </button>
            ))}
          </div>
        ) : (
          <select
            value={sectorSel}
            onChange={(e) => setSectorSel(e.target.value)}
            className="bg-[#0a0f1f] text-slate-200 text-sm border border-amber-500/30 rounded-lg px-3 py-2 focus:outline-none focus:border-amber-500/60"
          >
            {Object.entries(CIIU_SECTORES).map(([code, name]) => (
              <option key={code} value={code}>{name}</option>
            ))}
          </select>
        )}

        <div className="flex gap-1.5 ml-auto">
          <button
            onClick={() => setHorizonte('prediccion_1ano')}
            className={`px-3 py-2 text-sm font-semibold rounded-lg transition-all ${
              horizonte === 'prediccion_1ano'
                ? 'bg-gradient-to-b from-amber-300/20 to-amber-700/10 text-gold-400 border border-amber-500/50'
                : 'text-slate-400 hover:text-gold-400 border border-transparent'
            }`}
          >
            1 año
          </button>
          <button
            onClick={() => setHorizonte('prediccion_5anos')}
            className={`px-3 py-2 text-sm font-semibold rounded-lg transition-all ${
              horizonte === 'prediccion_5anos'
                ? 'bg-gradient-to-b from-amber-300/20 to-amber-700/10 text-gold-400 border border-amber-500/50'
                : 'text-slate-400 hover:text-gold-400 border border-transparent'
            }`}
          >
            5 años
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-3">
        <div className="plate card p-4 text-center">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">{geihData.ultimo_periodo_historico}</p>
          <p className="text-2xl font-bold text-white font-display">{fmtValor(ultimoValor)}</p>
          <p className="text-xs text-slate-500 mt-1">Último dato histórico</p>
        </div>
        <div className="plate card p-4 text-center">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">{nomHorizonte}</p>
          <p className="text-2xl font-bold text-gold-400 font-display">{fmtValor(valorFinal)}</p>
          <p className="text-xs text-slate-500 mt-1">Predicción final</p>
        </div>
        <div className="plate card p-4 text-center">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Cambio proyectado</p>
          <p className={`text-2xl font-bold font-display ${deltaPct == null ? 'text-slate-400' : deltaPct >= 0 ? 'text-green-400' : 'text-rose-400'}`}>
            {deltaPct == null ? '—' : `${deltaPct > 0 ? '+' : ''}${deltaPct.toFixed(1)}%`}
          </p>
          <p className="text-xs text-slate-500 mt-1">En {horizonte === 'prediccion_1ano' ? '1 año' : '5 años'}</p>
        </div>
      </div>

      {/* Gráfico de línea con bandas */}
      <div className="plate card p-5">
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
          <h2 className="text-xl font-bold text-white font-display flex items-center gap-2">
            <Icon.ObservatorioLinea size={20} /> {tituloIndicador}
          </h2>
          <span className="text-sm text-gold-400 uppercase tracking-wider font-semibold">Chronos T5 · {nomHorizonte}</span>
        </div>
        <p className="text-sm text-slate-500 mb-4">
          Histórico mensual {serie.historico[0]?.periodo}–{geihData.ultimo_periodo_historico} (línea sólida) ·
          Predicción {predArr[0]?.periodo}–{ultimoPred.periodo} con banda de confianza al 80% (línea punteada).
          Unidad: {unidadDescripcion}.
        </p>
        <ResponsiveContainer width="100%" height={380}>
          <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
            <defs>
              <linearGradient id="geihBandFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={colorLinea} stopOpacity={0.15} />
                <stop offset="100%" stopColor={colorLinea} stopOpacity={0.03} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2329" />
            <XAxis
              dataKey="periodo"
              stroke="#475569"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              interval={Math.max(1, Math.floor(chartData.length / 12))}
              tickFormatter={(v: string) => v}
            />
            <YAxis
              stroke="#475569"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => {
                if (vista === 'nacional' && indicador === 'salario_promedio_nacional') {
                  return `${(v / 1_000_000).toFixed(1)}M`
                }
                if (vista === 'sector') {
                  return `${(v / 1_000_000).toFixed(1)}M`
                }
                return `${v.toFixed(1)}${suffix}`
              }}
              width={70}
            />
            <Tooltip
              {...tooltipStyle}
              formatter={(v: number, name: string) => {
                if (v == null) return ['—', '']
                const labels: Record<string, string> = {
                  valor: 'Histórico',
                  mediana: 'Predicción',
                  p10: 'Mínimo (p10)',
                  p90: 'Máximo (p90)',
                }
                return [fmtValor(v), labels[name] || name]
              }}
            />
            <ReferenceLine
              x={geihData.ultimo_periodo_historico}
              stroke="#d4af37"
              strokeDasharray="5 5"
              label={{ value: 'Predicción', position: 'top', fill: '#d4af37', fontSize: 11 }}
            />
            {/* Banda de confianza */}
            <Area type="monotone" dataKey="p90" stroke="none" fill="url(#geihBandFill)" connectNulls name="p90" />
            <Area type="monotone" dataKey="p10" stroke="none" fill="#0a1226" connectNulls name="p10" />
            {/* Histórico */}
            <Line
              type="monotone"
              dataKey="valor"
              stroke={colorLinea}
              strokeWidth={2.5}
              dot={false}
              connectNulls
              name="valor"
            />
            {/* Predicción */}
            <Line
              type="monotone"
              dataKey="mediana"
              stroke={colorLinea}
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={false}
              connectNulls
              name="mediana"
            />
          </LineChart>
        </ResponsiveContainer>
        <div className="flex items-center justify-center gap-6 mt-3 text-sm flex-wrap">
          <div className="flex items-center gap-2">
            <span className="w-6 h-0.5 rounded" style={{ backgroundColor: colorLinea }} />
            <span className="text-slate-400">Histórico</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-6 h-0.5 rounded border-t-2 border-dashed" style={{ borderColor: colorLinea }} />
            <span className="text-slate-400">Predicción (mediana)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded" style={{ background: `linear-gradient(${colorLinea}20, ${colorLinea}05)` }} />
            <span className="text-slate-400">Banda de confianza (80%)</span>
          </div>
        </div>
      </div>

      {/* Resumen de sectores CIIU disponibles (solo en vista nacional) */}
      {vista === 'nacional' && (
        <div className="plate card p-5">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
            <h2 className="text-lg font-bold text-white font-display flex items-center gap-2">
              <Icon.Match size={18} /> Sectores CIIU con predicción mensual
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {Object.entries(CIIU_SECTORES).map(([code, name]) => {
              const sec = geihData.sectores[code]
              if (!sec) return null
              const histUlt = sec.historico[sec.historico.length - 1]
              const predUlt = sec.prediccion_1ano[sec.prediccion_1ano.length - 1]
              const empHist = histUlt?.valor ?? 0
              const empPred = predUlt?.mediana ?? 0
              const crec = empHist > 0 ? ((empPred - empHist) / empHist) * 100 : 0
              return (
                <button
                  key={code}
                  onClick={() => { setVista('sector'); setSectorSel(code); setHorizonte('prediccion_1ano') }}
                  className="plate card p-3 text-left hover:border-amber-500/40 transition-all group"
                >
                  <p className="text-xs text-slate-500 mb-1">CIIU {code}</p>
                  <p className="text-sm font-semibold text-slate-200 group-hover:text-gold-400 transition-colors">{name}</p>
                  <p className="text-lg font-bold text-white font-display mt-2">{(empPred / 1_000_000).toFixed(2)}M</p>
                  <p className={`text-xs font-medium ${crec >= 0 ? 'text-green-400' : 'text-rose-400'}`}>
                    {crec >= 0 ? '+' : ''}{crec.toFixed(1)}% en 1 año
                  </p>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}