import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import api from "../api"

const PrConfirmPage = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)
  const [workflow, setWorkflow] = useState(null)
  const [loading, setLoading] = useState(true)
  const [publishing, setPublishing] = useState(false)
  const [successData, setSuccessData] = useState(null)
  const [error, setError] = useState(null)

  // Input states
  const [method, setMethod] = useState("pr") // 'pr' or 'commit'
  const [branchName, setBranchName] = useState("hifi-ci-setup")
  const [commitMessage, setCommitMessage] = useState("Add CI/CD workflow via Pipeline.sh")

  useEffect(() => {
    api.get(`/projects/${id}`)
      .then((res) => {
        setProject(res.data.project)
        setWorkflow(res.data.workflow)
        if (!res.data.workflow) {
          setError("No workflow generated yet. Go to Review page to generate one.")
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [id])

  const handlePublish = async (e) => {
    e.preventDefault()
    setPublishing(true)
    setError(null)
    try {
      const payload = {
        method,
        commit_message: commitMessage.trim(),
      }
      if (method === "pr") {
        payload.branch_name = branchName.trim()
      }
      const res = await api.post(`/projects/${id}/publish`, payload)
      setSuccessData(res.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setPublishing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      </div>
    )
  }

  if (successData) {
    const isPr = method === "pr"
    const targetUrl = successData.workflow?.pr_url || "#"
    return (
      <div className="mx-auto max-w-xl text-center py-12 space-y-6">
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mx-auto animate-bounce">
          <svg className="h-10 w-10" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Workflow Published!</h1>
          <p className="mt-2 text-sm text-slate-400">
            {isPr
              ? `A Pull Request has been opened in your repository under branch "${branchName}".`
              : `The workflow has been committed directly to branch "${project?.default_branch || "main"}".`}
          </p>
        </div>

        <div className="rounded-xl border border-subtle bg-[#111827] p-5 text-left space-y-4">
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Repository</span>
            <span className="font-medium text-white">{project?.repo_owner}/{project?.repo_name}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Target Path</span>
            <span className="font-mono text-xs text-white">{workflow?.filename || ".github/workflows/hifi-ci.yml"}</span>
          </div>
          {isPr && successData.workflow?.pr_number && (
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">PR Number</span>
              <span className="font-semibold text-indigo-400">#{successData.workflow.pr_number}</span>
            </div>
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <a
            href={targetUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
          >
            {isPr ? "View Pull Request ↗" : "View Commit ↗"}
          </a>
          <button
            onClick={() => navigate(`/projects/${id}`)}
            className="rounded-lg border border-white/10 px-6 py-2.5 text-sm text-slate-400 hover:text-white transition-colors"
          >
            Back to Project
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-500 mb-1">
          <button onClick={() => navigate(`/projects/${id}`)} className="hover:text-slate-300 transition-colors">
            {project?.repo_owner}/{project?.repo_name}
          </button>
          <span>/</span>
          <span className="text-slate-300">Publish Workflow</span>
        </div>
        <h1 className="text-xl font-semibold text-white">Publish Workflow to GitHub</h1>
        <p className="mt-1 text-sm text-slate-400">
          Push your generated CI/CD configuration to your GitHub repository.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-400">
          {error}
        </div>
      )}

      <form onSubmit={handlePublish} className="space-y-6">
        {/* Method selection */}
        <div className="grid gap-4 sm:grid-cols-2">
          {/* PR option */}
          <button
            type="button"
            onClick={() => setMethod("pr")}
            className={`flex flex-col items-start text-left p-5 rounded-xl border transition ${
              method === "pr"
                ? "border-indigo-600 bg-indigo-600/5 ring-1 ring-indigo-600"
                : "border-subtle bg-[#111827] hover:border-slate-700"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className={`flex h-4 w-4 items-center justify-center rounded-full border ${
                method === "pr" ? "border-indigo-500 text-indigo-500" : "border-slate-500"
              }`}>
                {method === "pr" && <span className="h-2 w-2 rounded-full bg-indigo-500" />}
              </span>
              <span className="font-semibold text-white">Create Pull Request</span>
            </div>
            <p className="mt-2 text-xs text-slate-400 leading-relaxed">
              Create a new branch and open a PR. (Recommended for code review and testing before merging).
            </p>
          </button>

          {/* Direct Commit option */}
          <button
            type="button"
            onClick={() => setMethod("commit")}
            className={`flex flex-col items-start text-left p-5 rounded-xl border transition ${
              method === "commit"
                ? "border-indigo-600 bg-indigo-600/5 ring-1 ring-indigo-600"
                : "border-subtle bg-[#111827] hover:border-slate-700"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className={`flex h-4 w-4 items-center justify-center rounded-full border ${
                method === "commit" ? "border-indigo-500 text-indigo-500" : "border-slate-500"
              }`}>
                {method === "commit" && <span className="h-2 w-2 rounded-full bg-indigo-500" />}
              </span>
              <span className="font-semibold text-white">Direct Commit</span>
            </div>
            <p className="mt-2 text-xs text-slate-400 leading-relaxed">
              Commit the workflow directly to your default branch ({project?.default_branch || "main"}). Useful for instant activation.
            </p>
          </button>
        </div>

        {/* Inputs */}
        <div className="rounded-xl border border-subtle bg-[#111827] p-6 space-y-4">
          {method === "pr" && (
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-300">
                New Branch Name
              </label>
              <input
                type="text"
                required
                value={branchName}
                onChange={(e) => setBranchName(e.target.value.replace(/\s+/g, "-"))}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          )}

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              Commit Message
            </label>
            <input
              type="text"
              required
              value={commitMessage}
              onChange={(e) => setCommitMessage(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={() => navigate(`/projects/${id}/workflow`)}
            className="rounded-lg border border-white/10 px-5 py-2.5 text-sm text-slate-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={publishing || !workflow}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {publishing ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Publishing…
              </>
            ) : method === "pr" ? "Create Pull Request →" : "Commit Directly →"}
          </button>
        </div>
      </form>
    </div>
  )
}

export default PrConfirmPage
