import { useEffect, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { setAuthToken } from "../api"
import api from "../api"
import { useAuth } from "../hooks/AuthContext"

const GitHubSuccess = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { refreshUser } = useAuth()
  const [error, setError] = useState(null)

  useEffect(() => {
    const token = searchParams.get("token")
    if (!token) {
      setError("No token received from GitHub OAuth.")
      return
    }
    localStorage.setItem("hifi_token", token)
    setAuthToken(token)
    const redirect = sessionStorage.getItem("hifi_post_oauth_redirect") || "/dashboard"
    sessionStorage.removeItem("hifi_post_oauth_redirect")
    refreshUser()
      .then(() => navigate(redirect))
      .catch((err) => setError(err.message))
  }, [searchParams, navigate, refreshUser])

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg">
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-400 max-w-sm text-center">
          GitHub connection failed: {error}
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        <p className="text-sm text-slate-400">Connecting GitHub…</p>
      </div>
    </div>
  )
}

export default GitHubSuccess
