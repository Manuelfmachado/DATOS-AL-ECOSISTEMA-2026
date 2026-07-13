import { useEffect, useState } from 'react'
import api from '../services/api'
import FuentesBadge from '../components/FuentesBadge'

interface IdeaResultado {
  score_potencial: number
  veredicto: string
  razones_a_favor: string[]
  riesgos: string[]
  pasos: string[]
  fuentes_recursos: string[]
  oportunidad_nicho: string
}

interface TopSector {
  ciiu2: string
  sector: string
  indice_oportunidad: number
  empresas_activas: number
  empresas_nuevas: number
  cotizantes_formales: number
}

const departamentos = [
  'Amazonas', 'Antioquia', 'Arauca', 'Atlántico', 'Bolívar', 'Boyacá', 'Caldas', 'Caquetá',
  'Casanare', 'Cauca', 'Cesar', 'Chocó', 'Córdoba', 'Cundinamarca', 'Guainía', 'Guaviare',
  'Huila', 'La Guajira', 'Magdalena', 'Meta', 'Nariño', 'Norte de Santander', 'Putumayo',
  'Quindío', 'Risaralda', 'San Andrés y Providencia', 'Santander', 'Sucre', 'Tolima',
  'Valle del Cauca', 'Vaupés', 'Vichada', 'Bogotá D.C.'
]

const inversiones = [
  'Menos de $5 millones',
  '$5 - $20 millones',
  '$20 - $50 millones',
  '$50 - $200 millones',
  'Más de $200 millones',
]

const IDEA_EJEMPLO = `Quiero montar una microempresa de delivery de comida saludable y orgánica en Medellín, dirigida a profesionales de 25-40 años que trabajan desde casa. Inicio con cocina fantasma y apps de domicilios, luego quiero abrir punto físico.`

function TabButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
        active ? 'bg-alba-600 text-white shadow-sm' : 'text-gray-600 hover:bg-gray-100'
      }`}
    >
      {label}
    </button>
  )
}

function ScoreGauge({ score, label }: { score: number; label: string }) {
  const color = score >= 75 ? 'text-green-600' : score >= 50 ? 'text-amber-600' : 'text-rose-600'
  const bg = score >= 75 ? 'bg-green-100' : score >= 50 ? 'bg-amber-100' : 'bg-rose-100'
  return (
    <div className="flex items-center gap-4">
      <div className={`w-24 h-24 rounded-full ${bg} flex items-center justify-center border-4 border-white shadow-sm`}>
        <span className={`text-3xl font-bold ${color}`}>{Math.round(score)}</span>
      </div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className={`text-lg font-semibold ${color}`}>
          {score >= 75 ? 'Alto potencial' : score >= 50 ? 'Potencial moderado' : 'Bajo potencial'}
        </p>
      </div>
    </div>
  )
}

export default function EmprendeIA() {
  const [activeTab, setActiveTab] = useState<'idea' | 'oportunidades'>('idea')
  const [loading, setLoading] = useState(false)

  // Idea
  const [idea, setIdea] = useState(IDEA_EJEMPLO)
  const [departamento, setDepartamento] = useState('Antioquia')
  const [inversion, setInversion] = useState(inversiones[1])
  const [resultadoIdea, setResultadoIdea] = useState<IdeaResultado | null>(null)

  // Oportunidades
  const [deptoOportunidades, setDeptoOportunidades] = useState('Antioquia')
  const [topSectores, setTopSectores] = useState<TopSector[]>([])
  const [loadingTop, setLoadingTop] = useState(false)

  useEffect(() => {
    cargarTopSectores(deptoOportunidades)
  }, [])

  const cargarTopSectores = async (depto: string) => {
    setLoadingTop(true)
    try {
      const res = await api.get(`/emprende/top-sectores/${encodeURIComponent(depto)}`)
      setTopSectores(res.data.sectores || [])
    } catch {
      setTopSectores([])
    } finally {
      setLoadingTop(false)
    }
  }

  const evaluarIdea = async () => {
    if (!idea.trim()) return
    setLoading(true)
    setResultadoIdea(null)
    try {
      const res = await api.post('/emprende/evaluar-idea', {
        idea,
        departamento,
        inversion,
      })
      setResultadoIdea(res.data)
    } catch {
      setResultadoIdea({
        score_potencial: 0,
        veredicto: 'Error al evaluar la idea. Intenta de nuevo.',
        razones_a_favor: [],
        riesgos: [],
        pasos: [],
        fuentes_recursos: [],
        oportunidad_nicho: '',
      })
    }
    setLoading(false)
  }

  const colorScore = (score: number) => {
    if (score >= 75) return '#16a34a'
    if (score >= 50) return '#d97706'
    return '#dc2626'
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">
        Emprende IA
      </h1>
      <p className="text-gray-600 mb-6">
        Evalúa tu idea de negocio con IA y descubre oportunidades por departamento.
      </p>

      <div className="flex flex-wrap gap-2 mb-6">
        <TabButton active={activeTab === 'idea'} onClick={() => setActiveTab('idea')} label="Tengo una idea" />
        <TabButton active={activeTab === 'oportunidades'} onClick={() => setActiveTab('oportunidades')} label="Descubrir oportunidades" />
      </div>

      {/* Tengo una idea */}
      {activeTab === 'idea' && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Describe tu idea de negocio
            </label>
            <textarea
              value={idea}
              onChange={(e) => setIdea(e.target.value)}
              rows={6}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-alba-500 text-sm"
              placeholder="Ej: Quiero montar una cafetería especializada en café de origen en..."
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Departamento</label>
                <select
                  value={departamento}
                  onChange={(e) => setDepartamento(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm"
                >
                  {departamentos.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Inversión inicial aproximada</label>
                <select
                  value={inversion}
                  onChange={(e) => setInversion(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm"
                >
                  {inversiones.map((i) => (
                    <option key={i} value={i}>{i}</option>
                  ))}
                </select>
              </div>
            </div>

            <button
              onClick={evaluarIdea}
              disabled={loading || !idea.trim()}
              className="mt-5 w-full bg-alba-600 text-white py-3 rounded-lg font-medium hover:bg-alba-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>Evaluando con IA...</>
              ) : (
                <>Evaluar potencial</>
              )}
            </button>
          </div>

          {resultadoIdea && (
            <div className="space-y-6">
              {/* Score + veredicto */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                  <ScoreGauge score={resultadoIdea.score_potencial} label="Potencial del negocio" />
                  <div className="flex-1">
                    <h3 className="text-xl font-bold text-gray-900 mb-1">{resultadoIdea.veredicto}</h3>
                    <p className="text-sm text-gray-500">
                      Idea evaluada para <strong>{departamento}</strong> con inversión <strong>{inversion}</strong>.
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Razones a favor */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="font-bold text-gray-900 mb-4">
                    Razones a favor
                  </h3>
                  <ul className="space-y-3">
                    {resultadoIdea.razones_a_favor.map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Riesgos */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="font-bold text-gray-900 mb-4">
                    Riesgos principales
                  </h3>
                  <ul className="space-y-3">
                    {resultadoIdea.riesgos.map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Pasos */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h3 className="font-bold text-gray-900 mb-4">
                  Pasos concretos para empezar
                </h3>
                <ol className="space-y-3">
                  {resultadoIdea.pasos.map((p, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-gray-700">
                      <span className="bg-alba-50 text-alba-700 font-bold rounded-full w-6 h-6 flex items-center justify-center flex-shrink-0 text-xs">
                        {i + 1}
                      </span>
                      {p}
                    </li>
                  ))}
                </ol>
              </div>

              {/* Fuentes de recursos */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="font-bold text-gray-900 mb-4">
                    Fuentes y recursos
                  </h3>
                  <ul className="space-y-2">
                    {resultadoIdea.fuentes_recursos.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-amber-50 border border-amber-100 rounded-xl p-6">
                  <h3 className="font-semibold text-amber-900 mb-2">
                    Oportunidad de nicho
                  </h3>
                  <p className="text-sm text-amber-800">{resultadoIdea.oportunidad_nicho}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Descubrir oportunidades */}
      {activeTab === 'oportunidades' && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <label className="block text-sm font-semibold text-gray-700 mb-2">Selecciona un departamento</label>
            <div className="flex flex-col sm:flex-row gap-3">
              <select
                value={deptoOportunidades}
                onChange={(e) => setDeptoOportunidades(e.target.value)}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm"
              >
                {departamentos.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
              <button
                onClick={() => cargarTopSectores(deptoOportunidades)}
                disabled={loadingTop}
                className="bg-alba-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-alba-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loadingTop ? 'Analizando...' : 'Ver oportunidades'}
              </button>
            </div>
          </div>

          {topSectores.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="font-bold text-gray-900 mb-4">
                Sectores con mayor potencial en {deptoOportunidades}
              </h3>
              <div className="space-y-3">
                {topSectores.map((s, i) => (
                  <div key={i} className="flex items-center gap-4 p-4 rounded-lg border bg-gray-50 border-gray-200">
                    <div
                      className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold"
                      style={{ backgroundColor: colorScore(s.indice_oportunidad) }}
                    >
                      {s.indice_oportunidad}
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-900 text-sm">{s.sector}</h4>
                      <p className="text-xs text-gray-500">
                        Empresas activas: {s.empresas_activas.toLocaleString()} · Nuevas: {s.empresas_nuevas.toLocaleString()} · Cotizantes: {s.cotizantes_formales.toLocaleString()}
                      </p>
                    </div>
                    <span className="text-xs font-medium px-2 py-1 rounded-full bg-white border">
                      #{i + 1}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <FuentesBadge fuentes={['RUES', 'PILA', 'GEIH/DANE', 'Gemma 4 vía DeepInfra']} />
    </div>
  )
}
