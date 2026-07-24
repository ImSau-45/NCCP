import { useEffect, useRef, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useAuth } from "../hooks/AuthContext"

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ""

const RegisterPage = () => {
  const { register, googleSignIn } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const googleBtnRef = useRef(null)

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !window.google) return
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async (response) => {
        setError(null)
        setLoading(true)
        try {
          await googleSignIn(response.credential)
          navigate("/dashboard")
        } catch (err) {
          setError(err.message)
        } finally {
          setLoading(false)
        }
      },
    })
    window.google.accounts.id.renderButton(googleBtnRef.current, {
      theme: "outline",
      size: "large",
      width: "100%",
      text: "signup_with",
    })
  }, [googleSignIn, navigate])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    if (password.length < 6) {
      setError("Password must be at least 6 characters")
      return
    }
    setLoading(true)
    try {
      await register(email, password, name)
      navigate("/dashboard")
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-600">
            <svg className="h-6 w-6 text-white" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="text-2xl font-semibold text-white">Create your account</h1>
          <p className="text-sm text-slate-400">Start automating your CI/CD pipelines</p>
        </div>

        <div className="rounded-2xl border border-subtle bg-[#111827] p-8 shadow-2xl">
          {GOOGLE_CLIENT_ID && (
            <>
              <div ref={googleBtnRef} className="w-full" />
              <div className="my-5 flex items-center gap-3">
                <div className="h-px flex-1 bg-white/10" />
                <span className="text-xs text-slate-500">or register with email</span>
                <div className="h-px flex-1 bg-white/10" />
              </div>
            </>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-300">Full name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Jane Smith"
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-300">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-300">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Min. 6 characters"
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            {error && (
              <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3.5 py-2.5 text-sm text-rose-400">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-60"
            >
              {loading ? "Creating account…" : "Create account"}
            </button>
          </form>

          <p className="mt-5 text-center text-sm text-slate-500">
            Already have an account?{" "}
            <Link to="/login" className="text-indigo-400 hover:text-indigo-300">
              Sign in
            </Link>
          </p>
        </div>
      </div>

      {GOOGLE_CLIENT_ID && (
        <script src="https://accounts.google.com/gsi/client" async defer />
      )}
    </div>
  )
}

export default RegisterPage
