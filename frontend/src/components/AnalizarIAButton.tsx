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
      className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-rose-500/50 border border-rose-400/80 rounded-lg hover:bg-rose-500/70 hover:border-rose-300 hover:shadow-[0_0_14px_rgba(244,63,94,0.40)] transition-all flex-shrink-0 ${className}`}
      title="Analizar con IA"
    >
      <img src={albaChatBotSvg} alt="ALBA IA" className="inline-block" style={{ width: 32, height: 32, filter: 'sepia(1) saturate(2.8) hue-rotate(352deg) brightness(1.08)' }} />
      <span>Analizar con IA</span>
    </button>
  )
}
