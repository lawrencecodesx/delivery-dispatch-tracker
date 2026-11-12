import { ArrowDown, ArrowRight, Clock3, MapPin, PackageCheck, Radio, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/useAuth.js'
import { SplineScene } from '../components/SplineScene.jsx'

const features = [
  {
    icon: Radio,
    title: 'Live dispatch visibility',
    description: 'Keep your team and customers in sync from pickup through delivery.',
  },
  {
    icon: MapPin,
    title: 'Location-aware journeys',
    description: 'See pickup, destination, and the latest rider location together.',
  },
  {
    icon: ShieldCheck,
    title: 'Verified handoffs',
    description: 'Confirm delivery with a recipient code and a proof-of-delivery record.',
  },
]

export function HomePage() {
  const { user, loading } = useAuth()
  const role = String(user?.role || '').toLowerCase()

  return (
    <main className="min-h-screen overflow-hidden bg-[#f7f8fb] text-slate-900">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
        <Link className="flex items-center gap-3 font-bold tracking-tight" to="/">
          <span className="grid size-10 place-items-center rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-600/20">
            <PackageCheck size={20} />
          </span>
          <span>Parcel<span className="text-blue-600">Flow</span></span>
        </Link>
        <nav className="flex items-center gap-3">
          {!loading && user ? (
            <Link className="rounded-full bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700" to={`/${role}`}>
              Open workspace <ArrowRight className="ml-1 inline" size={16} />
            </Link>
          ) : (
            <>
              <Link className="hidden px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-900 sm:inline-flex" to="/login">
                Sign in
              </Link>
              <Link className="rounded-full bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700" to="/register">
                Get started
              </Link>
            </>
          )}
        </nav>
      </header>

      <section className="mx-auto grid max-w-7xl items-center gap-12 px-5 pb-20 pt-10 sm:px-8 lg:grid-cols-[0.92fr_1.08fr] lg:pb-28 lg:pt-16">
        <div className="relative z-10">
          <span className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-white px-3.5 py-2 text-xs font-bold uppercase tracking-[0.13em] text-blue-700 shadow-sm">
            <span className="size-2 animate-pulse rounded-full bg-emerald-500" />
            Dispatch, in real time
          </span>
          <h1 className="mt-7 max-w-2xl text-5xl font-black leading-[1.04] tracking-[-0.055em] text-slate-950 sm:text-6xl xl:text-7xl">
            Every delivery.
            <span className="block text-blue-600">Right on track.</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">
            One calm, connected workspace for booking deliveries, coordinating riders,
            and keeping every customer in the loop.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link className="inline-flex items-center gap-2 rounded-full bg-blue-600 px-6 py-3.5 font-semibold text-white shadow-xl shadow-blue-600/20 transition hover:-translate-y-0.5 hover:bg-blue-700" to={user ? `/${role}` : '/register'}>
              Start a delivery <ArrowRight size={18} />
            </Link>
            <a className="inline-flex items-center gap-2 rounded-full px-5 py-3.5 text-sm font-semibold text-slate-600 hover:text-blue-700" href="#how-it-works">
              Explore the platform <ArrowDown size={16} />
            </a>
          </div>
          <div className="mt-10 flex flex-wrap gap-x-7 gap-y-3 text-sm text-slate-500">
            <span className="inline-flex items-center gap-2"><Clock3 size={16} className="text-blue-600" /> Live status updates</span>
            <span className="inline-flex items-center gap-2"><ShieldCheck size={16} className="text-blue-600" /> Verified delivery</span>
          </div>
        </div>
        <div className="relative">
          <div className="absolute -inset-8 rounded-[3rem] bg-blue-400/10 blur-3xl" />
          <div className="relative">
            <SplineScene />
            <div className="absolute -bottom-5 left-5 flex items-center gap-3 rounded-2xl border border-slate-100 bg-white p-3.5 shadow-xl sm:left-10">
              <span className="grid size-10 place-items-center rounded-xl bg-emerald-50 text-emerald-600"><PackageCheck size={20} /></span>
              <div><p className="text-xs text-slate-500">Journey status</p><p className="text-sm font-bold text-slate-900">Moving smoothly</p></div>
              <span className="ml-2 size-2 rounded-full bg-emerald-500" />
            </div>
          </div>
        </div>
      </section>

      <section id="how-it-works" className="border-y border-slate-200/80 bg-white py-20">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <div className="max-w-2xl">
            <p className="text-sm font-bold uppercase tracking-[0.16em] text-blue-600">Built for the whole journey</p>
            <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">From first mile to final handoff.</h2>
          </div>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {features.map(({ icon: Icon, title, description }, index) => (
              <article className="rounded-3xl border border-slate-200 bg-[#fbfcfe] p-6 transition hover:-translate-y-1 hover:border-blue-200 hover:shadow-lg hover:shadow-slate-900/5" key={title}>
                <span className="grid size-12 place-items-center rounded-2xl bg-blue-50 text-blue-700"><Icon size={22} /></span>
                <p className="mt-5 text-xs font-bold uppercase tracking-widest text-slate-400">0{index + 1}</p>
                <h3 className="mt-2 text-lg font-bold">{title}</h3>
                <p className="mt-2 leading-7 text-slate-600">{description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
      <footer className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-7 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <span>ParcelFlow · Delivery coordination, made clear.</span>
        <span>Track every handoff with confidence.</span>
      </footer>
    </main>
  )
}
