import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Package, PackageCheck, Plus } from 'lucide-react'
import { Link } from 'react-router-dom'
import api from '../../services/api.js'
import { StatusBadge } from '../../components/StatusBadge.jsx'
import { DeliveryMap } from '../../components/DeliveryMap.jsx'

export function CustomerDashboard() {
  const { data: orders = [], isLoading, error } = useQuery({
    queryKey: ['customer-orders'],
    queryFn: async () => (await api.get('/orders')).data,
  })

  return (
    <section>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
        <p className="text-sm font-medium text-blue-700">Customer workspace</p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">My deliveries</h1>
        <p className="mt-2 text-sm text-slate-500">
          Review your delivery requests and follow their current status.
        </p>
        </div>
        <div className="flex gap-2">
          <Link className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:border-blue-200 hover:text-blue-700" to="/customer/track">
            Track order <ArrowRight size={16} />
          </Link>
          <Link className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-blue-700" to="/customer/create">
            <Plus size={17} /> New delivery
          </Link>
        </div>
      </div>
      {error && <p className="mb-4 text-sm text-rose-700">Could not load orders.</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        <SummaryCard icon={Package} label="Total deliveries" value={isLoading ? '…' : orders.length} />
        <SummaryCard
          icon={PackageCheck}
          label="Delivered"
          value={isLoading ? '…' : orders.filter((order) => order.current_status === 'delivered').length}
        />
        <SummaryCard
          icon={PackageCheck}
          label="In progress"
          value={isLoading ? '…' : orders.filter((order) => ['assigned', 'accepted', 'picked_up', 'in_transit'].includes(order.current_status)).length}
        />
      </div>
      <div className="mt-7 grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-2xl border border-white/10 bg-white p-3 shadow-2xl sm:p-4">
          <div className="flex items-center justify-between px-2 pb-3 pt-1">
            <div><h2 className="font-semibold text-slate-100">Delivery map</h2><p className="mt-1 text-xs text-slate-400">Pickup and destination points from your recent orders</p></div>
            <span className="text-xs font-medium text-blue-300">{orders.length} tracked</span>
          </div>
          <DeliveryMap
            markers={orders.flatMap((order) => [
              { id: `${order.id}-pickup`, type: 'pickup', position: [Number(order.pickup_latitude), Number(order.pickup_longitude)], label: `${order.tracking_number} · pickup` },
              { id: `${order.id}-destination`, type: 'destination', position: [Number(order.destination_latitude), Number(order.destination_longitude)], label: `${order.tracking_number} · destination` },
            ])}
            className="h-[320px]"
          />
        </div>
        <div className="overflow-hidden rounded-2xl border border-white/10 bg-white shadow-2xl">
          <h2 className="border-b border-white/10 px-5 py-4 font-semibold text-slate-100">Active delivery timeline</h2>
          {isLoading ? (
            <p className="p-5 text-sm text-slate-400">Loading delivery activity…</p>
          ) : orders.length ? (
            <ol className="divide-y divide-white/5">
              {orders.slice(0, 5).map((order) => (
                <li className="flex items-start gap-3 px-5 py-4" key={order.id}>
                  <span className="mt-1.5 size-2 shrink-0 rounded-full bg-blue-400 shadow-[0_0_12px_#3b82f6]" />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-2"><p className="truncate text-sm font-semibold text-slate-100">{order.tracking_number}</p><StatusBadge status={order.current_status} /></div>
                    <p className="mt-1 truncate text-xs text-slate-400">{order.destination_address}</p>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="p-5 text-sm text-slate-400">Your delivery activity will appear here.</p>
          )}
        </div>
      </div>
      <div className="mt-7 overflow-hidden rounded-2xl border border-white/10 bg-white shadow-2xl">
        <h2 className="border-b border-slate-100 px-5 py-4 font-semibold text-slate-900">
          Recent orders
        </h2>
        {isLoading ? (
          <p className="p-5 text-sm text-slate-500">Loading orders…</p>
        ) : orders.length === 0 ? (
          <p className="p-5 text-sm text-slate-500">Your delivery history will appear here.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {orders.map((order) => (
              <li className="flex flex-wrap items-center justify-between gap-3 px-5 py-4" key={order.id}>
                <div>
                  <p className="font-medium text-slate-900">{order.tracking_number}</p>
                  <p className="mt-1 text-sm text-slate-500">{order.destination_address}</p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={order.current_status} />
                  <Link aria-label={`Track order ${order.tracking_number}`} className="grid size-9 place-items-center rounded-lg border border-slate-200 text-slate-500 hover:border-blue-200 hover:text-blue-700" to={`/customer/track/${order.id}`}><ArrowRight size={16} /></Link>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}

function SummaryCard({ icon: Icon, label, value }) {
  return (
    <article className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white p-5 shadow-2xl">
      <span className="grid size-11 place-items-center rounded-xl bg-blue-50 text-blue-700">
        <Icon size={21} />
      </span>
      <div>
        <p className="text-sm text-slate-500">{label}</p>
        <p className="mt-1 text-xl font-bold text-slate-900">{value}</p>
      </div>
    </article>
  )
}
