import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center px-4 text-center">
      <div>
        <p className="text-sm font-semibold text-blue-700">404</p>
        <h1 className="mt-2 text-3xl font-bold text-slate-900">Page not found</h1>
        <Link className="mt-5 inline-block font-semibold text-blue-700 hover:underline" to="/">
          Return to your workspace
        </Link>
      </div>
    </main>
  )
}
