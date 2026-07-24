import { useEffect, useRef, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import api from "../api"

// ── Status helpers ────────────────────────────────────────────────────────────

const STATUS_META = {
  pending_analysis: { label: "Analysing…", color: "text-yellow-400", bg: "bg-yellow-500/15", dot: "bg-yellow-400" },
  analyzed:         { label: "Analysed",   color: "text-blue-400",   bg: "bg-blue-500/15",   dot: "bg-blue-400" },
  awaiting_approval:{ label: "Awaiting Approval", color: "text-orange-400", bg: "bg-orange-500/15", dot: "bg-orange-400" },
  generating_yaml:  { label: "Generating…", color: "text-purple-400", bg: "bg-purple-500/15", dot: "bg-purple-400" },
  pr_created:       { label: "PR Open",    color: "text-indigo-400", bg: "bg-indigo-500/15", dot: "bg-indigo-400" },
  pr_merged:        { label: "Live ✓",     color: "text-emerald-400",bg: "bg-emerald-500/15",dot: "bg-emerald-400" },
  failed:           { label: "Failed",     color: "text-rose-400",   bg: "bg-rose-500/15",   dot: "bg-rose-400" },
}

const StatusBadge = ({ status }) => {
  const m = STATUS_META[status] || { label: status, color: "text-slate-400", bg: "bg-slate-500/15", dot: "bg-slate-400" }
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${m.bg} ${m.color}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${m.dot}`} />
      {m.label}
    </span>
  )
}

// ── Analysis progress display ─────────────────────────────────────────────────

const PROGRESS_STEPS = [
  { key: "pending_analysis", label: "Reading repo tree…" },
  { key: "pending_analysis", label: "Detecting tech stack…" },
  { key: "analyzed",         label: "Generating step suggestions…" },
  { key: "awaiting_approval",label: "Ready for your review" },
]

const AnalysisProgress = ({ status }) => {
  const [visibleCount, setVisibleCount] = useState(1)
  const intervalRef = useRef(null)

  useEffect(() => {
    if (status !== "pending_analysis" && status !== "analyzed") return
    intervalRef.current = setInterval(() => {
      setVisibleCount((c) => {
        const max = status === "awaiting_approval" ? 4 : 3
        return c < max ? c + 1 : c
      })
    }, 1400)
    return () => clearInterval(intervalRef.current)
  }, [status])

  useEffect(() => {
    if (status === "awaiting_approval") setVisibleCount(4)
  }, [status])

  return (
    <div className="space-y-3">
      {PROGRESS_STEPS.slice(0, visibleCount).map((step, i) => (
        <div key={i} className="flex items-center gap-3 text-sm">
          {i < visibleCount - 1 || status === "awaiting_approval" ? (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 text-xs">✓</span>
          ) : (
            <span className="flex h-5 w-5 items-center justify-center">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
            </span>
          )}
          <span className={i < visibleCount - 1 || status === "awaiting_approval" ? "text-slate-300" : "text-white"}>
            {step.label}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Stack summary panel ───────────────────────────────────────────────────────

const StackPill = ({ label, value }) => {
  if (!value && value !== false) return null
  return (
    <div className="flex items-center justify-between rounded-lg bg-white/5 px-3 py-2 text-sm">
      <span className="text-slate-400">{label}</span>
      <span className={`font-medium ${value === true ? "text-emerald-400" : value === false ? "text-slate-500" : "text-white"}`}>
        {value === true ? "Yes" : value === false ? "No" : value}
      </span>
    </div>
  )
}

const StackPanel = ({ stack }) => (
  <div className="rounded-xl border border-subtle bg-[#111827] p-5">
    <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">Detected Stack</h3>
    <div className="space-y-1.5">
      <StackPill label="Language"        value={stack.language} />
      <StackPill label="Framework"       value={stack.framework} />
      <StackPill label="Package Manager" value={stack.package_manager} />
      <StackPill label="Test Framework"  value={stack.test_framework} />
      <StackPill label="Has Tests"       value={stack.has_tests} />
      <StackPill label="Has Dockerfile"  value={stack.has_dockerfile} />
      <StackPill label="Has CI already"  value={stack.has_ci} />
      {stack.node_version   && <StackPill label="Node version"   value={stack.node_version} />}
      {stack.python_version && <StackPill label="Python version" value={stack.python_version} />}
      {stack.lint_config    && <StackPill label="Lint config"    value={stack.lint_config} />}
    </div>
  </div>
)

// ── Step card ─────────────────────────────────────────────────────────────────

const STEP_ICONS = {
  lint:         "🔍",
  test:         "🧪",
  build:        "🔨",
  docker_build: "🐳",
  deploy:       "🚀",
}

const StepCard = ({ step }) => (
  <div className={`rounded-xl border p-5 transition ${step.recommended ? "border-indigo-500/30 bg-indigo-500/5" : "border-subtle bg-[#111827]"}`}>
    <div className="flex items-start gap-3">
      <span className="text-xl">{STEP_ICONS[step.step_key] || "⚙️"}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="font-medium text-white">{step.title}</p>
          {step.recommended && (
            <span className="rounded-full bg-indigo-500/20 px-2 py-0.5 text-xs font-medium text-indigo-400">
              Recommended
            </span>
          )}
        </div>
        <p className="mt-1.5 text-sm text-slate-400 leading-relaxed">{step.description}</p>
        {step.yaml_snippet_preview && (
          <pre className="mt-3 rounded-lg bg-slate-950 px-3 py-2 text-xs text-slate-300 overflow-x-auto">
            {step.yaml_snippet_preview}
          </pre>
        )}
      </div>
    </div>
  </div>
)

// ── Main component ────────────────────────────────────────────────────────────

const POLLING_STATUSES = new Set(["pending_analysis", "analyzed"])

const ProjectDetail = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reanalysing, setReanalysing] = useState(false)
  const pollRef = useRef(null)

  const fetchProject = async () => {
    try {
      const res = await api.get(`/projects/${id}`)
      setData(res.data)
      setError(null)
      return res.data.project.status
    } catch (err) {
      setError(err.message)
      return null
    } finally {
      setLoading(false)
    }
  }

  // Lightweight status poll — only fetches full data when status changes
  const startPolling = () => {
    clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const res = await api.get(`/projects/${id}/status`)
        const { status } = res.data
        if (!POLLING_STATUSES.has(status)) {
          clearInterval(pollRef.current)
          fetchProject()  // fetch full data once analysis is done
        }
      } catch {
        clearInterval(pollRef.current)
      }
    }, 2500)
  }

  useEffect(() => {
    fetchProject().then((status) => {
      if (POLLING_STATUSES.has(status)) startPolling()
    })
    return () => clearInterval(pollRef.current)
  }, [id])

  const handleReanalyse = async () => {
    setReanalysing(true)
    try {
      await api.post(`/projects/${id}/analyze`)
      await fetchProject()
      startPolling()
    } catch (err) {
      setError(err.message)
    } finally {
      setReanalysing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-400">
        {error}
      </div>
    )
  }

  const { project, steps, workflow } = data
  const isAnalysing = POLLING_STATUSES.has(project.status)
  const hasFailed = project.status === "failed"
  const stack = project.detected_stack || {}
  const hasStack = Object.keys(stack).some((k) => stack[k] !== null && stack[k] !== false)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-1">
            <button onClick={() => navigate("/projects")} className="hover:text-slate-300 transition-colors">
              Projects
            </button>
            <span>/</span>
            <span className="text-slate-300">{project.repo_name}</span>
          </div>
          <h1 className="text-xl font-semibold text-white">
            {project.repo_owner}/{project.repo_name}
          </h1>
          <a
            href={project.repo_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-0.5 text-xs text-slate-500 hover:text-indigo-400 transition-colors"
          >
            {project.repo_url} ↗
          </a>
        </div>
        <StatusBadge status={project.status} />
      </div>

      {/* Analysis in progress */}
      {isAnalysing && (
        <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-6">
          <h2 className="mb-4 font-semibold text-white">Analysing your repository…</h2>
          <AnalysisProgress status={project.status} />
          <p className="mt-4 text-xs text-slate-500">
            This usually takes 5–15 seconds. The page updates automatically.
          </p>
        </div>
      )}

      {/* Failed state */}
      {hasFailed && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6">
          <h2 className="mb-2 font-semibold text-rose-400">Analysis failed</h2>
          <p className="text-sm text-rose-300">{project.error_message || "An unknown error occurred."}</p>
          <div className="mt-4 flex gap-3">
            <button
              onClick={handleReanalyse}
              disabled={reanalysing}
              className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-500 disabled:opacity-50"
            >
              {reanalysing ? "Starting…" : "Re-analyse"}
            </button>
            <button
              onClick={() => navigate("/projects/new")}
              className="rounded-lg border border-rose-500/30 px-4 py-2 text-sm text-rose-400 hover:bg-rose-500/10"
            >
              Try a different repository
            </button>
          </div>
        </div>
      )}

      {/* Stack + Steps (shown once awaiting_approval or beyond) */}
      {!isAnalysing && !hasFailed && (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left: stack summary */}
          {hasStack && (
            <div className="lg:col-span-1">
              <StackPanel stack={stack} />
            </div>
          )}

          {/* Right: automation steps */}
          <div className={hasStack ? "lg:col-span-2" : "lg:col-span-3"}>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold text-white">
                Suggested Automation Steps
                <span className="ml-2 text-sm font-normal text-slate-500">({steps.length})</span>
              </h2>
              <div className="flex gap-2">
                <button
                  onClick={() => navigate(`/projects/${id}/autofix`)}
                  className="inline-flex items-center gap-2 rounded-lg border border-emerald-500/40 px-4 py-2 text-sm font-semibold text-emerald-400 hover:bg-emerald-500/10"
                >
                  🤖 Auto-Fix History
                </button>
                {workflow && (
                  <button
                    onClick={() => navigate(`/projects/${id}/workflow`)}
                    className="inline-flex items-center gap-2 rounded-lg border border-indigo-500/40 px-4 py-2 text-sm font-semibold text-indigo-400 hover:bg-indigo-500/10"
                  >
                    View Workflow
                  </button>
                )}
                {project.status === "awaiting_approval" && (
                  <button
                    onClick={() => navigate(`/projects/${id}/review`)}
                    className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
                  >
                    Review & Approve →
                  </button>
                )}
              </div>
            </div>

            {steps.length === 0 ? (
              <div className="rounded-xl border border-subtle bg-[#111827] p-8 text-center text-sm text-slate-400">
                No steps generated yet.
              </div>
            ) : (
              <div className="space-y-3">
                {steps.map((step) => <StepCard key={step.id} step={step} />)}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default ProjectDetail
