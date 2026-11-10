import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  ArrowUpRight,
  Bell,
  Check,
  CircleHelp,
  Clock3,
  DollarSign,
  Search,
  ShieldCheck,
  ShoppingBag,
  Users,
  X,
} from 'lucide-react'
import api, { apiErrorMessage } from '../../services/api.js'

const ACTIVE_DELIVERY_STATUSES = new Set(['assigned', 'accepted', 'picked_up', 'in_transit'])
const EMPTY_USERS = []
const EMPTY_ORDERS = []

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.07 } },
}

const rise = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.32, ease: 'easeOut' } },
}

export function AdminDashboard() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('pending')
  const [search, setSearch] = useState('')
  const [actionMessage, setActionMessage] = useState('')
  const [actionError, setActionError] = useState('')
  const searchInputRef = useRef(null)

  const usersQuery = useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => (await api.get('/users/', { params: { limit: 500 } })).data,
    refetchInterval: 30000,
  })
  const ordersQuery = useQuery({
    queryKey: ['admin-orders'],
    queryFn: async () => (await api.get('/orders/', { params: { limit: 100 } })).data,
    refetchInterval: 30000,
  })
  const users = usersQuery.data ?? EMPTY_USERS
  const orders = ordersQuery.data ?? EMPTY_ORDERS

  const approvalMutation = useMutation({
    mutationFn: async ({ userId, decision }) => (
      await api.patch(`/users/${userId}/${decision}`)
    ).data,
    onSuccess: async (account, variables) => {
      setActionError('')
      setActionMessage(
        variables.decision === 'approve'
          ? `${account.full_name || account.email} is approved and can sign in.`
          : `${account.full_name || account.email} was rejected and suspended.`,
      )
      await queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
    onError: (requestError) => {
      setActionMessage('')
      setActionError(apiErrorMessage(requestError, 'Could not update this account. Please try again.'))
    },
  })

  const pendingUsers = useMemo(
    () => users.filter(
      (user) => !user.is_verified
        && user.account_status === 'active'
        && ['dispatcher', 'rider'].includes(String(user.role).toLowerCase()),
    ),
    [users],
  )
  const filteredUsers = useMemo(() => {
    const source = activeTab === 'pending' ? pendingUsers : users
    const needle = search.trim().toLowerCase()
    if (!needle) return source
    return source.filter((user) => (
      [user.full_name, user.email, user.phone_number, user.role, user.account_status]
        .some((value) => String(value || '').toLowerCase().includes(needle))
    ))
  }, [activeTab, pendingUsers, search, users])

  const riders = users.filter((user) => String(user.role).toLowerCase() === 'rider')
  const activeDeliveries = orders.filter((order) => ACTIVE_DELIVERY_STATUSES.has(order.current_status))
  const completedOrders = orders.filter((order) => order.current_status === 'delivered')
  const revenue = completedOrders.reduce((total, order) => total + Number(order.delivery_fee || 0), 0)
  const riderTrend = dailySeries(riders)
  const approvalTrend = dailySeries(pendingUsers)
  const deliveryTrend = dailySeries(activeDeliveries)
  const revenueTrend = dailySeries(completedOrders, (order) => Number(order.delivery_fee || 0))
  const transactions = [...completedOrders]
    .sort((left, right) => new Date(right.created_at) - new Date(left.created_at))
    .slice(0, 4)
  const operationalUsers = users
    .filter((user) => ['rider', 'dispatcher'].includes(String(user.role).toLowerCase()))
    .slice(0, 6)
  const isLive = !usersQuery.isLoading
    && !ordersQuery.isLoading
    && !usersQuery.isError
    && !ordersQuery.isError
  const isUsersUnavailable = usersQuery.isLoading || usersQuery.isError
  const isOrdersUnavailable = ordersQuery.isLoading || ordersQuery.isError

  useEffect(() => {
    function focusSearch(event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        searchInputRef.current?.focus()
      }
    }

    window.addEventListener('keydown', focusSearch)
    return () => window.removeEventListener('keydown', focusSearch)
  }, [])

  function showPendingApprovals() {
    setActiveTab('pending')
    document.getElementById('admin-approvals')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  return (
    <section className="admin-dashboard">
      <div className="admin-ambient admin-ambient-one" aria-hidden="true" />
      <div className="admin-ambient admin-ambient-two" aria-hidden="true" />

      <header className="admin-dashboard-header">
        <div>
          <p className="admin-overline">Platform overview</p>
          <h1>Hey Admin!</h1>
          <p className="admin-header-subtitle">Here’s what’s happening across your delivery network.</p>
        </div>
        <div className="admin-header-tools">
          <label className="admin-search">
            <Search size={17} aria-hidden="true" />
            <input
              aria-label="Search users"
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search accounts..."
              ref={searchInputRef}
              value={search}
            />
            <kbd>⌘ K</kbd>
          </label>
          <span className={`admin-system-pill ${isLive ? 'is-live' : usersQuery.isError || ordersQuery.isError ? 'is-error' : 'is-waiting'}`}>
            <span />
            {isLive ? 'All systems operational' : usersQuery.isError || ordersQuery.isError ? 'System data unavailable' : 'Syncing system data'}
          </span>
          <button
            aria-label={`${pendingUsers.length} pending approvals. Jump to approvals`}
            className="admin-bell"
            onClick={showPendingApprovals}
            type="button"
          >
            <Bell size={18} />
            {pendingUsers.length > 0 && <span>{pendingUsers.length > 9 ? '9+' : pendingUsers.length}</span>}
          </button>
        </div>
      </header>

      {(usersQuery.isError || ordersQuery.isError) && (
        <div className="admin-alert admin-alert-error" role="alert">
          Some dashboard data could not be loaded. Use refresh to try again.
          <button
            onClick={() => {
              usersQuery.refetch()
              ordersQuery.refetch()
            }}
            type="button"
          >
            Refresh
          </button>
        </div>
      )}
      {actionError && <div className="admin-alert admin-alert-error" role="alert">{actionError}</div>}
      {actionMessage && <div className="admin-alert admin-alert-success" role="status">{actionMessage}</div>}

      <motion.div
        animate="visible"
        className="admin-kpi-grid"
        initial="hidden"
        variants={stagger}
      >
        <MetricCard
          icon={Users}
          label="Total Fleet / Riders"
          note={`${isUsersUnavailable ? '—' : riders.length} registered riders`}
          trend={riderTrend}
          value={isUsersUnavailable ? '—' : riders.length}
        />
        <MetricCard
          accent="violet"
          icon={ShieldCheck}
          label="Pending Approvals"
          note="Dispatchers and riders"
          trend={approvalTrend}
          value={isUsersUnavailable ? '—' : pendingUsers.length}
        />
        <MetricCard
          accent="amber"
          icon={ShoppingBag}
          label="Active Deliveries"
          note="Currently in progress"
          trend={deliveryTrend}
          value={isOrdersUnavailable ? '—' : activeDeliveries.length}
        />
        <MetricCard
          accent="emerald"
          icon={DollarSign}
          label="System Revenue"
          note="GH₵ · completed delivery fees"
          trend={revenueTrend}
          value={isOrdersUnavailable ? '—' : `GH₵ ${revenue.toFixed(2)}`}
          valueClass="admin-revenue-value"
        />
      </motion.div>

      <div className="admin-main-grid">
        <motion.section
          animate="visible"
          className="admin-card admin-fleet-card"
          initial="hidden"
          variants={rise}
          whileHover={{ y: -2 }}
        >
          <div className="admin-card-heading">
            <div>
              <span className="admin-section-kicker">People & operations</span>
              <h2>Fleet & dispatch teams</h2>
            </div>
            <button className="admin-text-action" onClick={() => setActiveTab('directory')} type="button">
              View directory <ArrowUpRight size={15} />
            </button>
          </div>
          {isUsersUnavailable ? (
            <p className="admin-empty-copy">{usersQuery.isError ? 'Fleet account data is unavailable.' : 'Loading fleet accounts…'}</p>
          ) : operationalUsers.length ? (
            <motion.div animate="visible" className="admin-fleet-grid" initial="hidden" variants={stagger}>
              {operationalUsers.map((user) => (
                <motion.article
                  className="admin-fleet-person"
                  key={user.id}
                  variants={rise}
                  whileHover={{ y: -2, scale: 1.01 }}
                >
                  <div className={`admin-person-avatar role-${String(user.role).toLowerCase()}`}>
                    {initials(user.full_name || user.email)}
                  </div>
                  <div className="admin-person-copy">
                    <strong>{user.full_name || 'Unnamed account'}</strong>
                    <span>{user.role}</span>
                  </div>
                  <StatusPill user={user} />
                </motion.article>
              ))}
            </motion.div>
          ) : (
            <p className="admin-empty-copy">Rider and dispatcher accounts will appear here.</p>
          )}
          <div className="admin-fleet-footer">
            <span><Users size={15} /> {isUsersUnavailable ? '—' : riders.length} riders registered</span>
            <span><Activity size={15} /> {isUsersUnavailable ? '—' : users.filter((user) => user.account_status === 'active' && user.is_verified).length} verified accounts active</span>
          </div>
        </motion.section>

        <motion.section
          animate="visible"
          className="admin-card admin-financial-card"
          initial="hidden"
          variants={rise}
          whileHover={{ y: -2 }}
        >
          <div className="admin-card-heading">
            <div>
              <span className="admin-section-kicker">Financials & analytics</span>
              <h2>Delivery fee overview</h2>
            </div>
            <span className="admin-period-pill">Recent completed orders</span>
          </div>
          <div className="admin-revenue-summary">
            <div>
              <span>Total completed fees</span>
              <strong>{isOrdersUnavailable ? '—' : `GH₵ ${revenue.toFixed(2)}`}</strong>
            </div>
            <span className="admin-revenue-icon"><ArrowUpRight size={18} /></span>
          </div>
          <RevenueChart values={revenueTrend} />
          <div className="admin-chart-caption">
            <span>Last 7 days</span>
            <span>{isOrdersUnavailable ? '—' : completedOrders.length} completed</span>
          </div>
          <div className="admin-transactions">
            <div className="admin-transactions-heading">
              <h3>Recent completed deliveries</h3>
              <span>Delivery fees</span>
            </div>
            {isOrdersUnavailable ? (
                  <p className="admin-empty-copy">{ordersQuery.isError ? 'Transaction data is unavailable.' : 'Loading transactions…'}</p>
            ) : transactions.length ? transactions.map((order) => (
              <div className="admin-transaction-row" key={order.id}>
                <span className="admin-transaction-icon"><ShoppingBag size={15} /></span>
                <span className="admin-transaction-copy">
                  <strong>{order.tracking_number}</strong>
                  <small>{new Date(order.created_at).toLocaleDateString()}</small>
                </span>
                <strong className="admin-transaction-amount">GH₵ {Number(order.delivery_fee).toFixed(2)}</strong>
              </div>
            )) : (
              <p className="admin-empty-copy">Completed delivery fees will appear here.</p>
            )}
          </div>
          <p className="admin-data-note">
            Revenue is the sum of delivery fees on completed orders; this API does not expose separate payment or commission records.
          </p>
        </motion.section>
      </div>

      <motion.section
        animate="visible"
        className="admin-card admin-approval-card"
        id="admin-approvals"
        initial="hidden"
        variants={rise}
      >
        <div className="admin-card-heading admin-approval-heading">
          <div>
            <span className="admin-section-kicker">Account verification</span>
            <h2>Team access requests</h2>
            <p>Review and decide access for dispatcher and rider accounts.</p>
          </div>
          <span className="admin-pending-count">
            <Clock3 size={15} /> {isUsersUnavailable ? '—' : pendingUsers.length} awaiting review
          </span>
        </div>

        <div className="admin-tabs" role="tablist" aria-label="Account management">
          <button
            aria-selected={activeTab === 'pending'}
            className={activeTab === 'pending' ? 'is-active' : ''}
            onClick={() => setActiveTab('pending')}
            role="tab"
            type="button"
          >
            Pending approvals <span>{isUsersUnavailable ? '—' : pendingUsers.length}</span>
          </button>
          <button
            aria-selected={activeTab === 'directory'}
            className={activeTab === 'directory' ? 'is-active' : ''}
            onClick={() => setActiveTab('directory')}
            role="tab"
            type="button"
          >
            User directory
          </button>
        </div>

        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            animate={{ opacity: 1, x: 0 }}
            className="admin-table-wrap"
            exit={{ opacity: 0, x: -8 }}
            initial={{ opacity: 0, x: 8 }}
            key={activeTab}
            transition={{ duration: 0.18 }}
            role="tabpanel"
          >
            {isUsersUnavailable ? (
              <p className="admin-empty-copy">{usersQuery.isError ? 'Account data is unavailable.' : 'Loading accounts…'}</p>
            ) : filteredUsers.length ? (
              <table className="admin-account-table">
                <thead>
                  <tr>
                    <th>Account</th>
                    <th>Account type</th>
                    <th>Verification</th>
                    <th>Joined</th>
                    {activeTab === 'pending' && <th className="admin-action-cell">Review</th>}
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((user) => (
                    <tr key={user.id}>
                      <td>
                        <div className="admin-table-account">
                          <span className={`admin-person-avatar small role-${String(user.role).toLowerCase()}`}>{initials(user.full_name || user.email)}</span>
                          <span><strong>{user.full_name || 'Unnamed account'}</strong><small>{user.email}</small></span>
                        </div>
                      </td>
                      <td><span className={`admin-role-tag role-${String(user.role).toLowerCase()}`}>{user.role}</span></td>
                      <td><StatusPill user={user} /></td>
                      <td className="admin-date-cell">{user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}</td>
                      {activeTab === 'pending' && (
                        <td className="admin-action-cell">
                          <div className="admin-row-actions">
                            {user.account_status === 'suspended' ? (
                              <button
                                className="admin-approve-button"
                                disabled={approvalMutation.isPending}
                                onClick={() => runDecision('approve', user.id)}
                                type="button"
                              >
                                <Check size={14} /> Restore & approve
                              </button>
                            ) : activeTab === 'pending' && (
                              <>
                                <button
                                  className="admin-approve-button"
                                  disabled={approvalMutation.isPending}
                                  onClick={() => runDecision('approve', user.id)}
                                  type="button"
                                >
                                  <Check size={14} /> Approve
                                </button>
                                <button
                                  aria-label={`Reject ${user.full_name || user.email}`}
                                  className="admin-reject-button"
                                  disabled={approvalMutation.isPending}
                                  onClick={() => runDecision('reject', user.id)}
                                  type="button"
                                >
                                  <X size={14} /> Reject
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="admin-empty-state">
                {activeTab === 'pending' ? <ShieldCheck size={27} /> : <CircleHelp size={27} />}
                <strong>{search.trim() ? 'No matching accounts' : activeTab === 'pending' ? 'You’re all caught up' : 'No accounts found'}</strong>
                <span>{search.trim() ? 'Try another name, email, or role.' : activeTab === 'pending' ? 'There are no dispatcher or rider accounts awaiting approval.' : 'Accounts will appear here when they register.'}</span>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </motion.section>
    </section>
  )

  function runDecision(decision, userId) {
    const account = users.find((user) => user.id === userId)
    if (
      decision === 'reject'
      && !window.confirm(`Reject ${account?.full_name || account?.email || 'this account'}? They will be suspended. An administrator can restore and approve them later.`)
    ) {
      return
    }
    setActionError('')
    setActionMessage('')
    approvalMutation.mutate({ userId, decision })
  }
}

function MetricCard({ icon: Icon, label, note, trend, value, accent = 'blue', valueClass = '' }) {
  return (
    <motion.article
      className={`admin-kpi-card accent-${accent}`}
      variants={rise}
      whileHover={{ y: -2 }}
    >
      <div className="admin-kpi-top">
        <span className="admin-kpi-icon"><Icon size={18} /></span>
        <ArrowUpRight className="admin-kpi-arrow" size={16} />
      </div>
      <span className="admin-kpi-label">{label}</span>
      <div className="admin-kpi-bottom">
        <div><strong className={valueClass}>{value}</strong><small>{note}</small></div>
        <Sparkline values={trend} />
      </div>
    </motion.article>
  )
}

function Sparkline({ values }) {
  const points = chartPoints(values, 100, 34, 3)
  return (
    <svg aria-hidden="true" className="admin-sparkline" viewBox="0 0 100 34">
      <polyline points={points} />
    </svg>
  )
}

function RevenueChart({ values }) {
  const points = chartPoints(values, 560, 118, 12)
  const pointList = points.split(' ').map((point) => point.split(',').map(Number))
  const line = pointList.map(([x, y], index) => `${index ? 'L' : 'M'} ${x} ${y}`).join(' ')
  const fill = `${line} L 548 118 L 12 118 Z`

  return (
    <div className="admin-chart">
      <div className="admin-chart-y-labels"><span>GH₵</span><span>Fees</span><span>0</span></div>
      <svg aria-label="Delivery fees for recent completed orders" className="admin-revenue-chart" role="img" viewBox="0 0 560 130" preserveAspectRatio="none">
        <defs>
          <linearGradient id="admin-chart-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#5b7cfa" stopOpacity=".22" />
            <stop offset="100%" stopColor="#5b7cfa" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[22, 53, 84, 116].map((y) => <line key={y} x1="12" x2="548" y1={y} y2={y} />)}
        <path className="admin-chart-area" d={fill} />
        <path className="admin-chart-line" d={line} />
        {pointList.map(([cx, cy], index) => <circle cx={cx} cy={cy} key={`${cx}-${index}`} r="3" />)}
      </svg>
    </div>
  )
}

function StatusPill({ user }) {
  const rejected = user.account_status === 'suspended' && !user.is_verified
  const verified = user.is_verified && user.account_status === 'active'
  const label = rejected ? 'Rejected' : verified ? 'Active' : 'Pending'
  return (
    <span className={`admin-status-pill ${verified ? 'status-active' : rejected ? 'status-rejected' : 'status-pending'}`}>
      <span />
      {label}
    </span>
  )
}

function initials(name) {
  return name
    .split(/[\s@._-]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('')
}

function chartPoints(values, width, height, padding) {
  const points = values.length ? values : [0, 0, 0, 0]
  const min = Math.min(...points)
  const max = Math.max(...points)
  const range = max - min || 1
  return points.map((value, index) => {
    const x = padding + (index * (width - padding * 2)) / Math.max(points.length - 1, 1)
    const y = height - padding - ((value - min) / range) * (height - padding * 2)
    return `${x},${y}`
  }).join(' ')
}

function dailySeries(records, getValue = () => 1) {
  const start = new Date()
  start.setUTCHours(0, 0, 0, 0)
  start.setUTCDate(start.getUTCDate() - 6)
  const values = Array(7).fill(0)

  records.forEach((record) => {
    const createdAt = new Date(record.created_at)
    if (Number.isNaN(createdAt.getTime())) return
    createdAt.setUTCHours(0, 0, 0, 0)
    const dayIndex = Math.floor((createdAt.getTime() - start.getTime()) / 86400000)
    if (dayIndex >= 0 && dayIndex < values.length) {
      values[dayIndex] += getValue(record)
    }
  })

  return values
}
