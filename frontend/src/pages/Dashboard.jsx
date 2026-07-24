import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { useAuth } from "../hooks/AuthContext"
import api from "../api"

const EmptyState = () => (
  <div className="flex flex-col items-center justify-center py-24 text-center">
    {/* Illustration */}
    <div className="relative mb-8">
      <div className="flex h-24 w-24 items-center justify-center rounded-3xl bg-indigo-600/10 ring-1 ring-indigo-500/20">
        <svg className="h-12 w-12 text-indigo-400" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
        </svg>
      </div>
      {/* Decorative dots */}
      <div className="absolute -right-3 -top-3 h-3 w-3 rounded-full bg-indigo-500/40" />
      <div className="absolute -bottom-2 -left-4 h-2 w-2 rounded-full bg-purple-500/40" />
    </div>

    <h2 className="text-xl font-semibold text-white">No pipelines yet</h2>
    <p className="mt-3 max-w-sm text-sm text-slate-400 leading-relaxed">
      Connect a GitHub repository and HiFi will automatically detect your tech stack,
      generate a CI/CD workflow, and open a pull request — in minutes.
    </p>

    {/* 3-step flow */}
    <div className="mt-8 flex items-center gap-3 text-xs text-slate-500">
      <div className="flex items-center gap-1.5">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-600/20 text-indigo-400 font-semibold">1</span>
        Connect GitHub
      </div>
      <div className="h-px w-6 bg-slate-700" />
      <div className="flex items-center gap-1.5">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-600/20 text-indigo-400 font-semibold">2</span>
        Approve steps
      </div>
      <div className="h-px w-6 bg-slate-700" />
      <div className="flex items-center gap-1.5">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-600/20 text-indigo-400 font-semibold">3</span>
        Merge PR
      </div>
    </div>

    <Link
      to="/projects/new"
      className="mt-8 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500"
    >
      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
      </svg>
      Connect GitHub &amp; Start
    </Link>
  </div>
)

const StatusBadge = ({ status }) => {
  const map = {
    pending_analysis: { label: "Analyzing…", cls: "bg-yellow-500/15 text-yellow-400" },
    analyzed: { label: "Analyzed", cls: "bg-blue-500/15 text-blue-400" },
    awaiting_approval: { label: "Awaiting Approval", cls: "bg-orange-500/15 text-orange-400" },
    generating_yaml: { label: "Generating…", cls: "bg-purple-500/15 text-purple-400" },
    pr_created: { label: "PR Open", cls: "bg-indigo-500/15 text-indigo-400" },
    pr_merged: { label: "Live ✓", cls: "bg-emerald-500/15 text-emerald-400" },
    failed: { label: "Failed", cls: "bg-rose-500/15 text-rose-400" },
  }
  const { label, cls } = map[status] || { label: status, cls: "bg-slate-500/15 text-slate-400" }
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>{label}</span>
}

const Dashboard = () => {
  const { user } = useAuth()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.get("/projects")
      .then((res) => setProjects(res.data.projects || []))
      .catch((err) => {
        // 404 means route not yet built (Phase 3) — treat as empty
        if (err.message?.includes("404") || err.message?.includes("Not found")) {
          setProjects([])
        } else {
          setError(err.message)
        }
      })
      .finally(() => setLoading(false))
  }, [])

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
        Failed to load dashboard: {error}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">
            Welcome back{user?.name ? `, ${user.name.split(" ")[0]}` : ""}
          </h1>
          <p className="mt-0.5 text-sm text-slate-400">
            {projects.length > 0
              ? `You have ${projects.length} project${projects.length !== 1 ? "s" : ""}`
              : "Get started by connecting your first repository"}
          </p>
        </div>
        {projects.length > 0 && (
          <Link
            to="/projects/new"
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            New Project
          </Link>
        )}
      </div>

      {projects.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <Link
              key={p.id}
              to={`/projects/${p.id}`}
              className="group rounded-xl border border-subtle bg-[#111827] p-5 transition hover:border-indigo-500/40 hover:bg-[#131d35]"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-medium text-white">{p.repo_name || p.repo_url}</p>
                  <p className="mt-0.5 truncate text-xs text-slate-500">{p.repo_owner}</p>
                </div>
                <StatusBadge status={p.status} />
              </div>
              <p className="mt-3 text-xs text-slate-500">
                Updated {new Date(p.updated_at || p.created_at).toLocaleDateString()}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export default Dashboard
