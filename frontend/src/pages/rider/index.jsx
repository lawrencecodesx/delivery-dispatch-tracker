import { useQuery } from '@tanstack/react-query'
import api from '../../services/api.js'
import { StatusBadge } from '../../components/StatusBadge.jsx'

export function RiderDashboard() {
  const { data: deliveries = [], isLoading, error } = useQuery({
    queryKey: ['rider-deliveries'],
    queryFn: async () => (await api.get('/rider/deliveries')).data,
  })

  return (
    <section>
      <div className="mb-7">
        <p className="text-sm font-medium text-blue-700">Rider workspace</p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">My assignments</h1>
        <p className="mt-2 text-sm text-slate-500">
          Review delivery tasks assigned to you and their current status.
        </p>
      </div>
      {error && <p className="mb-4 text-sm text-rose-700">Could not load assignments.</p>}
      <div className="rounded-xl border border-slate-200 bg-white">
        {isLoading ? (
          <p className="p-5 text-sm text-slate-500">Loading assignments…</p>
        ) : deliveries.length === 0 ? (
          <p className="p-5 text-sm text-slate-500">New assignments will appear here.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {deliveries.map((assignment) => (
              <li className="flex flex-wrap items-center justify-between gap-3 px-5 py-4" key={assignment.id}>
                <div>
                  <p className="font-medium text-slate-900">
                    {assignment.order?.tracking_number || `Order ${assignment.order_id}`}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    {assignment.order?.destination_address}
                  </p>
                </div>
                <StatusBadge status={assignment.order?.current_status} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
