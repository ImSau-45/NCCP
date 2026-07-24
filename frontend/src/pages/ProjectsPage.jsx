import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import api from "../api"

const STATUS_META = {
  pending_analysis:  { label: "Analysing…",        cls: "bg-yellow-500/15 text-yellow-400" },
  analyzed:          { label: "Analysed",           cls: "bg-blue-500/15 text-blue-400" },
  awaiting_approval: { label: "Awaiting Approval",  cls: "bg-orange-500/15 text-orange-400" },
  generating_yaml:   { label: "Generating…",        cls: "bg-purple-500/15 text-purple-400" },
  pr_created:        { label: "PR Open",            cls: "bg-indigo-500/15 text-indigo-400" },
  pr_merged:         { label: "Live ✓",             cls: "bg-emerald-500/15 text-emerald-400" },
  failed:            { label: "Failed",             cls: "bg-rose-500/15 text-rose-400" },
}

const StatusBadge = ({ status }) => {
  const m = STATUS_META[status] || { label: status, cls: "bg-slate-500/15 text-slate-400" }
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${m.cls}`}>{m.label}</span>
}

const timeAgo = (iso) => {
  if (!iso) return "—"
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

const ProjectsPage = () => {
  const navigate = useNavigate()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [deleting, setDeleting] = useState(null)

  const load = () => {
    setLoading(true)
    api.get("/projects")
      .then((res) => { setProjects(res.data.projects || []); setError(null) })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (e, id) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm("Delete this project? This cannot be undone.")) return
    setDeleting(id)
    try {
      await api.delete(`/projects/${id}`)
      setProjects((prev) => prev.filter((p) => p.id !== id))
    } catch (err) {
      alert(err.message)
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Projects</h1>
          {!loading && !error && (
            <p className="mt-0.5 text-sm text-slate-400">
              {projects.length} project{projects.length !== 1 ? "s" : ""}
            </p>
          )}
        </div>
        <Link
          to="/projects/new"
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          New Project
        </Link>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-24">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-400">
          Failed to load projects: {error}
          <button onClick={load} className="ml-3 underline hover:no-underline">Retry</button>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && projects.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-subtle bg-[#111827] py-20 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600/10 ring-1 ring-indigo-500/20 mb-4">
            <svg className="h-7 w-7 text-indigo-400" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
            </svg>
          </div>
          <h2 className="text-base font-semibold text-white">No projects yet</h2>
          <p className="mt-1.5 text-sm text-slate-400 max-w-xs">
            Connect a GitHub repository to generate your first CI/CD pipeline.
          </p>
          <Link
            to="/projects/new"
            className="mt-5 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
          >
            New Project
          </Link>
        </div>
      )}

      {/* Project list */}
      {!loading && !error && projects.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-subtle">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-subtle bg-white/3">
                <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Repository</th>
                <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Status</th>
                <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Branch</th>
                <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Updated</th>
                <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {projects.map((p) => (
                <tr
                  key={p.id}
                  onClick={() => navigate(`/projects/${p.id}`)}
                  className="cursor-pointer bg-[#111827] hover:bg-white/3 transition-colors"
                >
                  <td className="px-5 py-4">
                    <p className="font-medium text-white">{p.repo_owner}/{p.repo_name}</p>
                    <p className="text-xs text-slate-500 truncate max-w-xs">{p.repo_url}</p>
                  </td>
                  <td className="px-5 py-4">
                    <StatusBadge status={p.status} />
                  </td>
                  <td className="px-5 py-4 text-slate-400">
                    {p.default_branch || "main"}
                  </td>
                  <td className="px-5 py-4 text-slate-500">
                    {timeAgo(p.updated_at || p.created_at)}
                  </td>
                  <td className="px-5 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); navigate(`/projects/${p.id}`) }}
                        className="rounded-lg border border-white/10 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-white/5 hover:text-white transition-colors"
                      >
                        View
                      </button>
                      <button
                        onClick={(e) => handleDelete(e, p.id)}
                        disabled={deleting === p.id}
                        className="rounded-lg border border-rose-500/20 px-3 py-1.5 text-xs font-medium text-rose-400 hover:bg-rose-500/10 transition-colors disabled:opacity-50"
                      >
                        {deleting === p.id ? "…" : "Delete"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default ProjectsPage
