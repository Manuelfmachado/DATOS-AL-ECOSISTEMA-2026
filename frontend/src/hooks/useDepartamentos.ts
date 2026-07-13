import { useEffect, useState } from 'react'
import api from '../services/api'

export function useDepartamentos() {
  const [deptos, setDeptos] = useState<{ nombre: string; codigo: number }[]>([])
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    const cargar = async () => {
      try {
        // Obtener departamentos del endpoint de sectores con un departamento conocido
        const res = await api.get('/observatorio/departamentos/Bogot%C3%A1/sectores')
        if (res.data?.departamentos_disponibles) {
          setDeptos(res.data.departamentos_disponibles)
        } else {
          // Fallback: lista básica
          setDeptos([
            { nombre: 'Amazonas', codigo: 91 },
            { nombre: 'Antioquia', codigo: 5 },
            { nombre: 'Arauca', codigo: 81 },
            { nombre: 'Atlántico', codigo: 8 },
            { nombre: 'Bogotá', codigo: 11 },
            { nombre: 'Bolívar', codigo: 13 },
            { nombre: 'Boyacá', codigo: 15 },
            { nombre: 'Caldas', codigo: 17 },
            { nombre: 'Caquetá', codigo: 18 },
            { nombre: 'Casanare', codigo: 19 },
            { nombre: 'Cauca', codigo: 20 },
            { nombre: 'Cesar', codigo: 21 },
            { nombre: 'Chocó', codigo: 27 },
            { nombre: 'Córdoba', codigo: 23 },
            { nombre: 'Cundinamarca', codigo: 25 },
            { nombre: 'Guainía', codigo: 94 },
            { nombre: 'Guaviare', codigo: 95 },
            { nombre: 'Huila', codigo: 41 },
            { nombre: 'La Guajira', codigo: 44 },
            { nombre: 'Magdalena', codigo: 47 },
            { nombre: 'Meta', codigo: 50 },
            { nombre: 'Nariño', codigo: 52 },
            { nombre: 'Norte De Santander', codigo: 54 },
            { nombre: 'Putumayo', codigo: 86 },
            { nombre: 'Quindío', codigo: 63 },
            { nombre: 'Risaralda', codigo: 66 },
            { nombre: 'San Andrés', codigo: 88 },
            { nombre: 'Santander', codigo: 68 },
            { nombre: 'Sucre', codigo: 70 },
            { nombre: 'Tolima', codigo: 73 },
            { nombre: 'Valle Del Cauca', codigo: 76 },
            { nombre: 'Vaupés', codigo: 97 },
            { nombre: 'Vichada', codigo: 99 },
          ])
        }
      } catch (e) {
        setDeptos([])
      } finally {
        setCargando(false)
      }
    }
    cargar()
  }, [])

  return { deptos, cargando }
}
