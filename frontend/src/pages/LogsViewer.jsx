import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import api from "../api"

const LogsViewer = () => {
  const { pipelineId } = useParams()
  const navigate = useNavigate()
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!pipelineId) {
      setError("No pipeline ID provided.")
      setLoading(false)
      return
    }

    api.get(`/pipelines/${pipelineId}/logs`)
      .then((res) => {
        setLogs(res.data.logs || [])
      })
      .catch((err) => {
        setError(err.message)
      })
      .finally(() => {
        setLoading(false)
      })
  }, [pipelineId])

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
        Failed to load logs: {error}
        <button onClick={() => navigate(-1)} className="ml-4 underline hover:no-underline">
          Go Back
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-500 mb-1">
          <button onClick={() => navigate(-1)} className="hover:text-slate-300 transition-colors">
            Go Back
          </button>
          <span>/</span>
          <span className="text-slate-300">Pipeline logs</span>
        </div>
        <h1 className="text-xl font-semibold text-white">Logs Viewer</h1>
        <p className="mt-0.5 text-sm text-slate-400">
          Showing logs for Pipeline Execution #{pipelineId}.
        </p>
      </div>

      <div className="rounded-xl border border-subtle bg-[#0d1117] overflow-hidden">
        <div className="flex items-center justify-between border-b border-subtle px-4 py-2.5">
          <span className="text-xs font-medium text-slate-400">Console Output</span>
          <span className="text-xs text-slate-500">Pipeline #{pipelineId}</span>
        </div>
        <div className="max-h-[500px] overflow-y-auto p-5 font-mono text-xs leading-relaxed bg-[#0d1117]">
          {logs.length === 0 ? (
            <p className="text-slate-500 italic">No logs available for this pipeline run.</p>
          ) : (
            <pre className="whitespace-pre-wrap text-slate-300">
              {logs.map((log, index) => {
                const ts = new Date(log.timestamp).toLocaleTimeString()
                let statusColor = "text-indigo-400"
                if (log.status === "failed" || log.status?.toLowerCase().includes("err")) {
                  statusColor = "text-rose-400 font-semibold"
                } else if (log.status === "warning") {
                  statusColor = "text-yellow-400"
                } else if (log.status === "success" || log.status === "completed") {
                  statusColor = "text-emerald-400"
                }

                return (
                  <div key={index} className="py-0.5 hover:bg-white/2 transition-colors">
                    <span className="text-slate-500 mr-2">[{ts}]</span>
                    <span className={`${statusColor} mr-2 uppercase`}>[{log.status}]</span>
                    <span className="text-slate-400 font-semibold mr-1">{log.step_name}:</span>
                    <span>{log.message}</span>
                  </div>
                )
              })}
            </pre>
          )}
        </div>
      </div>
    </div>
  )
}

export default LogsViewer
