import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const DEFAULTS = { speakQuestions: true, showFeedback: true, captions: true, behaviorAnalysis: true }
const KEY = 'ais_settings'
const SettingsContext = createContext(null)
export const useSettings = () => useContext(SettingsContext)

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(() => {
    try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) || '{}') } } catch { return DEFAULTS }
  })
  useEffect(() => { try { localStorage.setItem(KEY, JSON.stringify(settings)) } catch { /* storage unavailable */ } }, [settings])
  const value = useMemo(() => ({ settings, update: (patch) => setSettings((s) => ({ ...s, ...patch })), reset: () => setSettings(DEFAULTS) }), [settings])
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
}
