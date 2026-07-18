import { useChat } from '../context/ChatContext'
import albaChatBotSvg from '../../SVG/ROSTRO ALBA.svg'

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
      className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-rose-300 bg-rose-500/15 border border-rose-400/40 rounded-lg hover:bg-rose-500/25 hover:border-rose-400/60 hover:shadow-[0_0_12px_rgba(244,63,94,0.25)] transition-all ${className}`}
      title="Analizar con IA"
    >
      <img src={albaChatBotSvg} alt="ALBA IA" className="inline-block" style={{ width: 32, height: 32 }} />
      <span>Analizar con IA</span>
    </button>
  )
}
