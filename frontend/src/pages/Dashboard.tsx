import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import MapaColombia, { type DeptoData } from '../components/MapaColombia'
import { formatCOP, formatCOPFull } from '../utils/format'
import albaRostroSvg from '../../SVG/ALBA ROSTRO.svg'

interface ProfesionDesempleo {
  profesion: string
  sector?: string
  riesgo_desempleo: number
  crecimiento_5a_pct?: number
}

interface ProfesionDemanda {
  profesion: string
  sector?: string
  demanda_score: number
}

interface SectorCrecimiento {
  sector: string
  crecimiento_2035_pct: number
  participacion_2025: number
  participacion_2035: number
}

interface DeptoInsights {
  departamento: string
  tasa_desempleo: number
  ingreso_promedio: number
  profesiones_mas_desempleo: ProfesionDesempleo[]
  profesiones_mas_demandadas: ProfesionDemanda[]
  sectores_mayor_crecimiento: SectorCrecimiento[]
}

const TableCard = ({
  title,
  rows,
  col1,
  col2,
  compact = false,
}: {
  title: string
  rows: { label: string; value: string; sub?: string; help?: string }[]
  col1: string
  col2: string
  compact?: boolean
}) => (
  <div className="executive-card rounded-xl p-3 gold-glow-border border-gold-top">
    <div className="mb-2">
      <h3 className="text-xs font-semibold text-gold-400 uppercase tracking-wider leading-tight">{title}</h3>
    </div>
    <div className="space-y-0">
      {rows.map((row, i) => (
        <div
          key={i}
          className="grid grid-cols-[1fr_auto] gap-2 py-1.5 px-1.5 rounded-lg text-xs transition-colors hover:bg-white/[0.02]"
          title={row.help || row.label}
        >
          <div className="min-w-0">
            <span className="block text-slate-300 break-words leading-tight">{row.label}</span>
            {!compact && row.sub && <span className="block text-[10px] text-slate-500 break-words leading-tight">{row.sub}</span>}
          </div>
          <span className="text-right whitespace-nowrap font-semibold text-slate-200 pl-2">
            {row.value}
          </span>
        </div>
      ))}
    </div>
  </div>
)

