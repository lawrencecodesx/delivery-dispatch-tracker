import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowLeft, ArrowRight, BadgeCheck, LockKeyhole, Mail, PackageCheck, Phone, Shield, Truck, User, UserRoundPlus } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/useAuth.js'
import api, { apiErrorMessage } from '../../services/api.js'

const panelVariants = {
  initial: (direction) => ({ opacity: 0, x: direction * 34, filter: 'blur(4px)' }),
  animate: { opacity: 1, x: 0, filter: 'blur(0px)' },
  exit: (direction) => ({ opacity: 0, x: direction * -34, filter: 'blur(4px)' }),
}

const transition = { duration: 0.28, ease: [0.22, 1, 0.36, 1] }

export function AuthPage() {
  const location = useLocation()
  const isRegister = location.pathname === '/register'
  const mode = isRegister ? 'register' : 'login'

  return (
    <main className="auth-shell relative flex min-h-screen items-center justify-center overflow-x-hidden px-4 py-10 text-white sm:px-6">
      <div aria-hidden="true" className="auth-ambient auth-ambient-one" />
      <div aria-hidden="true" className="auth-ambient auth-ambient-two" />
      <Link aria-label="ParcelFlow home" className="auth-back-link absolute left-5 top-5 z-20 inline-flex items-center gap-2 text-sm font-medium text-slate-300 transition hover:text-white sm:left-8 sm:top-8" to="/">
        <ArrowLeft size={16} /> <span className="hidden sm:inline">Back to home</span>
      </Link>

      <div className="auth-glass-panel relative z-10 grid w-full max-w-5xl rounded-3xl border border-white/10 bg-white/[0.06] shadow-2xl backdrop-blur-md lg:min-h-[650px] lg:grid-cols-[0.95fr_1.05fr]">
        <aside className="auth-welcome-panel relative hidden min-h-full overflow-hidden border-r border-white/10 p-10 lg:flex lg:flex-col lg:justify-between xl:p-14">
          <div aria-hidden="true" className="auth-welcome-glow" />
          <div className="relative z-10 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-indigo-200">
            <span className="size-2 animate-pulse rounded-full bg-cyan-300" />
            One connected journey
          </div>

          <AnimatePresence mode="wait" initial={false} custom={isRegister ? 1 : -1}>
            <motion.div
              key={`welcome-${mode}`}
              animate="animate"
              custom={isRegister ? 1 : -1}
              exit="exit"
              initial="initial"
              variants={panelVariants}
              transition={transition}
              className="relative z-10"
            >
              <div className="mb-7 grid size-14 place-items-center rounded-2xl border border-white/10 bg-white/[0.08] text-cyan-200 shadow-lg shadow-blue-950/30">
                {isRegister ? <UserRoundPlus size={25} /> : <PackageCheck size={26} />}
              </div>
              <p className="text-sm font-semibold text-cyan-200">
                {isRegister ? 'A smoother way to move' : 'Welcome back'}
              </p>
              <h2 className="mt-3 max-w-md text-4xl font-black leading-[1.08] tracking-[-0.04em] text-white xl:text-5xl">
                {isRegister
                  ? <>Your next delivery<br />starts right here.</>
                  : <>Good to see<br />you again.</>}
              </h2>
              <p className="mt-5 max-w-sm text-base leading-7 text-indigo-100/70">
                {isRegister
                  ? 'Create your account and keep every pickup, route, and handoff moving in the right direction.'
                  : 'Pick up where you left off. Your deliveries and operations are ready when you are.'}
              </p>
              <div className="mt-8 flex items-center gap-2">
                {[0, 1, 2].map((item) => (
                  <span className={`h-1 rounded-full transition-all ${item === (isRegister ? 1 : 0) ? 'w-8 bg-cyan-300' : 'w-2 bg-white/25'}`} key={item} />
                ))}
              </div>
            </motion.div>
          </AnimatePresence>

          <div className="relative z-10 rounded-2xl border border-white/10 bg-white/[0.06] p-5 backdrop-blur-sm">
            <p className="text-sm leading-6 text-indigo-100/80">
              {isRegister
                ? 'One clear view for customers, dispatch teams, and riders.'
                : 'Every parcel has a journey. Keep yours moving with confidence.'}
            </p>
            <div className="mt-5 flex items-center justify-between border-t border-white/10 pt-4">
              <span className="text-xs text-indigo-200/60">{isRegister ? 'Already on ParcelFlow?' : 'New to ParcelFlow?'}</span>
              <Link className="inline-flex items-center gap-2 rounded-full border border-indigo-200/20 bg-indigo-400/10 px-4 py-2 text-xs font-bold text-white transition hover:border-indigo-200/40 hover:bg-indigo-400/20" to={isRegister ? '/login' : '/register'}>
                {isRegister ? 'Sign in' : 'Create account'} <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </aside>

        <section className="auth-form-panel relative flex min-w-0 items-center px-6 py-12 sm:px-10 lg:px-12 xl:px-14">
          <div className="mx-auto w-full max-w-md">
            <div className="mb-9 flex items-center gap-3">
              <span className="grid size-11 place-items-center rounded-2xl border border-indigo-300/20 bg-indigo-400/10 text-indigo-200">
                <PackageCheck size={22} />
              </span>
              <div>
                <p className="font-bold tracking-tight text-white">ParcelFlow</p>
                <p className="mt-0.5 text-xs text-slate-400">Delivery, in good hands.</p>
              </div>
            </div>

            <AnimatePresence mode="wait" initial={false} custom={isRegister ? 1 : -1}>
              <motion.div
                key={mode}
                animate="animate"
                custom={isRegister ? 1 : -1}
                exit="exit"
                initial="initial"
                variants={panelVariants}
                transition={transition}
              >
                {isRegister ? (
                  <RegisterForm key="register-form" />
                ) : (
                  <LoginForm key="login-form" />
                )}
              </motion.div>
            </AnimatePresence>

            <div className="mt-8 flex items-center justify-center gap-2 text-xs text-slate-500">
              <Shield size={14} className="text-indigo-300" />
              Your account is protected with secure authentication
            </div>
          </div>
        </section>

        <div className="auth-mobile-toggle relative z-10 mx-6 mb-6 rounded-2xl border border-white/10 bg-white/[0.05] p-4 text-center text-sm text-slate-300 lg:hidden">
          {isRegister ? 'Already have an account?' : 'New to ParcelFlow?'}{' '}
          <Link className="ml-1 font-bold text-indigo-200 hover:text-white" to={isRegister ? '/login' : '/register'}>
            {isRegister ? 'Sign in' : 'Create account'}
          </Link>
        </div>
      </div>
    </main>
  )
}

