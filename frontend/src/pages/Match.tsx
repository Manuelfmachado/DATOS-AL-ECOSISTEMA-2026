import { useState, type ReactNode } from 'react'
import Icon from '../components/Icon'
import api from '../services/api'
import FuentesBadge from '../components/FuentesBadge'

interface Brecha {
  requisito: string
  peso: number
  como_cubrir: string
  checked?: boolean
}

interface CvResultado {
  score_match: number
  interpretacion: string
  fortalezas: string[]
  brechas: Brecha[]
  recomendacion_general: string
}

interface BrechaMercado {
  area: string
  nivel_importancia: 'alta' | 'media' | 'baja'
  sugerencia: string
}

interface PensumResultado {
  score_alineacion: number
  interpretacion: string
  fortalezas: string[]
  brechas_mercado: BrechaMercado[]
  recomendacion_general: string
}

interface TabButtonProps {
  active: boolean
  onClick: () => void
  icon: ReactNode
  label: string
}

function TabButton({ active, onClick, icon, label }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
        active ? 'bg-alba-600 text-white shadow-sm' : 'text-gray-600 hover:bg-gray-100'
      }`}
    >
      {icon}
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
          {score >= 75 ? 'Alto' : score >= 50 ? 'Medio' : 'Bajo'}
        </p>
      </div>
    </div>
  )
}

const CV_EJEMPLO = `Ingeniero de sistemas con 5 años de experiencia en Python, SQL, análisis de datos con pandas y trabajo en equipos ágiles. Conocimientos básicos en machine learning. Inglés intermedio. Proactivo y buen comunicador.`

const VACANTE_EJEMPLO = `Data Scientist Senior
Requisitos:
- Python avanzado
- SQL y bases de datos
- Machine learning y estadística
- Inglés B2+
- 3+ años de experiencia
- Comunicación efectiva y trabajo en equipo`

const PENSUM_EJEMPLO = `Programa de Ingeniería de Sistemas:
Semestres 1-2: Cálculo, Álgebra, Física, Programación básica.
Semestres 3-4: Estructuras de datos, Bases de datos, Redes, Ingeniería de software.
Semestres 5-6: Inteligencia artificial, Machine learning, Seguridad informática, Desarrollo web.
Semestres 7-8: Electivas, práctica profesional, trabajo de grado.`

export default function Match() {
  const [activeTab, setActiveTab] = useState<'cv' | 'pensum'>('cv')
  const [loading, setLoading] = useState(false)

  // CV vs Vacante
  const [cv, setCv] = useState(CV_EJEMPLO)
  const [vacante, setVacante] = useState(VACANTE_EJEMPLO)
  const [cvResultado, setCvResultado] = useState<CvResultado | null>(null)
  const [checkedBrechas, setCheckedBrechas] = useState<Record<number, boolean>>({})

  // Pensum
  const [pensum, setPensum] = useState(PENSUM_EJEMPLO)
  const [pensumResultado, setPensumResultado] = useState<PensumResultado | null>(null)

  const analizarCvVacante = async () => {
    if (!cv.trim() || !vacante.trim()) return
    setLoading(true)
    setCvResultado(null)
    setCheckedBrechas({})
    try {
      const res = await api.post('/match/cv-vacante', { cv, vacante })
      setCvResultado(res.data)
    } catch {
      setCvResultado({
        score_match: 0,
        interpretacion: 'Error al analizar el match. Intenta de nuevo.',
        fortalezas: [],
        brechas: [],
        recomendacion_general: '',
      })
    }
    setLoading(false)
  }

  const analizarPensum = async () => {
    if (!pensum.trim()) return
    setLoading(true)
    setPensumResultado(null)
    try {
      const res = await api.post('/match/pensum', { pensum })
      setPensumResultado(res.data)
    } catch {
      setPensumResultado({
        score_alineacion: 0,
        interpretacion: 'Error al analizar el pensum. Intenta de nuevo.',
        fortalezas: [],
        brechas_mercado: [],
        recomendacion_general: '',
      })
    }
    setLoading(false)
  }

  const toggleBrecha = (idx: number, peso: number) => {
    setCheckedBrechas((prev) => {
      const next = { ...prev, [idx]: !prev[idx] }
      return next
    })
  }

  const scoreSimulado = () => {
    if (!cvResultado) return 0
    let extra = 0
    cvResultado.brechas.forEach((b, idx) => {
      if (checkedBrechas[idx]) extra += b.peso
    })
    return Math.min(100, cvResultado.score_match + extra)
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-2 font-display">Match Inteligente</h1>
      <p className="text-gray-600 mb-6">Conecta perfiles y programas con la demanda laboral real usando IA.</p>

      <div className="flex flex-wrap gap-2 mb-6">
        <TabButton active={activeTab === 'cv'} onClick={() => setActiveTab('cv')} icon={<Icon.CoachDocumento size={18} />} label="CV vs Vacante" />
        <TabButton active={activeTab === 'pensum'} onClick={() => setActiveTab('pensum')} icon={<Icon.PrediccionUp size={18} />} label="Pensum vs Mercado" />
      </div>

      {/* CV vs VACANTE */}
      {activeTab === 'cv' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
              <label className="block text-sm font-semibold text-gray-700 mb-2">Pega tu CV o describe tu perfil</label>
              <textarea
                value={cv}
                onChange={(e) => setCv(e.target.value)}
                rows={10}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-alba-500 text-sm"
                placeholder="Ej: Ingeniero de sistemas con 3 años de experiencia..."
              />
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
              <label className="block text-sm font-semibold text-gray-700 mb-2">Pega la vacante laboral</label>
              <textarea
                value={vacante}
                onChange={(e) => setVacante(e.target.value)}
                rows={10}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-alba-500 text-sm"
                placeholder="Ej: Desarrollador Full Stack. Requisitos:..."
              />
            </div>
          </div>

          <button
            onClick={analizarCvVacante}
            disabled={loading || !cv.trim() || !vacante.trim()}
            className="w-full bg-alba-600 text-white py-3 rounded-lg font-medium hover:bg-alba-700 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <><span className="animate-spin inline-block"><Icon.Accion.Buscar size={18} /></span> Analizando con IA...</>
            ) : (
              <><Icon.Match size={18} /> Calcular match</>
            )}
          </button>

          {cvResultado && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                  <ScoreGauge score={cvResultado.score_match} label="Match actual" />
                  <div className="flex-1">
                    <p className="text-gray-700">{cvResultado.interpretacion}</p>
                  </div>
                </div>              </div>

              {cvResultado.fortalezas.length > 0 && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <span className="text-green-600 inline-flex"><Icon.Accion.Check size={20} /></span>
                    Fortalezas
                  </h3>
                  <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {cvResultado.fortalezas.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                        <span className="text-green-500 mt-0.5 inline-flex"><Icon.Accion.Check size={16} /></span>
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {cvResultado.brechas.length > 0 && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <span className="text-amber-500 inline-flex"><Icon.Kpi.Desempleo size={20} /></span>
                    ¿Qué te falta? Marca lo que ya cumples o podrías cubrir
                  </h3>
                  <div className="space-y-3">
                    {cvResultado.brechas.map((b, i) => (
                      <label
                        key={i}
                        className={`flex items-start gap-3 p-4 rounded-lg border cursor-pointer transition-colors ${
                          checkedBrechas[i] ? 'bg-green-50 border-green-300' : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                        }`}
                      >
                        <input
                          type="checkbox"
                          className="mt-1 w-4 h-4 text-alba-600"
                          checked={!!checkedBrechas[i]}
                          onChange={() => toggleBrecha(i, b.peso)}
                        />
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-gray-900">{b.requisito}</span>
                            <span className="text-xs font-medium bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">
                              +{b.peso} pts
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 mt-1">{b.como_cubrir}</p>
                        </div>
                      </label>
                    ))}
                  </div>

                  <div className="mt-6 p-5 bg-blue-50 border border-blue-100 rounded-xl flex items-center justify-between">
                    <div>
                      <p className="text-sm text-blue-900">Si cubres lo marcado, tu score podría subir a:</p>
                      <p className="text-xs text-blue-700">El puntaje es una estimación; el orden y la profundidad también importan.</p>
                    </div>
                    <div className="text-right">
                      <p className="text-3xl font-bold text-blue-700">{Math.round(scoreSimulado())}</p>
                      <p className="text-xs text-blue-600">puntos</p>
                    </div>
                  </div>
                </div>
              )}

              {cvResultado.recomendacion_general && (
                <div className="bg-amber-50 border border-amber-100 rounded-xl p-5">
                  <h4 className="font-semibold text-amber-900 mb-2 flex items-center gap-2">
                    <span className="text-amber-700 inline-flex"><Icon.EmprendeIdea size={18} /></span>
                    Recomendación general
                  </h4>
                  <p className="text-sm text-amber-800">{cvResultado.recomendacion_general}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* PENSUM vs MERCADO */}
      {activeTab === 'pensum' && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <label className="block text-sm font-semibold text-gray-700 mb-2">Pega el pensum académico o contenido del programa</label>
            <textarea
              value={pensum}
              onChange={(e) => setPensum(e.target.value)}
              rows={14}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-alba-500 text-sm"
              placeholder="Ej: Semestre 1: Cálculo, Programación básica..."
            />
          </div>

          <button
            onClick={analizarPensum}
            disabled={loading || !pensum.trim()}
            className="w-full bg-alba-600 text-white py-3 rounded-lg font-medium hover:bg-alba-700 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <><span className="animate-spin inline-block"><Icon.Accion.Buscar size={18} /></span> Analizando con IA...</>
            ) : (
              <><Icon.PrediccionUp size={18} /> Analizar alineación con el mercado</>
            )}
          </button>

          {pensumResultado && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                  <ScoreGauge score={pensumResultado.score_alineacion} label="Alineación con el mercado" />
                  <div className="flex-1">
                    <p className="text-gray-700">{pensumResultado.interpretacion}</p>
                  </div>
                </div>
              </div>

              {pensumResultado.fortalezas.length > 0 && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <span className="text-green-600 inline-flex"><Icon.Accion.Check size={20} /></span>
                    Fortalezas del pensum
                  </h3>
                  <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {pensumResultado.fortalezas.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                        <span className="text-green-500 mt-0.5 inline-flex"><Icon.Accion.Check size={16} /></span>
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {pensumResultado.brechas_mercado.length > 0 && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <span className="text-amber-500 inline-flex"><Icon.Kpi.Desempleo size={20} /></span>
                    Brechas con el mercado laboral
                  </h3>
                  <div className="space-y-3">
                    {pensumResultado.brechas_mercado.map((b, i) => (
                      <div key={i} className="p-4 rounded-lg border bg-gray-50 border-gray-200">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-semibold text-gray-900">{b.area}</span>
                          <span
                            className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                              b.nivel_importancia === 'alta'
                                ? 'bg-red-100 text-red-800'
                                : b.nivel_importancia === 'media'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-blue-100 text-blue-800'
                            }`}
                          >
                            {b.nivel_importancia === 'alta' ? 'Alta importancia' : b.nivel_importancia === 'media' ? 'Media importancia' : 'Baja importancia'}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600">{b.sugerencia}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {pensumResultado.recomendacion_general && (
                <div className="bg-amber-50 border border-amber-100 rounded-xl p-5">
                  <h4 className="font-semibold text-amber-900 mb-2 flex items-center gap-2">
                    <span className="text-amber-700 inline-flex"><Icon.EmprendeIdea size={18} /></span>
                    Recomendación general
                  </h4>
                  <p className="text-sm text-amber-800">{pensumResultado.recomendacion_general}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <FuentesBadge fuentes={['Gemma 4 vía DeepInfra', 'O*NET', 'ESCO', 'SNIES', 'SENA']} />
    </div>
  )
}
