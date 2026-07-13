import { Outlet, NavLink } from 'react-router-dom'
import SidebarChat from './SidebarChat'
import { useChat } from '../context/ChatContext'
import observatorioSvg from '../../SVG/nav_OBSERVATORIO_3.svg?raw'
import prediccionSvg from '../../SVG/nav_PREDICCION_GRAFICA.svg?raw'
import matchSvg from '../../SVG/nav_MATCH_FICHA.svg?raw'
import emprendeSvg from '../../SVG/nav_EMPRENDER_2.svg?raw'
import coachSvg from '../../SVG/nav_COACH.svg?raw'
import inicioSvg from '../../SVG/nav_INICIO.svg?raw'
import simulacionSvg from '../../SVG/nav_SIMULACION_2.svg?raw'

const SvgIcon = ({ raw }: { raw: string }) => (
  <span className="nav-svg-icon" dangerouslySetInnerHTML={{ __html: raw }} />
)

const navItems = [
  { to: '/', label: 'Inicio', icon: <SvgIcon raw={inicioSvg} /> },
  { to: '/observatorio', label: 'Observatorio', icon: <SvgIcon raw={observatorioSvg} /> },
  { to: '/prediccion', label: 'Predicción', icon: <SvgIcon raw={prediccionSvg} /> },
  { to: '/match', label: 'Match Inteligente', icon: <SvgIcon raw={matchSvg} /> },
  { to: '/emprende', label: 'Emprende IA', icon: <SvgIcon raw={emprendeSvg} /> },
  { to: '/coach', label: 'Coach IA', icon: <SvgIcon raw={coachSvg} /> },
  { to: '/simulacion', label: 'Simulación', icon: <SvgIcon raw={simulacionSvg} /> },
]

export default function Layout() {
  const { open } = useChat()

  return (
    <div className="app">
      <aside className="sidebar">
        {open ? (
          <SidebarChat />
        ) : (
          <>
            <span className="screw tl" />
            <span className="screw tr" />
            <span className="screw bl" />
            <span className="screw br" />

            <div className="brand">
              <img src="/logo-alba.png" alt="ALBA - Analítica Laboral Basada en IA" className="brand-logo-img" />
            </div>

            <nav className="nav">
              {navItems.map(({ to, label, icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                >
                  <div className="nav-left">
                    {icon}
                    <span className="nav-label">{label}</span>
                  </div>
                </NavLink>
              ))}
            </nav>
          </>
        )}
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
