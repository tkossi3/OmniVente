import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import api, { getToken, setToken } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [tenant, setTenant] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    async function restore() {
      if (!getToken()) {
        setLoading(false)
        return
      }
      try {
        const profile = await api.me()
        if (active) setTenant(profile)
      } catch {
        setToken('')
      } finally {
        if (active) setLoading(false)
      }
    }
    restore()
    return () => {
      active = false
    }
  }, [])

  const login = useCallback(async (credentials) => {
    const data = await api.login(credentials)
    setToken(data.access_token)
    setTenant(data.tenant)
    return data.tenant
  }, [])

  const register = useCallback(async (payload) => {
    const data = await api.register(payload)
    setToken(data.access_token)
    setTenant(data.tenant)
    return data.tenant
  }, [])

  const logout = useCallback(() => {
    setToken('')
    setTenant(null)
  }, [])

  const refresh = useCallback(async () => {
    const profile = await api.me()
    setTenant(profile)
    return profile
  }, [])

  const value = useMemo(
    () => ({ tenant, setTenant, loading, login, register, logout, refresh }),
    [tenant, loading, login, register, logout, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth doit etre utilise dans AuthProvider')
  return context
}
