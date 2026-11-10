import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { ArrowLeft, Clock3, MapPin, PackageCheck, Radio, ShieldCheck } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { DeliveryMap } from '../../components/DeliveryMap.jsx'
import { StatusBadge } from '../../components/StatusBadge.jsx'
import api, { apiErrorMessage } from '../../services/api.js'

const STATUS_STEPS = [
  ['pending', 'Request received'],
  ['confirmed', 'Order confirmed'],
  ['assigned', 'Rider assigned'],
  ['accepted', 'Rider accepted'],
  ['picked_up', 'Package picked up'],
  ['in_transit', 'On the way'],
  ['delivered', 'Delivered'],
]

function coordinates(latitude, longitude) {
  return [Number(latitude), Number(longitude)]
}

export function TrackOrder() {
  const { orderId } = useParams()
  const [deliveryCode, setDeliveryCode] = useState({ orderId: null, value: '' })
  const codeMutation = useMutation({
    mutationFn: async () => (await api.post(`/orders/${orderId}/delivery-code`)).data,
    onSuccess: (result) => setDeliveryCode({ orderId, value: result.verification_code }),
  })
  const ordersQuery = useQuery({
    queryKey: ['customer-orders'],
    queryFn: async () => (await api.get('/orders')).data,
  })
  const orderQuery = useQuery({
    queryKey: ['order-detail', orderId],
    queryFn: async () => (await api.get(`/orders/${orderId}`)).data,
    enabled: Boolean(orderId),
    refetchInterval: 15000,
  })
  const trackingQuery = useQuery({
    queryKey: ['order-tracking', orderId],
    queryFn: async () => (await api.get(`/tracking/${orderId}`)).data,
    enabled: Boolean(orderId),
    refetchInterval: 15000,
    retry: false,
  })
  const order = orderQuery.data
  const currentDeliveryCode = deliveryCode.orderId === orderId ? deliveryCode.value : ''
  const history = order?.status_history || []
  const activeStep = STATUS_STEPS.findIndex(([status]) => status === order?.current_status)
  const markers = order ? [
    { id: 'pickup', type: 'pickup', position: coordinates(order.pickup_latitude, order.pickup_longitude), label: `Pickup · ${order.pickup_address}` },
    { id: 'destination', type: 'destination', position: coordinates(order.destination_latitude, order.destination_longitude), label: `Destination · ${order.destination_address}` },
    ...(trackingQuery.data ? [{ id: 'rider', type: 'rider', position: coordinates(trackingQuery.data.latitude, trackingQuery.data.longitude), label: 'Latest rider location' }] : []),
  ] : []

  if (!orderId) {
    return (
      <section className="mx-auto max-w-5xl">
        <div className="mb-7"><p className="text-sm font-semibold text-blue-700">Live tracking</p><h1 className="mt-1 text-3xl font-black tracking-tight">Follow a delivery</h1></div>
        {ordersQuery.isLoading ? <p className="text-slate-500">Loading your deliveries…</p> : ordersQuery.data?.length ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {ordersQuery.data.map((item) => (
              <Link className="rounded-2xl border border-slate-200 bg-white p-5 transition hover:border-blue-300 hover:shadow-lg" key={item.id} to={`/customer/track/${item.id}`}>
                <div className="flex items-center justify-between gap-3"><span className="font-bold">{item.tracking_number}</span><StatusBadge status={item.current_status} /></div>
                <p className="mt-3 text-sm text-slate-500">{item.destination_address}</p>
                <span className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-blue-700">View journey <Radio size={16} /></span>
              </Link>
            ))}
          </div>
        ) : <EmptyState />}
      </section>
    )
  }

  return (
    <section className="mx-auto max-w-6xl">
      <Link className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-700" to="/customer">
        <ArrowLeft size={16} /> Back to deliveries
      </Link>
      {orderQuery.isLoading ? <p className="mt-8 text-slate-500">Loading delivery details…</p> : orderQuery.error ? (
        <p className="mt-8 rounded-2xl bg-rose-50 p-5 text-sm text-rose-700">We could not load this delivery. It may no longer be available.</p>
      ) : order && (
        <>
          <div className="mb-7 mt-5 flex flex-wrap items-end justify-between gap-4">
            <div><p className="text-sm font-semibold text-blue-700">Delivery tracking</p><h1 className="mt-1 text-3xl font-black tracking-tight">Your delivery is in view.</h1><p className="mt-2 text-sm text-slate-500">Tracking number · <span className="font-semibold text-slate-700">{order.tracking_number}</span></p></div>
            <StatusBadge status={order.current_status} />
          </div>
          {order.current_status === 'in_transit' && (
            <div className="mb-5 rounded-2xl border border-blue-200 bg-blue-50 p-4 sm:flex sm:items-center sm:justify-between sm:gap-4">
              <div>
                <p className="font-semibold text-blue-950">Delivery verification</p>
                <p className="mt-1 text-sm text-blue-800">Request a short-lived code and share it with the rider at handoff. Each order allows up to three code requests.</p>
                {currentDeliveryCode && <p className="mt-3 font-mono text-2xl font-black tracking-[0.3em] text-blue-950" aria-live="polite">{currentDeliveryCode}</p>}
                {codeMutation.isError && <p className="mt-2 text-sm text-rose-700" role="alert">{apiErrorMessage(codeMutation.error, 'Could not request a verification code.')}</p>}
              </div>
              <button
                className="mt-3 inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-blue-700 px-4 py-3 text-sm font-bold text-white transition hover:bg-blue-800 disabled:cursor-wait disabled:opacity-60 sm:mt-0"
                disabled={codeMutation.isPending}
                onClick={() => codeMutation.mutate()}
                type="button"
              >
                <ShieldCheck size={17} />{codeMutation.isPending ? 'Requesting…' : currentDeliveryCode ? 'Request a new code' : 'Show delivery code'}
              </button>
            </div>
          )}
          <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-3xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
              <div className="flex items-center justify-between px-2 pb-3 pt-1">
                <div><h2 className="font-bold">Route overview</h2><p className="mt-1 text-xs text-slate-500">Map refreshes every 15 seconds while this page is open.</p></div>
                <span className={`flex items-center gap-2 text-xs font-semibold ${trackingQuery.data ? 'text-emerald-700' : 'text-slate-400'}`}><span className={`size-2 rounded-full ${trackingQuery.data ? 'animate-pulse bg-emerald-500' : 'bg-slate-300'}`} />{trackingQuery.data ? 'Live location' : 'Waiting for rider'}</span>
              </div>
              <DeliveryMap markers={markers} className="h-[390px]" />
              {!trackingQuery.data && <p className="px-2 pt-3 text-xs text-slate-500">Rider location will appear once the rider shares a location during an active delivery.</p>}
              {trackingQuery.data && <p className="px-2 pt-3 text-xs text-slate-500">Last update: {new Date(trackingQuery.data.recorded_at).toLocaleString()}</p>}
            </div>
            <div className="space-y-5">
              <div className="rounded-3xl border border-slate-200 bg-white p-5 sm:p-6">
                <h2 className="font-bold">Journey timeline</h2>
                <ol className="mt-5 space-y-0">
                  {history.length ? history.map((entry, index) => (
                    <li className="relative flex gap-3 pb-5 last:pb-0" key={entry.id}>
                      {index < history.length - 1 && <span className="absolute left-[11px] top-6 h-full w-px bg-slate-200" />}
                      <span className="relative z-10 mt-0.5 grid size-6 shrink-0 place-items-center rounded-full bg-blue-50 text-blue-600"><Clock3 size={13} /></span>
                      <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><span className="text-sm font-semibold capitalize text-slate-800">{entry.new_status.replaceAll('_', ' ')}</span><time className="text-xs text-slate-400">{new Date(entry.updated_at).toLocaleString()}</time></div>{entry.remarks && <p className="mt-1 text-xs leading-5 text-slate-500">{entry.remarks}</p>}</div>
                    </li>
                  )) : STATUS_STEPS.map(([status, label], index) => (
                    <li className="relative flex gap-3 pb-5 last:pb-0" key={status}>
                      {index < STATUS_STEPS.length - 1 && <span className="absolute left-[11px] top-6 h-full w-px bg-slate-200" />}
                      <span className={`relative z-10 mt-0.5 grid size-6 shrink-0 place-items-center rounded-full ${index <= activeStep ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-400'}`}><PackageCheck size={13} /></span>
                      <span className={`pt-1 text-sm ${index <= activeStep ? 'font-semibold text-slate-800' : 'text-slate-400'}`}>{label}</span>
                    </li>
                  ))}
                </ol>
              </div>
              <div className="rounded-3xl bg-slate-950 p-5 text-white sm:p-6">
                <p className="text-xs font-bold uppercase tracking-widest text-blue-300">Delivery stops</p>
                <div className="mt-4 flex gap-3"><MapPin className="mt-0.5 shrink-0 text-emerald-400" size={18} /><div><p className="text-xs text-slate-400">Pickup</p><p className="mt-1 text-sm leading-5">{order.pickup_address}</p></div></div>
                <div className="my-4 ml-2.5 h-5 border-l border-dashed border-slate-600" />
                <div className="flex gap-3"><MapPin className="mt-0.5 shrink-0 text-rose-400" size={18} /><div><p className="text-xs text-slate-400">Destination</p><p className="mt-1 text-sm leading-5">{order.destination_address}</p></div></div>
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  )
}

function EmptyState() {
  return <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center"><PackageCheck className="mx-auto text-slate-300" size={32} /><p className="mt-3 font-semibold text-slate-700">No deliveries yet</p><p className="mt-1 text-sm text-slate-500">Create a delivery to start tracking its journey.</p><Link className="mt-5 inline-flex rounded-full bg-blue-600 px-5 py-2.5 text-sm font-bold text-white" to="/customer/create">Create a delivery</Link></div>
}
