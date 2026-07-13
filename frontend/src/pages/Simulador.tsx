import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { Search, Building2, GraduationCap, Users, Lightbulb, TrendingUp, AlertTriangle, CheckCircle, Briefcase } from 'lucide-react'
import api from '../services/api'

interface Metrica {
  label: string
  valor: string | number
}

interface SimResult {
  actor: string
  foco?: string
  departamento: string
  escenario: string
  horizonte_anos: number
  anios?: string[]
  series?: Record<string, number[]>
  metricas?: Metrica[]
  recomendaciones?: string[]
  recomendaciones_macro?: string[]
  contexto?: any
}

const ACTORES = [
  { key: 'gobierno', label: 'Gobierno / Alcaldía', icon: Building2 },
  { key: 'universidad', label: 'Universidad', icon: GraduationCap },
  { key: 'sena', label: 'SENA', icon: Briefcase },
]

const FOCOS = [
  { key: 'empleo', label: 'Empleo y demanda laboral' },
  { key: 'empresas', label: 'Empresas nuevas' },
  { key: 'educacion', label: 'Oferta educativa' },
]

const ESCENARIOS = [
  { key: 'optimista', label: 'Optimista', color: 'bg-green-100 text-green-800 border-green-300', desc: '+3.5% empleo, +12% empresas' },
  { key: 'base', label: 'Base', color: 'bg-blue-100 text-blue-800 border-blue-300', desc: '+1.5% empleo, +5% empresas' },
  { key: 'pesimista', label: 'Pesimista', color: 'bg-rose-100 text-rose-800 border-rose-300', desc: '-1.5% empleo, -5% empresas' },
]

