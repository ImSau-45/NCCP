const ErrorInsights = () => {
  return (
    <div className="space-y-6">
      <div className="glow-card p-6">
        <h1 className="text-2xl font-semibold">Error Insights</h1>
        <p className="mt-2 text-slate-400">AI-powered error summaries with debugging guidance for your CI/CD workflows.</p>
      </div>
      <div className="grid gap-4">
        <div className="rounded-3xl bg-slate-950 p-6">
          <h2 className="text-lg font-semibold">Flask import error</h2>
          <p className="mt-3 text-slate-300">Missing module `flask` in the CI environment. Suggested fix: add `flask` to requirements and rerun the workflow.</p>
        </div>
        <div className="rounded-3xl bg-slate-950 p-6">
          <h2 className="text-lg font-semibold">Docker build failed</h2>
          <p className="mt-3 text-slate-300">The Dockerfile cannot find `requirements.txt`. Confirm that the build context includes the backend directory.</p>
        </div>
      </div>
    </div>
  )
}

export default ErrorInsights
