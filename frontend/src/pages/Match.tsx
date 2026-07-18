import { useState } from 'react'
import api from '../services/api'
import { useAppMode } from '../hooks/useAppMode'

interface Recurso {
  tipo: 'SENA' | 'online' | 'certificacion' | 'libre'
  nombre: string
}

interface Brecha {
  requisito: string
  peso: number
  como_cubrir: string
  recursos?: Recurso[]
  checked?: boolean
}

interface CvResultado {
  score_match: number
  interpretacion: string
  fortalezas: string[]
  brechas: Brecha[]
  recomendacion_general: string
  // Datos reales del backend (ESCO + OLE)
  esco_ocupacion?: string
  habilidades_requeridas_esco?: number
  habilidades_detectadas?: string[]
  salario_real?: {
    rango_modal: string
    total_graduados: number
    fuente: string
  }
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
  label: string
}

function TabButton({ active, onClick, label }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 py-3 text-xl font-bold rounded-lg transition-all ${
        active
          ? 'bg-gradient-to-b from-amber-300/20 to-amber-700/10 text-white border border-amber-500/50'
          : 'text-white hover:text-gold-400 hover:bg-white/[0.04] border border-transparent'
      }`}
    >
      {label}
    </button>
  )
}

function ScoreGauge({ score, label }: { score: number; label: string }) {
  const color = score >= 75 ? 'text-green-400' : score >= 50 ? 'text-amber-400' : 'text-rose-400'
  const bg = score >= 75 ? 'bg-green-500/10' : score >= 50 ? 'bg-amber-500/10' : 'bg-rose-500/10'
  const border = score >= 75 ? 'border-green-500/30' : score >= 50 ? 'border-amber-500/30' : 'border-rose-500/30'
  return (
    <div className="flex items-center gap-6">
      <div className={`w-32 h-32 rounded-full ${bg} border-2 ${border} flex items-center justify-center`}>
        <span className={`text-5xl font-bold ${color}`}>{Math.round(score)}</span>
      </div>
      <div>
        <p className="text-base text-slate-400 font-semibold">{label}</p>
        <p className={`text-2xl font-bold ${color}`}>
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
  const { isOffline } = useAppMode()
  const iaLabel = isOffline ? 'IA local' : 'Gemini 2.5 Flash-Lite'

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

  const toggleBrecha = (idx: number) => {
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
    <div className="animate-fade-in space-y-5">
      <div>
        <h1 className="text-5xl font-bold text-gold-400 font-display">
          Match Inteligente
        </h1>
        <p className="text-base text-white font-semibold mt-1">
          Conecta perfiles y programas con la demanda laboral real usando IA.
        </p>
      </div>

      <div className="plate p-1.5 flex gap-1.5">
        <TabButton active={activeTab === 'cv'} onClick={() => setActiveTab('cv')} label="CV vs Vacante" />
        <TabButton active={activeTab === 'pensum'} onClick={() => setActiveTab('pensum')} label="Pensum vs Mercado" />
      </div>

      {/* Nota metodológica */}
      <div className="plate card p-5">
        <div className="flex items-start gap-3">
          <div>
            <p className="text-lg text-white font-bold mb-2">¿Cómo funciona este análisis?</p>
            <p className="text-base text-slate-300 leading-relaxed">
              La IA ({iaLabel}) analiza tu perfil o pensum comparándolo con los requisitos de la vacante o las tendencias del mercado laboral.
              El score es una estimación basada en el conocimiento del modelo sobre el mercado colombiano. Las brechas muestran qué te falta y cómo cubrirlo,
              con recursos clasificados por tipo: SENA (gratuito), online (plataformas como Coursera), certificaciones y recursos libres.
            </p>
          </div>
        </div>
      </div>

      {/* CV vs VACANTE */}
      {activeTab === 'cv' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="plate card p-5">
              <label className="block text-base text-white font-bold mb-2">Pega tu CV o describe tu perfil</label>
              <textarea
                value={cv}
                onChange={(e) => setCv(e.target.value)}
                rows={10}
                className="w-full px-4 py-3 border border-white/10 rounded-lg focus:ring-2 focus:ring-amber-500/50 text-base bg-white/[0.03] text-slate-100"
                placeholder="Ej: Ingeniero de sistemas con 3 años de experiencia..."
              />
            </div>

            <div className="plate card p-5">
              <label className="block text-base text-white font-bold mb-2">Pega la vacante laboral</label>
              <textarea
                value={vacante}
                onChange={(e) => setVacante(e.target.value)}
                rows={10}
                className="w-full px-4 py-3 border border-white/10 rounded-lg focus:ring-2 focus:ring-amber-500/50 text-base bg-white/[0.03] text-slate-100"
                placeholder="Ej: Desarrollador Full Stack. Requisitos:..."
              />
            </div>
          </div>

          <button
            onClick={analizarCvVacante}
            disabled={loading || !cv.trim() || !vacante.trim()}
            className="w-full bg-gradient-to-b from-amber-300 to-amber-600 text-[#0a0f1f] py-3 rounded-lg font-bold hover:shadow-lg hover:shadow-amber-500/30 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>Analizando con IA...</>
            ) : (
              <>Calcular match</>
            )}
          </button>

          {cvResultado && (
            <div className="space-y-6">
              <div className="plate card p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                  <ScoreGauge score={cvResultado.score_match} label="Match actual" />
                  <div className="flex-1">
                    <p className="text-lg text-white font-semibold">{cvResultado.interpretacion}</p>
                  </div>
                </div>
              </div>

              {/* Datos reales de ESCO + OLE */}
              {(cvResultado.esco_ocupacion || cvResultado.salario_real) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {cvResultado.esco_ocupacion && (
                        <div className="plate card p-5">
                          <h3 className="text-xl font-bold text-white mb-3">
                            Ocupación ESCO detectada
                          </h3>
                          <p className="text-xl font-semibold text-gold-400 mb-4">{cvResultado.esco_ocupacion}</p>
                          {cvResultado.habilidades_requeridas_esco !== undefined && (
                            <div className="flex items-center gap-6 text-base mb-3">
                              <div>
                                <span className="text-slate-400">Requeridas: </span>
                                <span className="font-bold text-white">{cvResultado.habilidades_requeridas_esco}</span>
                              </div>
                              <div>
                                <span className="text-slate-400">Detectadas en CV: </span>
                                <span className="font-bold text-green-400">{cvResultado.habilidades_detectadas?.length || 0}</span>
                              </div>
                            </div>
                          )}
                          {cvResultado.habilidades_detectadas && cvResultado.habilidades_detectadas.length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {cvResultado.habilidades_detectadas.map((h, i) => (
                                <span key={i} className="text-sm px-3 py-1 rounded-full bg-green-500/15 text-green-400 border border-green-500/30">
                                  {h}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {cvResultado.salario_real && (
                        <div className="plate card p-5">
                          <h3 className="text-xl font-bold text-white mb-3">
                            Salario real de egresados
                          </h3>
                          <p className="text-2xl font-bold text-gold-400 mb-2">{cvResultado.salario_real.rango_modal}</p>
                          <p className="text-base text-slate-300">
                            Basado en <strong className="text-white">{Math.round(cvResultado.salario_real.total_graduados).toLocaleString("es-CO")}</strong> graduados reales
                          </p>
                          <p className="text-sm text-slate-500 mt-1">Fuente: {cvResultado.salario_real.fuente}</p>
                        </div>
                      )}
                </div>
              )}

              {cvResultado.fortalezas.length > 0 && (
                <div className="plate card p-6">
                  <h3 className="text-xl font-bold text-white mb-4">
                    Fortalezas
                  </h3>
                  <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {cvResultado.fortalezas.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-base text-slate-200">
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {cvResultado.brechas.length > 0 && (
                <div className="plate card p-6">
                  <h3 className="text-xl font-bold text-white mb-4">
                    ¿Qué te falta? Marca lo que ya cumples o podrías cubrir
                  </h3>
                  <div className="space-y-4">
                    {cvResultado.brechas.map((b, i) => (
                      <label
                        key={i}
                        className={`flex items-start gap-3 p-5 rounded-lg border cursor-pointer transition-colors ${
                          checkedBrechas[i] ? 'bg-green-500/10 border-green-500/30' : 'bg-white/[0.03] border-white/10 hover:bg-white/[0.05]'
                        }`}
                      >
                        <input
                          type="checkbox"
                          className="mt-1 w-5 h-5 text-amber-600"
                          checked={!!checkedBrechas[i]}
                          onChange={() => toggleBrecha(i)}
                        />
                        <div className="flex-1">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-lg font-bold text-white">{b.requisito}</span>
                            <span className="text-sm font-bold bg-amber-500/20 text-amber-400 px-3 py-1 rounded-full border border-amber-500/30">
                              +{b.peso} pts
                            </span>
                          </div>
                          <p className="text-base text-slate-300 mb-3">{b.como_cubrir}</p>
                          {b.recursos && b.recursos.length > 0 && (
                            <div className="space-y-2">
                              <p className="text-sm text-slate-400 font-bold">Recursos recomendados:</p>
                              {b.recursos.map((r, idx) => (
                                <div key={idx} className="flex items-center gap-2 text-base">
                                  <span className={`px-2 py-0.5 rounded font-bold ${
                                    r.tipo === 'SENA' ? 'bg-green-500/20 text-green-400' :
                                    r.tipo === 'online' ? 'bg-blue-500/20 text-blue-400' :
                                    r.tipo === 'certificacion' ? 'bg-purple-500/20 text-purple-400' :
                                    'bg-slate-500/20 text-slate-400'
                                  }`}>
                                    {r.tipo}
                                  </span>
                                  <span className="text-slate-200">{r.nombre}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </label>
                    ))}
                  </div>

                  <div className="mt-6 p-5 bg-blue-500/10 border border-blue-500/30 rounded-xl flex items-center justify-between">
                    <div>
                      <p className="text-base text-blue-300">Si cubres lo marcado, tu score podría subir a:</p>
                      <p className="text-sm text-blue-400/70">El puntaje es una estimación; el orden y la profundidad también importan.</p>
                    </div>
                    <div className="text-right">
                      <p className="text-4xl font-bold text-blue-400">{Math.round(scoreSimulado())}</p>
                      <p className="text-sm text-blue-400/70">puntos</p>
                    </div>
                  </div>
                </div>
              )}

              {cvResultado.recomendacion_general && (
                <div className="plate card p-6 bg-amber-500/5 border-amber-500/20">
                  <h4 className="text-lg font-bold text-amber-300 mb-2">
                    Recomendación general
                  </h4>
                  <p className="text-base text-amber-200/90">{cvResultado.recomendacion_general}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* PENSUM vs MERCADO */}
      {activeTab === 'pensum' && (
        <div className="space-y-6">
          <div className="plate card p-5">
            <label className="block text-base text-white font-bold mb-2">Pega el pensum académico o contenido del programa</label>
            <textarea
              value={pensum}
              onChange={(e) => setPensum(e.target.value)}
              rows={14}
              className="w-full px-4 py-3 border border-white/10 rounded-lg focus:ring-2 focus:ring-amber-500/50 text-base bg-white/[0.03] text-slate-100"
              placeholder="Ej: Semestre 1: Cálculo, Programación básica..."
            />
          </div>

          <button
            onClick={analizarPensum}
            disabled={loading || !pensum.trim()}
            className="w-full bg-gradient-to-b from-amber-300 to-amber-600 text-[#0a0f1f] py-3 rounded-lg font-bold hover:shadow-lg hover:shadow-amber-500/30 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>Analizando con IA...</>
            ) : (
              <>Analizar alineación con el mercado</>
            )}
          </button>

          {pensumResultado && (
            <div className="space-y-6">
              <div className="plate card p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                  <ScoreGauge score={pensumResultado.score_alineacion} label="Alineación con el mercado" />
                  <div className="flex-1">
                    <p className="text-lg text-white font-semibold">{pensumResultado.interpretacion}</p>
                  </div>
                </div>
              </div>

              {pensumResultado.fortalezas.length > 0 && (
                <div className="plate card p-6">
                  <h3 className="text-xl font-bold text-white mb-4">
                    Fortalezas del pensum
                  </h3>
                  <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {pensumResultado.fortalezas.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-base text-slate-200">
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {pensumResultado.brechas_mercado.length > 0 && (
                <div className="plate card p-6">
                  <h3 className="text-xl font-bold text-white mb-4">
                    Brechas con el mercado laboral
                  </h3>
                  <div className="space-y-4">
                    {pensumResultado.brechas_mercado.map((b, i) => (
                      <div key={i} className="p-5 rounded-lg border bg-white/[0.03] border-white/10">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-lg font-bold text-white">{b.area}</span>
                          <span
                            className={`text-sm font-bold px-3 py-1 rounded-full ${
                              b.nivel_importancia === 'alta'
                                ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                                : b.nivel_importancia === 'media'
                                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                            }`}
                          >
                            {b.nivel_importancia === 'alta' ? 'Alta importancia' : b.nivel_importancia === 'media' ? 'Media importancia' : 'Baja importancia'}
                          </span>
                        </div>
                        <p className="text-base text-slate-300">{b.sugerencia}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {pensumResultado.recomendacion_general && (
                <div className="plate card p-6 bg-amber-500/5 border-amber-500/20">
                  <h4 className="text-lg font-bold text-amber-300 mb-2">
                    Recomendación general
                  </h4>
                  <p className="text-base text-amber-200/90">{pensumResultado.recomendacion_general}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

    </div>
  )
}
