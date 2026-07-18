import { useState } from 'react'
import api from '../services/api'
import { useAppMode } from '../hooks/useAppMode'

interface IdeaResultado {
  score_potencial: number
  veredicto: string
  razones_a_favor: string[]
  riesgos: string[]
  pasos: string[]
  fuentes_recursos: string[]
  oportunidad_nicho: string
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

function ScoreGauge({ score, label }: { score: number; label: string }) {
  const color = score >= 75 ? 'text-green-500' : score >= 50 ? 'text-amber-500' : 'text-rose-500'
  const bg = score >= 75 ? 'bg-green-500/10' : score >= 50 ? 'bg-amber-500/10' : 'bg-rose-500/10'
  const border = score >= 75 ? 'border-green-500/30' : score >= 50 ? 'border-amber-500/30' : 'border-rose-500/30'
  return (
    <div className="flex items-center gap-6">
      <div className={`w-28 h-28 rounded-full ${bg} ${border} border-2 flex items-center justify-center`}>
        <span className={`text-4xl font-bold ${color}`}>{Math.round(score)}</span>
      </div>
      <div>
        <p className="text-base text-slate-400 font-semibold">{label}</p>
        <p className={`text-2xl font-bold ${color}`}>
          {score >= 75 ? 'Alto potencial' : score >= 50 ? 'Potencial moderado' : 'Bajo potencial'}
        </p>
      </div>
    </div>
  )
}

export default function EmprendeIA() {
  const [loading, setLoading] = useState(false)
  const { isOffline } = useAppMode()
  const iaLabel = isOffline ? 'IA local' : 'Gemma 4 vía DeepInfra'

  // Idea
  const [idea, setIdea] = useState(IDEA_EJEMPLO)
  const [departamento, setDepartamento] = useState('Antioquia')
  const [inversion, setInversion] = useState(inversiones[1])
  const [resultadoIdea, setResultadoIdea] = useState<IdeaResultado | null>(null)

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
      <h1 className="text-5xl font-bold text-gold-400 mb-2 font-display">
        Emprende IA
      </h1>
      <p className="text-base text-white font-semibold mb-6">
        Evalúa tu idea de negocio con IA para el mercado colombiano.
      </p>

      <div className="space-y-6">
        <div className="plate card p-6">
          <h2 className="text-2xl font-bold text-white mb-1 font-display">
            Tu idea de negocio
          </h2>
          <p className="text-sm text-slate-400 mb-5">
            Describe la idea, el departamento y la inversión inicial para evaluar el potencial en Colombia.
          </p>

          <label className="block text-base text-white font-bold mb-2">
            Describe tu idea de negocio
          </label>
          <textarea
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            rows={6}
            className="w-full px-4 py-3 rounded-lg text-base bg-white/[0.03] border border-white/10 text-slate-100 placeholder:text-slate-500 focus:ring-2 focus:ring-gold-500/50"
            placeholder="Ej: Quiero montar una cafetería especializada en café de origen en..."
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div>
              <label className="block text-base text-white font-bold mb-2">Departamento</label>
              <select
                value={departamento}
                onChange={(e) => setDepartamento(e.target.value)}
                className="w-full px-4 py-3 rounded-lg text-base bg-white/[0.03] border border-white/10 text-slate-100"
              >
                {departamentos.map((d) => (
                  <option key={d} value={d} className="bg-[#0a0f1f] text-slate-100">{d}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-base text-white font-bold mb-2">Inversión inicial aproximada</label>
              <select
                value={inversion}
                onChange={(e) => setInversion(e.target.value)}
                className="w-full px-4 py-3 rounded-lg text-base bg-white/[0.03] border border-white/10 text-slate-100"
              >
                {inversiones.map((i) => (
                  <option key={i} value={i} className="bg-[#0a0f1f] text-slate-100">{i}</option>
                ))}
              </select>
            </div>
          </div>

          <button
            onClick={evaluarIdea}
            disabled={loading || !idea.trim()}
            className="btn btn-gold mt-5"
            style={{ width: '100%', justifyContent: 'center', padding: '14px' }}
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
            <div className="plate card p-6">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                <ScoreGauge score={resultadoIdea.score_potencial} label="Potencial del negocio" />
                <div className="flex-1">
                  <h3 className="text-2xl font-bold text-white mb-1">{resultadoIdea.veredicto}</h3>
                  <p className="text-base text-slate-400">
                    Idea evaluada para <strong className="text-white">{departamento}</strong> con inversión <strong className="text-white">{inversion}</strong>.
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Razones a favor */}
              <div className="plate card p-6">
                <h3 className="text-xl font-bold text-white mb-4 font-display">
                  Razones a favor
                </h3>
                <ul className="space-y-3">
                  {resultadoIdea.razones_a_favor.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-base text-slate-300">
                      {r}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Riesgos */}
              <div className="plate card p-6">
                <h3 className="text-xl font-bold text-white mb-4 font-display">
                  Riesgos principales
                </h3>
                <ul className="space-y-3">
                  {resultadoIdea.riesgos.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-base text-slate-300">
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Pasos */}
            <div className="plate card p-6">
              <h3 className="text-xl font-bold text-white mb-4 font-display">
                Pasos concretos para empezar
              </h3>
              <ol className="space-y-3">
                {resultadoIdea.pasos.map((p, i) => (
                  <li key={i} className="flex items-start gap-3 text-base text-slate-300">
                    <span className="w-7 h-7 rounded-full bg-gold-500/15 text-gold-400 border border-gold-500/30 font-bold flex items-center justify-center flex-shrink-0 text-sm">
                      {i + 1}
                    </span>
                    {p}
                  </li>
                ))}
              </ol>
            </div>

            {/* Fuentes de recursos */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="plate card p-6">
                <h3 className="text-xl font-bold text-white mb-4 font-display">
                  Fuentes y recursos
                </h3>
                <ul className="space-y-2">
                  {resultadoIdea.fuentes_recursos.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-base text-slate-300">
                      {f}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="plate card p-6 border-amber-500/20 bg-amber-500/5">
                <h3 className="text-xl font-bold text-amber-300 mb-2 font-display">
                  Oportunidad de nicho
                </h3>
                <p className="text-base text-amber-200/90">{resultadoIdea.oportunidad_nicho}</p>
              </div>
            </div>
          </div>
        )}
      </div>

    </div>
  )
}
