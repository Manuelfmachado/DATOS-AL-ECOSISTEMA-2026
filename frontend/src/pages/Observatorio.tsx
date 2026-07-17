import { useEffect, useState } from 'react'
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
  contentStyle: { background: '#0a0f1f', border: '1px solid rgba(212,175,55,0.3)', borderRadius: '10px', color: '#e9ecf5', fontSize: 13 },
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
  const [sectoresDepto, setSectoresDepto] = useState<any[] | null>(null)

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
        })
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

  // Procesar mapa: empleo + salarios
  const deptosEmpleo = [...mapa]
    .filter((d: any) => d.ocupados > 0)

  // Salarios: solo departamentos con muestra suficiente (>50K ocupados)
  const deptosSalarioConfiable = [...mapa]
    .filter((d: any) => d.ingreso_promedio > 0 && d.ocupados >= 50000)

  const topSalarios = [...deptosSalarioConfiable]
    .filter((d: any) => d.ingreso_promedio > 0)
    .sort((a: any, b: any) => b.ingreso_promedio - a.ingreso_promedio)
    .slice(0, 6)

  const bottomSalarios = [...deptosSalarioConfiable]
    .filter((d: any) => d.ingreso_promedio > 0)
    .sort((a: any, b: any) => a.ingreso_promedio - b.ingreso_promedio)
    .slice(0, 6)

  return (
    <div className="animate-fade-in space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-5xl font-bold text-white font-display">Panorama del empleo en Colombia</h1>
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
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
            <h2 className="text-2xl font-bold text-white font-display flex items-center gap-2">
              Tendencias del empleo
            </h2>
            <div className="flex items-center gap-3">
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
              <Tooltip {...chartTooltip} formatter={(v: number) => [compactNum(v), 'Empleados']} />
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
      {/* 3. Territorio laboral: empleo por departamento (ancho completo) */}
      {/* ================================================================ */}
      <div className="plate card p-5">
        <div className="flex items-center justify-between mb-3 pb-2 border-b border-gold-500/20">
          <h2 className="text-2xl font-bold text-white font-display flex items-center gap-2">
            Empleo por departamento
          </h2>
          <AnalizarIAButton
            dashboard="observatorio"
            widgetTitle="Empleo por departamento"
            widgetType="grafico"
            data={deptosEmpleo}
          />
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={deptosEmpleo.map((d: any, i: number) => ({
              name: cleanDepto(d.departamento),
              ocupados: d.ocupados || 0,
              fill: i < 3 ? '#d4af37' : '#64748b',
            }))}
            layout="vertical"
            margin={{ left: 10, right: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
            <XAxis type="number" stroke="#e9ecf5" tick={{ fill: '#e9ecf5', fontSize: 12, fontWeight: 600 }} tickLine={false} tickFormatter={(v) => compactNum(v)} />
            <YAxis type="category" dataKey="name" stroke="#e9ecf5" tick={{ fill: '#e9ecf5', fontSize: 12, fontWeight: 600 }} width={90} />
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
      {/* 3.1 Salarios por departamento (2 columnas) */}
      {/* ================================================================ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Mejores salarios */}
        <div className="plate card p-5">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-gold-500/20">
            <h2 className="text-xl font-bold text-white font-display flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-green-400" /> Salarios prom. más altos
            </h2>
            <AnalizarIAButton
              dashboard="observatorio"
              widgetTitle="Salarios promedio más altos"
              widgetType="tabla"
              data={topSalarios}
            />
          </div>
          <p className="text-xs text-slate-500 mb-2">Salario promedio mensual (GEIH) · solo deptos con +50 mil ocupados</p>
          <div className="space-y-1">
            {topSalarios.map((d: any, i: number) => (
              <div key={i} className="flex justify-between items-center py-1.5 border-b border-white/[0.04] text-sm">
                <span className="text-slate-300 truncate pr-2">{cleanDepto(d.departamento)}</span>
                <span className="text-gold-400 font-bold">{formatCOP(d.ingreso_promedio)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Menores salarios */}
        <div className="plate card p-5">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-gold-500/20">
            <h2 className="text-xl font-bold text-white font-display flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-rose-400" /> Salarios prom. más bajos
            </h2>
            <AnalizarIAButton
              dashboard="observatorio"
              widgetTitle="Salarios promedio más bajos"
              widgetType="tabla"
              data={bottomSalarios}
            />
          </div>
          <p className="text-xs text-slate-500 mb-2">Salario promedio mensual (GEIH) · solo deptos con +50 mil ocupados</p>
          <div className="space-y-1">
            {bottomSalarios.map((d: any, i: number) => (
              <div key={i} className="flex justify-between items-center py-1.5 border-b border-white/[0.04] text-sm">
                <span className="text-slate-300 truncate pr-2">{cleanDepto(d.departamento)}</span>
                <span className="text-slate-400 font-bold">{formatCOP(d.ingreso_promedio)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ================================================================ */}
      {/* 3.5 Empleo por sector departamental (GEIH depto-sector, 95K filas) */}
      {/* ================================================================ */}
      <div className="plate card p-5">
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-gold-500/20">
          <h2 className="text-2xl font-bold text-white font-display">Empleo por sector</h2>
          <div className="flex items-center gap-3">
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
              className="w-full md:w-1/2 bg-[#0a0f1f] text-slate-200 text-sm border border-amber-500/20 rounded-lg px-3 py-2.5 focus:outline-none focus:border-amber-500/50"
            >
              {departamentosLista.map((d) => (
                <option key={d.codigo} value={d.nombre}>
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
          <ResponsiveContainer width="100%" height={350}>
            <BarChart
            data={sectoresDepto.slice(0, 15).map((s: any) => ({
              name: s.rama_ciiu_nombre || `Sector ${s.rama_ciiu}`,
              empleo: s.empleo,
            }))}
              layout="vertical"
              margin={{ left: 10, right: 40 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
              <XAxis type="number" stroke="#e9ecf5" tick={{ fill: '#e9ecf5', fontSize: 12, fontWeight: 600 }} tickFormatter={(v) => compactNum(v)} />
              <YAxis type="category" dataKey="name" stroke="#e9ecf5" tick={{ fill: '#e9ecf5', fontSize: 12, fontWeight: 600 }} width={100} />
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
      {/* 4. Sectores: formales PILA + emergentes RUES */}
      {/* ================================================================ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Sectores formales PILA */}
        <div className="plate card p-5 relative">
          <div className="absolute top-4 right-4 z-10">
            <AnalizarIAButton
              dashboard="observatorio"
              widgetTitle="Sectores formales PILA"
              widgetType="tabla"
              data={formalList}
            />
          </div>
          <div className="mb-3 pb-2 border-b border-gold-500/20 pr-28">
            <h2 className="text-xl font-bold text-white font-display">Sectores formales</h2>
            <p className="text-sm text-slate-300 mt-1">Personas cotizantes por actividad económica (PILA)</p>
          </div>
          <div className="space-y-0 max-h-64 overflow-y-auto">
            {formalList.map((s: any, i: number) => (
              <div key={i} className="flex justify-between items-center py-2 border-b border-white/[0.04] text-sm">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <span className="w-5 h-5 rounded-full bg-dark-800 border border-gold-500/20 flex items-center justify-center text-[10px] text-gold-400 flex-shrink-0">{i + 1}</span>
                  <span className="text-slate-300 truncate">{s.sector}</span>
                </div>
                <span className="text-gold-400 font-bold ml-2">{compactNum(s.cotizantes)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Sectores emergentes RUES - grafico historico */}
        {emer?.sectores && (() => {
          const top5 = emer.sectores.slice(0, 5)
          // Transformar a formato para LineChart: [{ano, Sector1: val, Sector2: val, ...}]
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
          <div className="plate card p-5 relative">
            <div className="absolute top-4 right-4 z-10">
              <AnalizarIAButton
                dashboard="observatorio"
                widgetTitle="Sectores emergentes RUES (historico)"
                widgetType="grafico"
                data={top5}
              />
            </div>
          <div className="mb-3 pb-2 border-b border-gold-500/20 pr-28">
            <h2 className="text-xl font-bold text-white font-display">Sectores emergentes</h2>
            <p className="text-sm text-slate-300 mt-1">Nuevas empresas registradas por año (2020-2025)</p>
          </div>
          <ResponsiveContainer width="100%" height={260}>
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
      </div>

      {/* ================================================================ */}
      {/* 4.1 Ocupaciones en alza SENA (ancho completo) */}
      {/* ================================================================ */}
      <div className="plate card p-5 relative">
        <div className="absolute top-4 right-4 z-10">
          <AnalizarIAButton
            dashboard="observatorio"
            widgetTitle="Sectores en alza"
            widgetType="tabla"
            data={spe.slice(0, 8)}
          />
        </div>
        <div className="mb-3 pb-2 border-b border-gold-500/20 pr-28">
          <h2 className="text-xl font-bold text-white font-display">Sectores en alza</h2>
          <p className="text-sm text-slate-300 mt-1">Crecimiento real de empleo por sector (GEIH 2022-2025)</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {spe.slice(0, 8).map((o: any, i: number) => (
            <div key={i} className="flex items-center gap-3 bg-white/[0.02] rounded-lg p-3 border border-cyan-500/20">
              <span className="w-7 h-7 rounded-full bg-dark-800 border border-cyan-500/30 flex items-center justify-center text-xs text-cyan-400 flex-shrink-0">{i + 1}</span>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-slate-200 font-medium truncate">{o.ocupacion}</p>
                <p className="text-cyan-400 font-bold text-sm">+{Number(o.variacion_pct).toFixed(0)}%</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ================================================================ */}
      {/* 5. Brecha oferta vs demanda */}
      {/* ================================================================ */}
      {brecha && (
        <div className="plate card p-5">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-gold-500/20">
            <div>
              <h2 className="text-2xl font-bold text-white font-display">Brecha: oferta educativa vs demanda laboral</h2>
              <p className="text-sm text-slate-300 mt-1">
                Compara cuántos estudiantes se forman en cada área contra cuántos empleos reales hay.
              </p>
            </div>
            <AnalizarIAButton
              dashboard="observatorio"
              widgetTitle="Brecha oferta vs demanda"
              widgetType="grafico"
              data={{ sobre: brecha.top_sobre_oferta, sub: brecha.top_sub_oferta }}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              <p className="text-sm text-slate-200">
                <span className="text-red-400 font-bold">Sobre-formación (rojo):</span> hay más graduados que empleos disponibles. 
                Más difícil conseguir trabajo en esa área.
              </p>
            </div>
            <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-lg p-3">
              <p className="text-sm text-slate-200">
                <span className="text-cyan-400 font-bold">Oportunidad (cyan):</span> hay más empleos que graduados. 
                Buena opción para estudiar o buscar trabajo.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Sobre-oferta */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="w-3 h-3 rounded-full bg-red-500" />
                <h3 className="text-base font-bold text-red-400">Sobrea formación</h3>
              </div>
              <div className="space-y-2">
                {brecha.top_sobre_oferta?.map((b: any) => (
                  <div key={b.categoria} className="bg-white/[0.02] rounded-lg p-3 border border-red-900/20">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm text-slate-200 font-bold">{b.categoria?.replace(/_/g, ' ')}</span>
                      <span className="text-sm font-bold text-red-400">+{b.desajuste?.toFixed(1)}%</span>
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-blue-400 w-10">Oferta</span>
                        <div className="flex-1 h-2 bg-dark-900 rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500 rounded-full" style={{ width: `${b.oferta_share}%` }} />
                        </div>
                        <span className="text-xs text-blue-400 font-bold w-8 text-right">{b.oferta_share?.toFixed(0)}%</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-amber-400 w-10">Demanda</span>
                        <div className="flex-1 h-2 bg-dark-900 rounded-full overflow-hidden">
                          <div className="h-full bg-amber-500 rounded-full" style={{ width: `${b.demanda_share}%` }} />
                        </div>
                        <span className="text-xs text-amber-400 font-bold w-8 text-right">{b.demanda_share?.toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Sub-oferta */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="w-3 h-3 rounded-full bg-cyan-400" />
                <h3 className="text-base font-bold text-cyan-400">Oportunidad</h3>
              </div>
              <div className="space-y-2">
                {brecha.top_sub_oferta?.map((b: any) => (
                  <div key={b.categoria} className="bg-white/[0.02] rounded-lg p-3 border border-cyan-900/20">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm text-slate-200 font-bold">{b.categoria?.replace(/_/g, ' ')}</span>
                      <span className="text-sm font-bold text-cyan-400">{b.desajuste?.toFixed(1)}%</span>
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-blue-400 w-10">Oferta</span>
                        <div className="flex-1 h-2 bg-dark-900 rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500 rounded-full" style={{ width: `${b.oferta_share}%` }} />
                        </div>
                        <span className="text-xs text-blue-400 font-bold w-8 text-right">{b.oferta_share?.toFixed(0)}%</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-amber-400 w-10">Demanda</span>
                        <div className="flex-1 h-2 bg-dark-900 rounded-full overflow-hidden">
                          <div className="h-full bg-amber-500 rounded-full" style={{ width: `${b.demanda_share}%` }} />
                        </div>
                        <span className="text-xs text-amber-400 font-bold w-8 text-right">{b.demanda_share?.toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================================================================ */}
      {/* 6. Prioridad de intervención departamental */}
      {/* ================================================================ */}
      {prior?.departamentos && (
        <div className="plate card p-5">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-gold-500/20">
            <div>
              <h2 className="text-2xl font-bold text-white font-display">Prioridad de intervención por departamento</h2>
              <p className="text-sm text-slate-300 mt-1">
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
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-center">
              <p className="text-red-400 font-bold text-lg">≥70</p>
              <p className="text-sm text-slate-300">Urgente: alta necesidad de políticas públicas y programas</p>
            </div>
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-center">
              <p className="text-amber-400 font-bold text-lg">50-69</p>
              <p className="text-sm text-slate-300">Atención: necesita seguimiento e intervenciones focalizadas</p>
            </div>
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3 text-center">
              <p className="text-green-400 font-bold text-lg">&lt;50</p>
              <p className="text-sm text-slate-300">Estable: menor prioridad de intervención</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {prior.departamentos.map((d: any) => {
              const isUrgente = d.indice_prioridad >= 70
              const isAtencion = d.indice_prioridad >= 50
              const barColor = isUrgente ? '#ef4444' : isAtencion ? '#f59e0b' : '#22c55e'
              return (
                <div key={d.departamento} className="flex items-center gap-3 bg-white/[0.02] rounded-lg px-3 py-2 border border-white/[0.04]">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold" style={{ backgroundColor: `${barColor}20`, color: barColor }}>
                    {d.indice_prioridad}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-slate-200 font-medium truncate">{cleanDepto(d.departamento)}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all" style={{ width: `${d.indice_prioridad}%`, backgroundColor: barColor }} />
                      </div>
                      <span className="text-[10px] uppercase font-bold" style={{ color: barColor }}>{d.nivel}</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

    </div>
  )
}
