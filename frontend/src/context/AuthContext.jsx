import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, setUnauthorizedHandler, tokenStore } from '../services/api'

const AuthContext = createContext(null)
export const useAuth = () => useContext(AuthContext)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!tokenStore.get())

  const logout = useCallback(() => { tokenStore.clear(); setUser(null) }, [])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    if (!tokenStore.get()) return
    api.me().then((d) => setUser(d.user)).catch(() => tokenStore.clear()).finally(() => setLoading(false))
  }, [logout])

  const authenticate = useCallback(async (mode, payload) => {
    const d = mode === 'login' ? await api.login(payload) : await api.register(payload)
    tokenStore.set(d.token)
    setUser(d.user)
  }, [])

  const value = useMemo(() => ({ user, loading, authenticate, logout }), [user, loading, authenticate, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
