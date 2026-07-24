import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import api from "../api"

const STEP_ICONS = {
  lint: "🔍", test: "🧪", build: "🔨", docker_build: "🐳", deploy: "🚀",
}

const Toggle = ({ checked, onChange }) => (
  <button
    type="button"
    onClick={() => onChange(!checked)}
    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none ${
      checked ? "bg-indigo-600" : "bg-slate-700"
    }`}
  >
    <span
      className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200 ${
        checked ? "translate-x-5" : "translate-x-0"
      }`}
    />
  </button>
)

const ReviewPage = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [steps, setSteps] = useState([])
  const [project, setProject] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.get(`/projects/${id}`)
      .then((res) => {
        setProject(res.data.project)
        setSteps(res.data.steps.map((s) => ({ ...s })))
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [id])

  const toggleStep = (stepId) => {
    setSteps((prev) =>
      prev.map((s) => s.id === stepId ? { ...s, approved: !s.approved } : s)
    )
  }

  const handleSaveAndGenerate = async () => {
    const approvedCount = steps.filter((s) => s.approved).length
    if (approvedCount === 0) {
      setError("Approve at least one step before generating.")
      return
    }
    setError(null)
    setSaving(true)
    try {
      // 1. Persist approvals
      await api.patch(`/projects/${id}/steps`, steps.map((s) => ({ id: s.id, approved: s.approved })))
      setSaving(false)
      setGenerating(true)
      // 2. Generate YAML
      const res = await api.post(`/projects/${id}/generate`)
      navigate(`/projects/${id}/workflow`, { state: { workflow: res.data.workflow } })
    } catch (err) {
      setError(err.message)
      setSaving(false)
      setGenerating(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      </div>
    )
  }

  const approvedCount = steps.filter((s) => s.approved).length
  const isBusy = saving || generating

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-500 mb-1">
          <button onClick={() => navigate(`/projects/${id}`)} className="hover:text-slate-300 transition-colors">
            {project?.repo_owner}/{project?.repo_name}
          </button>
          <span>/</span>
          <span className="text-slate-300">Review Steps</span>
        </div>
        <h1 className="text-xl font-semibold text-white">Review & Approve Steps</h1>
        <p className="mt-1 text-sm text-slate-400">
          Toggle the steps you want included in your CI/CD workflow, then generate the YAML.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-400">
          {error}
        </div>
      )}

      {/* Step list */}
      <div className="space-y-3">
        {steps.map((step) => (
          <div
            key={step.id}
            className={`rounded-xl border p-5 transition-colors ${
              step.approved
                ? "border-indigo-500/40 bg-indigo-500/8"
                : "border-subtle bg-[#111827] opacity-60"
            }`}
          >
            <div className="flex items-start gap-4">
              <span className="text-xl mt-0.5">{STEP_ICONS[step.step_key] || "⚙️"}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium text-white">{step.title}</p>
                    {step.recommended && (
                      <span className="rounded-full bg-indigo-500/20 px-2 py-0.5 text-xs font-medium text-indigo-400">
                        Recommended
                      </span>
                    )}
                  </div>
                  <Toggle checked={step.approved} onChange={() => toggleStep(step.id)} />
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
        ))}
      </div>

      {/* Footer actions */}
      <div className="flex items-center justify-between rounded-xl border border-subtle bg-[#111827] px-5 py-4">
        <p className="text-sm text-slate-400">
          <span className="font-semibold text-white">{approvedCount}</span> of{" "}
          <span className="font-semibold text-white">{steps.length}</span> steps selected
        </p>
        <div className="flex gap-3">
          <button
            onClick={() => navigate(`/projects/${id}`)}
            className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSaveAndGenerate}
            disabled={isBusy || approvedCount === 0}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {generating ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Generating…
              </>
            ) : saving ? "Saving…" : "Generate Workflow →"}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ReviewPage
