import { useState } from "react"
import { useAuth } from "../hooks/AuthContext"
import api from "../api"

const Settings = () => {
  const { user, refreshUser } = useAuth()
  const [notifEmail, setNotifEmail] = useState(user?.notification_email || user?.email || "")
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState(null)
  const [saveError, setSaveError] = useState(null)
  const [githubError, setGithubError] = useState(null)

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setSaveMsg(null)
    setSaveError(null)
    try {
      await api.patch("/auth/profile", { notification_email: notifEmail })
      await refreshUser()
      setSaveMsg("Settings saved.")
    } catch (err) {
      setSaveError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDisconnectGitHub = async () => {
    if (!confirm("Disconnect GitHub? This will remove your stored token.")) return
    try {
      await api.post("/auth/github/disconnect")
      await refreshUser()
    } catch (err) {
      alert(err.message)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <h1 className="text-xl font-semibold text-white">Settings</h1>

      {/* Account */}
      <section className="rounded-xl border border-subtle bg-[#111827] p-6">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Account</h2>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Name</span>
            <span className="text-white">{user?.name || "—"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Email</span>
            <span className="text-white">{user?.email}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Role</span>
            <span className="text-white capitalize">{user?.role || "developer"}</span>
          </div>
        </div>
      </section>

      {/* GitHub connection */}
      <section className="rounded-xl border border-subtle bg-[#111827] p-6">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">GitHub</h2>
        {user?.github_connected ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500/15">
                <svg className="h-4 w-4 text-emerald-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-white">Connected</p>
                {user.github_login && (
                  <p className="text-xs text-slate-500">@{user.github_login}</p>
                )}
              </div>
            </div>
            <button
              onClick={handleDisconnectGitHub}
              className="rounded-lg border border-rose-500/30 px-3 py-1.5 text-xs font-medium text-rose-400 hover:bg-rose-500/10"
            >
              Disconnect
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-700">
                <svg className="h-4 w-4 text-slate-400" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12" />
                </svg>
              </div>
              <p className="text-sm text-slate-400">GitHub not connected</p>
            </div>
            <div className="flex flex-col items-end gap-1.5">
              {githubError && (
                <p className="text-xs text-rose-400 max-w-xs text-right">{githubError}</p>
              )}
              <button
                onClick={async () => {
                  setGithubError(null)
                  try {
                    const res = await api.get("/auth/github/login/url")
                    window.location.href = res.data.url
                  } catch (err) {
                    setGithubError(err.message)
                  }
                }}
                className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500"
              >
                Connect GitHub
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Notifications */}
      <section className="rounded-xl border border-subtle bg-[#111827] p-6">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Notifications</h2>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              Notification email
            </label>
            <input
              type="email"
              value={notifEmail}
              onChange={(e) => setNotifEmail(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
            <p className="mt-1.5 text-xs text-slate-500">
              Pipeline status emails will be sent here.
            </p>
          </div>

          {saveMsg && <p className="text-sm text-emerald-400">{saveMsg}</p>}
          {saveError && <p className="text-sm text-rose-400">{saveError}</p>}

          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
        </form>
      </section>
    </div>
  )
}

export default Settings
