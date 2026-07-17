import { useEffect, useState } from 'react'
import api from '../services/api'

let _cachedMode: { isOffline: boolean; llm: string } | null = null

export function useAppMode() {
  const [mode, setMode] = useState(_cachedMode ?? { isOffline: false, llm: 'Gemini' })

  useEffect(() => {
    if (_cachedMode) return
    api.get('/health').then((res) => {
      const m = { isOffline: res.data?.mode === 'offline', llm: res.data?.llm || 'Gemini' }
      _cachedMode = m
      setMode(m)
    }).catch(() => {
      _cachedMode = { isOffline: false, llm: 'Gemini' }
      setMode(_cachedMode)
    })
  }, [])

  return mode
}
