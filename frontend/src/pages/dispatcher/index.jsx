import { useQuery } from '@tanstack/react-query'
import { MapView } from '../../components/MapView.jsx'
import { StatusBadge } from '../../components/StatusBadge.jsx'
import api from '../../services/api.js'

export function DispatcherDashboard() {
  const ordersQuery = useQuery({
    queryKey: ['dispatch-orders'],
    queryFn: async () => (await api.get('/dispatch/orders')).data,
  })
  const ridersQuery = useQuery({
    queryKey: ['available-riders'],
    queryFn: async () => (await api.get('/dispatch/riders')).data,
  })

  return (
    <section>
      <div className="mb-7">
        <p className="text-sm font-medium text-blue-700">Dispatch workspace</p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">Operations overview</h1>
        <p className="mt-2 text-sm text-slate-500">
          Review incoming orders and identify available riders.
        </p>
      </div>
      {(ordersQuery.error || ridersQuery.error) && (
        <p className="mb-4 text-sm text-rose-700">Some dispatch data could not be loaded.</p>
      )}
      <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <div className="rounded-xl border border-slate-200 bg-white">
          <h2 className="border-b border-slate-100 px-5 py-4 font-semibold text-slate-900">
            Orders awaiting dispatch
          </h2>
          {ordersQuery.isLoading ? (
            <p className="p-5 text-sm text-slate-500">Loading orders…</p>
          ) : ordersQuery.data?.length ? (
            <ul className="divide-y divide-slate-100">
              {ordersQuery.data.map((order) => (
                <li className="flex items-center justify-between gap-3 px-5 py-4" key={order.id}>
                  <div>
                    <p className="font-medium text-slate-900">{order.tracking_number}</p>
                    <p className="mt-1 text-sm text-slate-500">{order.pickup_address}</p>
                  </div>
                  <StatusBadge status={order.current_status} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="p-5 text-sm text-slate-500">No orders are waiting for dispatch.</p>
          )}
        </div>
        <div className="rounded-xl border border-slate-200 bg-white">
          <h2 className="border-b border-slate-100 px-5 py-4 font-semibold text-slate-900">
            Available riders
          </h2>
          {ridersQuery.isLoading ? (
            <p className="p-5 text-sm text-slate-500">Loading riders…</p>
          ) : ridersQuery.data?.length ? (
            <ul className="divide-y divide-slate-100">
              {ridersQuery.data.map((rider) => (
                <li className="px-5 py-4" key={rider.rider_id}>
                  <p className="font-medium text-slate-900">{rider.full_name || 'Rider'}</p>
                  <p className="mt-1 text-sm text-slate-500">
                    {rider.vehicle_type} · {rider.vehicle_registration}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="p-5 text-sm text-slate-500">No available riders found.</p>
          )}
        </div>
      </div>
      <div className="mt-5 rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="mb-4 font-semibold text-slate-900">Operations map</h2>
        <MapView />
      </div>
    </section>
  )
}
