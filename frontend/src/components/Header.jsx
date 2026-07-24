import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../hooks/AuthContext"

const Avatar = ({ user }) => {
  const initials = user?.name
    ? user.name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() || "?"

  if (user?.avatar_url) {
    return (
      <img
        src={user.avatar_url}
        alt={user.name || "avatar"}
        className="h-8 w-8 rounded-full object-cover"
      />
    )
  }

  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-xs font-semibold text-white">
      {initials}
    </div>
  )
}

const Header = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate("/login")
  }

  return (
    <header className="flex h-14 flex-shrink-0 items-center justify-between border-b border-subtle bg-[#0a0f1e]/80 px-6 backdrop-blur-xl">
      {/* Left: page context (empty for now, pages can portal content here) */}
      <div className="flex items-center gap-2 text-sm text-slate-400">
        <span className="text-white font-medium">HiFi</span>
        <span className="text-slate-600">/</span>
        <span>CI/CD Pipeline Generator</span>
      </div>

      {/* Right: user menu */}
      {user && (
        <div className="relative">
          <button
            onClick={() => setMenuOpen((o) => !o)}
            className="flex items-center gap-2.5 rounded-lg px-2 py-1.5 hover:bg-white/5 transition-colors"
          >
            <Avatar user={user} />
            <span className="hidden text-sm font-medium text-slate-200 sm:block">
              {user.name || user.email}
            </span>
            <svg className="h-3.5 w-3.5 text-slate-500" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {menuOpen && (
            <>
              {/* Backdrop */}
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-full z-20 mt-1.5 w-52 rounded-xl border border-white/10 bg-[#111827] py-1 shadow-2xl">
                <div className="border-b border-subtle px-4 py-3">
                  <p className="text-sm font-medium text-white truncate">{user.name || "User"}</p>
                  <p className="text-xs text-slate-500 truncate">{user.email}</p>
                </div>
                <button
                  onClick={() => { setMenuOpen(false); navigate("/settings") }}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5 hover:text-white"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  Settings
                </button>
                <button
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-rose-400 hover:bg-white/5"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </header>
  )
}

export default Header
