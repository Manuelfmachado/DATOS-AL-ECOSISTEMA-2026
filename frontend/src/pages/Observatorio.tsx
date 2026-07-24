import { useEffect, useState, Fragment } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  Cell, LineChart, Line, Legend,
} from 'recharts'
import api from '../services/api'
import { formatCOP } from '../utils/format'
import AnalizarIAButton from '../components/AnalizarIAButton'
import { useDepartamentos } from '../hooks/useDepartamentos'

function compactNum(n: number): string {
  return Math.round(n).toLocaleString('es-CO')
}

function cleanDepto(name: string): string {
  return (name || '')
    .replace('ARCHIPIÉLAGO DE SAN ANDRÉS', 'San Andrés')
    .replace('BOGOTÁ D.C.', 'Bogotá')
    .replace('NORTE DE SANTANDER', 'N. Santander')
}

const chartTooltip = {
  contentStyle: { background: '#0a0f1f', border: '1px solid rgba(212,175,55,0.3)', borderRadius: '10px', color: '#e9ecf5', fontSize: 15 },
  itemStyle: { color: '#e9ecf5' },
  labelStyle: { color: '#d4af37', fontWeight: 700 },
}

const MACRO_COLORS = ['#d4af37', '#3b82f6', '#22c55e', '#a855f7', '#f97316', '#ec4899', '#06b6d4', '#84cc16']

// Limpiar nombres bureaucraticos de PILA a algo entendible
function cleanPilaName(desc: string): string {
  const d = desc.toUpperCase()
  if (d.includes('PROFESIONAL') || d.includes('CIENTIF')) return 'Servicios profesionales'
  if (d.includes('REGULADOR') || d.includes('FACILITAD')) return 'Administracion publica'
  if (d.includes('APOYO A LAS EMPRES')) return 'Servicios empresariales'
  if (d.includes('PRACTICA MEDICA') || d.includes('SALUD')) return 'Salud'
  if (d.includes('SERVICIOS PERSONALES')) return 'Servicios personales'
  if (d.includes('DETECTIVE') || d.includes('SEGURIDAD')) return 'Seguridad privada'
  if (d.includes('ASOCIACIO')) return 'Asociaciones'
  if (d.includes('ADMINISTRACION EMPRES')) return 'Gestion empresarial'
  if (d.includes('JURIDIC')) return 'Servicios juridicos'
  if (d.includes('COMBINADAS DE SERVICIOS ADMIN')) return 'Servicios administrativos'
  if (d.includes('EDUCAC')) return 'Educacion'
  if (d.includes('CONSTRUCC')) return 'Construccion'
  if (d.includes('COMERCIO')) return 'Comercio'
  if (d.includes('TRANSPORTE')) return 'Transporte'
  if (d.includes('ALOJAMIENTO') || d.includes('COMIDA')) return 'Hosteleria'
  if (d.includes('FINANCI') || d.includes('SEGURO')) return 'Finanzas'
  if (d.includes('AGRICULT') || d.includes('GANADER') || d.includes('AGRO')) return 'Agricultura'
  if (d.includes('INDUSTRIA') || d.includes('MANUFACTUR')) return 'Industria'
  if (d.includes('TELECOM') || d.includes('INFORMAT')) return 'Tecnologia'
  return desc.length > 35 ? desc.slice(0, 33) + '...' : desc
}

