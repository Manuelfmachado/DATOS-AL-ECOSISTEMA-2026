import { useState, useRef, useEffect } from 'react'
import api from '../services/api'
import FuentesBadge from '../components/FuentesBadge'
import { CoachLiveClient, CoachLiveEvent } from '../services/geminiLive'

interface CvResultado {
  cv_mejorado: string
  por_que_es_bueno: string
  palabras_clave_ats: string[]
  cambios_realizados: string[]
}

const CV_EJEMPLO = `NOMBRE: Juan Pérez
PROFESIÓN: Ingeniero de sistemas
EXPERIENCIA:
- 3 años desarrollando aplicaciones web en una startup
- Manejo de Python, JavaScript y SQL
- Trabajo en equipo bajo metodología Scrum

EDUCACIÓN:
- Ingeniero de Sistemas, Universidad Nacional

HABILIDADES:
- Python, JavaScript, SQL, Git, trabajo en equipo, resolución de problemas`

const VACANTE_EJEMPLO = `Desarrollador Full Stack Senior. Requisitos: 4+ años de experiencia, Python, React, bases de datos SQL, Git, inglés intermedio, liderazgo técnico.`

function TabButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className="btn text-lg font-bold text-white"
      style={active ? {
        color: '#ffffff',
        background: 'linear-gradient(180deg, rgba(212, 175, 55, 0.18) 0%, rgba(212, 175, 55, 0.06) 100%)',
        borderColor: 'rgba(212, 175, 55, 0.95)',
        boxShadow: '0 0 0 1px rgba(212, 175, 55, 0.35), 0 0 22px -2px rgba(212, 175, 55, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.18)',
      } : {
        color: '#ffffff',
      }}
    >
      {label}
    </button>
  )
}

interface MensajeChat {
  rol: 'alba' | 'usuario'
  text: string
}

interface FeedbackFinal {
  puntaje_general: number
  fortalezas: string[]
  areas_mejora: string[]
  recomendacion: string
  sugerencia_practica: string
}

