import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MapPin, PackageCheck, ShieldCheck, Truck } from 'lucide-react'
import { StatusBadge } from '../../components/StatusBadge.jsx'
import api, { apiErrorMessage } from '../../services/api.js'

export function RiderDashboard() {
  const queryClient = useQueryClient()
  const [proofOrder, setProofOrder] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const deliveriesQuery = useQuery({
    queryKey: ['rider-deliveries'],
    queryFn: async () => (await api.get('/rider/deliveries')).data,
    refetchInterval: 20000,
  })
  const refreshDeliveries = async () => queryClient.invalidateQueries({ queryKey: ['rider-deliveries'] })
  const respond = useMutation({
    mutationFn: async ({ assignmentId, decision }) => (await api.patch(`/rider/assignments/${assignmentId}/respond`, { decision })).data,
    onSuccess: async (_result, variables) => {
      setError('')
      setNotice(variables.decision === 'accept' ? 'Assignment accepted. Head to the pickup point.' : 'Assignment declined.')
      await refreshDeliveries()
    },
    onError: (requestError) => setError(apiErrorMessage(requestError, 'Could not update this assignment.')),
  })
  const updateStatus = useMutation({
    mutationFn: async ({ orderId, status }) => (await api.patch(`/rider/orders/${orderId}/status`, { status })).data,
    onSuccess: async (_result, variables) => {
      setError('')
      setNotice(variables.status === 'in_transit' ? 'Delivery is in transit. The recipient has received a verification code.' : 'Delivery status updated.')
      await refreshDeliveries()
    },
    onError: (requestError) => setError(apiErrorMessage(requestError, 'Could not update delivery status.')),
  })
  const shareLocation = useMutation({
    mutationFn: async (orderId) => {
      if (!navigator.geolocation) throw new Error('Location sharing is not supported by this browser.')
      const position = await new Promise((resolve, reject) => navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }))
      return (await api.post('/rider/location', {
        order_id: orderId,
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
      })).data
    },
    onSuccess: () => { setError(''); setNotice('Your latest location has been shared with the customer.') },
    onError: (requestError) => setError(apiErrorMessage(requestError, requestError.message || 'Could not share your location.')),
  })
  const activeCount = (deliveriesQuery.data || []).filter((item) => item.assignment_status === 'accepted').length

  return (
    <section className="mx-auto max-w-5xl">
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-sm font-semibold text-blue-700">Rider workspace</p><h1 className="mt-1 text-3xl font-black tracking-tight text-slate-950">Today’s deliveries</h1><p className="mt-2 text-sm text-slate-500">Your route, handoffs, and active assignments in one place.</p></div>
        <div className="rounded-2xl bg-blue-50 px-4 py-3"><p className="text-xs text-blue-700">Active deliveries</p><p className="mt-0.5 text-xl font-black text-blue-950">{activeCount}</p></div>
      </div>
      {error && <p className="mb-4 rounded-xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p>}
      {notice && <p className="mb-4 rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{notice}</p>}
      {deliveriesQuery.error && <p className="mb-4 rounded-xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700">Could not load your assignments. Refresh the page to try again.</p>}
      {deliveriesQuery.isLoading ? <p className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">Loading your deliveries…</p> : deliveriesQuery.data?.length ? (
        <div className="grid gap-4">
          {deliveriesQuery.data.map((assignment) => {
            const order = assignment.order
            const status = order?.current_status
            const busy = respond.isPending || updateStatus.isPending || shareLocation.isPending
            return (
              <article className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm" key={assignment.id}>
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4 sm:px-6">
                  <div><p className="text-xs font-semibold uppercase tracking-widest text-slate-400">Delivery task</p><h2 className="mt-1 font-bold text-slate-950">{order?.tracking_number || `Order ${assignment.order_id}`}</h2></div>
                  <div className="flex items-center gap-2"><StatusBadge status={status} /><span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${assignment.assignment_status === 'pending' ? 'bg-amber-50 text-amber-800' : 'bg-slate-100 text-slate-600'}`}>{assignment.assignment_status} assignment</span></div>
                </div>
                <div className="grid gap-5 px-5 py-5 sm:px-6 lg:grid-cols-[1fr_auto] lg:items-center">
                  <div className="space-y-4">
                    <Stop label="Pickup" address={order?.pickup_address} tone="pickup" />
                    <Stop label="Deliver to" address={order?.destination_address} tone="destination" />
                    <div className="rounded-2xl bg-slate-50 p-3.5"><p className="text-xs font-semibold text-slate-500">Package</p><p className="mt-1 text-sm leading-5 text-slate-800">{order?.package_description}</p><p className="mt-2 text-xs text-slate-500">Recipient: {order?.recipient_name} · {order?.recipient_phone}</p></div>
                  </div>
                  <div className="flex flex-wrap gap-2 lg:max-w-52 lg:justify-end">
                    {assignment.assignment_status === 'pending' && (
                      <>
                        <button className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-bold text-white hover:bg-blue-700 disabled:opacity-50" disabled={busy} onClick={() => respond.mutate({ assignmentId: assignment.id, decision: 'accept' })} type="button">Accept delivery</button>
                        <button className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50" disabled={busy} onClick={() => respond.mutate({ assignmentId: assignment.id, decision: 'reject' })} type="button">Decline</button>
                      </>
                    )}
                    {assignment.assignment_status === 'accepted' && status === 'accepted' && <StatusAction label="Mark picked up" busy={busy} onClick={() => updateStatus.mutate({ orderId: assignment.order_id, status: 'picked_up' })} />}
                    {assignment.assignment_status === 'accepted' && status === 'picked_up' && <StatusAction label="Start delivery" busy={busy} onClick={() => updateStatus.mutate({ orderId: assignment.order_id, status: 'in_transit' })} />}
                    {assignment.assignment_status === 'accepted' && status === 'in_transit' && <button className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-bold text-white hover:bg-emerald-700" onClick={() => { setError(''); setProofOrder({ id: assignment.order_id, tracking: order?.tracking_number }) }} type="button"><ShieldCheck size={17} /> Verify delivery</button>}
                    {assignment.assignment_status === 'accepted' && ['accepted', 'picked_up', 'in_transit'].includes(status) && <button className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-700 hover:border-blue-200 hover:text-blue-700 disabled:opacity-50" disabled={shareLocation.isPending} onClick={() => shareLocation.mutate(assignment.order_id)} type="button"><MapPin size={16} />{shareLocation.isPending ? 'Sharing…' : 'Share my location'}</button>}
                    {assignment.assignment_status === 'completed' && <p className="w-full rounded-xl bg-emerald-50 px-4 py-3 text-center text-sm font-semibold text-emerald-800">Delivery completed</p>}
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      ) : <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center"><Truck className="mx-auto text-slate-300" size={34} /><p className="mt-3 font-semibold text-slate-700">No assignments yet</p><p className="mt-1 text-sm text-slate-500">New delivery tasks will appear here when dispatch assigns them.</p></div>}

      {proofOrder && <ProofModal order={proofOrder} onClose={() => setProofOrder(null)} onError={setError} onSuccess={async () => { setProofOrder(null); setError(''); setNotice('Delivery verified and marked complete.'); await refreshDeliveries() }} />}
    </section>
  )
}

function Stop({ label, address, tone }) {
  return <div className="flex items-start gap-3"><span className={`mt-0.5 grid size-8 shrink-0 place-items-center rounded-xl ${tone === 'pickup' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}><MapPin size={16} /></span><div><p className="text-xs font-semibold text-slate-500">{label}</p><p className="mt-1 text-sm font-medium leading-5 text-slate-800">{address || 'Address not available'}</p></div></div>
}

function StatusAction({ label, busy, onClick }) {
  return <button className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-bold text-white hover:bg-blue-700 disabled:opacity-50" disabled={busy} onClick={onClick} type="button"><PackageCheck size={17} />{busy ? 'Updating…' : label}</button>
}

function ProofModal({ order, onClose, onError, onSuccess }) {
  const [code, setCode] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [requestError, setRequestError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setRequestError('')
    onError('')
    setSubmitting(true)
    try {
      await api.post(`/rider/orders/${order.id}/proof`, {
        verification_code: code,
        image_url: imageUrl,
      })
      await onSuccess()
    } catch (requestErrorResponse) {
      const message = apiErrorMessage(requestErrorResponse, 'Could not verify this delivery.')
      setRequestError(message)
      onError(message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[1000] grid place-items-center bg-slate-950/50 p-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <section aria-labelledby="proof-title" aria-modal="true" className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl sm:p-7" role="dialog">
        <span className="grid size-12 place-items-center rounded-2xl bg-emerald-50 text-emerald-700"><ShieldCheck size={23} /></span>
        <h2 className="mt-4 text-xl font-black text-slate-950" id="proof-title">Verify handoff</h2>
        <p className="mt-1 text-sm text-slate-500">Ask the recipient for the 6-digit code. Order {order.tracking}.</p>
        <form className="mt-5 space-y-4" onSubmit={submit}>
          <label className="block text-sm font-semibold text-slate-700">Recipient verification code<input autoComplete="one-time-code" className="form-input mt-1.5 text-center text-2xl font-black tracking-[0.35em]" inputMode="numeric" maxLength={6} minLength={6} onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))} pattern="[0-9]{6}" placeholder="000000" required value={code} /></label>
          <label className="block text-sm font-semibold text-slate-700">Proof photo URL<input className="form-input mt-1.5" onChange={(event) => setImageUrl(event.target.value)} placeholder="https://…" required type="url" value={imageUrl} /></label>
          <p className="text-xs leading-5 text-slate-500">The API requires a proof image URL and the recipient code. Use an approved image link; image upload is not provided by the current backend.</p>
          {requestError && <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{requestError}</p>}
          <div className="flex gap-2 pt-1"><button className="flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-600" onClick={onClose} type="button">Cancel</button><button className="flex-1 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-50" disabled={submitting} type="submit">{submitting ? 'Verifying…' : 'Confirm delivery'}</button></div>
        </form>
      </section>
    </div>
  )
}
