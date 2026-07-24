const RepoCard = ({ repo }) => {
  return (
    <div className="rounded-3xl bg-slate-950 p-5 border border-slate-800">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold">{repo.name}</h3>
          {repo.description && <p className="mt-2 text-slate-400">{repo.description}</p>}
        </div>
        <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">{repo.visibility || "private"}</span>
      </div>
      {repo.stage && <p className="mt-4 text-slate-300">Stage: {repo.stage}</p>}
    </div>
  )
}

export default RepoCard
