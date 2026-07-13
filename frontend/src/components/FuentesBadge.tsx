interface FuentesBadgeProps {
  fuentes: string[]
  explicacion?: string
}

export default function FuentesBadge({ fuentes, explicacion }: FuentesBadgeProps) {
  return (
    <div className="text-xs text-[#9aa3b8] mt-6">
      <span className="font-medium text-[#c2cad8]">Fuentes:</span>{' '}
      {fuentes.join(' · ')}
      {explicacion && (
        <span className="block mt-1 text-[#8a93a8] text-[0.85rem]">{explicacion}</span>
      )}
    </div>
  )
}
