import { useEffect, useState } from "react"
import api, { setAuthToken } from "../api"

const TOKEN_KEY = "pipeline_sh_token"

export function useAuth() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem(TOKEN_KEY) || "")

  useEffect(() => {
    if (token) {
      setAuthToken(token)
      localStorage.setItem(TOKEN_KEY, token)
    }
  }, [token])

  const login = async (email, password) => {
    const resp = await api.post("/auth/login", { email, password })
    setToken(resp.data.access_token)
    setUser(resp.data.user)
    return resp.data
  }

  const logout = () => {
    setToken("")
    setUser(null)
    localStorage.removeItem(TOKEN_KEY)
    setAuthToken(null)
  }

  return { user, token, login, logout }
}
