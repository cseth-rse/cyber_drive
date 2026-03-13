// src/context/AuthContext.jsx
import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { api, setAccessToken, clearAccessToken } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)       // { email, role }
  const [loading, setLoading] = useState(true) // resolving on mount

  // On mount: try a silent refresh to restore session from cookie
  useEffect(() => {
    api.auth.refresh()
      .then(({ data }) => {
        setAccessToken(data.access_token)
        // Decode payload (no library needed — just base64)
        const payload = JSON.parse(atob(data.access_token.split('.')[1]))
        setUser({ email: payload.email, role: payload.role, id: payload.sub })
      })
      .catch(() => {/* no valid session */})
      .finally(() => setLoading(false))
  }, [])

  // Listen for forced logout from the interceptor
  useEffect(() => {
    const handler = () => { setUser(null); clearAccessToken() }
    window.addEventListener('auth:logout', handler)
    return () => window.removeEventListener('auth:logout', handler)
  }, [])

  const login = useCallback((accessToken, role, email) => {
    setAccessToken(accessToken)
    const payload = JSON.parse(atob(accessToken.split('.')[1]))
    setUser({ email: payload.email || email, role: payload.role || role, id: payload.sub })
  }, [])

  const logout = useCallback(async () => {
    try { await api.auth.logout() } catch {}
    clearAccessToken()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
