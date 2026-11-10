import { ChevronDown, LogOut, PackageCheck, UserRound } from 'lucide-react'
import { useAuth } from '../context/useAuth.js'
import { Link } from 'react-router-dom'

export function Navbar() {
  const { user, logout } = useAuth()
  const role = String(user?.role || '').toLowerCase()
  const initials = (user?.full_name || user?.email || 'Account')
    .split(/[ @._-]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('')

  return (
    <header className="dashboard-navbar sticky top-0 z-30 flex h-16 items-center justify-between px-5 md:px-8">
      <Link to={`/${role}`} className="flex items-center gap-2 font-semibold text-slate-100">
        <span className="dashboard-brand-mark grid size-9 place-items-center rounded-xl">
          <PackageCheck size={19} />
        </span>
        <span>Dispatch<span className="text-blue-400"> Tracker</span></span>
      </Link>
      <details className="dashboard-profile">
        <summary className="dashboard-profile-trigger">
          <span className="dashboard-avatar">{initials || <UserRound size={16} />}</span>
          <span className="hidden text-left sm:block">
            <span className="block max-w-40 truncate text-sm font-semibold text-slate-100">{user?.full_name || user?.email || 'Account'}</span>
            <span className="block text-[11px] capitalize text-slate-400">{role || 'workspace'}</span>
          </span>
          <ChevronDown size={15} className="text-slate-400" />
        </summary>
        <div className="dashboard-profile-menu">
          <p className="truncate px-3 py-2 text-xs text-slate-400">{user?.email}</p>
          <button type="button" onClick={logout}>
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </details>
    </header>
  )
}
