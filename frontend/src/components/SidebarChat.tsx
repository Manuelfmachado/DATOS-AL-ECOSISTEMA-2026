import { useState, useRef, useEffect } from 'react'
import api from '../services/api'
import { useChat, type ChatMessage } from '../context/ChatContext'
import albaChatBotSvg from '../../SVG/ALBA ROSTRO.svg'

const AlbaIcon = ({ className = '', size = 28 }: { className?: string; size?: number }) => (
  <img
    src={albaChatBotSvg}
    alt="ALBA"
    className={`inline-block ${className}`}
    style={{ width: size, height: size }}
  />
)

function formatMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/### (.*)/g, '<h4 class="text-gold-400 font-bold mt-3 mb-1">$1</h4>')
    .replace(/## (.*)/g, '<h3 class="text-gold-400 font-bold mt-4 mb-2">$1</h3>')
    .replace(/# (.*)/g, '<h2 class="text-gold-400 font-bold mt-4 mb-2">$1</h2>')
    .replace(/`([^`]+)`/g, '<code class="bg-white/10 px-1 rounded text-gold-300">$1</code>')
    .replace(/\n/g, '<br />')
}

export default function SidebarChat() {
  const { open, widget, messages, loading, closeChat, addMessage, setLoading } = useChat()
  const [question, setQuestion] = useState('')
  const [error, setError] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  const handleSubmit = async () => {
    if (!question.trim()) return
    const userMessage: ChatMessage = { role: 'user', content: question.trim() }
    addMessage(userMessage)
    setQuestion('')
    setError('')
    setLoading(true)

    try {
      const res = await api.post('/ia/analizar-widget', {
        dashboard: widget?.dashboard,
        widget_title: widget?.widgetTitle,
        widget_type: widget?.widgetType,
        filters: widget?.filters || null,
        data: widget?.data || null,
        question: userMessage.content,
        historial: messages.map((m) => ({ role: m.role, content: m.content })),
      })

      addMessage({ role: 'assistant', content: res.data.respuesta })
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

  if (!open) return null

  return (
    <div className="sidebar-chat">
      {/* Botón flotante para cerrar desde el main */}
      <button
        onClick={closeChat}
        className="fixed top-4 left-[336px] z-70 w-8 h-8 rounded-full bg-[#0a0f1f] border border-gold-500/50 text-gold-400 hover:text-white hover:border-gold-400 flex items-center justify-center shadow-lg shadow-black/50"
        title="Cerrar consulta"
      >
        ×
      </button>

      {/* Header */}
      <div className="sidebar-chat-header">
        <div className="flex items-center gap-2">
          <AlbaIcon size={36} />
          <div>
            <h3 className="text-base font-bold text-white font-display leading-tight">ALBA Chat IA</h3>
            {widget && <p className="text-xs text-slate-400 truncate max-w-[160px]">{widget.widgetTitle}</p>}
          </div>
        </div>
        <button
          onClick={closeChat}
          className="text-slate-400 hover:text-white transition-colors text-2xl leading-none"
          title="Cerrar consulta"
        >
          ×
        </button>
      </div>

      {/* Messages */}
      <div className="sidebar-chat-messages">
        {messages.length === 0 && (
          <div className="text-sm text-slate-400 italic">
            {widget
              ? `Pregúntale a ALBA sobre "${widget.widgetTitle}". El chat mantendrá el contexto de la conversación.`
              : 'Pregúntale a ALBA sobre los datos que estás viendo.'}
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`sidebar-chat-bubble ${m.role}`}>
            {m.role === 'assistant' && <AlbaIcon size={20} />}
            <div className="sidebar-chat-bubble-content">
              {m.role === 'assistant' ? (
                <div
                  className="text-sm text-slate-200 leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: formatMarkdown(m.content) }}
                />
              ) : (
                <div className="text-sm text-white leading-relaxed">{m.content}</div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="sidebar-chat-bubble assistant">
            <AlbaIcon size={20} />
            <div className="sidebar-chat-bubble-content">
              <div className="flex items-center gap-2 text-slate-400">
                <span className="animate-spin text-base">⚙️</span>
                <span className="text-sm">Analizando datos con IA...</span>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg">
            <p className="text-sm text-rose-400">{error}</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="sidebar-chat-input">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          className="w-full px-3 py-2 border border-white/10 rounded-lg focus:ring-2 focus:ring-gold-500/50 text-sm bg-white/[0.03] text-slate-100 resize-none"
          placeholder="Escribe tu pregunta..."
          disabled={loading}
        />
        <button
          onClick={handleSubmit}
          disabled={!question.trim() || loading}
          className="w-full mt-2 px-3 py-2 bg-gradient-to-b from-amber-300 to-amber-600 text-[#0a0f1f] rounded-lg text-sm font-semibold hover:shadow-lg hover:shadow-amber-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Analizando...' : 'Enviar'}
        </button>
      </div>
    </div>
  )
}
