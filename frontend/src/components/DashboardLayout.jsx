import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { Navbar } from './Navbar.jsx'
import { Sidebar } from './Sidebar.jsx'

export function DashboardLayout() {
  useEffect(() => {
    const root = document.documentElement
    root.dataset.dashboard = 'true'
    return () => {
      delete root.dataset.dashboard
    }
  }, [])

  return (
    <div className="dashboard-shell min-h-screen">
      <Navbar />
      <div className="dashboard-body md:flex">
        <Sidebar />
        <main className="dashboard-main min-w-0 flex-1 p-5 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
