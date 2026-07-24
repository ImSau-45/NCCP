import { createContext, useCallback, useContext, useEffect, useState } from "react"
import api, { setAuthToken } from "../api"

const AuthContext = createContext(null)

const TOKEN_KEY = "hifi_token"

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // On mount, restore session from localStorage
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      setLoading(false)
      return
    }
    setAuthToken(token)
    api.get("/auth/me")
      .then((res) => setUser(res.data.user))
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY)
        setAuthToken(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const _storeSession = useCallback((token, userData) => {
    localStorage.setItem(TOKEN_KEY, token)
    setAuthToken(token)
    setUser(userData)
  }, [])

  const login = useCallback(async (email, password) => {
    const res = await api.post("/auth/login", { email, password })
    _storeSession(res.data.access_token, res.data.user)
    return res.data.user
  }, [_storeSession])

  const register = useCallback(async (email, password, name) => {
    const res = await api.post("/auth/register", { email, password, name })
    _storeSession(res.data.access_token, res.data.user)
    return res.data.user
  }, [_storeSession])

  const googleSignIn = useCallback(async (idToken) => {
    const res = await api.post("/auth/google", { id_token: idToken })
    _storeSession(res.data.access_token, res.data.user)
    return res.data.user
  }, [_storeSession])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setAuthToken(null)
    setUser(null)
  }, [])

  const refreshUser = useCallback(async () => {
    const res = await api.get("/auth/me")
    setUser(res.data.user)
    return res.data.user
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, googleSignIn, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider")
  return ctx
}
