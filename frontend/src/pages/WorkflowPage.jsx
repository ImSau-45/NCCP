import { useEffect, useState } from "react"
import { useLocation, useNavigate, useParams } from "react-router-dom"
import api from "../api"

const WorkflowPage = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [workflow, setWorkflow] = useState(location.state?.workflow || null)
  const [project, setProject] = useState(null)
  const [loading, setLoading] = useState(!workflow)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (workflow && project) return
    api.get(`/projects/${id}`)
      .then((res) => {
        setProject(res.data.project)
        if (!workflow && res.data.workflow) setWorkflow(res.data.workflow)
        else if (!workflow) setError("No workflow found. Generate one from the Review page.")
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [id])

  const handleCopy = () => {
    navigator.clipboard.writeText(workflow.yaml_content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      </div>
    )
  }

  if (error || !workflow) {
    return (
      <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-400">
        {error || "Workflow not found."}
        <button
          onClick={() => navigate(`/projects/${id}/review`)}
          className="ml-4 underline hover:no-underline"
        >
          Go to Review page
        </button>
      </div>
    )
  }

  const lineCount = workflow.yaml_content.split("\n").length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-500 mb-1">
          <button onClick={() => navigate(`/projects/${id}`)} className="hover:text-slate-300 transition-colors">
            {project?.repo_owner}/{project?.repo_name}
          </button>
          <span>/</span>
          <span className="text-slate-300">Generated Workflow</span>
        </div>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-semibold text-white">Generated Workflow</h1>
            <p className="mt-1 text-sm text-slate-400">
              <span className="font-mono text-slate-300">{workflow.filename}</span>
              {" · "}{lineCount} lines
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-300 hover:text-white hover:border-white/20 transition-colors"
            >
              {copied ? "✓ Copied" : "Copy YAML"}
            </button>
            <button
              onClick={() => navigate(`/projects/${id}/review`)}
              className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
            >
              ← Edit Steps
            </button>
          </div>
        </div>
      </div>

      {/* YAML viewer */}
      <div className="rounded-xl border border-subtle bg-[#0d1117] overflow-hidden">
        <div className="flex items-center justify-between border-b border-subtle px-4 py-2.5">
          <span className="text-xs font-medium text-slate-400">YAML</span>
          <span className="text-xs text-slate-600">{workflow.filename}</span>
        </div>
        <div className="overflow-x-auto">
          <pre className="p-5 text-xs leading-relaxed text-slate-300 whitespace-pre">
            {workflow.yaml_content}
          </pre>
        </div>
      </div>

      {/* Next step — Phase 6 */}
      <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="font-semibold text-white">Ready to push to GitHub?</p>
            <p className="mt-1 text-sm text-slate-400">
              Create a pull request that adds this workflow file to your repository.
            </p>
          </div>
          <button
            onClick={() => navigate(`/projects/${id}/pr`)}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
          >
            Create PR →
          </button>
        </div>
      </div>
    </div>
  )
}

export default WorkflowPage
