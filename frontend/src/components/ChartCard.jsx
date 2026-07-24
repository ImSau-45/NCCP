const ChartCard = ({ title, value }) => {
  return (
    <div className="rounded-3xl bg-slate-950 p-6 shadow-xl border border-slate-800">
      <p className="text-slate-400">{title}</p>
      <p className="mt-4 text-4xl font-semibold text-white">{value}</p>
    </div>
  )
}

export default ChartCard