export default function Dashboard() {
  const [departamentos, setDepartamentos] = useState<DeptoData[]>([])
  const [sectorLiderNacional, setSectorLiderNacional] = useState<{ sector: string; crecimiento_2035_pct: number } | null>(null)
  const [hoveredDepto, setHoveredDepto] = useState<DeptoData | null>(null)
  const [selectedDepto, setSelectedDepto] = useState<DeptoData | null>(null)
  const [insights, setInsights] = useState<DeptoInsights | null>(null)
  const [insightsLoading, setInsightsLoading] = useState(false)
  const [resumenNacional, setResumenNacional] = useState<any>(null)
  const [loadingMapa, setLoadingMapa] = useState(true)
  const [loadingRankings, setLoadingRankings] = useState(true)
  const [loadingKpis, setLoadingKpis] = useState(true)

  useEffect(() => {
    // Cargar datos del mapa desde la API (datos completos), fallback a JSON estatico
    api.get('/observatorio/dashboard')
      .then((res) => res.data)
      .catch(() => fetch('/dashboard.json').then((res) => res.ok ? res.json() : Promise.reject('no static')))
      .then((d: any) => {
        setResumenNacional(d.resumen_nacional || null)
        const data = d.mapa?.departamentos || []
        const mapa = new Map<string, DeptoData>()
        data.forEach((depto: any) => { mapa.set(depto.departamento, depto) })
        setDepartamentos(Array.from(mapa.values()))
        setSectorLiderNacional(d.mapa?.sector_lider_nacional || null)
        setLoadingMapa(false)
        setLoadingRankings(false)
        setLoadingKpis(false)
      })
      .catch(() => {})
      .finally(() => {
        setLoadingMapa(false)
        setLoadingRankings(false)
        setLoadingKpis(false)
      })
  }, [])

  const loading = loadingMapa && loadingRankings && loadingKpis

  useEffect(() => {
    if (!selectedDepto?.departamento) {
      setInsights(null)
      return
    }
    const depto = selectedDepto.departamento
    setInsightsLoading(true)
    api.get(`/observatorio/departamento-insights/${encodeURIComponent(depto)}`)
      .then(res => {
        setInsights(res.data)
      })
      .catch(() => setInsights(null))
      .finally(() => setInsightsLoading(false))
  }, [selectedDepto?.departamento])

  const profesionesDesempleoRows = useMemo(() => {
    return (insights?.profesiones_mas_desempleo || []).map(p => ({
      label: p.profesion,
      value: `${p.riesgo_desempleo.toFixed(0)}/100`,
      help: `Crecimiento proyectado a 5 años: ${p.crecimiento_5a_pct?.toFixed(1) ?? 'N/D'}%.`,
    }))
  }, [insights])

  const profesionesDemandaRows = useMemo(() => {
    return (insights?.profesiones_mas_demandadas || []).map(p => ({
      label: p.profesion,
      value: `+${p.demanda_score.toFixed(1)}%`,
      help: `Se espera que las oportunidades de empleo crezcan ${p.demanda_score.toFixed(1)}% en los próximos 5 años.`,
    }))
  }, [insights])

  const sectoresRows = useMemo(() => {
    return (insights?.sectores_mayor_crecimiento || []).map(s => ({
      label: s.sector,
      value: `${s.crecimiento_2035_pct >= 0 ? '+' : ''}${s.crecimiento_2035_pct.toFixed(1)}%`,
      sub: `${s.participacion_2025.toFixed(1)}% del empleo hoy → ${s.participacion_2035.toFixed(1)}% en 2035`,
      help: `Participación sectorial proyectada: de ${s.participacion_2025.toFixed(1)}% a ${s.participacion_2035.toFixed(1)}% para 2035.`,
    }))
  }, [insights])

  // Rankings nacionales calculados desde los datos del mapa
  const rankingNacional = useMemo(() => {
    if (!departamentos.length) return null
    const conDesempleo = departamentos.filter(d => d.tasa_desempleo != null)
    const conIngreso = departamentos.filter(d => d.ingreso_promedio != null && d.ingreso_promedio > 0)
    const conInformalidad = departamentos.filter(d => d.tasa_formalidad != null)

    const mejorDesempleo = [...conDesempleo].sort((a, b) => (a.tasa_desempleo! - b.tasa_desempleo!)).slice(0, 3)
    const peorDesempleo = [...conDesempleo].sort((a, b) => (b.tasa_desempleo! - a.tasa_desempleo!)).slice(0, 3)
    const mejorIngreso = [...conIngreso].sort((a, b) => (b.ingreso_promedio! - a.ingreso_promedio!)).slice(0, 3)
    const peorIngreso = [...conIngreso].sort((a, b) => (a.ingreso_promedio! - b.ingreso_promedio!)).slice(0, 3)
    const masFormal = [...conInformalidad].sort((a, b) => (b.tasa_formalidad! - a.tasa_formalidad!)).slice(0, 3)
    const masInformal = [...conInformalidad].sort((a, b) => (a.tasa_formalidad! - b.tasa_formalidad!)).slice(0, 3)

    // Promedios nacionales
    const promDesempleo = conDesempleo.reduce((s, d) => s + (d.tasa_desempleo || 0), 0) / conDesempleo.length
    const promIngreso = conIngreso.reduce((s, d) => s + (d.ingreso_promedio || 0), 0) / conIngreso.length
    const promFormalidad = conInformalidad.reduce((s, d) => s + (d.tasa_formalidad || 0), 0) / conInformalidad.length

    return {
      mejorDesempleo, peorDesempleo, mejorIngreso, peorIngreso,
      masFormal, masInformal,
      promDesempleo, promIngreso, promFormalidad,
    }
  }, [departamentos])

  return (
    <>
      {/* Top bar */}
      <header className="topbar">
        <div className="flex items-center gap-4 w-full">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-4">
              <h1 className="text-5xl font-bold text-white font-display">Bienvenido a ALBA</h1>
              <img src={albaRostroSvg} alt="Sol ALBA" className="flex-shrink-0" style={{ width: 60, height: 60 }} />
            </div>
            <p className="hello-sub">
              <span className="text-2xl text-gold-400 font-bold font-display">A</span>nalítica{' '}
              <span className="text-gold-400 font-bold font-display">L</span>aboral{' '}
              <span className="text-gold-400 font-bold font-display">B</span>asada en{' '}
              <span className="text-gold-400 font-bold font-display">IA</span>
            </p>
          </div>
        </div>

      </header>

      {/* Flujo ALBA */}
      <section className="flujo-alba">
        {[
          { to: '/observatorio', label: 'Observar', desc: '' },
          { to: '/observatorio', label: 'Analizar', desc: '' },
          { to: '/prediccion', label: 'Predecir', desc: '' },
          { to: '/emprende', label: 'Decidir', desc: '' },
          { to: '/coach', label: 'Mejorar', desc: '' },
        ].map((paso, i, arr) => (
          <div key={paso.label} className="flujo-paso">
            <Link to={paso.to} className="flujo-card">
              <div className="flujo-label">{paso.label}</div>
              <div className="flujo-desc">{paso.desc}</div>
            </Link>
            {i < arr.length - 1 && <span className="flujo-arrow text-gold-400 text-lg font-bold">→</span>}
          </div>
        ))}
      </section>

      {/* KPIs nacionales: todos en una misma línea */}
      <section className="grid grid-cols-2 lg:grid-cols-3 gap-3 mb-3">
        <div className="plate card py-3 px-4 flex items-center gap-3">
          <div>
            <div className="kpi-label leading-none">Ocupados Colombia</div>
            <div className="kpi-value text-2xl mt-0.5">{loadingKpis ? (
              <span className="inline-block w-24 h-5 bg-slate-700/40 rounded animate-pulse" />
            ) : (
              resumenNacional ? Math.round(resumenNacional.ocupados_totales || resumenNacional.empleo_nacional || 0).toLocaleString('es-CO') : '—'
            )}</div>
          </div>
        </div>

        <div className="plate card p-3 text-center flex flex-col justify-center min-h-[64px]">
          <p className="kpi-label">Desempleo</p>
          <p className="text-xl font-bold text-white font-display leading-tight">{loadingKpis ? (
            <span className="inline-block w-12 h-5 bg-slate-700/40 rounded animate-pulse" />
          ) : (
            resumenNacional ? (resumenNacional.tasa_desempleo_nacional ?? 0).toFixed(1) : '—'
          )}%</p>
        </div>
        <div className="plate card p-3 text-center flex flex-col justify-center min-h-[64px]">
          <p className="kpi-label">Informalidad</p>
          <p className="text-xl font-bold text-white font-display leading-tight">{loadingKpis ? (
            <span className="inline-block w-12 h-5 bg-slate-700/40 rounded animate-pulse" />
          ) : (
            resumenNacional ? (resumenNacional.tasa_informalidad_nacional ?? 0).toFixed(0) : '—'
          )}%</p>
        </div>
      </section>

      {/* Mapa + insights lado a lado */}
      <section className="plate card p-1">
          <div className="p-4 sm:p-5 border-b border-white/[0.06]">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-xl sm:text-2xl font-bold text-white font-display flex items-center gap-2">
                Mapa laboral de Colombia
              </h2>
              <Link to="/observatorio" className="link text-sm">
                Ver observatorio completo →
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-12 gap-0 items-stretch">
            {/* Mapa */}
            <div className="xl:col-span-7 relative h-[70vh] min-h-[480px] max-h-[780px] bg-[#050813] rounded-bl-xl overflow-hidden">
            {loadingMapa ? (
              <div className="w-full h-full flex flex-col items-center justify-center text-[#6b7390]">
                <span className="inline-block w-16 h-16 border-4 border-slate-700 border-t-gold-500 rounded-full animate-spin mb-3" />
                <span className="text-sm">Cargando mapa...</span>
              </div>
            ) : (
              <MapaColombia
                data={departamentos}
                metric="desempleo"
                onHoverDepto={setHoveredDepto}
                onSelectDepto={setSelectedDepto}
                selectedDepto={selectedDepto?.departamento || null}
                sectorLiderNacional={sectorLiderNacional}
              />
            )}
          </div>

          {/* Panel derecho: panorama nacional en tablas claras tipo factura */}
          <div className="xl:col-span-5 border-t xl:border-t-0 xl:border-l border-gold-500/20 p-4 sm:p-5 flex flex-col overflow-y-auto">
            {loadingRankings ? (
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-2 pb-3 border-b border-gold-500/30">
                  <span className="text-xl font-bold text-gold-400 font-display">Panorama nacional</span>
                </div>
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <div key={i} className="h-24 bg-slate-700/20 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : rankingNacional ? (
              <div className="flex flex-col gap-4">
                {/* Titulo */}
                <div className="flex items-center gap-2 pb-3 border-b border-gold-500/30">
                  <span className="text-xl font-bold text-gold-400 font-display">Panorama nacional</span>
                  {selectedDepto && (
                    <span className="text-sm text-slate-400 ml-auto">
                      {selectedDepto.departamento.replace('ARCHIPIÉLAGO DE SAN ANDRÉS', 'SAN ANDRÉS')}
                    </span>
                  )}
                </div>



                {/* Dos columnas: Mejores y Peores */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Columna Mejores */}
                  <div className="flex flex-col gap-3">
                    <div className="rounded-lg border border-gold-500/30 overflow-hidden">
                      <div className="bg-[rgba(212,175,55,0.15)] px-3 py-2.5 text-base font-bold text-gold-400 uppercase tracking-wider border-b border-gold-500/30">
                        Menor desempleo
                      </div>
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gold-500/20">
                            <th className="text-left py-2 px-3 text-base text-slate-400 font-medium">Departamento</th>
                            <th className="text-right py-2 px-3 text-base text-cyan-400 font-medium">Tasa</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rankingNacional.mejorDesempleo.map((d, i) => (
                            <tr key={i} className="border-b border-white/[0.04] hover:bg-white/[0.04] cursor-pointer"
                              onClick={() => setSelectedDepto(d)}
                            >
                              <td className="py-2 px-3 text-slate-300">{d.departamento.replace('ARCHIPIÉLAGO DE SAN ANDRÉS', 'SAN ANDRÉS')}</td>
                              <td className="py-2 px-3 text-right text-cyan-400 font-semibold">{d.tasa_desempleo?.toFixed(1)}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="rounded-lg border border-gold-500/30 overflow-hidden">
                      <div className="bg-[rgba(212,175,55,0.15)] px-3 py-2.5 text-base font-bold text-gold-400 uppercase tracking-wider border-b border-gold-500/30">
                        Mejores salarios
                      </div>
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gold-500/20">
                            <th className="text-left py-2 px-3 text-base text-slate-400 font-medium">Departamento</th>
                            <th className="text-right py-2 px-3 text-base text-gold-400 font-medium">Salario</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rankingNacional.mejorIngreso.map((d, i) => (
                            <tr key={i} className="border-b border-white/[0.04] hover:bg-white/[0.04] cursor-pointer"
                              onClick={() => setSelectedDepto(d)}
                            >
                              <td className="py-2 px-3 text-slate-300">{d.departamento.replace('ARCHIPIÉLAGO DE SAN ANDRÉS', 'SAN ANDRÉS')}</td>
                              <td className="py-2 px-3 text-right text-gold-400 font-semibold">{formatCOP(d.ingreso_promedio)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="rounded-lg border border-gold-500/30 overflow-hidden">
                      <div className="bg-[rgba(212,175,55,0.15)] px-3 py-2.5 text-base font-bold text-gold-400 uppercase tracking-wider border-b border-gold-500/30">
                        Mayor formalidad
                      </div>
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gold-500/20">
                            <th className="text-left py-2 px-3 text-base text-slate-400 font-medium">Departamento</th>
                            <th className="text-right py-2 px-3 text-base text-cyan-400 font-medium">Formal</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rankingNacional.masFormal.map((d, i) => (
                            <tr key={i} className="border-b border-white/[0.04] hover:bg-white/[0.04] cursor-pointer"
                              onClick={() => setSelectedDepto(d)}
                            >
                              <td className="py-2 px-3 text-slate-300">{d.departamento.replace('ARCHIPIÉLAGO DE SAN ANDRÉS', 'SAN ANDRÉS')}</td>
                              <td className="py-2 px-3 text-right text-cyan-400 font-semibold">{d.tasa_formalidad?.toFixed(0)}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Columna Peores */}
                  <div className="flex flex-col gap-3">
                    <div className="rounded-lg border border-gold-500/30 overflow-hidden">
                      <div className="bg-[rgba(212,175,55,0.15)] px-3 py-2.5 text-base font-bold text-gold-400 uppercase tracking-wider border-b border-gold-500/30">
                        Mayor desempleo
                      </div>
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gold-500/20">
                            <th className="text-left py-2 px-3 text-base text-slate-400 font-medium">Departamento</th>
                            <th className="text-right py-2 px-3 text-base text-red-400 font-medium">Tasa</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rankingNacional.peorDesempleo.map((d, i) => (
                            <tr key={i} className="border-b border-white/[0.04] hover:bg-white/[0.04] cursor-pointer"
                              onClick={() => setSelectedDepto(d)}
                            >
                              <td className="py-2 px-3 text-slate-300">{d.departamento.replace('ARCHIPIÉLAGO DE SAN ANDRÉS', 'SAN ANDRÉS')}</td>
                              <td className="py-2 px-3 text-right text-red-400 font-semibold">{d.tasa_desempleo?.toFixed(1)}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="rounded-lg border border-gold-500/30 overflow-hidden">
                      <div className="bg-[rgba(212,175,55,0.15)] px-3 py-2.5 text-base font-bold text-gold-400 uppercase tracking-wider border-b border-gold-500/30">
                        Menores salarios
                      </div>
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gold-500/20">
                            <th className="text-left py-2 px-3 text-base text-slate-400 font-medium">Departamento</th>
                            <th className="text-right py-2 px-3 text-base text-slate-400 font-medium">Salario</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rankingNacional.peorIngreso.map((d, i) => (
                            <tr key={i} className="border-b border-white/[0.04] hover:bg-white/[0.04] cursor-pointer"
                              onClick={() => setSelectedDepto(d)}
                            >
                              <td className="py-2 px-3 text-slate-300">{d.departamento.replace('ARCHIPIÉLAGO DE SAN ANDRÉS', 'SAN ANDRÉS')}</td>
                              <td className="py-2 px-3 text-right text-slate-400 font-semibold">{formatCOP(d.ingreso_promedio)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="rounded-lg border border-gold-500/30 overflow-hidden">
                      <div className="bg-[rgba(212,175,55,0.15)] px-3 py-2.5 text-base font-bold text-gold-400 uppercase tracking-wider border-b border-gold-500/30">
                        Mayor informalidad
                      </div>
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gold-500/20">
                            <th className="text-left py-2 px-3 text-base text-slate-400 font-medium">Departamento</th>
                            <th className="text-right py-2 px-3 text-base text-red-400 font-medium">Informal</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rankingNacional.masInformal.map((d, i) => (
                            <tr key={i} className="border-b border-white/[0.04] hover:bg-white/[0.04] cursor-pointer"
                              onClick={() => setSelectedDepto(d)}
                            >
                              <td className="py-2 px-3 text-slate-300">{d.departamento.replace('ARCHIPIÉLAGO DE SAN ANDRÉS', 'SAN ANDRÉS')}</td>
                              <td className="py-2 px-3 text-right text-red-400 font-semibold">{(100 - (d.tasa_formalidad || 0)).toFixed(0)}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </section>

    </>
  )
}
