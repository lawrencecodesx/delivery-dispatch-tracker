import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/useAuth.js'

export function ProtectedRoute({ allowedRoles }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Checking your session…</div>
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  if (allowedRoles && !allowedRoles.includes(String(user.role).toUpperCase())) {
    return <Navigate to="/" replace />
  }
  return <Outlet />
}
