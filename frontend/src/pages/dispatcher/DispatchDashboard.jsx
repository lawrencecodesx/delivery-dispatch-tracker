import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Check, MapPinned, PackageCheck, RefreshCw, Truck, Users, X } from 'lucide-react'
import { DeliveryMap } from '../../components/DeliveryMap.jsx'
import { StatusBadge } from '../../components/StatusBadge.jsx'
import api, { apiErrorMessage } from '../../services/api.js'

const EMPTY_ORDERS = []

export function DispatchDashboard() {
  const queryClient = useQueryClient()
  const [selectedOrder, setSelectedOrder] = useState(null)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const ordersQuery = useQuery({
    queryKey: ['dispatch-orders'],
    queryFn: async () => (await api.get('/dispatch/orders')).data,
    refetchInterval: 30000,
  })
  const ridersQuery = useQuery({
    queryKey: ['available-riders'],
    queryFn: async () => (await api.get('/dispatch/riders')).data,
    refetchInterval: 30000,
  })
  const candidatesQuery = useQuery({
    queryKey: ['assignment-candidates', selectedOrder?.id],
    queryFn: async () => (await api.get('/dispatch/riders', {
      params: {
        pickup_latitude: selectedOrder.pickup_latitude,
        pickup_longitude: selectedOrder.pickup_longitude,
      },
    })).data,
    enabled: Boolean(selectedOrder),
  })

  const refreshOperations = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['dispatch-orders'] }),
      queryClient.invalidateQueries({ queryKey: ['available-riders'] }),
    ])
  }
  const reviewOrder = useMutation({
    mutationFn: async ({ orderId, decision }) => (await api.patch(`/dispatch/orders/${orderId}/review`, { decision })).data,
    onSuccess: async (_result, variables) => {
      setError('')
      setNotice(variables.decision === 'confirm' ? 'Order confirmed and ready for assignment.' : 'Order was declined.')
      await refreshOperations()
    },
    onError: (requestError) => setError(apiErrorMessage(requestError, 'Could not update this order.')),
  })
  const assignRider = useMutation({
    mutationFn: async ({ orderId, riderId }) => (await api.post('/dispatch/assignments', { order_id: orderId, rider_id: riderId })).data,
    onSuccess: async () => {
      setSelectedOrder(null)
      setNotice('Rider assigned. The rider can now accept or decline the delivery.')
      setError('')
      await refreshOperations()
    },
    onError: (requestError) => setError(apiErrorMessage(requestError, 'Could not assign this rider. Refresh the list and try again.')),
  })

  const orders = ordersQuery.data ?? EMPTY_ORDERS
  const pendingCount = orders.filter((order) => order.current_status === 'pending').length
  const confirmedCount = orders.filter((order) => order.current_status === 'confirmed').length
  const markers = useMemo(() => orders.flatMap((order) => [
    { id: `${order.id}-pickup`, type: 'pickup', position: [Number(order.pickup_latitude), Number(order.pickup_longitude)], label: `${order.tracking_number} · pickup` },
    { id: `${order.id}-destination`, type: 'destination', position: [Number(order.destination_latitude), Number(order.destination_longitude)], label: `${order.tracking_number} · destination` },
  ]), [orders])

  return (
    <section className="mx-auto max-w-[1500px]">
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-sm font-semibold text-blue-700">Dispatch control room</p><h1 className="mt-1 text-3xl font-black tracking-tight text-slate-950">Operations overview</h1><p className="mt-2 text-sm text-slate-500">Review incoming deliveries and match confirmed orders with available riders.</p></div>
        <button className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm hover:border-blue-200 hover:text-blue-700" onClick={() => { ordersQuery.refetch(); ridersQuery.refetch() }} type="button"><RefreshCw size={16} className={ordersQuery.isFetching || ridersQuery.isFetching ? 'animate-spin' : ''} /> Refresh</button>
      </div>
      {error && <p className="mb-4 rounded-xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p>}
      {notice && <p className="mb-4 rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{notice}</p>}
      {(ordersQuery.error || ridersQuery.error) && <p className="mb-4 rounded-xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700">Dispatch information could not be loaded. Check your connection and refresh.</p>}

      <div className="mb-5 grid gap-4 sm:grid-cols-3">
        <Metric icon={PackageCheck} label="Open orders" value={ordersQuery.isLoading ? '…' : orders.length} tone="blue" />
        <Metric icon={MapPinned} label="Awaiting review" value={ordersQuery.isLoading ? '…' : pendingCount} tone="amber" />
        <Metric icon={Users} label="Available riders" value={ridersQuery.isLoading ? '…' : (ridersQuery.data || []).length} tone="emerald" />
      </div>

      <div className="grid gap-5 2xl:grid-cols-[minmax(0,1.3fr)_minmax(340px,0.7fr)]">
        <div className="space-y-5">
          <div className="rounded-3xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
            <div className="flex items-center justify-between px-2 pb-3 pt-1"><div><h2 className="font-bold text-slate-900">Order operations map</h2><p className="mt-1 text-xs text-slate-500">Pickup and destination points for open orders</p></div><MapPinned size={20} className="text-blue-600" /></div>
            <DeliveryMap markers={markers} className="h-[350px]" />
            <div className="flex gap-5 px-2 pt-3 text-xs text-slate-500"><span className="inline-flex items-center gap-2"><i className="size-2.5 rounded-full bg-emerald-500" /> Pickups</span><span className="inline-flex items-center gap-2"><i className="size-2.5 rounded-full bg-rose-500" /> Destinations</span></div>
          </div>
          <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4"><div><h2 className="font-bold">Orders awaiting dispatch</h2><p className="mt-1 text-xs text-slate-500">Confirm new requests before assigning a rider.</p></div><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600">{orders.length} open</span></div>
            {ordersQuery.isLoading ? <p className="p-6 text-sm text-slate-500">Loading open orders…</p> : orders.length ? (
              <ul className="divide-y divide-slate-100">
                {orders.map((order) => (
                  <li className="p-5" key={order.id}>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div><div className="flex flex-wrap items-center gap-2"><p className="font-bold text-slate-900">{order.tracking_number}</p><StatusBadge status={order.current_status} /></div><p className="mt-2 text-sm text-slate-600">{order.pickup_address}</p><p className="mt-1 flex items-center gap-1.5 text-sm text-slate-500"><ArrowRight size={14} />{order.destination_address}</p></div>
                      <p className="text-sm font-bold text-slate-800">GH₵ {Number(order.delivery_fee).toFixed(2)}</p>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {order.current_status === 'pending' ? (
                        <>
                          <button className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-2 text-xs font-bold text-white hover:bg-blue-700 disabled:opacity-50" disabled={reviewOrder.isPending} onClick={() => reviewOrder.mutate({ orderId: order.id, decision: 'confirm' })} type="button"><Check size={15} /> Confirm order</button>
                          <button className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3.5 py-2 text-xs font-bold text-slate-600 hover:bg-rose-50 hover:text-rose-700 disabled:opacity-50" disabled={reviewOrder.isPending} onClick={() => reviewOrder.mutate({ orderId: order.id, decision: 'reject' })} type="button"><X size={15} /> Decline</button>
                        </>
                      ) : (
                        <button className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-3.5 py-2 text-xs font-bold text-white hover:bg-blue-700" onClick={() => { setError(''); setSelectedOrder(order) }} type="button"><Truck size={15} /> Assign rider</button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            ) : <p className="p-6 text-sm text-slate-500">No orders are waiting for review or assignment.</p>}
          </div>
        </div>

        <aside className="rounded-3xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4"><div><h2 className="font-bold">Rider availability</h2><p className="mt-1 text-xs text-slate-500">Eligible for a new assignment</p></div><span className="grid size-10 place-items-center rounded-xl bg-emerald-50 text-emerald-700"><Users size={18} /></span></div>
          {ridersQuery.isLoading ? <p className="p-5 text-sm text-slate-500">Loading rider roster…</p> : ridersQuery.data?.length ? (
            <ul className="divide-y divide-slate-100">
              {ridersQuery.data.map((rider) => (
                <li className="flex items-start gap-3 px-5 py-4" key={rider.rider_id}>
                  <span className="grid size-10 shrink-0 place-items-center rounded-full bg-blue-50 text-sm font-bold text-blue-700">{(rider.full_name || 'R').slice(0, 1).toUpperCase()}</span>
                  <div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-2"><p className="truncate text-sm font-bold text-slate-800">{rider.full_name || 'Rider'}</p><span className="size-2 shrink-0 rounded-full bg-emerald-500" /></div><p className="mt-1 text-xs text-slate-500">{rider.vehicle_type} · {rider.vehicle_registration}</p>{rider.distance_km != null && <p className="mt-1 text-xs font-medium text-blue-700">{rider.distance_km} km from pickup</p>}</div>
                </li>
              ))}
            </ul>
          ) : <div className="px-5 py-8 text-center"><Users className="mx-auto text-slate-300" size={26} /><p className="mt-2 text-sm font-semibold text-slate-700">No riders available</p><p className="mt-1 text-xs leading-5 text-slate-500">Riders will appear here when their accounts are active and they are free.</p></div>}
          <div className="border-t border-slate-100 p-5"><div className="flex items-center justify-between text-sm"><span className="text-slate-500">Confirmed, unassigned</span><span className="font-bold text-slate-900">{confirmedCount}</span></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-blue-500" style={{ width: `${orders.length ? Math.min((confirmedCount / orders.length) * 100, 100) : 0}%` }} /></div></div>
        </aside>
      </div>

      {selectedOrder && <AssignmentModal
        order={selectedOrder}
        candidates={candidatesQuery.data || []}
        isLoading={candidatesQuery.isLoading || assignRider.isPending}
        error={candidatesQuery.error ? 'Could not load eligible riders.' : ''}
        onClose={() => setSelectedOrder(null)}
        onAssign={(riderId) => assignRider.mutate({ orderId: selectedOrder.id, riderId })}
      />}
    </section>
  )
}

function Metric({ icon: Icon, label, value, tone }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-700',
    amber: 'bg-amber-50 text-amber-700',
    emerald: 'bg-emerald-50 text-emerald-700',
  }
  return <article className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><span className={`grid size-11 place-items-center rounded-xl ${colors[tone]}`}><Icon size={20} /></span><div><p className="text-xs font-medium text-slate-500">{label}</p><p className="mt-1 text-2xl font-black text-slate-900">{value}</p></div></article>
}

function AssignmentModal({ order, candidates, isLoading, error, onClose, onAssign }) {
  const [riderId, setRiderId] = useState('')
  return (
    <div className="fixed inset-0 z-[1000] grid place-items-center bg-slate-950/50 p-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <section aria-labelledby="assign-title" aria-modal="true" className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl sm:p-7" role="dialog">
        <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-widest text-blue-700">Rider assignment</p><h2 className="mt-1 text-xl font-black text-slate-950" id="assign-title">Choose a rider</h2><p className="mt-1 text-sm text-slate-500">{order.tracking_number} · {order.pickup_address}</p></div><button aria-label="Close assignment dialog" className="grid size-9 place-items-center rounded-full bg-slate-100 text-slate-600 hover:bg-slate-200" onClick={onClose} type="button"><X size={18} /></button></div>
        {error && <p className="mt-5 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
        {isLoading ? <p className="py-8 text-center text-sm text-slate-500">Loading eligible riders…</p> : candidates.length ? (
          <div className="mt-5 max-h-72 space-y-2 overflow-y-auto">
            {candidates.map((rider) => (
              <label className={`flex cursor-pointer items-center gap-3 rounded-2xl border p-3.5 transition ${String(riderId) === String(rider.rider_id) ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-blue-200'}`} key={rider.rider_id}>
                <input checked={String(riderId) === String(rider.rider_id)} className="accent-blue-600" name="rider" onChange={() => setRiderId(String(rider.rider_id))} type="radio" value={rider.rider_id} />
                <span className="min-w-0 flex-1"><span className="block truncate text-sm font-bold text-slate-800">{rider.full_name || 'Rider'}</span><span className="mt-0.5 block text-xs text-slate-500">{rider.vehicle_type} · {rider.vehicle_registration}{rider.distance_km != null ? ` · ${rider.distance_km} km away` : ''}</span></span>
              </label>
            ))}
          </div>
        ) : !error && <p className="mt-5 rounded-2xl bg-amber-50 p-4 text-sm leading-6 text-amber-800">There are no available riders for this delivery right now.</p>}
        <div className="mt-6 flex justify-end gap-2"><button className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50" onClick={onClose} type="button">Cancel</button><button className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50" disabled={!riderId || isLoading} onClick={() => onAssign(Number(riderId))} type="button">Assign rider</button></div>
      </section>
    </div>
  )
}