export default function Simulador() {
  const [modo, setModo] = useState<'proyectar' | 'departamento' | 'recomendaciones'>('proyectar')
  const [actor, setActor] = useState('gobierno')
  const [foco, setFoco] = useState('empleo')
  const [departamento, setDepartamento] = useState('Bogotá')
  const [carrera, setCarrera] = useState('')
  const [sector, setSector] = useState('')
  const [horizonte, setHorizonte] = useState(3)
  const [escenario, setEscenario] = useState('base')
  const [loading, setLoading] = useState(false)
  const [resultado, setResultado] = useState<SimResult | null>(null)
  const [error, setError] = useState('')

  const simular = async () => {
    setLoading(true)
    setError('')
    try {
      let res
      if (modo === 'proyectar') {
        res = await api.post('/simulador/proyectar', {
          actor,
          foco,
          departamento,
          carrera,
          sector,
          horizonte,
          escenario,
        })
      } else if (modo === 'departamento') {
        res = await api.post('/simulador/departamento', {
          departamento,
          horizonte,
          escenario,
        })
      } else {
        res = await api.post('/simulador/recomendaciones', {
          actor,
          departamento,
          sector_prioritario: sector,
          carrera_prioritaria: carrera,
        })
      }
      setResultado(res.data)
    } catch (e) {
      setError('Error al ejecutar la simulación. Intenta de nuevo.')
      setResultado(null)
    }
    setLoading(false)
  }

  // Preparar datos para Recharts
  const chartData = (() => {
    if (!resultado) return []
    const anios = resultado.anios || Array.from({ length: resultado.horizonte_anos }, (_, i) => `${2026 + i}`)
    const series = resultado.series || {}
    return anios.map((anio, i) => {
      const point: any = { anio }
      Object.entries(series).forEach(([key, vals]) => {
        point[key] = vals[i]
      })
      return point
    })
  })()

  const seriesColors: Record<string, string> = {
    ocupados: '#16a34a',
    no_ocupados: '#dc2626',
    demanda_laboral: '#2563eb',
    demanda_spe: '#2563eb',
    empresas_nuevas: '#7c3aed',
    matriculados: '#ea580c',
  }

  const seriesLabels: Record<string, string> = {
    ocupados: 'Ocupados',
    no_ocupados: 'No ocupados',
    demanda_laboral: 'Demanda laboral',
    demanda_spe: 'Demanda SPE',
    empresas_nuevas: 'Empresas nuevas',
    matriculados: 'Matriculados',
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Simulador IA</h1>
      <p className="text-gray-600 mb-6">Anticipa cambios en el mercado laboral y genera recomendaciones de política pública</p>

      {/* Tabs de modo */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-1 flex mb-6">
        {[
          { key: 'proyectar', label: 'Proyección por foco', icon: TrendingUp },
          { key: 'departamento', label: 'Proyección departamental', icon: Building2 },
          { key: 'recomendaciones', label: 'Recomendaciones', icon: Lightbulb },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => { setModo(tab.key as any); setResultado(null); setError('') }}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium rounded-lg transition-colors ${
              modo === tab.key ? 'bg-alba-600 text-white' : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Panel de controles */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-5">
          {modo !== 'departamento' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Actor</label>
              <div className="grid grid-cols-1 gap-2">
                {ACTORES.map((a) => (
                  <button
                    key={a.key}
                    onClick={() => setActor(a.key)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-colors ${
                      actor === a.key
                        ? 'border-alba-500 bg-alba-50 text-alba-800'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <a.icon size={16} />
                    {a.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {modo === 'proyectar' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Foco de análisis</label>
              <div className="space-y-2">
                {FOCOS.map((f) => (
                  <label key={f.key} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="foco"
                      value={f.key}
                      checked={foco === f.key}
                      onChange={() => setFoco(f.key)}
                      className="text-alba-600 focus:ring-alba-500"
                    />
                    <span className="text-sm text-gray-700">{f.label}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Departamento</label>
            <input
              type="text"
              value={departamento}
              onChange={(e) => setDepartamento(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-alba-500"
            />
          </div>

          {modo !== 'departamento' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Carrera / programa (opcional)</label>
                <input
                  type="text"
                  value={carrera}
                  onChange={(e) => setCarrera(e.target.value)}
                  placeholder="Ej: ingeniería, derecho"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-alba-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sector prioritario (opcional)</label>
                <input
                  type="text"
                  value={sector}
                  onChange={(e) => setSector(e.target.value)}
                  placeholder="Ej: tecnología, salud"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-alba-500"
                />
              </div>
            </>
          )}

          {modo !== 'recomendaciones' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Horizonte: {horizonte} años</label>
                <input
                  type="range"
                  min={1}
                  max={5}
                  value={horizonte}
                  onChange={(e) => setHorizonte(parseInt(e.target.value))}
                  className="w-full accent-alba-600"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Escenario</label>
                <div className="space-y-2">
                  {ESCENARIOS.map((esc) => (
                    <button
                      key={esc.key}
                      onClick={() => setEscenario(esc.key)}
                      className={`w-full text-left px-3 py-2 rounded-lg border text-sm transition-colors ${
                        escenario === esc.key
                          ? esc.color
                          : 'border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <span className="font-medium">{esc.label}</span>
                      <span className="block text-xs opacity-80">{esc.desc}</span>
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}

          <button
            onClick={simular}
            disabled={loading}
            className="w-full bg-alba-600 text-white py-2.5 rounded-lg hover:bg-alba-700 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Search size={18} />
            {loading ? 'Simulando...' : modo === 'recomendaciones' ? 'Generar recomendaciones' : 'Ejecutar simulación'}
          </button>
        </div>

        {/* Panel de resultados */}
        <div className="lg:col-span-2 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
              {error}
            </div>
          )}

          {!resultado && !error && !loading && (
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-8 text-center text-gray-500">
              <TrendingUp size={48} className="mx-auto mb-3 text-gray-400" />
              <p>Configura los parámetros y ejecuta una simulación para ver resultados.</p>
            </div>
          )}

          {resultado && (
            <>
              {/* Métricas */}
              {resultado.metricas && resultado.metricas.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {resultado.metricas.map((m, i) => (
                    <div key={i} className="bg-white rounded-xl border p-4 text-center">
                      <p className="text-2xl font-bold text-alba-600">{typeof m.valor === 'number' ? m.valor.toLocaleString(undefined, { maximumFractionDigits: 0 }) : m.valor}</p>
                      <p className="text-xs text-gray-600 mt-1">{m.label}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Gráfico */}
              {chartData.length > 0 && Object.keys(resultado.series || {}).length > 0 && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="font-bold text-gray-900 mb-4">Proyección {resultado.horizonte_anos} años - Escenario {resultado.escenario}</h3>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="anio" />
                        <YAxis tickFormatter={(v) => v >= 1000000 ? `${(v / 1000000).toFixed(1)}M` : v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v} />
                        <Tooltip formatter={(value: any) => Number(value).toLocaleString()} />
                        <Legend />
                        {Object.keys(resultado.series || {}).map((key) => (
                          <Line
                            key={key}
                            type="monotone"
                            dataKey={key}
                            name={seriesLabels[key] || key}
                            stroke={seriesColors[key] || '#666'}
                            strokeWidth={2}
                            dot={false}
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Recomendaciones */}
              {(resultado.recomendaciones || resultado.recomendaciones_macro) && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <Lightbulb size={20} className="text-amber-500" />
                    Recomendaciones para {ACTORES.find(a => a.key === actor)?.label || 'el actor seleccionado'}
                  </h3>
                  <div className="space-y-3">
                    {(resultado.recomendaciones || resultado.recomendaciones_macro || []).map((rec, i) => (
                      <div key={i} className="flex items-start gap-3 p-3 bg-amber-50 rounded-lg border border-amber-100">
                        <CheckCircle size={18} className="text-amber-600 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-gray-800">{rec}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Contexto en recomendaciones */}
              {resultado.contexto && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {resultado.contexto.top_demanda_spe && (
                    <div className="bg-white rounded-xl border p-4">
                      <h4 className="font-semibold text-gray-900 mb-2 text-sm">Top demanda SPE SENA</h4>
                      <ul className="text-sm space-y-1">
                        {resultado.contexto.top_demanda_spe.slice(0, 5).map((o: string, i: number) => (
                          <li key={i} className="text-gray-700">{i + 1}. {o}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {resultado.contexto.cursos_sena_disponibles && (
                    <div className="bg-white rounded-xl border p-4">
                      <h4 className="font-semibold text-gray-900 mb-2 text-sm">Cursos SENA disponibles</h4>
                      <ul className="text-sm space-y-1">
                        {resultado.contexto.cursos_sena_disponibles.slice(0, 5).map((c: string, i: number) => (
                          <li key={i} className="text-gray-700">• {c}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