export default function Coach() {
  const [tab, setTab] = useState<'cv' | 'entrevista' | 'voz'>('cv')
  const [loading, setLoading] = useState(false)

  // CV
  const [cv, setCv] = useState(CV_EJEMPLO)
  const [vacanteCv, setVacanteCv] = useState(VACANTE_EJEMPLO)
  const [archivo, setArchivo] = useState<File | null>(null)
  const [resultadoCv, setResultadoCv] = useState<CvResultado | null>(null)
  const [copiado, setCopiado] = useState(false)

  // Entrevista estructurada
  const [cvEnt, setCvEnt] = useState(CV_EJEMPLO)
  const [vacanteEnt, setVacanteEnt] = useState(VACANTE_EJEMPLO)
  const [entrevistaIniciada, setEntrevistaIniciada] = useState(false)
  const [entrevistaIniciando, setEntrevistaIniciando] = useState(false)
  const [entrevistaFinalizada, setEntrevistaFinalizada] = useState(false)
  const [numeroPregunta, setNumeroPregunta] = useState(0)
  const [totalPreguntas] = useState(10)
  const [mensajes, setMensajes] = useState<MensajeChat[]>([])
  const [respuestaInput, setRespuestaInput] = useState('')
  const [enviandoRespuesta, setEnviandoRespuesta] = useState(false)
  const [feedback, setFeedback] = useState<FeedbackFinal | null>(null)
  const [sessionId, setSessionId] = useState('')
  const [errorEnt, setErrorEnt] = useState('')
  const chatEndRef = useRef<HTMLDivElement | null>(null)

  // Entrevista por voz (Gemini Live API)
  const [modoVoz, setModoVoz] = useState<'realista' | 'libre'>('realista')
  const [cvVoz, setCvVoz] = useState(CV_EJEMPLO)
  const [vacanteVoz, setVacanteVoz] = useState(VACANTE_EJEMPLO)
  const [vozLive, setVozLive] = useState('Puck')
  const [liveStatus, setLiveStatus] = useState<'idle' | 'connecting' | 'connected' | 'disconnected' | 'error'>('idle')
  const [transcripciones, setTranscripciones] = useState<{ rol: 'user' | 'gemini'; text: string }[]>([])
  const clientRef = useRef<CoachLiveClient | null>(null)

  const VOCES = [
    { id: 'Puck', label: 'Puck (masculina, ágil)' },
    { id: 'Charon', label: 'Charon (masculina, grave)' },
    { id: 'Orus', label: 'Orus (masculina, firme)' },
    { id: 'Kore', label: 'Kore (femenina, cálida)' },
    { id: 'Aoede', label: 'Aoede (femenina, suave)' },
    { id: 'Leda', label: 'Leda (femenina, joven)' },
    { id: 'Sulafat', label: 'Sulafat (femenina, madura)' },
    { id: 'Zephyr', label: 'Zephyr (neutra, ligera)' },
    { id: 'Fenrir', label: 'Fenrir (neutra, profunda)' },
    { id: 'Autonoe', label: 'Autonoe (neutra, moderna)' },
    { id: 'Laomedeia', label: 'Laomedeia (neutra, serena)' },
    { id: 'Despina', label: 'Despina (neutra, clara)' },
  ]

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajes])

  const mejorarCv = async () => {
    setLoading(true)
    setResultadoCv(null)
    try {
      let res
      if (archivo) {
        const form = new FormData()
        form.append('file', archivo)
        form.append('vacante', vacanteCv)
        res = await api.post('/coach/mejorar-cv-archivo', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      } else {
        res = await api.post('/coach/mejorar-cv', { cv, vacante: vacanteCv })
      }
      setResultadoCv(res.data)
    } catch {
      setResultadoCv({
        cv_mejorado: 'Error al mejorar el CV. Intenta de nuevo.',
        por_que_es_bueno: '',
        palabras_clave_ats: [],
        cambios_realizados: [],
      })
    }
    setLoading(false)
  }

  const copiarCv = async () => {
    if (!resultadoCv?.cv_mejorado) return
    await navigator.clipboard.writeText(resultadoCv.cv_mejorado)
    setCopiado(true)
    setTimeout(() => setCopiado(false), 2000)
  }

  // Entrevista estructurada
  const iniciarEntrevista = async () => {
    setEntrevistaIniciando(true)
    setErrorEnt('')
    setMensajes([])
    setFeedback(null)
    setEntrevistaFinalizada(false)
    try {
      const res = await api.post('/coach/entrevista-realista/iniciar', {
        cv: cvEnt,
        vacante: vacanteEnt,
      })
      setSessionId(res.data.session_id)
      const saludo = res.data.saludo || ''
      const pregunta = res.data.pregunta_actual || ''
      setMensajes([
        { rol: 'alba', text: saludo },
        { rol: 'alba', text: pregunta },
      ])
      setNumeroPregunta(1)
      setEntrevistaIniciada(true)
    } catch (e: any) {
      setErrorEnt(e?.response?.data?.detail || 'No se pudo iniciar la entrevista. Intenta de nuevo.')
    }
    setEntrevistaIniciando(false)
  }

  const enviarRespuesta = async () => {
    if (!respuestaInput.trim() || enviandoRespuesta) return
    const resp = respuestaInput.trim()
    setMensajes((prev) => [...prev, { rol: 'usuario', text: resp }])
    setRespuestaInput('')
    setEnviandoRespuesta(true)
    try {
      const res = await api.post('/coach/entrevista-realista/avanzar', {
        session_id: sessionId,
        respuesta: resp,
      })
      if (res.data.estado === 'finalizada') {
        setEntrevistaFinalizada(true)
        setFeedback(res.data.feedback)
        setMensajes((prev) => [...prev, { rol: 'alba', text: '¡Gracias por tu tiempo! Aquí está mi evaluación de tu entrevista:' }])
      } else {
        const reconocimiento = res.data.breve_reconocimiento || ''
        const nuevaPregunta = res.data.pregunta_actual || ''
        setNumeroPregunta(res.data.numero_pregunta)
        if (reconocimiento) {
          setMensajes((prev) => [...prev, { rol: 'alba', text: `${reconocimiento} Pasemos a la pregunta ${res.data.numero_pregunta} de 10.` }])
        }
        setMensajes((prev) => [...prev, { rol: 'alba', text: nuevaPregunta }])
      }
    } catch (e: any) {
      setErrorEnt(e?.response?.data?.detail || 'Error al procesar tu respuesta.')
    }
    setEnviandoRespuesta(false)
  }

  const reiniciarEntrevista = () => {
    setEntrevistaIniciada(false)
    setEntrevistaFinalizada(false)
    setMensajes([])
    setFeedback(null)
    setRespuestaInput('')
    setNumeroPregunta(0)
    setSessionId('')
    setErrorEnt('')
  }

  // Entrevista por voz: gestion del cliente Gemini Live
  const handleLiveEvent = (event: CoachLiveEvent) => {
    if (event.type === 'user' && event.text) {
      setTranscripciones((prev) => {
        const last = prev[prev.length - 1]
        if (last && last.rol === 'user') {
          return [...prev.slice(0, -1), { rol: 'user', text: last.text + event.text }]
        }
        return [...prev, { rol: 'user', text: event.text! }]
      })
    } else if (event.type === 'gemini' && event.text) {
      setTranscripciones((prev) => {
        const last = prev[prev.length - 1]
        if (last && last.rol === 'gemini') {
          return [...prev.slice(0, -1), { rol: 'gemini', text: last.text + event.text }]
        }
        return [...prev, { rol: 'gemini', text: event.text! }]
      })
    } else if (event.type === 'interrupted') {
      clientRef.current?.stopAudioPlayback()
    } else if (event.type === 'error') {
      console.error('[CoachLive] Error:', event.error)
    }
  }

  const connectLive = async () => {
    setTranscripciones([])
    setLiveStatus('connecting')
    const client = new CoachLiveClient({
      onEvent: handleLiveEvent,
      onStatus: (status) => setLiveStatus(status),
    })
    clientRef.current = client
    try {
      await client.connect({
        modo: modoVoz,
        cv: modoVoz === 'realista' ? cvVoz : '',
        vacante: vacanteVoz,
        voice: vozLive,
      })
      await client.startMic()
    } catch (e) {
      console.error('[CoachLive] No se pudo conectar:', e)
      setLiveStatus('error')
    }
  }

  const disconnectLive = () => {
    clientRef.current?.disconnect()
    clientRef.current = null
  }

  useEffect(() => {
    return () => {
      clientRef.current?.disconnect()
      clientRef.current = null
    }
  }, [])

  const connected = liveStatus === 'connected'

  return (
    <div className="animate-fade-in">
      <header className="topbar">
        <div>
          <h1 className="text-5xl font-bold text-white font-display">Coach IA</h1>
          <p className="hello-sub text-base text-white font-semibold">Prepárate para conseguir empleo: mejora tu CV o practica una entrevista en vivo por voz.</p>
        </div>
      </header>

      {/* Pestañas */}
      <div className="flex gap-2 mb-6">
        <TabButton active={tab === 'cv'} onClick={() => setTab('cv')} label="Mejorar CV" />
        <TabButton active={tab === 'entrevista'} onClick={() => setTab('entrevista')} label="Practicar entrevista" />
        <TabButton active={tab === 'voz'} onClick={() => setTab('voz')} label="Entrevista por voz" />
      </div>

      {tab === 'cv' && (
        <div className="space-y-6">
          <div className="plate card">
            <div className="panel-head">
              <div>
                <h2 className="panel-title text-2xl font-bold text-white">Mejorar tu CV con IA</h2>
                <p className="panel-sub">Pega tu CV o carga un archivo y la IA lo optimiza para filtros ATS</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" style={{ position: 'relative', zIndex: 1 }}>
              <div>
                <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--text-dim)' }}>Pega tu CV o carga un archivo</label>
                <textarea
                  value={cv}
                  onChange={(e) => setCv(e.target.value)}
                  rows={10}
                  className="w-full px-4 py-3 rounded-lg text-sm"
                  style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.10)',
                    color: 'var(--text)',
                  }}
                  placeholder="Pega aquí el texto de tu CV..."
                />
                <div className="mt-3">
                  <label
                    className="flex items-center gap-2 px-4 py-2 rounded-lg cursor-pointer text-sm w-fit"
                    style={{
                      border: '1px solid rgba(255,255,255,0.10)',
                      background: 'rgba(255,255,255,0.03)',
                      color: 'var(--text-dim)',
                    }}
                  >
                    {archivo ? archivo.name : 'Cargar PDF o Word'}
                    <input
                      type="file"
                      accept=".pdf,.doc,.docx"
                      className="hidden"
                      onChange={(e) => setArchivo(e.target.files?.[0] || null)}
                    />
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--text-dim)' }}>Vacante a la que te postulas (opcional)</label>
                <textarea
                  value={vacanteCv}
                  onChange={(e) => setVacanteCv(e.target.value)}
                  rows={10}
                  className="w-full px-4 py-3 rounded-lg text-sm"
                  style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.10)',
                    color: 'var(--text)',
                  }}
                  placeholder="Pega aquí la descripción de la vacante..."
                />
              </div>
            </div>

            <button
              onClick={mejorarCv}
              disabled={loading || (!cv.trim() && !archivo)}
              className="btn btn-gold mt-5"
              style={{ width: '100%', justifyContent: 'center', padding: '14px' }}
            >
              {loading ? (
                <>Mejorando CV con IA...</>
              ) : (
                <>Mejorar CV</>
              )}
            </button>
          </div>

          {resultadoCv && (
            <div className="space-y-6">
              <div className="plate card">
                <div className="flex items-center justify-between mb-4" style={{ position: 'relative', zIndex: 1 }}>
                  <h3 className="panel-title text-2xl font-bold text-white">
                    CV mejorado
                  </h3>
                  <button
                    onClick={copiarCv}
                    className="link flex items-center gap-1"
                  >
                    {copiado ? 'Copiado' : 'Copiar'}
                  </button>
                </div>
                <pre
                  className="whitespace-pre-wrap text-sm p-4 rounded-lg"
                  style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    color: 'var(--text)',
                    position: 'relative',
                    zIndex: 1,
                  }}
                >
                  {resultadoCv.cv_mejorado}
                </pre>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="plate card">
                  <h4 className="font-semibold mb-2" style={{ color: 'var(--green)', position: 'relative', zIndex: 1 }}>
                    ¿Por qué es un buen CV?
                  </h4>
                  <p className="text-sm" style={{ color: 'var(--text)', position: 'relative', zIndex: 1 }}>{resultadoCv.por_que_es_bueno}</p>
                </div>

                <div className="plate card">
                  <h4 className="font-semibold mb-3" style={{ color: 'var(--text)', position: 'relative', zIndex: 1 }}>
                    Palabras clave para ATS
                  </h4>
                  <div className="flex flex-wrap gap-2" style={{ position: 'relative', zIndex: 1 }}>
                    {resultadoCv.palabras_clave_ats.map((p, i) => (
                      <span
                        key={i}
                        className="px-2 py-1 text-xs rounded-full"
                        style={{
                          background: 'rgba(212, 175, 55, 0.12)',
                          border: '1px solid rgba(212, 175, 55, 0.30)',
                          color: 'var(--gold-soft)',
                        }}
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="plate card">
                <h4 className="font-semibold mb-3" style={{ color: 'var(--text)', position: 'relative', zIndex: 1 }}>Cambios realizados</h4>
                <ul className="space-y-2" style={{ position: 'relative', zIndex: 1 }}>
                  {resultadoCv.cambios_realizados.map((c, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm" style={{ color: 'var(--text)' }}>
                      {c}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          <FuentesBadge fuentes={['Gemini 2.5 Flash-Lite', 'O*NET', 'ESCO']} />
        </div>
      )}

      {tab === 'entrevista' && (
        <div className="space-y-6">
          <div className="plate card">
            <div className="panel-head">
              <div>
                <h2 className="panel-title text-2xl font-bold text-white">
                  Practicar entrevista con ALBA
                </h2>
                <p className="panel-sub">
                  ALBA analizará tu CV y la vacante, generará 10 preguntas y te dará feedback al final.
                </p>
              </div>
            </div>

            <div style={{ position: 'relative', zIndex: 1 }}>
              {!entrevistaIniciada ? (
                <>
                  <div className="mb-4">
                    <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--text-dim)' }}>Tu CV</label>
                    <textarea
                      value={cvEnt}
                      onChange={(e) => setCvEnt(e.target.value)}
                      rows={6}
                      className="w-full px-4 py-3 rounded-lg text-sm"
                      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.10)', color: 'var(--text)' }}
                      placeholder="Pega tu CV aquí..."
                    />
                  </div>
                  <div className="mb-4">
                    <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--text-dim)' }}>Vacante objetivo</label>
                    <textarea
                      value={vacanteEnt}
                      onChange={(e) => setVacanteEnt(e.target.value)}
                      rows={3}
                      className="w-full px-4 py-3 rounded-lg text-sm"
                      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.10)', color: 'var(--text)' }}
                      placeholder="Pega la descripción de la vacante..."
                    />
                  </div>
                  {errorEnt && (
                    <p className="text-sm mb-3" style={{ color: '#ff6b6b' }}>{errorEnt}</p>
                  )}
                  <button
                    onClick={iniciarEntrevista}
                    disabled={entrevistaIniciando || !cvEnt.trim() || !vacanteEnt.trim()}
                    className="btn btn-gold"
                    style={{ width: '100%', justifyContent: 'center', padding: '14px' }}
                  >
                    {entrevistaIniciando ? 'Analizando CV y preparando preguntas...' : 'Iniciar entrevista'}
                  </button>
                </>
              ) : (
                <>
                  {/* Barra de progreso */}
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-semibold" style={{ color: 'var(--gold-soft)' }}>
                      {entrevistaFinalizada ? 'Entrevista completada' : `Pregunta ${numeroPregunta} de ${totalPreguntas}`}
                    </span>
                    {!entrevistaFinalizada && (
                      <button onClick={reiniciarEntrevista} className="text-xs" style={{ color: 'var(--text-dim)' }}>
                        Reiniciar
                      </button>
                    )}
                  </div>
                  {!entrevistaFinalizada && (
                    <div className="h-2 rounded-full mb-4 overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${(numeroPregunta / totalPreguntas) * 100}%`, background: 'linear-gradient(90deg, #d4af37, #e8c252)' }}
                      />
                    </div>
                  )}

                  {/* Chat */}
                  <div className="space-y-3 max-h-[420px] overflow-y-auto mb-4" style={{ position: 'relative', zIndex: 1 }}>
                    {mensajes.map((m, i) => (
                      <div key={i} className={`flex ${m.rol === 'usuario' ? 'justify-end' : 'justify-start'}`}>
                        <div
                          className="max-w-[80%] px-4 py-3 rounded-lg text-sm"
                          style={
                            m.rol === 'usuario'
                              ? {
                                  background: 'linear-gradient(180deg, rgba(212, 175, 55, 0.25) 0%, rgba(212, 175, 55, 0.12) 100%)',
                                  border: '1px solid rgba(212, 175, 55, 0.50)',
                                  color: 'var(--gold-soft)',
                                  borderRadius: '12px 12px 2px 12px',
                                }
                              : {
                                  background: 'rgba(255,255,255,0.04)',
                                  border: '1px solid rgba(255,255,255,0.10)',
                                  color: 'var(--text)',
                                  borderRadius: '12px 12px 12px 2px',
                                }
                          }
                        >
                          <span className="block text-xs font-semibold mb-1" style={{ opacity: 0.6 }}>
                            {m.rol === 'usuario' ? 'Tú' : 'ALBA'}
                          </span>
                          {m.text}
                        </div>
                      </div>
                    ))}
                    {enviandoRespuesta && (
                      <div className="flex justify-start">
                        <div className="px-4 py-3 rounded-lg text-sm" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.10)', color: 'var(--text-dim)' }}>
                          <span className="inline-block w-2 h-2 rounded-full animate-pulse mr-1" style={{ background: 'var(--gold-soft)' }} />
                          ALBA está evaluando tu respuesta...
                        </div>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>

                  {/* Input de respuesta */}
                  {!entrevistaFinalizada && (
                    <div className="flex gap-2">
                      <textarea
                        value={respuestaInput}
                        onChange={(e) => setRespuestaInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault()
                            enviarRespuesta()
                          }
                        }}
                        rows={3}
                        disabled={enviandoRespuesta}
                        className="flex-1 px-4 py-3 rounded-lg text-sm resize-none"
                        style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.10)', color: 'var(--text)' }}
                        placeholder="Escribe tu respuesta... (Enter para enviar)"
                      />
                      <button
                        onClick={enviarRespuesta}
                        disabled={!respuestaInput.trim() || enviandoRespuesta}
                        className="btn btn-gold"
                        style={{ alignSelf: 'flex-end' }}
                      >
                        Enviar
                      </button>
                    </div>
                  )}

                  {/* Feedback final */}
                  {entrevistaFinalizada && feedback && (
                    <div className="mt-4 p-5 rounded-xl" style={{ background: 'rgba(212, 175, 55, 0.06)', border: '1px solid rgba(212, 175, 55, 0.30)' }}>
                      <div className="flex items-center gap-4 mb-4">
                        <div className="text-center">
                          <div className="text-4xl font-bold" style={{ color: 'var(--gold-soft)' }}>
                            {feedback.puntaje_general}
                          </div>
                          <div className="text-xs" style={{ color: 'var(--text-dim)' }}>de 100</div>
                        </div>
                        <div className="flex-1">
                          <h4 className="font-bold text-lg text-white mb-1">Evaluación final</h4>
                          <p className="text-sm" style={{ color: 'var(--text)' }}>{feedback.recomendacion}</p>
                        </div>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                        <div>
                          <h5 className="text-sm font-semibold mb-2" style={{ color: '#22c55e' }}>Fortalezas</h5>
                          <ul className="space-y-1">
                            {feedback.fortalezas.map((f, i) => (
                              <li key={i} className="text-sm flex items-start gap-2" style={{ color: 'var(--text)' }}>
                                <span style={{ color: '#22c55e' }}>+</span> {f}
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <h5 className="text-sm font-semibold mb-2" style={{ color: '#f59e0b' }}>Áreas de mejora</h5>
                          <ul className="space-y-1">
                            {feedback.areas_mejora.map((a, i) => (
                              <li key={i} className="text-sm flex items-start gap-2" style={{ color: 'var(--text)' }}>
                                <span style={{ color: '#f59e0b' }}>→</span> {a}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                      <div className="pt-3 border-t border-white/[0.08]">
                        <h5 className="text-sm font-semibold mb-1" style={{ color: 'var(--gold-soft)' }}>Sugerencia práctica</h5>
                        <p className="text-sm" style={{ color: 'var(--text)' }}>{feedback.sugerencia_practica}</p>
                      </div>
                      <button onClick={reiniciarEntrevista} className="btn btn-gold mt-4" style={{ width: '100%', justifyContent: 'center' }}>
                        Hacer otra entrevista
                      </button>
                    </div>
                  )}
                  {errorEnt && (
                    <p className="text-sm mt-3" style={{ color: '#ff6b6b' }}>{errorEnt}</p>
                  )}
                </>
              )}
            </div>
          </div>

          <FuentesBadge fuentes={['Gemini 2.5 Flash-Lite']} />
        </div>
      )}

      {tab === 'voz' && (
        <div className="space-y-6">
          <div className="plate card">
            <div className="panel-head">
              <div>
                <h2 className="panel-title text-2xl font-bold text-white">
                  Entrevista por voz con Gemini Live
                </h2>
                <p className="panel-sub">Habla con ALBA en tiempo real. Escucha tus respuestas y responde con voz natural.</p>
              </div>
            </div>

            <div style={{ position: 'relative', zIndex: 1 }}>
              <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--text-dim)' }}>Modo de entrevista</label>
              <div className="flex gap-2 mb-4">
                <button
                  type="button"
                  onClick={() => setModoVoz('realista')}
                  disabled={connected}
                  className="btn text-sm font-bold text-white"
                  style={modoVoz === 'realista' ? {
                    background: 'linear-gradient(180deg, rgba(212, 175, 55, 0.18) 0%, rgba(212, 175, 55, 0.06) 100%)',
                    borderColor: 'rgba(212, 175, 55, 0.95)',
                  } : {}}
                >
                  Reclutador real (CV + vacante)
                </button>
                <button
                  type="button"
                  onClick={() => setModoVoz('libre')}
                  disabled={connected}
                  className="btn text-sm font-bold text-white"
                  style={modoVoz === 'libre' ? {
                    background: 'linear-gradient(180deg, rgba(212, 175, 55, 0.18) 0%, rgba(212, 175, 55, 0.06) 100%)',
                    borderColor: 'rgba(212, 175, 55, 0.95)',
                  } : {}}
                >
                  Entrevista libre
                </button>
              </div>

              {modoVoz === 'realista' && (
                <>
                  <div className="mb-4">
                    <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--text-dim)' }}>CV del candidato</label>
                    <textarea
                      value={cvVoz}
                      onChange={(e) => setCvVoz(e.target.value)}
                      rows={6}
                      disabled={connected}
                      className="w-full px-4 py-3 rounded-lg text-sm"
                      style={{
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid rgba(255,255,255,0.10)',
                        color: 'var(--text)',
                        opacity: connected ? 0.6 : 1,
                      }}
                      placeholder="Pega el CV para que ALBA haga preguntas basadas en tu perfil real..."
                    />
                  </div>

                  <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--text-dim)' }}>Vacante objetivo</label>
                  <textarea
                    value={vacanteVoz}
                    onChange={(e) => setVacanteVoz(e.target.value)}
                    rows={3}
                    disabled={connected}
                    className="w-full px-4 py-3 rounded-lg text-sm"
                    style={{
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid rgba(255,255,255,0.10)',
                      color: 'var(--text)',
                      opacity: connected ? 0.6 : 1,
                    }}
                    placeholder="Pega la vacante para una entrevista adaptada..."
                  />
                </>
              )}

              <label className="block text-sm font-semibold mb-2 mt-4" style={{ color: 'var(--text-dim)' }}>Voz de ALBA</label>
              <select
                value={vozLive}
                onChange={(e) => setVozLive(e.target.value)}
                disabled={connected}
                className="w-full md:w-72 px-4 py-2.5 rounded-lg text-sm"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.10)',
                  color: 'var(--text)',
                  opacity: connected ? 0.6 : 1,
                }}
              >
                {VOCES.map((v) => (
                  <option key={v.id} value={v.id} style={{ background: 'var(--metal-mid)', color: 'var(--text)' }}>{v.label}</option>
                ))}
              </select>

              <div className="flex flex-wrap gap-3 mt-5">
                {!connected ? (
                  <button
                    onClick={connectLive}
                    disabled={liveStatus === 'connecting' || (modoVoz === 'realista' && (!cvVoz.trim() || !vacanteVoz.trim()))}
                    className="btn btn-gold"
                  >
                    {liveStatus === 'connecting' ? 'Conectando...' : `Iniciar entrevista ${modoVoz === 'realista' ? 'realista' : 'libre'}`}
                  </button>
                ) : (
                  <>
                    <button
                      onClick={disconnectLive}
                      className="btn"
                      style={{
                        background: 'linear-gradient(180deg, #d63a5a 0%, #a02844 100%)',
                        color: '#fff',
                        borderColor: 'rgba(255, 100, 120, 0.5)',
                        boxShadow: '0 4px 12px rgba(200, 40, 60, 0.3)',
                      }}
                    >
                      Terminar entrevista
                    </button>
                    <button
                      onClick={() => clientRef.current?.requestFeedback()}
                      className="btn btn-gold"
                    >
                      Generar feedback final
                    </button>
                  </>
                )}
              </div>

              {liveStatus === 'connecting' && (
                <p className="text-sm mt-3 flex items-center gap-2" style={{ color: 'var(--text-dim)' }}>
                  <span className="inline-block w-2 h-2 rounded-full animate-pulse" style={{ background: 'var(--gold-soft)' }} />
                  Estableciendo conexión con Gemini Live...
                </p>
              )}
              {liveStatus === 'connected' && (
                <div className="mt-3 p-3 rounded-lg flex items-center gap-3" style={{ background: 'rgba(34, 197, 94, 0.08)', border: '1px solid rgba(34, 197, 94, 0.25)' }}>
                  <span className="inline-block w-3 h-3 rounded-full animate-pulse" style={{ background: '#22c55e' }} />
                  <span className="text-sm font-semibold" style={{ color: '#22c55e' }}>
                    Entrevista en curso
                  </span>
                  <span className="text-xs" style={{ color: 'var(--text-dim)' }}>
                    ALBA escucha lo que dices. Habla con naturalidad cuando termine su pregunta.
                  </span>
                </div>
              )}
              {liveStatus === 'disconnected' && (
                <p className="text-sm mt-3 flex items-center gap-2" style={{ color: 'var(--text-dim)' }}>
                  <span className="inline-block w-2 h-2 rounded-full" style={{ background: 'var(--text-dim)' }} />
                  La sesión finalizó. Puedes iniciar otra entrevista cuando quieras.
                </p>
              )}
              {liveStatus === 'error' && (
                <p className="text-sm mt-3 flex items-center gap-2" style={{ color: '#ff6b6b' }}>
                  <span className="inline-block w-2 h-2 rounded-full" style={{ background: '#ff6b6b' }} />
                  Error de conexión. Verifica que el backend esté corriendo y tengas credenciales de Gemini configuradas.
                </p>
              )}
            </div>
          </div>

          {/* Transcripción */}
          {transcripciones.length > 0 && (
            <div className="plate card">
              <div className="panel-head">
                <h3 className="panel-title text-2xl font-bold text-white">Transcripción de la entrevista</h3>
              </div>
              <div className="space-y-3 max-h-96 overflow-y-auto" style={{ position: 'relative', zIndex: 1 }}>
                {transcripciones.map((m, i) => (
                  <div
                    key={i}
                    className={`flex ${m.rol === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className="max-w-[80%] px-4 py-2 rounded-lg text-sm"
                      style={
                        m.rol === 'user'
                          ? {
                              background: 'linear-gradient(180deg, rgba(212, 175, 55, 0.25) 0%, rgba(212, 175, 55, 0.12) 100%)',
                              border: '1px solid rgba(212, 175, 55, 0.50)',
                              color: 'var(--gold-soft)',
                              borderRadius: '12px 12px 2px 12px',
                            }
                          : {
                              background: 'rgba(255,255,255,0.04)',
                              border: '1px solid rgba(255,255,255,0.10)',
                              color: 'var(--text)',
                              borderRadius: '12px 12px 12px 2px',
                            }
                      }
                    >
                      <span className="block text-xs font-semibold mb-1" style={{ opacity: 0.6 }}>
                        {m.rol === 'user' ? 'Tú' : 'ALBA'}
                      </span>
                      {m.text}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <FuentesBadge fuentes={['Gemini Live API', 'Gemini 2.5 Flash-Lite']} />
        </div>
      )}
    </div>
  )
}