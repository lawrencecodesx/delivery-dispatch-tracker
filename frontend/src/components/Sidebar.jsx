import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, MapPinned, Package, Plus } from 'lucide-react'
import { useAuth } from '../context/useAuth.js'

const ROLE_LINKS = {
  CUSTOMER: [
    { label: 'My deliveries', path: '/customer', icon: Package },
    { label: 'Create delivery', path: '/customer/create', icon: Plus },
    { label: 'Track an order', path: '/customer/track', icon: MapPinned },
  ],
  DISPATCHER: [{ label: 'Dispatch overview', path: '/dispatcher', icon: LayoutDashboard }],
  RIDER: [{ label: 'My assignments', path: '/rider', icon: Package }],
  ADMIN: [{ label: 'Administration', path: '/admin', icon: LayoutDashboard }],
}

export function Sidebar() {
  const { user } = useAuth()
  const location = useLocation()
  const links = ROLE_LINKS[String(user?.role || '').toUpperCase()] || []

  return (
    <aside className="dashboard-sidebar w-full shrink-0 p-3 md:min-h-[calc(100vh-4rem)] md:w-60 md:p-5">
      <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
        Workspace
      </p>
      <nav className="flex gap-2 overflow-x-auto md:flex-col">
        {links.map(({ label, path, icon: Icon }) => {
          const active = location.pathname === path
            || (path !== '/customer' && location.pathname.startsWith(`${path}/`))
          return (
            <Link
              key={label}
              to={path}
              className={`flex shrink-0 items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${
                active
                  ? 'dashboard-sidebar-link-active'
                  : 'dashboard-sidebar-link'
              }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
