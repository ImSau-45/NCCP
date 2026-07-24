import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../hooks/AuthContext"
import api from "../api"

const GitHubIcon = () => (
  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12" />
  </svg>
)

const Step = ({ n, label, active, done }) => (
  <div className={`flex items-center gap-2 text-sm ${done ? "text-emerald-400" : active ? "text-white" : "text-slate-500"}`}>
    <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold
      ${done ? "bg-emerald-500/20 text-emerald-400" : active ? "bg-indigo-600 text-white" : "bg-white/5 text-slate-500"}`}>
      {done ? "✓" : n}
    </span>
    {label}
  </div>
)

const NewProject = () => {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [repoUrl, setRepoUrl] = useState("")
  const [urlError, setUrlError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const githubConnected = user?.github_connected

  // Live URL validation
  const validateUrl = (val) => {
    if (!val) return null
    if (!val.includes("github.com")) return "Only GitHub repositories are supported"
    const parts = val.replace("https://github.com/", "").replace("git@github.com:", "").split("/")
    if (parts.length < 2 || !parts[0] || !parts[1]) return "Use format: https://github.com/owner/repo"
    return null
  }

  const handleUrlChange = (e) => {
    const val = e.target.value
    setRepoUrl(val)
    setUrlError(validateUrl(val))
    setSubmitError(null)
  }

  const handleConnectGitHub = async () => {
    sessionStorage.setItem("hifi_post_oauth_redirect", "/projects/new")
    try {
      const res = await api.get("/auth/github/login/url")
      window.location.href = res.data.url
    } catch (err) {
      setSubmitError(err.message)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const err = validateUrl(repoUrl)
    if (err) { setUrlError(err); return }
    if (!githubConnected) { setSubmitError("Connect GitHub first"); return }

    setSubmitting(true)
    setSubmitError(null)
    try {
      const res = await api.post("/projects", { repo_url: repoUrl.trim() })
      navigate(`/projects/${res.data.project.id}`)
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const currentStep = !githubConnected ? 1 : !repoUrl ? 2 : 3

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-white">New Project</h1>
        <p className="mt-1 text-sm text-slate-400">
          Connect a GitHub repo and HiFi will generate a CI/CD pipeline for it.
        </p>
      </div>

      {/* Progress steps */}
      <div className="flex items-center gap-6 rounded-xl border border-subtle bg-[#111827] px-6 py-4">
        <Step n={1} label="Connect GitHub" active={currentStep === 1} done={currentStep > 1} />
        <div className="h-px flex-1 bg-white/10" />
        <Step n={2} label="Enter repo URL" active={currentStep === 2} done={currentStep > 2} />
        <div className="h-px flex-1 bg-white/10" />
        <Step n={3} label="Analyse & generate" active={currentStep === 3} done={false} />
      </div>

      {/* Step 1 — GitHub connect */}
      <section className="rounded-xl border border-subtle bg-[#111827] p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold text-white">GitHub Account</h2>
            <p className="mt-1 text-sm text-slate-400">
              HiFi needs read access to your repositories (scopes: <code className="text-indigo-400">repo</code>, <code className="text-indigo-400">read:org</code>).
              We never ask for a personal access token.
            </p>
          </div>
          {githubConnected ? (
            <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-1.5 text-sm font-medium text-emerald-400 ring-1 ring-emerald-500/20 shrink-0">
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Connected{user?.github_login ? ` as @${user.github_login}` : ""}
            </div>
          ) : (
            <button
              onClick={handleConnectGitHub}
              className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-[#24292e] px-4 py-2 text-sm font-semibold text-white hover:bg-[#2f363d] transition-colors"
            >
              <GitHubIcon />
              Connect GitHub
            </button>
          )}
        </div>
      </section>

      {/* Step 2 — Repo URL */}
      <section className={`rounded-xl border bg-[#111827] p-6 transition-opacity ${!githubConnected ? "opacity-40 pointer-events-none" : "border-subtle"}`}>
        <h2 className="mb-4 font-semibold text-white">Repository URL</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              GitHub repository URL
            </label>
            <input
              type="url"
              value={repoUrl}
              onChange={handleUrlChange}
              placeholder="https://github.com/your-org/your-repo"
              disabled={!githubConnected}
              className={`w-full rounded-lg border px-3.5 py-2.5 text-sm text-white placeholder-slate-500 bg-white/5 outline-none transition
                focus:ring-1 focus:ring-indigo-500
                ${urlError ? "border-rose-500 focus:border-rose-500" : "border-white/10 focus:border-indigo-500"}`}
            />
            {urlError && (
              <p className="mt-1.5 flex items-center gap-1.5 text-xs text-rose-400">
                <svg className="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                </svg>
                {urlError}
              </p>
            )}
            <p className="mt-1.5 text-xs text-slate-500">
              Public or private repos you have access to. e.g. <span className="text-slate-400">https://github.com/vercel/next.js</span>
            </p>
          </div>

          {submitError && (
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3.5 py-2.5 text-sm text-rose-400">
              {submitError}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || !!urlError || !repoUrl || !githubConnected}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Creating project…
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Analyse Repository
              </>
            )}
          </button>
        </form>
      </section>

      {/* Info box */}
      <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4 text-sm text-slate-400">
        <p className="font-medium text-indigo-300 mb-1">What happens next?</p>
        <ul className="space-y-1 list-disc list-inside">
          <li>HiFi reads your repo's file tree and key config files</li>
          <li>Detects your language, framework, test setup, and Docker usage</li>
          <li>Generates tailored CI/CD step suggestions with per-repo reasoning</li>
          <li>You review and approve steps before anything touches your repo</li>
        </ul>
      </div>
    </div>
  )
}

export default NewProject
