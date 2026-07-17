import { useChat } from '../context/ChatContext'
import albaChatBotSvg from '../../SVG/ALBA ROSTRO.svg?raw'

interface AnalizarIAButtonProps {
  dashboard: string
  widgetTitle: string
  widgetType: 'grafico' | 'tabla' | 'kpi' | 'mapa'
  filters?: Record<string, any>
  data?: any
  className?: string
}

export default function AnalizarIAButton({
  dashboard,
  widgetTitle,
  widgetType,
  filters,
  data,
  className = '',
}: AnalizarIAButtonProps) {
  const { openChat } = useChat()

  return (
    <button
      onClick={() => openChat({ dashboard, widgetTitle, widgetType, filters, data })}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gold-400 bg-gold-500/10 border border-gold-500/30 rounded-lg hover:bg-gold-500/20 hover:border-gold-500/50 transition-all ${className}`}
      title="Analizar con IA"
    >
      <span className="nav-svg-icon flex items-center justify-center" dangerouslySetInnerHTML={{ __html: albaChatBotSvg }} style={{ width: 32, height: 32 }} />
      <span>Analizar con IA</span>
    </button>
  )
}
