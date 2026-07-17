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
import logoFinalSvg from '../../SVG/LOGO FINAL.svg'

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
    <div className={`app ${open ? 'app-chat-open' : ''}`}>
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
              <div className="brand-logo-wrap">
                <img src={logoFinalSvg} alt="ALBA" className="brand-logo-svg" />
                <div className="brand-subtext">
                  <span className="brand-subtext-small">A</span>nalítica{' '}
                  <span className="brand-subtext-small">L</span>aboral{' '}
                  <span className="brand-subtext-small">B</span>asada en{' '}
                  <span className="brand-subtext-small">I</span>A
                </div>
              </div>
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

            <div className="mt-auto pt-4 pb-4 px-3">
              <a
                href="https://github.com/Manuelfmachado/DATOS-AL-ECOSISTEMA-2026/releases/latest"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-offline"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 flex-shrink-0">
                  <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
                </svg>
                <span>Descargar ALBA Offline</span>
              </a>
            </div>
          </>
        )}
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
