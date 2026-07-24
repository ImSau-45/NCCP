const PipelineCard = ({ title, status, environment }) => {
  return (
    <div className="rounded-3xl bg-slate-950 p-5 border border-slate-800">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-slate-400 text-sm">{environment.toUpperCase()}</p>
          <h3 className="mt-2 text-lg font-semibold">{title}</h3>
        </div>
        <span className={`rounded-full px-3 py-1 text-sm ${status === "Success" ? "bg-emerald-500/20 text-emerald-300" : "bg-rose-500/20 text-rose-300"}`}>{status}</span>
      </div>
    </div>
  )
}

export default PipelineCard
