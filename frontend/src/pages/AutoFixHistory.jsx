import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import api from "../api"

const STATUS_META = {
  received:            { label: "Received",         color: "text-slate-300",  bg: "bg-slate-500/15" },
  diagnosing:          { label: "Diagnosing…",      color: "text-yellow-400", bg: "bg-yellow-500/15" },
  fix_generated:       { label: "Fix generated",    color: "text-blue-400",   bg: "bg-blue-500/15" },
  pr_opened:           { label: "PR opened",        color: "text-indigo-400", bg: "bg-indigo-500/15" },
  fix_failed:          { label: "Fix failed",       color: "text-rose-400",   bg: "bg-rose-500/15" },
  max_retries_reached: { label: "Max retries",      color: "text-orange-400", bg: "bg-orange-500/15" },
}

const StatusBadge = ({ status }) => {
  const m = STATUS_META[status] || { label: status, color: "text-slate-300", bg: "bg-slate-500/15" }
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${m.bg} ${m.color}`}>
      {m.label}
    </span>
  )
}

export default function AutoFixHistory() {
  const { id } = useParams()
  const [runs, setRuns] = useState([])
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = async () => {
    try {
      const { data } = await api.get(`/autofix/projects/${id}/runs`)
      setRuns(data.runs || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const iv = setInterval(load, 8000)
    return () => clearInterval(iv)
  }, [id])

  const openDetail = async (runId) => {
    try {
      const { data } = await api.get(`/autofix/runs/${runId}`)
      setDetail(data.run)
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to={`/projects/${id}`} className="text-sm text-slate-400 hover:text-slate-200">
            ← Back to project
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-100">Auto-Fix History</h1>
          <p className="text-sm text-slate-400">
            Every CI failure detected on this project and how the AI responded.
          </p>
        </div>
        <button
          onClick={load}
          className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-800"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-md border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-slate-400 text-sm">Loading…</div>
      ) : runs.length === 0 ? (
        <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-8 text-center text-slate-400">
          No auto-fix runs yet. When CI fails on this project, the AI will try to fix it and results appear here.
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-900/60 text-left text-slate-400">
              <tr>
                <th className="px-4 py-2 font-medium">When</th>
                <th className="px-4 py-2 font-medium">Branch</th>
                <th className="px-4 py-2 font-medium">Failure</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Attempts</th>
                <th className="px-4 py-2 font-medium">PR</th>
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {runs.map((r) => (
                <tr key={r.id} className="hover:bg-slate-800/40">
                  <td className="px-4 py-2 text-slate-300">
                    {new Date(r.created_date).toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-slate-300">{r.trigger_branch}</td>
                  <td className="px-4 py-2 text-slate-300 max-w-xs truncate">
                    {r.failure_summary || "—"}
                  </td>
                  <td className="px-4 py-2"><StatusBadge status={r.status} /></td>
                  <td className="px-4 py-2 text-slate-300">{r.attempt_count}</td>
                  <td className="px-4 py-2">
                    {r.pr_url ? (
                      <a href={r.pr_url} target="_blank" rel="noreferrer"
                         className="text-indigo-400 hover:underline">#{r.pr_number}</a>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button onClick={() => openDetail(r.id)}
                            className="text-sm text-blue-400 hover:underline">
                      Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
             onClick={() => setDetail(null)}>
          <div className="max-h-[85vh] w-full max-w-3xl overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-6"
               onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-100">Run #{detail.id}</h2>
                <p className="text-sm text-slate-400">{detail.failure_summary}</p>
              </div>
              <button onClick={() => setDetail(null)}
                      className="text-slate-400 hover:text-slate-200">✕</button>
            </div>
            <div className="mt-4 space-y-6">
              {(detail.attempts || []).map((a) => (
                <div key={a.id} className="rounded-md border border-slate-800 p-4">
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-medium text-slate-200">
                      Attempt {a.attempt_number}
                      {typeof a.confidence === "number" && (
                        <span className="ml-2 text-xs text-slate-400">
                          confidence {a.confidence.toFixed(2)}
                        </span>
                      )}
                    </div>
                    {a.pr_url && (
                      <a href={a.pr_url} target="_blank" rel="noreferrer"
                         className="text-xs text-indigo-400 hover:underline">Open PR</a>
                    )}
                  </div>
                  {a.diagnosis && (
                    <p className="mt-2 whitespace-pre-wrap text-sm text-slate-300">{a.diagnosis}</p>
                  )}
                  {a.files_changed?.length > 0 && (
                    <div className="mt-2 text-xs text-slate-400">
                      Files: {a.files_changed.map((f) => <code key={f} className="mr-1">{f}</code>)}
                    </div>
                  )}
                  {a.proposed_diff && (
                    <pre className="mt-3 max-h-72 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-200">
{a.proposed_diff}
                    </pre>
                  )}
                </div>
              ))}
              {detail.failure_log && (
                <details className="rounded-md border border-slate-800 p-4">
                  <summary className="cursor-pointer text-sm text-slate-300">CI failure log</summary>
                  <pre className="mt-3 max-h-72 overflow-auto text-xs text-slate-400">{detail.failure_log}</pre>
                </details>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
