import { useEffect } from 'react'
import {
  ArrowDown,
  ArrowRight,
  Boxes,
  Check,
  Clock3,
  LocateFixed,
  MapPin,
  Navigation,
  Package,
  Radio,
  Route,
  ShieldCheck,
  Truck,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/useAuth.js'

const portalSections = [
  {
    id: 'customer',
    eyebrow: 'For customers',
    title: 'Your delivery,',
    highlight: 'always in view.',
    description:
      'Book a pickup, follow every milestone, and know exactly when your package reaches its destination.',
    primaryLabel: 'Get Started',
    secondaryLabel: 'Explore Dispatcher',
    secondaryTarget: '#dispatcher',
    proof: ['Live order tracking', 'Verified handoffs'],
    glyphs: [
      { icon: Package, className: 'glyph-customer-package', depth: 'slow' },
      { icon: MapPin, className: 'glyph-customer-pin', depth: 'fast' },
      { icon: Route, className: 'glyph-customer-route', depth: 'medium' },
      { icon: Radio, className: 'glyph-customer-radio', depth: 'slow' },
      { icon: Navigation, className: 'glyph-customer-nav', depth: 'fast' },
      { icon: Boxes, className: 'glyph-customer-boxes', depth: 'medium' },
      { icon: LocateFixed, className: 'glyph-customer-locate', depth: 'slow' },
      { icon: Check, className: 'glyph-customer-check', depth: 'fast' },
    ],
  },
  {
    id: 'dispatcher',
    eyebrow: 'For dispatch teams',
    title: 'The whole fleet,',
    highlight: 'working in sync.',
    description:
      'Turn incoming orders into clear plans with a live view of rider availability, assignments, and delivery progress.',
    primaryLabel: 'Explore Portal',
    secondaryLabel: 'Meet the Rider Portal',
    secondaryTarget: '#rider',
    proof: ['One live operations view', 'Flexible rider assignments'],
    glyphs: [
      { icon: Radio, className: 'glyph-dispatch-radio', depth: 'slow' },
      { icon: Truck, className: 'glyph-dispatch-truck', depth: 'fast' },
      { icon: Route, className: 'glyph-dispatch-route', depth: 'medium' },
      { icon: MapPin, className: 'glyph-dispatch-pin', depth: 'fast' },
      { icon: Boxes, className: 'glyph-dispatch-boxes', depth: 'slow' },
      { icon: LocateFixed, className: 'glyph-dispatch-locate', depth: 'medium' },
      { icon: Navigation, className: 'glyph-dispatch-nav', depth: 'fast' },
      { icon: Package, className: 'glyph-dispatch-package', depth: 'slow' },
    ],
  },
  {
    id: 'rider',
    eyebrow: 'For riders',
    title: 'Every stop,',
    highlight: 'one clear route.',
    description:
      'Keep your assigned deliveries close at hand, update each stop in seconds, and confirm the final handoff securely.',
    primaryLabel: 'Join as a Rider',
    secondaryLabel: 'Back to Customer Portal',
    secondaryTarget: '#customer',
    proof: ['Mobile-ready assignments', 'Secure delivery verification'],
    glyphs: [
      { icon: Navigation, className: 'glyph-rider-nav', depth: 'fast' },
      { icon: Package, className: 'glyph-rider-package', depth: 'slow' },
      { icon: MapPin, className: 'glyph-rider-pin', depth: 'medium' },
      { icon: Route, className: 'glyph-rider-route', depth: 'fast' },
      { icon: Truck, className: 'glyph-rider-truck', depth: 'slow' },
      { icon: Radio, className: 'glyph-rider-radio', depth: 'medium' },
      { icon: LocateFixed, className: 'glyph-rider-locate', depth: 'fast' },
      { icon: ShieldCheck, className: 'glyph-rider-shield', depth: 'slow' },
    ],
  },
]

function PortalIllustration({ section }) {
  return (
    <div className={`portal-illustration portal-illustration-${section.id}`} aria-hidden="true">
      <div className="portal-orbit portal-orbit-one" />
      <div className="portal-orbit portal-orbit-two" />
      <div className="portal-map-grid" />
      <svg className="portal-route-line" viewBox="0 0 520 420" fill="none">
        <path d="M92 310C150 310 144 202 225 202S299 103 374 103s52 122 95 122" />
      </svg>
      <div className="portal-center-card">
        <div className="portal-center-icon"><Truck size={30} strokeWidth={1.7} /></div>
        <div className="portal-center-copy">
          <span>{section.id === 'customer' ? 'Delivery in progress' : section.id === 'dispatcher' ? 'Fleet overview' : 'Next delivery'}</span>
          <strong>{section.id === 'customer' ? 'On the way' : section.id === 'dispatcher' ? '12 active routes' : 'Pickup confirmed'}</strong>
        </div>
        <span className="portal-live-dot" />
      </div>
      <div className="portal-floating-glyphs">
        {section.glyphs.map(({ icon: Icon, className, depth }, index) => (
          <span
            className={`portal-glyph ${className} parallax-${depth}`}
            key={className}
          >
            <Icon size={index % 3 === 0 ? 25 : 20} strokeWidth={1.65} />
          </span>
        ))}
      </div>
      <div className="portal-map-label portal-label-origin"><span /> PICKUP</div>
      <div className="portal-map-label portal-label-destination"><span /> DESTINATION</div>
    </div>
  )
}

function PortalSection({ section, index, primaryHref }) {
  return (
    <section
      className={`portal-section portal-section-${section.id}`}
      data-portal={section.id}
      id={section.id}
      aria-labelledby={`${section.id}-title`}
    >
      <div className="portal-section-inner">
        <div className="portal-copy">
          <span className="portal-eyebrow"><span />{section.eyebrow}</span>
          <h1 id={`${section.id}-title`}>
            {section.title}
            <span>{section.highlight}</span>
          </h1>
          <p className="portal-description">{section.description}</p>
          <div className="portal-actions">
            <Link className="portal-button portal-button-primary" to={primaryHref}>
              {section.primaryLabel}<ArrowRight size={17} />
            </Link>
            <a className="portal-button portal-button-secondary" href={section.secondaryTarget}>
              {section.secondaryLabel}<ArrowDown size={16} />
            </a>
          </div>
          <div className="portal-proof-list">
            {section.proof.map((item) => (
              <span key={item}><Check size={15} />{item}</span>
            ))}
          </div>
        </div>
        <PortalIllustration section={section} />
        <div className="portal-section-index">
          <span>0{index + 1}</span><span className="portal-index-rule" />03
        </div>
      </div>
    </section>
  )
}

export function Landing() {
  const { user, loading } = useAuth()
  const role = String(user?.role || '').toLowerCase()
  const primaryHref = !loading && user ? `/${role}` : '/register'

  useEffect(() => {
    const root = document.documentElement
    const sections = portalSections
      .map(({ id }) => document.getElementById(id))
      .filter(Boolean)

    root.dataset.portal = 'customer'
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            root.dataset.portal = entry.target.id
          }
        }
      },
      { rootMargin: '-50% 0px -50% 0px', threshold: 0 },
    )

    sections.forEach((section) => observer.observe(section))
    return () => observer.disconnect()
  }, [])

  return (
    <main className="landing-page" data-portal="customer">
      <header className="landing-header">
        <Link className="landing-brand" to="/" aria-label="ParcelFlow home">
          <span className="landing-brand-mark"><Package size={19} /></span>
          <span>Parcel<span>Flow</span></span>
        </Link>
        <nav className="landing-nav" aria-label="Portal navigation">
          <a href="#customer">Customer</a>
          <a href="#dispatcher">Dispatcher</a>
          <a href="#rider">Rider</a>
        </nav>
        <div className="landing-header-actions">
          {!loading && user ? (
            <Link className="landing-header-link" to={`/${role}`}>Open workspace<ArrowRight size={15} /></Link>
          ) : (
            <>
              <Link className="landing-header-link landing-signin" to="/login">Sign in</Link>
              <Link className="landing-header-cta" to="/register">Get Started<ArrowRight size={15} /></Link>
            </>
          )}
        </div>
      </header>

      <div className="portal-sections">
        {portalSections.map((section, index) => (
          <PortalSection
            key={section.id}
            section={section}
            index={index}
            primaryHref={primaryHref}
          />
        ))}
      </div>

      <footer className="landing-footer">
        <span>ParcelFlow · Delivery coordination, made clear.</span>
        <span><Clock3 size={14} /> Every handoff, in view.</span>
      </footer>
    </main>
  )
}