function LoginForm() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [values, setValues] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function update(event) {
    setValues((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function submit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(values)
      navigate(location.state?.from?.pathname || '/', { replace: true })
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Unable to sign in. Check your credentials.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-300">Sign in</p>
      <h1 className="mt-2 text-3xl font-black tracking-tight text-white sm:text-4xl">Welcome back</h1>
      <p className="mt-2 text-sm leading-6 text-slate-400">Sign in to continue to your workspace.</p>
      {location.state?.registered && <p className="mt-4 rounded-xl border border-emerald-300/20 bg-emerald-400/10 px-3 py-2.5 text-sm text-emerald-200">Account created. You can sign in now.</p>}
      <form className="mt-7 space-y-4" onSubmit={submit}>
        <IconInput autoComplete="email" icon={Mail} label="Email address" name="email" onChange={update} placeholder="you@example.com" required type="email" value={values.email} />
        <IconInput autoComplete="current-password" icon={LockKeyhole} label="Password" name="password" onChange={update} placeholder="Enter your password" required type="password" value={values.password} />
        {error && <p aria-live="polite" className="rounded-xl border border-rose-300/20 bg-rose-400/10 px-3 py-2.5 text-sm text-rose-200">{error}</p>}
        <button className="auth-submit-button group mt-2 flex w-full items-center justify-center gap-2 rounded-xl px-5 py-3.5 text-sm font-bold text-white shadow-lg shadow-indigo-950/30 transition hover:-translate-y-0.5 disabled:cursor-wait disabled:opacity-60" disabled={submitting} type="submit">
          {submitting ? 'Signing in…' : 'Sign in to your account'}
          {!submitting && <ArrowRight className="transition-transform group-hover:translate-x-1" size={17} />}
        </button>
      </form>
    </>
  )
}

function RegisterForm() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [values, setValues] = useState({
    role: 'CUSTOMER',
    full_name: '',
    email: '',
    phone_number: '',
    password: '',
    vehicle_type: '',
    vehicle_registration: '',
  })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [pendingApproval, setPendingApproval] = useState(false)
  const privilegedRole = values.role !== 'CUSTOMER'

  function update(event) {
    setValues((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function submit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const payload = { ...values }
      if (payload.role !== 'RIDER') {
        delete payload.vehicle_type
        delete payload.vehicle_registration
      }
      await api.post('/auth/register', payload)
      if (privilegedRole) {
        setPendingApproval(true)
        return
      }
      const user = await login({ email: values.email, password: values.password })
      const rolePath = {
        CUSTOMER: '/customer',
        DISPATCHER: '/dispatcher',
        RIDER: '/rider',
      }[String(user.role || '').toUpperCase()]
      navigate(rolePath || '/', { replace: true })
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Unable to create your account.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-300">Create an account</p>
      <h1 className="mt-2 text-3xl font-black tracking-tight text-white sm:text-4xl">Join ParcelFlow</h1>
      <p className="mt-2 text-sm leading-6 text-slate-400">Select your account type to get started.</p>
      <form className="mt-6 space-y-3.5" onSubmit={submit}>
        <label className="block text-xs font-semibold text-slate-300">
          Account Type / Role
          <select className="auth-select mt-1.5" name="role" onChange={update} value={values.role}>
            <option value="CUSTOMER">Customer</option>
            <option value="DISPATCHER">Dispatcher</option>
            <option value="RIDER">Rider</option>
          </select>
        </label>
        {privilegedRole && <p className="rounded-lg border border-blue-300/20 bg-blue-400/10 px-3 py-2 text-xs leading-5 text-blue-100">Dispatcher and Rider accounts require administrator approval before sign-in.</p>}
        <IconInput autoComplete="name" icon={User} label="Full name" maxLength={100} name="full_name" onChange={update} placeholder="Your name" required type="text" value={values.full_name} />
        <IconInput autoComplete="email" icon={Mail} label="Email address" name="email" onChange={update} placeholder="you@example.com" required type="email" value={values.email} />
        <IconInput autoComplete="tel" icon={Phone} label="Phone number" maxLength={30} name="phone_number" onChange={update} placeholder="Your phone number" type="tel" value={values.phone_number} />
        {values.role === 'RIDER' && (
          <>
            <IconInput autoComplete="off" icon={Truck} label="Vehicle type" maxLength={50} name="vehicle_type" onChange={update} placeholder="Bike, car, or van" required type="text" value={values.vehicle_type} />
            <IconInput autoComplete="off" icon={BadgeCheck} label="Vehicle registration" maxLength={30} name="vehicle_registration" onChange={update} placeholder="Registration number" required type="text" value={values.vehicle_registration} />
          </>
        )}
        <IconInput autoComplete="new-password" icon={LockKeyhole} label="Password" minLength={8} name="password" onChange={update} placeholder="At least 8 characters" required type="password" value={values.password} />
        {error && <p aria-live="polite" className="rounded-xl border border-rose-300/20 bg-rose-400/10 px-3 py-2.5 text-sm text-rose-200">{error}</p>}
        <button className="auth-submit-button group mt-1 flex w-full items-center justify-center gap-2 rounded-xl px-5 py-3.5 text-sm font-bold text-white shadow-lg shadow-indigo-950/30 transition hover:-translate-y-0.5 disabled:cursor-wait disabled:opacity-60" disabled={submitting} type="submit">
          {submitting ? 'Creating account…' : 'Create account'}
          {!submitting && <ArrowRight className="transition-transform group-hover:translate-x-1" size={17} />}
        </button>
      </form>
      {pendingApproval && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/75 p-4 backdrop-blur-md" role="presentation">
          <section aria-labelledby="registration-pending-title" aria-modal="true" className="auth-glass-panel relative w-full max-w-md rounded-3xl border border-white/10 bg-slate-900/90 p-7 text-center shadow-2xl sm:p-9" role="dialog">
            <span className="mx-auto grid size-14 place-items-center rounded-2xl border border-blue-300/20 bg-blue-400/10 text-blue-200">
              <Shield size={26} />
            </span>
            <h2 className="mt-5 text-2xl font-black tracking-tight text-white" id="registration-pending-title">Registration submitted!</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              An administrator must approve your account before you can sign in.
            </p>
            <p className="mt-2 text-xs leading-5 text-slate-400">
              You can return to this page and sign in after receiving approval.
            </p>
            <div className="mt-6 flex flex-col-reverse justify-center gap-2 sm:flex-row">
              <button className="rounded-xl border border-white/10 px-4 py-3 text-sm font-semibold text-slate-300 transition hover:bg-white/5" onClick={() => setPendingApproval(false)} type="button">Close</button>
              <Link className="auth-submit-button rounded-xl px-4 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-950/30" to="/login">Go to sign in</Link>
            </div>
          </section>
        </div>
      )}
    </>
  )
}

function IconInput({ icon: Icon, label, ...inputProps }) {
  return (
    <label className="block text-xs font-semibold text-slate-300">
      {label}
      <span className="auth-input-wrap mt-1.5 flex items-center gap-3 rounded-xl border border-white/10 bg-slate-950/35 px-3.5 transition focus-within:border-indigo-300/60 focus-within:ring-2 focus-within:ring-indigo-400/20">
        <Icon aria-hidden="true" className="shrink-0 text-indigo-300/80" size={17} />
        <input className="min-w-0 flex-1 bg-transparent py-3 text-sm font-medium text-white outline-none placeholder:font-normal placeholder:text-slate-500" {...inputProps} />
      </span>
    </label>
  )
}
