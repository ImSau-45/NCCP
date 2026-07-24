import { Link } from "react-router-dom"

const LandingPage = () => {
  return (
    <div className="container mx-auto py-16 px-6">
      <div className="grid gap-10 lg:grid-cols-2 items-center">
        <div>
          <p className="text-sm uppercase tracking-[0.3em] text-accent">Pipeline.sh</p>
          <h1 className="mt-6 text-5xl font-semibold text-white">AI-powered CI/CD automation for modern teams</h1>
          <p className="mt-6 text-slate-300 max-w-xl">Connect GitHub repositories, generate workflows automatically, deploy to AWS, analyze logs with AI, and monitor pipelines in real time.</p>
          <div className="mt-8 flex gap-4">
            <Link to="/register" className="rounded-full bg-accent px-6 py-3 text-white">Start free</Link>
            <Link to="/login" className="rounded-full border border-slate-600 px-6 py-3 text-slate-200">Login</Link>
          </div>
        </div>
        <div className="rounded-3xl border border-white/10 bg-white/5 p-8 shadow-xl backdrop-blur-lg">
          <div className="space-y-6">
            <div className="rounded-3xl bg-slate-950 p-6 text-white">
              <p className="text-sm uppercase text-slate-400">Live Analytics</p>
              <h2 className="mt-4 text-3xl font-semibold">Pipeline health: 94%</h2>
              <p className="mt-3 text-slate-400">AI predictions recommend improved caching and rollback staging for faster delivery.</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-3xl bg-slate-950 p-5">Active repos<span className="block text-3xl mt-3">18</span></div>
              <div className="rounded-3xl bg-slate-950 p-5">Deployments<span className="block text-3xl mt-3">27</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LandingPage
