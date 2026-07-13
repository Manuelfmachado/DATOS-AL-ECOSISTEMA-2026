import { useState } from 'react'
import { GraduationCap, AlertCircle } from 'lucide-react'
import api from '../services/api'

export default function AlertaCurricular() {
  const [programa, setPrograma] = useState('')
  const [departamento, setDepartamento] = useState('BOGOTÁ')
  const [resultado, setResultado] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const analizar = async () => {
    if (!programa) return
    setLoading(true)
    try {
      const res = await api.post('/alerta-curricular/brecha', { programa, departamento })
      setResultado(res.data)
    } catch (e) {
      setResultado({ error: 'Error al analizar' })
    }
    setLoading(false)
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Sistema de Alerta Curricular Nacional</h1>
      <p className="text-gray-600 mb-8">Detecta brechas entre la oferta educativa y la demanda del mercado laboral</p>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Programa académico</label>
            <input
              type="text"
              value={programa}
              onChange={e => setPrograma(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && analizar()}
              placeholder="ej: ingeniería, contaduría, derecho"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-alba-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Departamento</label>
            <select
              value={departamento}
              onChange={e => setDepartamento(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-alba-500"
            >
              {['BOGOTÁ', 'ANTIOQUIA', 'VALLE DEL CAUCA', 'ATLÁNTICO', 'SANTANDER', 'CUNDINAMARCA', 'BOLÍVAR'].map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
        </div>
        <button
          onClick={analizar}
          disabled={loading}
          className="mt-4 bg-alba-600 text-white px-6 py-3 rounded-lg hover:bg-alba-700 disabled:opacity-50 flex items-center gap-2"
        >
          <GraduationCap size={20} /> {loading ? 'Analizando...' : 'Analizar brecha'}
        </button>
      </div>

      {resultado && !resultado.error && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <h2 className="text-lg font-bold mb-4">Oferta educativa</h2>
            <div className="space-y-3">
              <div className="flex justify-between"><span>Programas SNIES:</span><span className="font-bold">{resultado.oferta_educatica?.programas_snies || resultado.oferta_educativa?.programas_snies || 0}</span></div>
              <div className="flex justify-between"><span>Cursos SENA:</span><span className="font-bold">{resultado.oferta_educativa?.cursos_sena || 0}</span></div>
              <div className="flex justify-between"><span>Total matriculados:</span><span className="font-bold">{Math.round(resultado.oferta_educativa?.total_matriculados || 0).toLocaleString()}</span></div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border p-6">
            <h2 className="text-lg font-bold mb-4">Demanda laboral</h2>
            <div className="space-y-3">
              <div className="flex justify-between"><span>Sectores formales:</span><span className="font-bold">{resultado.demanda_laboral?.sectores_formales_top || 0}</span></div>
              <div className="flex justify-between"><span>Cotizantes total:</span><span className="font-bold">{Math.round(resultado.demanda_laboral?.cotizantes_total || 0).toLocaleString()}</span></div>
            </div>
          </div>

          {resultado.cursos_sena_recomendados?.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border p-6 lg:col-span-2">
              <h2 className="text-lg font-bold mb-4">Cursos SENA recomendados</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {resultado.cursos_sena_recomendados.map((c: any, i: number) => (
                  <div key={i} className="border rounded-lg p-4">
                    <p className="font-medium text-gray-800">{c.programa}</p>
                    <p className="text-sm text-gray-500 mt-1">Área: {c.area} · Duración: {c.duracion}h</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
