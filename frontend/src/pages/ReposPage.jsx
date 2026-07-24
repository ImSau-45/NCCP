import { useState } from "react"
import RepoCard from "../components/RepoCard"

const ReposPage = () => {
  const [query, setQuery] = useState("")
  const repos = [
    { name: "pipeline-sh", description: "AI CI/CD automation platform", visibility: "private" },
    { name: "flask-dashboard", description: "Monitoring dashboard for deployments", visibility: "public" },
  ]
  const filtered = repos.filter((repo) => repo.name.includes(query) || repo.description.includes(query))

  return (
    <div className="space-y-6">
      <div className="glow-card p-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Repository Management</h1>
          <p className="text-slate-400">Connect GitHub repos, install webhooks, and generate workflows.</p>
        </div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search repositories"
          className="rounded-3xl border border-slate-700 bg-slate-900 px-4 py-3 text-white"
        />
      </div>
      <div className="grid gap-4">
        {filtered.map((repo) => (
          <RepoCard key={repo.name} repo={repo} />
        ))}
      </div>
    </div>
  )
}

export default ReposPage
