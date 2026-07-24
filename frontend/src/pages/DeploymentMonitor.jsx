const DeploymentMonitor = () => {
  const deployments = [
    { name: "pipeline-sh", env: "production", status: "Running", updated: "2m ago" },
    { name: "flask-api", env: "staging", status: "Failed", updated: "12m ago" },
  ]

  return (
    <div className="space-y-6">
      <div className="glow-card p-6">
        <h1 className="text-2xl font-semibold">Deployment Monitor</h1>
        <p className="mt-2 text-slate-400">Track live AWS EC2 deployments, logs, and health status.</p>
      </div>
      <div className="grid gap-4">
        {deployments.map((deployment) => (
          <div key={deployment.name} className="rounded-3xl border border-slate-700 bg-slate-950 p-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold">{deployment.name}</h2>
                <p className="text-slate-400">{deployment.env} · Updated {deployment.updated}</p>
              </div>
              <span className={`rounded-full px-3 py-1 text-sm ${deployment.status === "Running" ? "bg-emerald-500/20 text-emerald-300" : "bg-rose-500/20 text-rose-300"}`}>{deployment.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default DeploymentMonitor
