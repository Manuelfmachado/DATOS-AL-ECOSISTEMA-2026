import { Outlet, NavLink } from 'react-router-dom'
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
  return (
    <div className="app">
      <aside className="sidebar">
        <span className="screw tl" />
        <span className="screw tr" />
        <span className="screw bl" />
        <span className="screw br" />

        <div className="brand">
          <div className="brand-logo">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" />
              <path d="M12 12l8-4.5M12 12L4 7.5M12 12v9" />
            </svg>
          </div>
          <div className="brand-text">
            <div className="name"><span className="brand-first">A</span>LBA</div>
            <div className="sub"><span className="brand-first">A</span>nalítica <span className="brand-first">L</span>aboral <span className="brand-first">B</span>asada en <span className="brand-first">AI</span></div>
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

      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
