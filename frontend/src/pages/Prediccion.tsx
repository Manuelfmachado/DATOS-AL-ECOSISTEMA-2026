import { useEffect, useState } from 'react'
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, XAxis, YAxis,
  Tooltip, ResponsiveContainer, CartesianGrid, Cell, LabelList,
  ReferenceLine, Legend
} from 'recharts'
import api from '../services/api'
import { formatCOP } from '../utils/format'
import AnalizarIAButton from '../components/AnalizarIAButton'

function compactNum(n: number): string {
  return Math.round(n).toLocaleString('es-CO')
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

interface SalarioReal {
  oficio_codigo: number
  oficio_nombre?: string
  salario_promedio: number
  salario_mediano: number
  empleo_total: number
  ocupados_muestra: number
  periodo: string
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


const COLORS: Record<string, string> = {
  Servicios: '#2563eb',
  Industria: '#0891b2',
  Agricultura: '#65a30d',
  alta: '#4ade80',
  media: '#fbbf24',
  baja: '#ff6b6b',
}

const TABS: { key: string; label: string }[] = [
  { key: 'sectores', label: 'Sectores' },
  { key: 'profesiones', label: 'Profesiones' },
  { key: 'habilidades', label: 'Habilidades' },
  { key: 'salarios', label: 'Salarios' },
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
  const [todosSectores, setTodosSectores] = useState<any[] | null>(null)
  const [todosSectoresMeta, setTodosSectoresMeta] = useState<any>(null)
  const [salariosReales, setSalariosReales] = useState<SalarioReal[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const load = async () => {
      try {
        const [resumen, sectores, profesiones, habilidades, salarios, todosSec, salariosReal] = await Promise.all([
          api.get('/prediccion/resumen'),
          api.get('/prediccion/sectores'),
          api.get('/prediccion/profesiones'),
          api.get('/prediccion/habilidades'),
          api.get('/prediccion/salarios'),
          api.get('/prediccion/todos-los-sectores'),
          api.get('/prediccion/salarios-reales?limit=50&ordenar_por=empleo_total').catch(() => null),
        ])
        setData({
          ...resumen.data,
          sectores: sectores.data,
          otros_indicadores: resumen.data.otros_indicadores || {},
          profesiones: profesiones.data.profesiones,
          habilidades: habilidades.data.habilidades,
          salarios: salarios.data,
        })
        if (salariosReal?.data?.ocupaciones) {
          setSalariosReales(salariosReal.data.ocupaciones)
        }
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
        <h1 className="text-5xl font-bold text-white font-display">
          Predicción IA
        </h1>
        <p className="text-base text-white font-semibold mt-1">
          Proyecciones del mercado laboral colombiano a 5 y 10 años. Basadas en datos del Banco Mundial con Chronos T5.
        </p>
      </div>

      {loading && (
        <div className="plate card rounded-2xl h-64 flex items-center justify-center">
          <div className="text-slate-500 text-sm">
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
                className={`flex-1 py-3 text-xl font-bold rounded-lg transition-all ${
                  tab === t.key
                    ? 'bg-gradient-to-b from-amber-300/20 to-amber-700/10 text-white border border-amber-500/50'
                    : 'text-white hover:text-gold-400 hover:bg-white/[0.04] border border-transparent'
                }`}
              >
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
                        
                        <div>
                          <p className="text-sm text-slate-200 font-semibold mb-1">¿Qué muestran estas cifras?</p>
                          <p className="text-xs text-slate-400 leading-relaxed">
                            Empleo por macrosector según la GEIH del DANE. La proyección a 10 años combina el crecimiento base del empleo y la tendencia sectorial reciente.
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Crecimiento proyectado */}
                    <div className="plate card p-5">
                      <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
                        <h2 className="text-2xl font-bold text-white font-display">Crecimiento proyectado a 10 años</h2>
                        <div className="flex items-center gap-3">
                          <AnalizarIAButton
                            dashboard="prediccion"
                            widgetTitle="Crecimiento proyectado a 10 años"
                            widgetType="grafico"
                            data={barData}
                            filters={{ anioBase, periodoHistorico }}
                          />
                          <span className="text-sm text-gold-400 uppercase tracking-wider">GEIH + Chronos T5</span>
                        </div>
                      </div>
                      <p className="text-xs text-slate-500 mb-4">
                        10 macrosectores colombianos. Ordenados por crecimiento esperado {anioBase}-2035.
                      </p>
                      <ResponsiveContainer width="100%" height={380}>
                        <BarChart data={barData} layout="vertical" margin={{ left: 10, right: 60 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                          <XAxis type="number" stroke="#cbd5e1" fontSize={12} fontWeight={600} tickFormatter={(v) => `+${v}%`} />
                          <YAxis type="category" dataKey="sector" stroke="#e2e8f0" fontSize={12} fontWeight={600} width={180} />
                          <Tooltip
                            contentStyle={{ background: '#0a0f1f', border: '1px solid rgba(212,175,55,0.3)', borderRadius: '10px', color: '#e9ecf5', fontSize: 14, fontWeight: 600 }}
                            formatter={(v: any, name: string, props: any) => {
                              const s = barData.find((x) => x.sector === props.payload.sector)
                              return [`+${v}% en 10 años → ${compactNum(s?.empleo_10y || 0)} empleos`, 'Crecimiento 2025-2035']
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
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {todosSectores.map((s: any, i: number) => (
                        <div key={s.sector} className="plate card p-6 text-center group relative">
                          <p className="text-2xl font-bold text-white mb-4 font-display">{s.sector}</p>
                          <div className="space-y-4">
                            <div className="flex flex-col">
                              <p className="text-sm text-slate-200 uppercase tracking-wider mb-1 font-semibold">Empleados en {anioBase}</p>
                              <p className="text-3xl font-bold text-gold-400 font-display">{Math.round(s.empleo_actual).toLocaleString('es-CO')}</p>
                            </div>
                            <div className="flex flex-col">
                              <p className="text-sm text-slate-200 uppercase tracking-wider mb-1 font-semibold">Proyección 2035</p>
                              <p className="text-3xl font-bold text-gold-400 font-display">{Math.round(s.empleo_10y).toLocaleString('es-CO')}</p>
                            </div>
                            <div className="pt-4 border-t border-gold-500/20">
                              <p className="text-sm text-slate-200 uppercase tracking-wider mb-1 font-semibold">Crecimiento</p>
                              <p className="text-2xl font-bold" style={{ color: COLORS[i % COLORS.length] }}>
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
                        <h2 className="text-2xl font-bold text-white font-display">Evolución del empleo (histórico + proyección)</h2>
                        <div className="flex items-center gap-3">
                          <AnalizarIAButton
                            dashboard="prediccion"
                            widgetTitle="Evolución del empleo histórico + proyección"
                            widgetType="grafico"
                            data={lineData}
                            filters={{ anioBase, periodoHistorico }}
                          />
                          <span className="text-sm text-slate-500">{anioInicioHistorico}-2035</span>
                        </div>
                      </div>
                      <p className="text-xs text-slate-500 mb-4">
                        Línea sólida: histórico GEIH ({periodoHistorico}). Línea punteada después de {anioBase}: proyección. Top 6 sectores por empleo.
                      </p>
                      <ResponsiveContainer width="100%" height={380}>
                        <LineChart data={lineData} margin={{ top: 10, right: 30, left: 10, bottom: 45 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                          <XAxis
                            dataKey="año"
                            stroke="#cbd5e1"
                            fontSize={13}
                            fontWeight={600}
                            tickMargin={10}
                            interval={1}
                            angle={0}
                          />
                          <YAxis
                            stroke="#cbd5e1"
                            fontSize={13}
                            fontWeight={600}
                            tickFormatter={(v) => Math.round(v).toLocaleString('es-CO')}
                            width={60}
                          />
                          <Tooltip
                            contentStyle={{ background: '#0a0f1f', border: '1px solid rgba(212,175,55,0.3)', borderRadius: '10px', color: '#e9ecf5', fontSize: 14, fontWeight: 600 }}
                            formatter={(v: number, name: string, props: any) => {
                              const esProyeccion = props?.payload?.año > anioBase
                              return [compactNum(v), `${name}${esProyeccion ? ' (proy.)' : ''}`]
                            }}
                            labelFormatter={(label) => `${label}${Number(label) > anioBase ? ' — proyección' : ''}`}
                          />
                          <ReferenceLine x={anioBase} stroke="#d4af37" strokeDasharray="5 5" label={{ value: 'Proyección →', position: 'insideTopRight', fill: '#d4af37', fontSize: 12, fontWeight: 700 }} />
                          <Legend formatter={(v: string) => <span style={{ color: '#e9ecf5', fontSize: 13, fontWeight: 600 }}>{v}</span>} />
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
              {/* Nota metodológica */}
              <div className="plate card p-4">
                <div className="flex items-start gap-3">
                  
                  <div>
                    <p className="text-sm text-slate-200 font-semibold mb-1">¿Qué muestran estas cifras?</p>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Profesiones con mayor proyección de demanda laboral. El crecimiento es de demanda, no salarial. Fuentes: O*NET, ESCO y WEF Future of Jobs.
                    </p>
                  </div>
                </div>
              </div>

              {/* Gráfico de crecimiento de demanda */}
              <div className="plate card p-5">
                <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
                  <h2 className="text-2xl font-bold text-white font-display">Crecimiento de demanda a 10 años</h2>
                  <div className="flex items-center gap-3">
                    <AnalizarIAButton
                      dashboard="prediccion"
                      widgetTitle="Crecimiento de demanda a 10 años"
                      widgetType="grafico"
                      data={data.profesiones.slice(0, 10)}
                    />
                    <span className="text-sm text-gold-400 uppercase tracking-wider">O*NET + ESCO + WEF</span>
                  </div>
                </div>
                <p className="text-xs text-slate-500 mb-4">
                  Top 10 profesiones ordenadas por crecimiento esperado de demanda 2025-2035.
                </p>
                <ResponsiveContainer width="100%" height={380}>
                  <BarChart data={data.profesiones.slice(0, 10)} layout="vertical" margin={{ left: 10, right: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                    <XAxis type="number" stroke="#64748b" fontSize={11} tickFormatter={(v) => `+${v}%`} />
                    <YAxis type="category" dataKey="profesion" stroke="#94a3b8" fontSize={11} width={200} />
                    <Tooltip
                      contentStyle={{ background: '#0a0f1f', border: '1px solid rgba(212,175,55,0.3)', borderRadius: '10px', color: '#e9ecf5', fontSize: 13 }}
                      formatter={(v: any, name: string, props: any) => {
                        const p = data.profesiones.find((x) => x.profesion === props.payload.profesion)
                        return [`+${v}% demanda → ${formatCOP(p?.salario_10a_cop || 0)}/mes en 2035`, 'Proyección 10 años']
                      }}
                    />
                    <Bar dataKey="crecimiento_10a_pct" radius={[0, 4, 4, 0]}>
                      {data.profesiones.slice(0, 10).map((p, i) => (
                        <Cell key={i} fill={p.demanda === 'alta' ? COLORS.alta : p.demanda === 'media' ? COLORS.media : COLORS.baja} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Tarjetas top 3 */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {data.profesiones.slice(0, 3).map((p, i) => (
                  <div key={i} className="plate card p-5 relative overflow-hidden">
                    <div className="absolute top-0 right-0 bg-gradient-to-b from-amber-300 to-amber-600 text-[#0a0f1f] text-xs font-bold px-3 py-1 rounded-bl-lg">
                      #{i + 1}
                    </div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-8 h-8 rounded-lg border border-amber-500/40 bg-amber-500/10 flex items-center justify-center text-gold-400">
                        {true ? "" : ""}
                      </span>
                      <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">{p.sector}</span>
                    </div>
                    <h3 className="font-bold text-white text-lg mb-3 pr-10">{p.profesion}</h3>
                    <div className="space-y-2">
                      <div>
                        <p className="text-xs text-slate-500 mb-1">Crecimiento de demanda</p>
                        <p className="text-2xl font-bold text-green-400 font-display">+{p.crecimiento_10a_pct}%</p>
                        <p className="text-xs text-slate-500">en 10 años (2025-2035)</p>
                      </div>
                      <div className="pt-2 border-t border-gold-500/20">
                        <p className="text-xs text-slate-500 mb-1">Salario mensual 2025</p>
                        <p className="text-xl font-bold text-gold-400 font-display">${Math.round(p.salario_mensual_cop).toLocaleString("es-CO")}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Ranking completo */}
              <div className="plate card p-5">
                <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
                  <h2 className="text-2xl font-bold text-white font-display flex items-center gap-2">
                     Ranking completo de profesiones
                  </h2>
                  <div className="flex items-center gap-3">
                    <AnalizarIAButton
                      dashboard="prediccion"
                      widgetTitle="Ranking completo de profesiones"
                      widgetType="tabla"
                      data={data.profesiones}
                    />
                    <span className="text-sm text-gold-400 uppercase tracking-wider font-semibold">{data.profesiones.length} profesiones</span>
                  </div>
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
                        <th className="px-3 py-3 text-right">Salario 2025</th>
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
                              {'—'}
                              {p.demanda}
                            </span>
                          </td>
                          <td className={`px-3 py-3 text-right font-bold ${p.crecimiento_10a_pct >= 0 ? 'text-green-400' : 'text-rose-400'}`}>
                            {pctFmt(p.crecimiento_10a_pct)}
                          </td>
                          <td className="px-3 py-3 text-right text-slate-300">${Math.round(p.salario_mensual_cop).toLocaleString("es-CO")}</td>
                          <td className="px-3 py-3 text-right font-semibold text-white">${Math.round(p.salario_10a_cop).toLocaleString("es-CO")}</td>
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
              {/* Nota metodológica */}
              <div className="plate card p-4">
                <div className="flex items-start gap-3">
                  
                  <div>
                    <p className="text-sm text-slate-200 font-semibold mb-1">¿Qué muestran estas cifras?</p>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Habilidades más demandadas para el futuro laboral. Puntuación de 0 a 100 según el WEF Future of Jobs Report, adaptado al contexto colombiano.
                    </p>
                  </div>
                </div>
              </div>

              {/* Gráfico de habilidades */}
              <div className="plate card p-5">
                <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
                  <h2 className="text-2xl font-bold text-white font-display flex items-center gap-2">
                     Top 10 habilidades más demandadas
                  </h2>
                  <div className="flex items-center gap-3">
                    <AnalizarIAButton
                      dashboard="prediccion"
                      widgetTitle="Top 10 habilidades más demandadas"
                      widgetType="grafico"
                      data={data.habilidades.slice(0, 10)}
                    />
                    <span className="text-sm text-gold-400 uppercase tracking-wider font-semibold">WEF Future of Jobs</span>
                  </div>
                </div>
                <p className="text-sm text-slate-500 mb-4">
                  Puntuación 0–100. Más alta = más importante para el futuro laboral.
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

              {/* Tarjetas de niveles */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="plate card p-4 text-center">
                  <div className="w-3 h-3 rounded-full mx-auto mb-2" style={{ backgroundColor: COLORS.alta }} />
                  <p className="text-sm font-bold text-green-400 mb-1">Alta (85+)</p>
                  <p className="text-xs text-slate-500">Crítico para el futuro</p>
                  <p className="text-xs text-slate-400 mt-2">
                    {data.habilidades.filter(h => h.demanda >= 85).length} habilidades
                  </p>
                </div>
                <div className="plate card p-4 text-center">
                  <div className="w-3 h-3 rounded-full mx-auto mb-2" style={{ backgroundColor: COLORS.media }} />
                  <p className="text-sm font-bold text-amber-400 mb-1">Media (70–84)</p>
                  <p className="text-xs text-slate-500">Muy relevante</p>
                  <p className="text-xs text-slate-400 mt-2">
                    {data.habilidades.filter(h => h.demanda >= 70 && h.demanda < 85).length} habilidades
                  </p>
                </div>
                <div className="plate card p-4 text-center">
                  <div className="w-3 h-3 rounded-full mx-auto mb-2" style={{ backgroundColor: COLORS.baja }} />
                  <p className="text-sm font-bold text-rose-400 mb-1">Baja (&lt;70)</p>
                  <p className="text-xs text-slate-500">Importante de reforzar</p>
                  <p className="text-xs text-slate-400 mt-2">
                    {data.habilidades.filter(h => h.demanda < 70).length} habilidades
                  </p>
                </div>
              </div>

              {/* Tabla completa */}
              <div className="plate card p-5">
                <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
                  <h2 className="text-2xl font-bold text-white font-display flex items-center gap-2">
                     Ranking completo de habilidades
                  </h2>
                  <div className="flex items-center gap-3">
                    <AnalizarIAButton
                      dashboard="prediccion"
                      widgetTitle="Ranking completo de habilidades"
                      widgetType="tabla"
                      data={data.habilidades}
                    />
                    <span className="text-sm text-gold-400 uppercase tracking-wider font-semibold">{data.habilidades.length} habilidades</span>
                  </div>
                </div>
                <p className="text-sm text-slate-500 mb-4">
                  Todas las habilidades evaluadas según su importancia para el mercado laboral futuro.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead>
                      <tr className="text-xs text-slate-400 uppercase tracking-wider border-b border-white/[0.08]">
                        <th className="px-3 py-3">#</th>
                        <th className="px-3 py-3">Habilidad</th>
                        <th className="px-3 py-3">Nivel</th>
                        <th className="px-3 py-3 text-right">Puntuación</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04]">
                      {data.habilidades.map((h, i) => (
                        <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                          <td className="px-3 py-3 text-slate-500 font-mono">{i + 1}</td>
                          <td className="px-3 py-3">
                            <div className="font-semibold text-slate-200">{h.habilidad}</div>
                          </td>
                          <td className="px-3 py-3">
                            <span
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                                h.demanda >= 85
                                  ? 'bg-green-500/15 text-green-400 border border-green-500/30'
                                  : h.demanda >= 70
                                  ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                                  : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                              }`}
                            >
                              {h.demanda >= 85 ? 'Alta' : h.demanda >= 70 ? 'Media' : 'Baja'}
                            </span>
                          </td>
                          <td className="px-3 py-3 text-right font-bold text-gold-400">{h.demanda}/100</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ================= SALARIOS ================= */}
          {tab === 'salarios' && (
            <div className="space-y-5">
              {/* Nota metodológica */}
              <div className="plate card p-4">
                <div className="flex items-start gap-3">
                  
                  <div>
                    <p className="text-sm text-slate-200 font-semibold mb-1">¿Qué muestran estas cifras?</p>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Proyección salarial mensual por profesión en pesos colombianos. Basada en GEIH del DANE con crecimiento real anual del 3.5%.
                    </p>
                  </div>
                </div>
              </div>

              {/* Gráfico de salarios */}
              <div className="plate card p-5">
                <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
                  <h2 className="text-2xl font-bold text-white font-display flex items-center gap-2">
                     Proyección salarial por profesión
                  </h2>
                  <div className="flex items-center gap-3">
                    <AnalizarIAButton
                      dashboard="prediccion"
                      widgetTitle="Proyección salarial por profesión"
                      widgetType="grafico"
                      data={data.profesiones.slice(0, 10).sort((a, b) => b.salario_mensual_cop - a.salario_mensual_cop)}
                    />
                    <span className="text-sm text-gold-400 uppercase tracking-wider font-semibold">GEIH + 3.5% anual</span>
                  </div>
                </div>
                <p className="text-xs text-slate-500 mb-4">
                  Top 10 profesiones ordenadas por salario mensual en 2025. Proyección a 2035 con crecimiento real del 3.5% anual.
                </p>
                <ResponsiveContainer width="100%" height={380}>
                  <BarChart data={data.profesiones.slice(0, 10).sort((a, b) => b.salario_mensual_cop - a.salario_mensual_cop)} layout="vertical" margin={{ left: 10, right: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                    <XAxis type="number" stroke="#64748b" fontSize={11} tickFormatter={(v) => `$${Math.round(v).toLocaleString("es-CO")}`} />
                    <YAxis type="category" dataKey="profesion" stroke="#94a3b8" fontSize={11} width={200} />
                    <Tooltip
                      contentStyle={{ background: '#0a0f1f', border: '1px solid rgba(212,175,55,0.3)', borderRadius: '10px', color: '#e9ecf5', fontSize: 13 }}
                      formatter={(v: any, name: string) => {
                        const label = name === 'Salario 2035' ? 'Salario proyectado 2035' : 'Salario actual 2025'
                        return [formatCOP(v), label]
                      }}
                    />
                    <Legend formatter={(v: string) => <span style={{ color: '#e9ecf5', fontSize: 12 }}>{v}</span>} />
                    <Bar dataKey="salario_mensual_cop" name="Salario 2025" fill="#d4af37" radius={[0, 4, 4, 0]} />
                    <Bar dataKey="salario_10a_cop" name="Salario 2035" fill="#4ade80" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Tarjetas de salarios */}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                {data.profesiones.slice(0, 10).sort((a, b) => b.salario_mensual_cop - a.salario_mensual_cop).map((p, i) => {
                  const crecSalarial10 = ((p.salario_10a_cop / p.salario_mensual_cop) - 1) * 100
                  return (
                    <div key={i} className="plate card p-4 text-center">
                      <p className="text-sm font-bold text-white mb-2">{p.profesion}</p>
                      <div className="space-y-2">
                        <div>
                          <p className="text-xs text-slate-500 mb-1">Salario 2025</p>
                          <p className="text-base font-bold text-gold-400 font-display">${Math.round(p.salario_mensual_cop).toLocaleString("es-CO")}</p>
                        </div>
                        <div>
                          <p className="text-xs text-slate-500 mb-1">Salario 2035</p>
                          <p className="text-base font-bold text-white font-display">${Math.round(p.salario_10a_cop).toLocaleString("es-CO")}</p>
                        </div>
                        <div className="pt-2 border-t border-gold-500/20">
                          <p className="text-xs text-slate-500 mb-1">Crecimiento</p>
                          <p className="text-base font-bold text-green-400">
                            +{crecSalarial10.toFixed(1)}%
                          </p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Tabla completa */}
              <div className="plate card p-5">
                <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
                  <h2 className="text-2xl font-bold text-white font-display flex items-center gap-2">
                     Ranking completo de salarios
                  </h2>
                  <div className="flex items-center gap-3">
                    <AnalizarIAButton
                      dashboard="prediccion"
                      widgetTitle="Ranking completo de salarios"
                      widgetType="tabla"
                      data={data.profesiones.slice().sort((a, b) => b.salario_mensual_cop - a.salario_mensual_cop)}
                    />
                    <span className="text-sm text-gold-400 uppercase tracking-wider font-semibold">Ordenado por salario 2025</span>
                  </div>
                </div>
                <p className="text-sm text-slate-500 mb-4">
                  Todas las profesiones con proyección salarial a 5 y 10 años.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead>
                      <tr className="text-xs text-slate-400 uppercase tracking-wider border-b border-white/[0.08]">
                        <th className="px-3 py-3">Profesión</th>
                        <th className="px-3 py-3 text-right">Salario 2025</th>
                        <th className="px-3 py-3 text-right">Salario 2030</th>
                        <th className="px-3 py-3 text-right">Salario 2035</th>
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
                              <td className="px-3 py-3 text-right text-slate-300">${Math.round(p.salario_mensual_cop).toLocaleString("es-CO")}</td>
                              <td className="px-3 py-3 text-right text-slate-300">${Math.round(p.salario_5a_cop).toLocaleString("es-CO")}</td>
                              <td className="px-3 py-3 text-right font-semibold text-white">${Math.round(p.salario_10a_cop).toLocaleString("es-CO")}</td>
                              <td className="px-3 py-3 text-right font-bold text-green-400">+{crecSalarial10.toFixed(1)}%</td>
                            </tr>
                          )
                        })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Salarios reales del DANE GEIH (406 ocupaciones) */}
              {salariosReales && salariosReales.length > 0 && (
                <div className="plate card p-5">
                  <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
<h2 className="text-2xl font-bold text-white font-display flex items-center gap-2">
                       Salarios reales por ocupación — DANE GEIH
                    </h2>
                    <div className="flex items-center gap-3">
                      <AnalizarIAButton
                        dashboard="prediccion"
                        widgetTitle="Salarios reales por ocupación DANE GEIH"
                        widgetType="tabla"
                        data={salariosReales}
                      />
                      <span className="text-sm text-green-400 uppercase tracking-wider font-semibold">{salariosReales.length} ocupaciones</span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500 mb-4">
                    Datos oficiales de la Gran Encuesta Integrada de Hogares (GEIH) del DANE — {salariosReales[0]?.periodo}.
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead>
                        <tr className="text-xs text-slate-400 uppercase tracking-wider border-b border-white/[0.08]">
                          <th className="px-3 py-3">Ocupación</th>
                          <th className="px-3 py-3 text-right">Salario promedio</th>
                          <th className="px-3 py-3 text-right">Salario mediano</th>
                          <th className="px-3 py-3 text-right">Empleo total</th>
                          <th className="px-3 py-3 text-right">Muestra</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.04]">
                        {salariosReales.map((s, i) => (
                          <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                            <td className="px-3 py-3 font-semibold text-slate-200">{s.oficio_nombre || s.oficio_codigo}</td>
                            <td className="px-3 py-3 text-right text-gold-400 font-semibold">${Math.round(s.salario_promedio).toLocaleString('es-CO')}</td>
                            <td className="px-3 py-3 text-right text-slate-300">${Math.round(s.salario_mediano).toLocaleString('es-CO')}</td>
                            <td className="px-3 py-3 text-right text-slate-300">{Math.round(s.empleo_total).toLocaleString('es-CO')}</td>
                            <td className="px-3 py-3 text-right text-slate-500">{s.ocupados_muestra}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

        </>
      )}

    </div>
  )
}

