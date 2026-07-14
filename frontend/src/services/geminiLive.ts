// Cliente de la entrevista en vivo con Gemini Live API (solo microfono).
// Conecta un WebSocket al backend /api/coach/live y gestiona:
//   - captura de audio del microfono (16kHz mono PCM 16-bit)
//   - envio de chunks al backend
//   - recepcion y reproduccion del audio de respuesta (24kHz mono PCM 16-bit)
//   - eventos de transcripcion (usuario / gemini), turn_complete, interrupted, error

export interface CoachLiveEvent {
  type: 'user' | 'gemini' | 'turn_complete' | 'interrupted' | 'error'
  text?: string
  error?: string
}

export interface CoachLiveCallbacks {
  onEvent: (event: CoachLiveEvent) => void
  onStatus: (status: 'connecting' | 'connected' | 'disconnected' | 'error') => void
}

export interface CoachLiveConfig {
  modo: 'realista' | 'libre'
  cv?: string
  vacante?: string
  voice?: string
}

const INPUT_SAMPLE_RATE = 16000
const OUTPUT_SAMPLE_RATE = 24000

export class CoachLiveClient {
  private ws: WebSocket | null = null
  private audioContext: AudioContext | null = null
  private mediaStream: MediaStream | null = null
  private audioWorkletNode: AudioWorkletNode | null = null
  private nextStartTime = 0
  private scheduledSources: AudioBufferSourceNode[] = []
  private isRecording = false
  private readonly callbacks: CoachLiveCallbacks

  constructor(callbacks: CoachLiveCallbacks) {
    this.callbacks = callbacks
  }

  isConnected(): boolean {
    return !!this.ws && this.ws.readyState === WebSocket.OPEN
  }

  isMicActive(): boolean {
    return this.isRecording
  }

  async connect(config: CoachLiveConfig): Promise<void> {
    this.callbacks.onStatus('connecting')

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = import.meta.env.VITE_API_URL
      ? import.meta.env.VITE_API_URL.replace(/^https?:\/\//, '')
      : window.location.host
    const params = new URLSearchParams()
    if (config.vacante) params.set('vacante', config.vacante)
    if (config.voice) params.set('voice', config.voice)
    if (config.modo) params.set('modo', config.modo)
    const qs = params.toString()
    const wsUrl = `${protocol}//${wsHost}/api/coach/live${qs ? '?' + qs : ''}`

    await this.initializeAudio()

    this.ws = new WebSocket(wsUrl)
    this.ws.binaryType = 'arraybuffer'

    this.ws.onopen = () => {
      if (config.modo === 'realista' && config.cv && this.ws) {
        this.ws.send(JSON.stringify({ tipo: 'cv', cv: config.cv }))
      }
      this.callbacks.onStatus('connected')
    }

    this.ws.onmessage = (event: MessageEvent) => {
      if (typeof event.data === 'string') {
        try {
          const msg = JSON.parse(event.data) as CoachLiveEvent
          this.callbacks.onEvent(msg)
        } catch (e) {
          console.error('[CoachLive] Parse error:', e)
        }
      } else {
        this.playAudio(event.data)
      }
    }

    this.ws.onclose = () => {
      this.callbacks.onStatus('disconnected')
    }

    this.ws.onerror = () => {
      this.callbacks.onStatus('error')
    }
  }

  async initializeAudio(): Promise<void> {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
      await this.audioContext.audioWorklet.addModule('/pcm-processor.js')
    }
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume()
    }
  }

  async startMic(): Promise<void> {
    if (!this.audioContext) await this.initializeAudio()
    if (!this.audioContext) throw new Error('AudioContext no disponible')

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const source = this.audioContext.createMediaStreamSource(this.mediaStream)
      this.audioWorkletNode = new AudioWorkletNode(this.audioContext, 'pcm-processor')

      this.audioWorkletNode.port.onmessage = (e: MessageEvent) => {
        if (!this.isRecording) return
        const downsampled = this.downsampleBuffer(
          e.data as Float32Array,
          this.audioContext!.sampleRate,
          INPUT_SAMPLE_RATE,
        )
        const pcm16 = this.convertFloat32ToInt16(downsampled)
        if (this.isConnected()) {
          this.ws!.send(pcm16)
        }
      }

      source.connect(this.audioWorkletNode)
      const muteGain = this.audioContext.createGain()
      muteGain.gain.value = 0
      this.audioWorkletNode.connect(muteGain)
      muteGain.connect(this.audioContext.destination)

      this.isRecording = true
    } catch (e) {
      console.error('[CoachLive] Error iniciando microfono:', e)
      throw e
    }
  }

  stopMic(): void {
    this.isRecording = false
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop())
      this.mediaStream = null
    }
    if (this.audioWorkletNode) {
      this.audioWorkletNode.disconnect()
      this.audioWorkletNode = null
    }
  }

  private playAudio(arrayBuffer: ArrayBuffer): void {
    if (!this.audioContext) return
    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume()
    }

    const pcmData = new Int16Array(arrayBuffer)
    const float32Data = new Float32Array(pcmData.length)
    for (let i = 0; i < pcmData.length; i++) {
      float32Data[i] = pcmData[i] / 32768.0
    }

    const buffer = this.audioContext.createBuffer(1, float32Data.length, OUTPUT_SAMPLE_RATE)
    buffer.getChannelData(0).set(float32Data)

    const src = this.audioContext.createBufferSource()
    src.buffer = buffer
    src.connect(this.audioContext.destination)

    const now = this.audioContext.currentTime
    this.nextStartTime = Math.max(now, this.nextStartTime)
    src.start(this.nextStartTime)
    this.nextStartTime += buffer.duration

    this.scheduledSources.push(src)
    src.onended = () => {
      const idx = this.scheduledSources.indexOf(src)
      if (idx > -1) this.scheduledSources.splice(idx, 1)
    }
  }

  stopAudioPlayback(): void {
    this.scheduledSources.forEach((s) => {
      try {
        s.stop()
      } catch {
        // ignore
      }
    })
    this.scheduledSources = []
    if (this.audioContext) {
      this.nextStartTime = this.audioContext.currentTime
    }
  }

  requestFeedback(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ tipo: 'feedback' }))
    }
  }

  disconnect(): void {
    this.stopMic()
    this.stopAudioPlayback()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.callbacks.onStatus('disconnected')
  }

  private downsampleBuffer(buffer: Float32Array, sampleRate: number, outSampleRate: number): Float32Array {
    if (outSampleRate === sampleRate) return buffer
    const ratio = sampleRate / outSampleRate
    const newLength = Math.round(buffer.length / ratio)
    const result = new Float32Array(newLength)
    let offsetResult = 0
    let offsetBuffer = 0
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio)
      let accum = 0
      let count = 0
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
        accum += buffer[i]
        count++
      }
      result[offsetResult] = accum / count
      offsetResult++
      offsetBuffer = nextOffsetBuffer
    }
    return result
  }

  private convertFloat32ToInt16(buffer: Float32Array): ArrayBuffer {
    const l = buffer.length
    const buf = new Int16Array(l)
    for (let i = 0; i < l; i++) {
      buf[i] = Math.min(1, Math.max(-1, buffer[i])) * 0x7fff
    }
    return buf.buffer
  }
}
