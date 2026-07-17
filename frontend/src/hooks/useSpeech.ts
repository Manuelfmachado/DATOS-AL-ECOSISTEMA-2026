import { useState, useRef, useCallback, useEffect } from 'react'

// Tipos para Web Speech API
interface SpeechRecognitionEvent extends Event {
  readonly resultIndex: number
  readonly results: SpeechRecognitionResultList
}

interface SpeechRecognitionResultList {
  readonly length: number
  item(index: number): SpeechRecognitionResult
  [index: number]: SpeechRecognitionResult
}

interface SpeechRecognitionResult {
  readonly length: number
  item(index: number): SpeechRecognitionAlternative
  [index: number]: SpeechRecognitionAlternative
  readonly isFinal: boolean
}

interface SpeechRecognitionAlternative {
  readonly transcript: string
  readonly confidence: number
}

interface SpeechRecognition extends EventTarget {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  start(): void
  stop(): void
  abort(): void
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: Event) => void) | null
  onend: (() => void) | null
  onstart: (() => void) | null
}

type SpeechRecognitionConstructor = new () => SpeechRecognition

function getSpeechRecognitionConstructor(): SpeechRecognitionConstructor | null {
  if (typeof window === 'undefined') return null
  return (
    (window as any).SpeechRecognition ||
    (window as any).webkitSpeechRecognition ||
    null
  )
}

function isSpeechSynthesisSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

export interface UseSpeechState {
  // TTS
  hablar: (texto: string, onEnd?: () => void) => void
  detenerHabla: () => void
  hablando: boolean
  vozActiva: boolean
  setVozActiva: (v: boolean) => void
  // STT
  escuchar: () => void
  detenerEscucha: () => void
  escuchando: boolean
  textoReconocido: string
  resetTexto: () => void
  // Soporte
  ttsSoportado: boolean
  sttSoportado: boolean
}

export function useSpeech(lang = 'es-CO'): UseSpeechState {
  const [hablando, setHablando] = useState(false)
  const [escuchando, setEscuchando] = useState(false)
  const [textoReconocido, setTextoReconocido] = useState('')
  const [vozActiva, setVozActiva] = useState(true)

  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const onEndRef = useRef<(() => void) | null>(null)

  const ttsSoportado = isSpeechSynthesisSupported()
  const sttSoportado = !!getSpeechRecognitionConstructor()

  const hablar = useCallback(
    (texto: string, onEnd?: () => void) => {
      if (!vozActiva || !ttsSoportado || !texto.trim()) {
        onEnd?.()
        return
      }
      window.speechSynthesis.cancel()
      const utterance = new SpeechSynthesisUtterance(texto)
      utterance.lang = lang
      utterance.rate = 1.0
      utterance.pitch = 1.0

      const voces = window.speechSynthesis.getVoices()
      const vozEs = voces.find(
        (v) => v.lang.startsWith('es') && (v.lang.includes('CO') || v.lang.includes('MX') || v.lang.includes('US')),
      ) || voces.find((v) => v.lang.startsWith('es'))
      if (vozEs) utterance.voice = vozEs

      utterance.onstart = () => setHablando(true)
      utterance.onend = () => {
        setHablando(false)
        onEnd?.()
      }
      utterance.onerror = () => {
        setHablando(false)
        onEnd?.()
      }
      onEndRef.current = onEnd || null
      window.speechSynthesis.speak(utterance)
    },
    [vozActiva, ttsSoportado, lang],
  )

  const detenerHabla = useCallback(() => {
    if (ttsSoportado) {
      window.speechSynthesis.cancel()
    }
    setHablando(false)
  }, [ttsSoportado])

  const escuchar = useCallback(() => {
    const SR = getSpeechRecognitionConstructor()
    if (!SR || escuchando) return

    const recognition = new SR()
    recognition.lang = lang
    recognition.continuous = false
    recognition.interimResults = true
    recognition.maxAlternatives = 1

    let textoFinal = ''

    recognition.onstart = () => setEscuchando(true)

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          textoFinal += result[0].transcript + ' '
        } else {
          interim += result[0].transcript
        }
      }
      setTextoReconocido((textoFinal + interim).trim())
    }

    recognition.onerror = () => {
      setEscuchando(false)
    }

    recognition.onend = () => {
      setEscuchando(false)
    }

    recognitionRef.current = recognition
    recognition.start()
  }, [escuchando, lang])

  const detenerEscucha = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    setEscuchando(false)
  }, [])

  const setTextoReconocidoSafe = useCallback((v: string) => {
    setTextoReconocido(v)
  }, [])

  const resetTexto = useCallback(() => {
    setTextoReconocidoSafe('')
  }, [setTextoReconocidoSafe])

  // Cleanup
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort()
      }
      if (ttsSoportado) {
        window.speechSynthesis.cancel()
      }
    }
  }, [ttsSoportado])

  return {
    hablar,
    detenerHabla,
    hablando,
    vozActiva,
    setVozActiva,
    escuchar,
    detenerEscucha,
    escuchando,
    textoReconocido,
    resetTexto,
    ttsSoportado,
    sttSoportado,
  }
}