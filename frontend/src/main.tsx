import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import { ChatProvider } from './context/ChatContext'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Observatorio from './pages/Observatorio'
import Prediccion from './pages/Prediccion'
import Match from './pages/Match'
import EmprendeIA from './pages/EmprendeIA'
import Coach from './pages/Coach'
import Simulacion from './pages/Simulacion'
import ErrorBoundary from './components/ErrorBoundary'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ChatProvider>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="observatorio" element={<ErrorBoundary><Observatorio /></ErrorBoundary>} />
            <Route path="prediccion" element={<ErrorBoundary><Prediccion /></ErrorBoundary>} />
            <Route path="match" element={<Match />} />
            <Route path="emprende" element={<EmprendeIA />} />
            <Route path="coach" element={<Coach />} />
            <Route path="simulacion" element={<ErrorBoundary><Simulacion /></ErrorBoundary>} />
          </Route>
        </Routes>
      </ChatProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
