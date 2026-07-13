import { useState } from 'react'
import AnalizarIAModal from './AnalizarIAModal'

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
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gold-400 bg-gold-500/10 border border-gold-500/30 rounded-lg hover:bg-gold-500/20 hover:border-gold-500/50 transition-all ${className}`}
        title="Analizar con IA"
      >
        <span>🤖</span>
        <span>Analizar con IA</span>
      </button>

      <AnalizarIAModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        dashboard={dashboard}
        widgetTitle={widgetTitle}
        widgetType={widgetType}
        filters={filters}
        data={data}
      />
    </>
  )
}
