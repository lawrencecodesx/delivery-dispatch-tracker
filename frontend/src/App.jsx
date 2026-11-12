import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext.jsx'
import { useAuth } from './context/useAuth.js'
import { DashboardLayout } from './components/DashboardLayout.jsx'
import { ProtectedRoute } from './components/ProtectedRoute.jsx'

const Landing = lazy(() =>
  import('./pages/Landing.jsx').then((module) => ({ default: module.Landing })),
)
const AuthPage = lazy(() =>
  import('./pages/auth/AuthPage.jsx').then((module) => ({ default: module.AuthPage })),
)
const CustomerDashboard = lazy(() =>
  import('./pages/customer/index.jsx').then((module) => ({
    default: module.CustomerDashboard,
  })),
)
const CreateOrder = lazy(() =>
  import('./pages/customer/CreateOrder.jsx').then((module) => ({
    default: module.CreateOrder,
  })),
)
const TrackOrder = lazy(() =>
  import('./pages/customer/TrackOrder.jsx').then((module) => ({
    default: module.TrackOrder,
  })),
)
const DispatcherDashboard = lazy(() =>
  import('./pages/dispatcher/DispatchDashboard.jsx').then((module) => ({
    default: module.DispatchDashboard,
  })),
)
const RiderDashboard = lazy(() =>
  import('./pages/rider/RiderDashboard.jsx').then((module) => ({ default: module.RiderDashboard })),
)
const AdminDashboard = lazy(() =>
  import('./pages/admin/AdminDashboard.jsx').then((module) => ({ default: module.AdminDashboard })),
)
const NotFoundPage = lazy(() =>
  import('./pages/NotFoundPage.jsx').then((module) => ({ default: module.NotFoundPage })),
)

function HomeRedirect() {
  const { user, loading } = useAuth()

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Loading your workspace…</div>
  }
  if (!user) {
    return <Landing />
  }

  const role = String(user.role || '').toUpperCase()
  const rolePath = {
    CUSTOMER: '/customer',
    DISPATCHER: '/dispatcher',
    RIDER: '/rider',
    ADMIN: '/admin',
  }[role]
  return <Navigate to={rolePath || '/login'} replace />
}

function AppRoutes() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-500">Loading page…</div>}>
      <Routes>
        <Route path="/" element={<HomeRedirect />} />
        <Route path="/login" element={<AuthPage />} />
        <Route path="/register" element={<AuthPage />} />

        <Route element={<ProtectedRoute allowedRoles={['CUSTOMER']} />}>
          <Route path="/customer" element={<DashboardLayout />}>
            <Route index element={<CustomerDashboard />} />
            <Route path="create" element={<CreateOrder />} />
            <Route path="track" element={<TrackOrder />} />
            <Route path="track/:orderId" element={<TrackOrder />} />
          </Route>
        </Route>
        <Route element={<ProtectedRoute allowedRoles={['DISPATCHER']} />}>
          <Route path="/dispatcher" element={<DashboardLayout />}>
            <Route index element={<DispatcherDashboard />} />
          </Route>
        </Route>
        <Route element={<ProtectedRoute allowedRoles={['RIDER']} />}>
          <Route path="/rider" element={<DashboardLayout />}>
            <Route index element={<RiderDashboard />} />
          </Route>
        </Route>
        <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
          <Route path="/admin" element={<DashboardLayout />}>
            <Route index element={<AdminDashboard />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
