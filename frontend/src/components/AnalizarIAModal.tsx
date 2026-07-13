import { useState } from 'react'
import api from '../services/api'

interface AnalizarIAModalProps {
  isOpen: boolean
  onClose: () => void
  dashboard: string
  widgetTitle: string
  widgetType: 'grafico' | 'tabla' | 'kpi' | 'mapa'
  filters?: Record<string, any>
  data?: any
}

export default function AnalizarIAModal({
  isOpen,
  onClose,
  dashboard,
  widgetTitle,
  widgetType,
  filters,
  data,
}: AnalizarIAModalProps) {
  const [question, setQuestion] = useState('')
  const [respuesta, setRespuesta] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!question.trim()) return

    setLoading(true)
    setError('')
    setRespuesta('')

    try {
      const res = await api.post('/ia/analizar-widget', {
        dashboard,
        widget_title: widgetTitle,
        widget_type: widgetType,
        filters: filters || null,
        data: data || null,
        question: question.trim(),
      })

      setRespuesta(res.data.respuesta)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Error al analizar. Intenta de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="plate card w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-gold-500/20">
          <div>
            <h3 className="text-lg font-bold text-white font-display flex items-center gap-2">
              <span className="text-gold-400">🤖</span>
              Analizar con IA
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">{widgetTitle}</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          {/* Pregunta */}
          <div>
            <label className="block text-sm font-semibold text-slate-200 mb-2">
              ¿Qué deseas saber sobre este {widgetType}?
            </label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={3}
              className="w-full px-4 py-3 border border-white/10 rounded-lg focus:ring-2 focus:ring-gold-500/50 text-sm bg-white/[0.03] text-slate-100 resize-none"
              placeholder="Ej: ¿Por qué bajó el empleo en este sector? ¿Qué tendencia observas?"
              disabled={loading}
            />
            <p className="text-xs text-slate-500 mt-1">
              Presiona Enter para enviar
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg">
              <p className="text-sm text-rose-400">{error}</p>
            </div>
          )}

          {/* Respuesta */}
          {respuesta && (
            <div className="p-4 bg-gold-500/5 border border-gold-500/20 rounded-lg">
              <h4 className="text-sm font-semibold text-gold-400 mb-2">Respuesta de ALBA:</h4>
              <div className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                {respuesta}
              </div>
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="flex items-center gap-2 text-slate-400">
              <span className="animate-spin">⚙️</span>
              <span className="text-sm">Analizando datos con IA...</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-gold-500/20 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
          >
            Cerrar
          </button>
          <button
            onClick={handleSubmit}
            disabled={!question.trim() || loading}
            className="px-4 py-2 bg-gradient-to-b from-amber-300 to-amber-600 text-[#0a0f1f] rounded-lg text-sm font-semibold hover:shadow-lg hover:shadow-amber-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Analizando...' : 'Analizar'}
          </button>
        </div>
      </div>
    </div>
  )
}
