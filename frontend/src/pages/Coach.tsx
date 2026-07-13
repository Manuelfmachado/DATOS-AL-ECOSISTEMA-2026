import { useState, useRef, useEffect, type ReactNode } from 'react'
import Icon from '../components/Icon'
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

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className="btn"
      style={active ? {
        color: 'var(--gold)',
        background: 'linear-gradient(180deg, rgba(212, 175, 55, 0.18) 0%, rgba(212, 175, 55, 0.06) 100%)',
        borderColor: 'rgba(212, 175, 55, 0.95)',
        boxShadow: '0 0 0 1px rgba(212, 175, 55, 0.35), 0 0 22px -2px rgba(212, 175, 55, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.18)',
      } : undefined}
    >
      {icon}
      {label}
    </button>
  )
}

export default function Coach() {
  const [tab, setTab] = useState<'cv' | 'live'>('cv')
  const [loading, setLoading] = useState(false)

  // CV
  const [cv, setCv] = useState(CV_EJEMPLO)
  const [vacanteCv, setVacanteCv] = useState(VACANTE_EJEMPLO)
  const [archivo, setArchivo] = useState<File | null>(null)
  const [resultadoCv, setResultadoCv] = useState<CvResultado | null>(null)
  const [copiado, setCopiado] = useState(false)

  // Entrevista en vivo
  const [vacanteLive, setVacanteLive] = useState(VACANTE_EJEMPLO)
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

  // Entrevista en vivo: gestion del cliente
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
    const client = new CoachLiveClient({
      onEvent: handleLiveEvent,
      onStatus: (status) => setLiveStatus(status),
    })
    clientRef.current = client
    try {
      await client.connect(vacanteLive, vozLive)
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
          <h1 className="hello" style={{ fontSize: '32px' }}>Coach IA</h1>
          <p className="hello-sub">Prepárate para conseguir empleo: mejora tu CV o practica una entrevista en vivo por voz.</p>
        </div>
      </header>

      {/* Pestañas */}
      <div className="flex gap-2 mb-6">
        <TabButton active={tab === 'cv'} onClick={() => setTab('cv')} icon={<Icon.Coach size={16} />} label="Mejorar CV" />
        <TabButton active={tab === 'live'} onClick={() => setTab('live')} icon={<Icon.Coach size={16} />} label="Entrevista en vivo" />
      </div>

      {tab === 'cv' && (
        <div className="space-y-6">
          <div className="plate card">
            <div className="panel-head">
              <div>
                <h2 className="panel-title">Mejorar tu CV con IA</h2>
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
                    <Icon.Accion.Subir size={16} />
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
                <><span className="animate-spin inline-block"><Icon.Coach size={18} /></span> Mejorando CV con IA...</>
              ) : (
                <><Icon.Coach size={18} /> Mejorar CV</>
              )}
            </button>
          </div>

          {resultadoCv && (
            <div className="space-y-6">
              <div className="plate card">
                <div className="flex items-center justify-between mb-4" style={{ position: 'relative', zIndex: 1 }}>
                  <h3 className="panel-title flex items-center gap-2">
                    <span style={{ color: 'var(--gold)' }}><Icon.CoachDocumento size={20} /></span>
                    CV mejorado
                  </h3>
                  <button
                    onClick={copiarCv}
                    className="link flex items-center gap-1"
                  >
                    {copiado ? <Icon.Accion.Check size={16} /> : <Icon.Accion.Copiar size={16} />}
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
                  <h4 className="font-semibold mb-2 flex items-center gap-2" style={{ color: 'var(--green)', position: 'relative', zIndex: 1 }}>
                    <span style={{ color: 'var(--green)' }}><Icon.Accion.Check size={18} /></span>
                    ¿Por qué es un buen CV?
                  </h4>
                  <p className="text-sm" style={{ color: 'var(--text)', position: 'relative', zIndex: 1 }}>{resultadoCv.por_que_es_bueno}</p>
                </div>

                <div className="plate card">
                  <h4 className="font-semibold mb-3 flex items-center gap-2" style={{ color: 'var(--text)', position: 'relative', zIndex: 1 }}>
                    <span style={{ color: 'var(--gold)' }}><Icon.EmprendeIdea size={18} /></span>
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
                      <span className="flex-shrink-0 mt-0.5" style={{ color: 'var(--green)' }}><Icon.Accion.Check size={16} /></span>
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

      {tab === 'live' && (
        <div className="space-y-6">
          <div className="plate card">
            <div className="panel-head">
              <div>
                <h2 className="panel-title flex items-center gap-2">
                  <span style={{ color: 'var(--gold)' }}><Icon.Coach size={20} /></span>
                  Entrevista en vivo con Gemini Live
                </h2>
                <p className="panel-sub">Conecta por voz con ALBA. Al iniciar, te saludará y empezará la entrevista automáticamente.</p>
              </div>
            </div>

            <div style={{ position: 'relative', zIndex: 1 }}>
              <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--text-dim)' }}>Vacante objetivo (opcional)</label>
              <textarea
                value={vacanteLive}
                onChange={(e) => setVacanteLive(e.target.value)}
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
                    disabled={liveStatus === 'connecting'}
                    className="btn btn-gold"
                  >
                    <Icon.Accion.Telefono size={18} />
                    {liveStatus === 'connecting' ? 'Conectando...' : 'Iniciar entrevista'}
                  </button>
                ) : (
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
                    <Icon.Accion.TelefonoOff size={18} />
                    Terminar entrevista
                  </button>
                )}
              </div>

              {liveStatus === 'connecting' && (
                <p className="text-sm mt-3" style={{ color: 'var(--text-dim)' }}>Estableciendo conexión con Gemini Live...</p>
              )}
              {liveStatus === 'connected' && (
                <p className="text-sm mt-3 flex items-center gap-1" style={{ color: 'var(--green)' }}>
                  <span className="inline-block w-2 h-2 rounded-full animate-pulse" style={{ background: 'var(--green)' }} />
                  Entrevista en curso. Habla normalmente para responder a ALBA.
                </p>
              )}
              {liveStatus === 'disconnected' && (
                <p className="text-sm mt-3" style={{ color: 'var(--text-dim)' }}>La sesión finalizó.</p>
              )}
              {liveStatus === 'error' && (
                <p className="text-sm mt-3" style={{ color: '#ff6b6b' }}>Error de conexión. Verifica que el backend esté corriendo y tengas credenciales de Gemini configuradas.</p>
              )}
            </div>
          </div>

          {/* Transcripción */}
          {transcripciones.length > 0 && (
            <div className="plate card">
              <div className="panel-head">
                <h3 className="panel-title">Transcripción de la entrevista</h3>
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