export default function Observatorio() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [loadingSectores, setLoadingSectores] = useState(false)
  const { deptos: departamentosLista, cargando: cargandoDeptos } = useDepartamentos()
  const deptoDefault = departamentosLista.find((d) => d.nombre === 'Bogotá')?.nombre || (departamentosLista[0]?.nombre ?? null)

  const [deptoSeleccionado, setDeptoSeleccionado] = useState<string | null>(deptoDefault)
  const [selectedDepto, setSelectedDepto] = useState<string | null>(null)
  const [sectoresDepto, setSectoresDepto] = useState<any[] | null>(null)
  const [micronegocios, setMicronegocios] = useState<any[] | null>(null)
  const [verTodosSectores, setVerTodosSectores] = useState(false)

  useEffect(() => {
    if (deptoDefault) {
      cargarSectoresDepto(deptoDefault)
    }
  }, [deptoDefault])

  useEffect(() => {
    // Cargar del JSON estatico (instantaneo), fallback a API si no existe
    fetch('/dashboard.json')
      .then((res) => res.ok ? res.json() : Promise.reject('no static'))
      .catch(() => api.get('/observatorio/dashboard').then((res) => res.data))
      .then((d: any) => {
        // Deduplicar SPE por nombre de ocupacion (la tabla SENA tiene filas repetidas)
        const speRaw = d.spe?.ocupaciones_demanda_creciente || []
        const speVistos = new Set<string>()
        const speDedup = speRaw.filter((o: any) => {
          const nombre = o?.ocupacion || ''
          if (speVistos.has(nombre)) return false
          speVistos.add(nombre)
          return true
        })
        setData({
          kpi: d.resumen_nacional,
          tendencia: d.tendencia,
          emergentes: d.emergentes,
          prioridad: d.prioridad,
          brecha: d.brecha,
          sectores_formales: d.sectores_formales?.sectores || [],
          spe: speDedup,
          mapa: d.mapa?.departamentos || [],
          macro: d.macro_worldbank?.indicadores || [],
          informalidad: d.informalidad_territorial?.departamentos || [],
          composicion: d.composicion_formal?.tipos || [],
          sectoresCrecimiento: d.sectores_crecimiento?.sectores_crecimiento || [],
          sectoresCrecimientoPeriodo: d.sectores_crecimiento?.periodo || '',
          resumenGenerado: d._generado || null,
          indice_oportunidad: d.indice_oportunidad || null,
        })
        setMicronegocios(d.micronegocios?.sectores || null)
      })
      .catch((e) => {
        console.error('[Observatorio]', e)
      })
      .finally(() => setLoading(false))
  }, [])

  const cargarSectoresDepto = async (depto: string) => {
    setDeptoSeleccionado(depto)
    setLoadingSectores(true)
    setSectoresDepto(null)
    try {
      const res = await api.get(`/observatorio/departamentos/${encodeURIComponent(depto)}/sectores`)
      setSectoresDepto(res.data.sectores)
    } catch {
      setSectoresDepto(null)
    }
    setLoadingSectores(false)
  }

  const Skeleton = ({ height = 'h-64' }: { height?: string }) => (
    <div className={`plate card rounded-2xl ${height} bg-slate-800/20 animate-pulse border border-white/5`} />
  )

  if (loading) {
    return (
      <div className="animate-fade-in space-y-5">
        <div className="plate card p-5 h-32 bg-slate-800/20 animate-pulse border border-white/5" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <Skeleton height="h-80" />
          <Skeleton height="h-80" />
        </div>
        <Skeleton height="h-96" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <Skeleton height="h-72" />
          <Skeleton height="h-72" />
          <Skeleton height="h-72" />
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="animate-fade-in">
        <div className="plate card rounded-2xl h-96 flex items-center justify-center">
          <p className="text-rose-400 text-sm">Error al cargar datos. Verifica la conexión con el backend.</p>
        </div>
      </div>
    )
  }

  const kpi = data.kpi
  const tend = data.tendencia
  const emer = data.emergentes
  const prior = data.prioridad
  const brecha = data.brecha
  const formales = data.sectores_formales
  const spe = data.spe
  const informalidad = data.informalidad
  const mapa = data.mapa

  // Procesar sectores formales PILA (nombres limpios + deduplicar)
  const formalList = [...formales]
    .reduce((acc: { sector: string; cotizantes: number }[], s: any) => {
      const name = cleanPilaName(String(s.actividadeconomicadesc || '').replace(/^\d+\s*-\s*/, '').trim())
      if (!name) return acc
      const existing = acc.find((a) => a.sector === name)
      if (existing) { existing.cotizantes += s.total_cotizantes || 0 }
      else acc.push({ sector: name, cotizantes: s.total_cotizantes || 0 })
      return acc
    }, [])
    .sort((a, b) => b.cotizantes - a.cotizantes)
    .slice(0, 8)

  // Procesar mapa: empleo por departamento (grafico principal)
  const deptosEmpleo = [...mapa]
    .filter((d: any) => d.ocupados > 0)
    .sort((a: any, b: any) => b.ocupados - a.ocupados)

  return (
    <div className="animate-fade-in space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-5xl font-bold text-gold-400 font-display">Panorama del empleo en Colombia</h1>
        <p className="text-base text-white font-semibold mt-1">
          Datos oficiales para orientar políticas de empleo y formación profesional.
        </p>
      </div>

      {/* ================================================================ */}
      {/* 1. KPIs nacionales */}
      {/* ================================================================ */}
      <div className="grid grid-cols-3 gap-3">
        <div className="plate card p-4 text-center">
          <p className="text-xl font-bold text-white mb-1">Ocupados</p>
          <p className="text-3xl font-bold text-white font-display mt-1">
            {compactNum(kpi.ocupados_totales || kpi.empleo_nacional || 0)}
          </p>
        </div>
        <div className="plate card p-4 text-center">
          <p className="text-xl font-bold text-white mb-1">Desempleo</p>
          <p className="text-3xl font-bold text-rose-400 font-display mt-1">
            {kpi.tasa_desempleo_nacional?.toFixed(1)}%
          </p>
        </div>
        <div className="plate card p-4 text-center">
          <p className="text-xl font-bold text-white mb-1">Informalidad</p>
          <p className="text-3xl font-bold text-amber-400 font-display mt-1">
            {kpi.tasa_informalidad_nacional?.toFixed(0)}%
          </p>
        </div>
      </div>

      {/* ================================================================ */}
      {/* 2. Tendencias del empleo (2022-2026) */}
      {/* ================================================================ */}
      {tend?.sectores && (
        <div className="plate card p-5">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20 gap-3">
            <h2 className="text-2xl font-bold text-white font-display flex items-center gap-2 truncate min-w-0">
              Tendencias del empleo
            </h2>
            <div className="flex items-center gap-3 flex-shrink-0">
              <AnalizarIAButton
                dashboard="observatorio"
                widgetTitle="Tendencias del empleo"
                widgetType="grafico"
                data={tend.sectores}
                filters={{ periodo: tend.periodo }}
              />
            </div>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="ano" stroke="#e9ecf5" tick={{ fill: '#e9ecf5', fontSize: 13, fontWeight: 600 }} allowDuplicatedCategory={false} />
              <YAxis stroke="#e9ecf5" tick={{ fill: '#e9ecf5', fontSize: 13, fontWeight: 600 }} tickFormatter={(v) => Math.round(v).toLocaleString("es-CO")} />
              <Tooltip {...chartTooltip} formatter={(v: number, name: string) => [compactNum(v), name || 'Empleados']} />
              <Legend formatter={(v: string) => <span style={{ color: '#e9ecf5', fontSize: 12 }}>{v}</span>} />
              {tend.sectores.map((s: any, i: number) => (
                <Line
                  key={s.sector}
                  data={s.datos}
                  dataKey="empleo"
                  name={`${s.sector}  ${s.tendencia === 'crece' ? '↑' : s.tendencia === 'declina' ? '↓' : '→'}`}
                  stroke={MACRO_COLORS[i % MACRO_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ================================================================ */}
      {/* 2.5 Sectores emergentes RUES */}
      {/* ================================================================ */}
      {emer?.sectores && (() => {
        const top5 = emer.sectores.slice(0, 5)
        const anosSet = new Set<number>()
        top5.forEach((s: any) => (s.datos || []).forEach((d: any) => anosSet.add(d.ano)))
        const anos = Array.from(anosSet).sort((a, b) => a - b)
        const histData = anos.map((ano) => {
          const row: any = { ano }
          top5.forEach((s: any) => {
            const d = (s.datos || []).find((x: any) => x.ano === ano)
            row[s.sector] = d ? d.empresas : null
          })
          return row
        })
        return (
        <div className="plate card p-5">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20 gap-3">
            <h2 className="text-2xl font-bold text-white font-display flex items-center gap-2 truncate min-w-0">
              Sectores emergentes
            </h2>
            <AnalizarIAButton
              dashboard="observatorio"
              widgetTitle="Sectores emergentes RUES (historico)"
              widgetType="grafico"
              data={top5}
            />
          </div>
          <p className="text-base text-slate-300 -mt-3 mb-3">Nuevas empresas registradas por año (2020-2025)</p>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={histData} margin={{ left: 10, right: 20, top: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="ano" stroke="#e9ecf5" tick={{ fill: '#e9ecf5', fontSize: 12, fontWeight: 600 }} />
              <YAxis stroke="#e9ecf5" tick={{ fill: '#e9ecf5', fontSize: 11 }} tickFormatter={(v) => compactNum(v)} />
              <Tooltip {...chartTooltip} formatter={(v: number) => [v?.toLocaleString(), '']} />
              <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
              {top5.map((s: any, i: number) => (
                <Line key={i} type="monotone" dataKey={s.sector} stroke={MACRO_COLORS[i % MACRO_COLORS.length]} strokeWidth={2} dot={{ r: 3 }} connectNulls />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
        )
      })()}

      {/* ================================================================ */}
      {/* 2.6 Actividades económicas en alza (debajo de sectores emergentes) */}
      {/* ================================================================ */}
      <div className="plate card p-5 relative">
        <div className="absolute top-4 right-4 z-10">
          <AnalizarIAButton
            dashboard="observatorio"
            widgetTitle="Actividades económicas en alza"
            widgetType="tabla"
            data={spe.slice(0, 8)}
          />
        </div>
        <div className="mb-3 pb-2 border-b border-gold-500/20 pr-28">
          <h2 className="text-xl font-bold text-white font-display">Actividades económicas en alza</h2>
          <p className="text-base text-slate-300 mt-1">Crecimiento real de empleo por sector (GEIH 2022-2025)</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {spe.slice(0, 8).map((o: any, i: number) => (
            <div key={i} className="flex items-center gap-3 bg-white/[0.02] rounded-lg p-3 border border-cyan-500/20">
              <span className="w-7 h-7 rounded-full bg-dark-800 border border-cyan-500/30 flex items-center justify-center text-xs text-cyan-400 flex-shrink-0">{i + 1}</span>
              <div className="min-w-0 flex-1">
                <p className="text-base text-slate-200 font-medium truncate">{o.ocupacion}</p>
                <p className="text-cyan-400 font-bold text-sm">+{Number(o.variacion_pct).toFixed(0)}%</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ================================================================ */}
      {/* 3. Territorio laboral: empleo por departamento (ancho completo) */}
      {/* ================================================================ */}
      <div className="plate card p-5">
        <div className="flex items-center justify-between mb-3 pb-2 border-b border-gold-500/20">
          <h2 className="text-2xl font-bold text-white font-display flex items-center gap-2 truncate min-w-0">
            Empleo por departamento
          </h2>
          <div className="flex-shrink-0">
            <AnalizarIAButton
              dashboard="observatorio"
              widgetTitle="Empleo por departamento"
              widgetType="grafico"
              data={deptosEmpleo}
            />
          </div>
        </div>
        <ResponsiveContainer width="100%" height={Math.max(300, deptosEmpleo.length * 22)}>
          <BarChart
            data={deptosEmpleo.map((d: any, i: number) => ({
              name: cleanDepto(d.departamento).toUpperCase(),
              ocupados: d.ocupados || 0,
              fill: i < 3 ? '#d4af37' : '#64748b',
            }))}
            layout="vertical"
            margin={{ left: 10, right: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
            <XAxis type="number" stroke="#e9ecf5" tick={{ fill: '#e9ecf5', fontSize: 12, fontWeight: 600 }} tickLine={false} tickFormatter={(v) => compactNum(v)} />
            <YAxis type="category" dataKey="name" stroke="#e9ecf5" tick={{ fill: '#e9ecf5', fontSize: 10, fontWeight: 600 }} width={90} interval={0} />
            <Tooltip {...chartTooltip} formatter={(v: number) => [v.toLocaleString(), 'Ocupados']} />
            <Bar dataKey="ocupados" radius={[0, 4, 4, 0]}>
              {deptosEmpleo.map((_: any, i: number) => (
                <Cell key={i} fill={i < 3 ? '#d4af37' : '#64748b'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* ================================================================ */}
      {/* 3.5 Empleo por sector departamental (GEIH depto-sector, 95K filas) */}
      {/* ================================================================ */}
      <div className="plate card p-5">
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20 gap-3">
          <h2 className="text-2xl font-bold text-white font-display truncate min-w-0">Empleo por sector</h2>
          <div className="flex items-center gap-3 flex-shrink-0">
            {sectoresDepto && (
              <AnalizarIAButton
                dashboard="observatorio"
                widgetTitle="Empleo por sector departamental"
                widgetType="grafico"
                data={sectoresDepto}
                filters={{ departamento: deptoSeleccionado || undefined }}
              />
            )}
          </div>
        </div>
        <p className="text-base text-white font-semibold mb-4">
          Selecciona un departamento para ver el desglose de empleo por sector económico.
        </p>
        <div className="mb-4">
          {cargandoDeptos ? (
            <p className="text-slate-500 text-sm">Cargando departamentos...</p>
          ) : (
            <select
              value={deptoSeleccionado || ''}
              onChange={(e) => cargarSectoresDepto(e.target.value)}
              className="w-full md:w-1/2 bg-[#0a0f1f] text-white text-sm border border-amber-500/40 rounded-lg px-3 py-3 focus:outline-none focus:border-amber-500/80 focus:ring-1 focus:ring-amber-500/30 appearance-none cursor-pointer"
              style={{
                backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%23d4af37' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`,
                backgroundPosition: 'right 0.75rem center',
                backgroundRepeat: 'no-repeat',
                backgroundSize: '1.2em 1.2em',
                paddingRight: '2.5rem',
              }}
            >
              <option value="" disabled>
                Selecciona un departamento
              </option>
              {departamentosLista.map((d) => (
                <option key={d.codigo} value={d.nombre} className="bg-[#0a0f1f] text-white">
                  {d.nombre}
                </option>
              ))}
            </select>
          )}
        </div>

        {loadingSectores && (
          <p className="text-slate-500 text-sm">Cargando sectores...</p>
        )}

        {sectoresDepto && sectoresDepto.length > 0 && (
          <ResponsiveContainer width="100%" height={Math.max(400, sectoresDepto.slice(0, 15).length * 32)}>
            <BarChart
            data={sectoresDepto.slice(0, 15).map((s: any) => ({
              name: s.rama_ciiu_nombre || `Sector ${s.rama_ciiu}`,
              empleo: s.empleo,
            }))}
              layout="vertical"
              margin={{ left: 10, right: 40 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
              <XAxis type="number" stroke="#cbd5e1" tick={{ fill: '#cbd5e1', fontSize: 12, fontWeight: 600 }} tickFormatter={(v) => compactNum(v)} />
              <YAxis type="category" dataKey="name" stroke="#e2e8f0" tick={{ fill: '#e2e8f0', fontSize: 13, fontWeight: 600 }} width={240} interval={0} />
              <Tooltip {...chartTooltip} formatter={(v: number) => [v.toLocaleString(), 'Empleo']} />
              <Bar dataKey="empleo" radius={[0, 4, 4, 0]}>
                {sectoresDepto.slice(0, 15).map((_: any, i: number) => (
                  <Cell key={i} fill={i < 3 ? '#d4af37' : i < 6 ? '#3b82f6' : '#64748b'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}

        {deptoSeleccionado && !loadingSectores && (!sectoresDepto || sectoresDepto.length === 0) && (
          <p className="text-slate-500 text-sm">No hay datos de empleo por sector para este departamento.</p>
        )}
      </div>

      {/* ================================================================ */}
      {/* 3.6 Informalidad territorial (EMICRON) */}
      {/* ================================================================ */}
      {informalidad && informalidad.length > 0 && (
        (() => {
          const totalNacional = informalidad.reduce((a: number, d: any) => a + (d.micronegocios || 0), 0)
          const anioFin: number = typeof informalidad[0]?.ano === 'number' ? informalidad[0].ano : new Date().getFullYear()
          // Variacion real: comparamos el total del ultimo anio vs el primer anio disponible
          const aniosSet = new Set<number>()
          informalidad.forEach((d: any) => { if (typeof d.ano === 'number') aniosSet.add(d.ano) })
          const aniosDisponibles: number[] = Array.from(aniosSet).sort((a, b) => a - b)
          const anioInicio: number = aniosDisponibles[0] ?? anioFin - 2
          const totalInicio = informalidad
            .filter((d: any) => d.ano === anioInicio)
            .reduce((a: number, d: any) => a + (d.micronegocios || 0), 0)
          const totalFin = informalidad
            .filter((d: any) => d.ano === anioFin)
            .reduce((a: number, d: any) => a + (d.micronegocios || 0), 0)
          const variacionNacional = totalInicio > 0 ? ((totalFin - totalInicio) / totalInicio) * 100 : null
          return (
        <div className="plate card p-5 relative">
          <div className="absolute top-3 right-3 z-10">
            <AnalizarIAButton
              dashboard="observatorio"
              widgetTitle="Informalidad territorial: micronegocios por departamento"
              widgetType="grafico"
              data={informalidad.slice(0, 15)}
            />
          </div>
          <div className="mb-3 pb-2 border-b border-gold-500/20 pr-28">
            <h2 className="text-xl font-bold text-white font-display truncate min-w-0">
              Dónde se concentran los micronegocios
            </h2>
            <p className="text-base text-slate-300 mt-1">
              Los micronegocios son negocios con menos de 10 personas que no cotizan a seguridad social. Aquí ves los departamentos donde más se concentran.
            </p>
          </div>

          <div className="mb-4">
            <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-4">
              <p className="text-xs text-amber-300/80 uppercase tracking-wide font-semibold">Total nacional {anioFin}</p>
              <p className="text-3xl font-bold text-white mt-1">{compactNum(totalNacional)}</p>
              <p className="text-sm text-slate-400">micronegocios en todo el país</p>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={Math.max(300, Math.min(informalidad.length, 15) * 28)}>
            <BarChart
              data={informalidad.slice(0, 15).map((d: any) => ({
                name: cleanDepto(d.departamento),
                micronegocios: d.micronegocios || 0,
              }))}
              layout="vertical"
              margin={{ left: 10, right: 40 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
              <XAxis type="number" stroke="#cbd5e1" tick={{ fill: '#cbd5e1', fontSize: 12, fontWeight: 600 }} tickFormatter={(v) => compactNum(v)} />
              <YAxis type="category" dataKey="name" stroke="#e2e8f0" tick={{ fill: '#e2e8f0', fontSize: 11, fontWeight: 600 }} width={130} interval={0} />
              <Tooltip {...chartTooltip} formatter={(v: number) => [compactNum(v), 'Micronegocios']} />
              <Bar dataKey="micronegocios" radius={[0, 4, 4, 0]}>
                {informalidad.slice(0, 15).map((_: any, i: number) => (
                  <Cell key={i} fill={i < 3 ? '#22c55e' : i < 6 ? '#06b6d4' : '#64748b'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
          )
        })()
      )}

      {/* ================================================================ */}
      {/* 4. Sectores con más empleo (GEIH) */}
      {/* ================================================================ */}
      {kpi.top_sectores_empleo && kpi.top_sectores_empleo.length > 0 && (
        (() => {
          const top5 = kpi.top_sectores_empleo.slice(0, 5)
          const totalTop5 = top5.reduce((a: number, s: any) => a + (s.empleo || 0), 0)
          const totalNacional = kpi.ocupados_totales || kpi.empleo_nacional || 0
          const listaVisible = verTodosSectores ? kpi.top_sectores_empleo : top5
          const maxEmp = Math.max(...kpi.top_sectores_empleo.map((x: any) => x.empleo || 0), 1)
          return (
        <div className="plate card p-5 relative">
          <div className="absolute top-4 right-4 z-10">
            <AnalizarIAButton
              dashboard="observatorio"
              widgetTitle="Sectores con más empleo (GEIH)"
              widgetType="tabla"
              data={kpi.top_sectores_empleo}
            />
          </div>
          <div className="mb-3 pb-2 border-b border-gold-500/20 pr-28">
            <h2 className="text-xl font-bold text-white font-display">Sectores que más emplean</h2>
            <p className="text-base text-slate-300 mt-1">
              Cuántas personas ocupadas tiene cada sector económico del país.
              {kpi.periodo && (
                <span className="text-slate-400"> · Dato de {kpi.periodo} (GEIH).</span>
              )}
              {totalTop5 > 0 && totalNacional > 0 && (
                <span className="block text-slate-400 mt-1">
                  Los 5 principales concentran <span className="text-gold-400 font-semibold">{compactNum(totalTop5)} personas</span> ({((totalTop5 / totalNacional) * 100).toFixed(1)}% del empleo nacional).
                </span>
              )}
            </p>
          </div>
          <div className="space-y-1.5">
            {listaVisible.map((s: any, i: number) => {
              return (
                <div key={i} className="group flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-white/[0.03] transition-colors">
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs flex-shrink-0 font-bold border ${i < 3 ? 'bg-gold-500/10 border-gold-500/40 text-gold-400' : 'bg-dark-800 border-gold-500/30 text-gold-400'}`}>{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between gap-3 mb-1">
                      <span className="text-sm text-slate-200 font-medium leading-snug truncate">{s.rama_ciiu_nombre || `Sector ${s.rama_ciiu}`}</span>
                      <span className="font-bold text-sm flex-shrink-0 text-slate-200">{compactNum(s.empleo)} <span className="text-xs text-slate-500 font-normal">personas</span></span>
                    </div>
                    <div className="h-1.5 w-full bg-white/[0.04] rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-gradient-to-r from-gold-500/60 to-gold-400" style={{ width: `${Math.min(100, (s.empleo / maxEmp) * 100)}%` }} />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
          {kpi.top_sectores_empleo.length > 5 && (
            <button
              type="button"
              onClick={() => setVerTodosSectores((v) => !v)}
              className="mt-4 w-full text-sm text-gold-400 hover:text-gold-300 font-semibold py-2 border border-gold-500/30 rounded-lg hover:bg-gold-500/5 transition-colors"
            >
              {verTodosSectores
                ? `Ver solo los 5 principales`
                : `Ver los ${kpi.top_sectores_empleo.length} sectores`}
            </button>
          )}
        </div>
          )
        })()
      )}

      {/* ================================================================ */}
      {/* 5. El trabajo informal también mueve la economía */}
      {/* ================================================================ */}
      {micronegocios && micronegocios.length > 0 && (
        (() => {
          const total = micronegocios.reduce((a: number, s: any) => a + (s.empleo_informal || s.micronegocios || 0), 0)
          const anio = data.micronegocios?.ano || micronegocios[0]?.ano
          return (
        <div className="grid grid-cols-1 gap-5">
          <div className="plate card p-5 relative">
            <div className="absolute top-3 right-3 z-10">
              <AnalizarIAButton
                dashboard="observatorio"
                widgetTitle="Empleo informal: micronegocios por sector"
                widgetType="grafico"
                data={micronegocios.slice(0, 10)}
              />
            </div>
            <div className="mb-3 pb-2 border-b border-gold-500/20 pr-28">
              <h2 className="text-xl font-bold text-white font-display">El trabajo informal también mueve la economía</h2>
              <p className="text-base text-slate-300 mt-1">
                Los micronegocios son negocios con menos de 10 personas que no cotizan a seguridad social. Aquí ves en qué sectores se concentran.
              </p>
            </div>

            <div className="mb-4">
              <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-4">
                <p className="text-xs text-amber-300/80 uppercase tracking-wide font-semibold">Total pais</p>
                <p className="text-3xl font-bold text-white mt-1">{compactNum(total)}</p>
                <p className="text-sm text-slate-400">micronegocios{anio ? ` · ${anio}` : ''}</p>
              </div>
            </div>

            <ResponsiveContainer width="100%" height={Math.max(320, micronegocios.slice(0, 10).length * 42)}>
              <BarChart
                data={micronegocios.slice(0, 10).map((s: any) => ({
                  name: s.sector || '',
                  micronegocios: s.micronegocios,
                  participacion: s.pct_participacion,
                }))}
                layout="vertical"
                margin={{ left: 10, right: 40 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                <XAxis type="number" stroke="#cbd5e1" tick={{ fill: '#cbd5e1', fontSize: 13, fontWeight: 600 }} tickFormatter={(v) => compactNum(v)} />
                <YAxis type="category" dataKey="name" stroke="#e2e8f0" tick={{ fill: '#e2e8f0', fontSize: 13, fontWeight: 600 }} width={260} interval={0} />
                <Tooltip {...chartTooltip} formatter={(v: number, _n: any, p: any) => [`${compactNum(v)} (${p.payload.participacion?.toFixed(1) || 0}%)`, 'Micronegocios']} />
                <Bar dataKey="micronegocios" radius={[0, 4, 4, 0]}>
                  {micronegocios.slice(0, 10).map((_: any, i: number) => (
                    <Cell key={i} fill={i < 3 ? '#22c55e' : i < 6 ? '#06b6d4' : '#64748b'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
          )
        })()
      )}

      {/* ================================================================ */}
      {/* 6. Indice de Oportunidad Laboral (GEIH + SPE + RUES) */}
      {/* ================================================================ */}
      {data.indice_oportunidad?.indices && data.indice_oportunidad.indices.length > 0 && (
        <div className="plate card p-5 relative">
          <div className="absolute top-3 right-3 z-10">
            <AnalizarIAButton
              dashboard="observatorio"
              widgetTitle="Indice de Oportunidad Laboral"
              widgetType="tabla"
              data={data.indice_oportunidad.indices}
            />
          </div>
          <div className="mb-4 pb-3 border-b border-gold-500/20 pr-28">
            <h2 className="text-2xl font-bold text-white font-display">Indice de Oportunidad Laboral</h2>
            <p className="text-base text-slate-300 mt-2">
              Para cada area del conocimiento, calculamos un puntaje <span className="text-gold-400 font-semibold">0-100</span> combinando tres senales oficiales:
            </p>
            <p className="text-sm text-slate-400 mt-1">
              <span className="text-blue-300 font-semibold">Empleo real (GEIH)</span> &middot; <span className="text-purple-300 font-semibold">Vacantes registradas (SPE)</span> &middot; <span className="text-emerald-300 font-semibold">Nuevas empresas (RUES)</span>
            </p>
            <p className="text-sm text-slate-400 mt-1">
              Cuanto mas alto el puntaje, mas oportunidades laborales tiene el area.
            </p>
            <div className="grid grid-cols-3 gap-2 mt-3 text-sm">
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-2 text-center">
                <div className="text-emerald-400 font-bold">75-100</div>
                <div className="text-emerald-300/80 text-xs">Alta oportunidad</div>
              </div>
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-2 text-center">
                <div className="text-amber-400 font-bold">50-74</div>
                <div className="text-amber-300/80 text-xs">Oportunidad media</div>
              </div>
              <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-2 text-center">
                <div className="text-rose-400 font-bold">0-49</div>
                <div className="text-rose-300/80 text-xs">Baja oportunidad</div>
              </div>
            </div>
          </div>
          <div className="space-y-3">
            {data.indice_oportunidad.indices.map((idx: any) => (
              <div key={idx.categoria} className="rounded-lg p-4 border border-white/10">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 text-center">
                    <div className={`text-3xl font-bold ${idx.color === 'alta' ? 'text-emerald-400' : idx.color === 'media' ? 'text-amber-400' : 'text-rose-400'}`}>
                      {idx.score.toFixed(0)}<span className="text-base text-slate-500">/100</span>
                    </div>
                    <div className={`text-[10px] uppercase tracking-wider font-bold ${idx.color === 'alta' ? 'text-emerald-400' : idx.color === 'media' ? 'text-amber-400' : 'text-rose-400'}`}>
                      {idx.color === 'alta' ? 'Oportunidad alta' : idx.color === 'media' ? 'Oportunidad media' : 'Oportunidad baja'}
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between gap-3 mb-2">
                      <span className="text-lg font-bold text-white truncate">{idx.categoria_nombre}</span>
                      <span className={`text-sm font-bold flex-shrink-0 ${idx.tendencia === 'crece' ? 'text-emerald-400' : idx.tendencia === 'decline' ? 'text-rose-400' : 'text-slate-400'}`}>
                        {idx.tendencia === 'crece' ? '↑' : idx.tendencia === 'decline' ? '↓' : '→'} {idx.tendencia === 'crece' ? 'Creciendo' : idx.tendencia === 'decline' ? 'En declive' : 'Estable'}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div className="bg-black/20 rounded p-2">
                        <div className="text-slate-400 text-[10px] uppercase tracking-wide">Empleo</div>
                        <div className="text-slate-500 text-[10px]">(2022-2026)</div>
                        <div className={`font-bold text-sm ${idx.geih_crecimiento_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {idx.geih_crecimiento_pct >= 0 ? '+' : ''}{idx.geih_crecimiento_pct.toFixed(1)}%
                        </div>
                      </div>
                      <div className="bg-black/20 rounded p-2">
                        <div className="text-slate-400 text-[10px] uppercase tracking-wide">Vacantes</div>
                        <div className="text-slate-500 text-[10px]">(2019-2023)</div>
                        <div className={`font-bold text-sm ${idx.spe_crecimiento_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {idx.spe_crecimiento_pct >= 0 ? '+' : ''}{idx.spe_crecimiento_pct.toFixed(1)}%
                        </div>
                      </div>
                      <div className="bg-black/20 rounded p-2">
                        <div className="text-slate-400 text-[10px] uppercase tracking-wide">Empresas</div>
                        <div className="text-slate-500 text-[10px]">(2020-2026)</div>
                        <div className={`font-bold text-sm ${idx.rues_crecimiento_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {idx.rues_crecimiento_pct >= 0 ? '+' : ''}{idx.rues_crecimiento_pct.toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <details className="mt-4">
            <summary className="text-slate-400 text-xs cursor-pointer hover:text-slate-200">Como se calcula este puntaje?</summary>
            <p className="text-slate-500 text-xs mt-2 leading-relaxed">
              {data.indice_oportunidad.metodologia}
              <br /><br />
              <span className="text-slate-400">Periodos de los datos:</span> GEIH {data.indice_oportunidad.fuentes?.geih} &middot; SPE {data.indice_oportunidad.fuentes?.spe} &middot; RUES {data.indice_oportunidad.fuentes?.rues}.
            </p>
          </details>
        </div>
      )}

      {/* ================================================================ */}
      {/* 7. Prioridad de intervención departamental */}
      {/* ================================================================ */}
      {prior?.departamentos && (
        <div className="plate card p-5">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-gold-500/20 gap-3">
            <div className="min-w-0">
              <h2 className="text-2xl font-bold text-white font-display truncate">Prioridad de intervención por departamento</h2>
              <p className="text-base text-slate-300 mt-1">
                Puntaje 0-100 que mide qué departamentos más necesitan ayuda.
              </p>
            </div>
            <AnalizarIAButton
              dashboard="observatorio"
              widgetTitle="Prioridad de intervención por departamento"
              widgetType="tabla"
              data={prior.departamentos}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
            <div className="bg-red-600/75 border border-red-400/60 rounded-lg p-3 text-center">
              <p className="text-red-200 font-bold text-lg">≥70</p>
              <p className="text-sm text-white">Urgente: alta necesidad de políticas públicas y programas</p>
            </div>
            <div className="bg-amber-600/75 border border-amber-400/60 rounded-lg p-3 text-center">
              <p className="text-amber-200 font-bold text-lg">50-69</p>
              <p className="text-sm text-white">Atención: necesita seguimiento e intervenciones focalizadas</p>
            </div>
            <div className="bg-green-600/75 border border-green-400/60 rounded-lg p-3 text-center">
              <p className="text-green-200 font-bold text-lg">&lt;50</p>
              <p className="text-sm text-white">Estable: menor prioridad de intervención</p>
            </div>
          </div>

          <div className="overflow-hidden rounded-lg">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.08] bg-white/[0.03]">
                  <th className="text-left py-3 px-3 text-base text-slate-300 font-semibold w-8">#</th>
                  <th className="text-left py-3 px-3 text-base text-slate-300 font-semibold">Departamento</th>
                  <th className="text-right py-3 px-3 text-base text-slate-300 font-semibold w-16">Score</th>
                  <th className="text-right py-3 px-3 text-base text-slate-300 font-semibold w-16">Nivel</th>
                </tr>
              </thead>
              <tbody>
            {prior.departamentos.map((d: any, i: number) => {
              const isUrgente = d.indice_prioridad >= 70
              const isAtencion = d.indice_prioridad >= 50
              const barColor = isUrgente ? '#ef4444' : isAtencion ? '#f59e0b' : '#22c55e'
              const sel = selectedDepto === d.departamento
              const desglose = d.desglose && d.desglose.length > 0 ? d.desglose : [
                d.tasa_informalidad != null ? `Informalidad ${Math.round(100 - (d.tasa_formalidad || 0))}%` : '',
                d.tasa_desempleo != null ? `Desempleo ${d.tasa_desempleo}%` : '',
                d.dnp_desempeno != null ? `Gestión pública ${d.dnp_desempeno}/100` : '',
                d.pct_educacion_superior != null ? `Educación superior ${d.pct_educacion_superior}%` : '',
                d.ingreso_promedio != null ? `Ingreso promedio ${formatCOP(d.ingreso_promedio)}` : '',
              ].filter(Boolean)
              return (
                <Fragment key={d.departamento}>
                  <tr
                    onClick={() => setSelectedDepto(sel ? null : d.departamento)}
                    className={`border-b border-white/[0.04] cursor-pointer transition-colors ${
                      i % 2 === 0 ? 'bg-white/[0.01]' : 'bg-transparent'
                    } ${sel ? 'bg-amber-500/10 border-amber-500/20' : 'hover:bg-white/[0.04]'}`}
                  >
                    <td className="py-2.5 px-3 text-slate-500 font-mono text-xs">{i + 1}</td>
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-3">
                        <span className="text-base text-slate-200 font-medium">{cleanDepto(d.departamento)}</span>
                        <div className="flex-1 h-3 bg-white/[0.06] rounded-full overflow-hidden hidden sm:block max-w-[380px]">
                          <div className="h-full rounded-full transition-all" style={{ width: `${d.indice_prioridad}%`, background: `linear-gradient(90deg, ${barColor}, ${barColor}dd)` }} />
                        </div>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <span className="font-bold font-display text-base" style={{ color: barColor }}>{d.indice_prioridad}</span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <span className="text-xs uppercase tracking-wider font-bold px-2 py-0.5 rounded" style={{ backgroundColor: `${barColor}30`, color: barColor }}>{d.nivel}</span>
                    </td>
                  </tr>
                  {sel && desglose.length > 0 && (
                    <tr>
                      <td colSpan={4} className="py-2.5 px-6 bg-amber-500/[0.04] border-b border-amber-500/10">
                        <div className="text-xs text-slate-400 space-y-1">
                          {desglose.filter(Boolean).map((line: string, j: number) => (
                            <div key={j} className="flex items-center gap-2">
                              <span className="w-1 h-1 rounded-full bg-amber-500/60 flex-shrink-0" />
                              <span>{line}</span>
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  )
}
