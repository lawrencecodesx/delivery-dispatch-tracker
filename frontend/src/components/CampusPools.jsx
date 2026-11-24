import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Clock3, MapPin, Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import api, { apiErrorMessage } from '../services/api.js'

function poolItems(data) {
  return Array.isArray(data) ? data : data?.pools ?? data?.items ?? []
}

function countdown(deadline, now) {
  if (!deadline) return null
  const remaining = new Date(deadline).getTime() - now
  if (!Number.isFinite(remaining)) return null
  if (remaining <= 0) return 'Closed'
  const hours = Math.floor(remaining / 3600000)
  const minutes = Math.floor((remaining % 3600000) / 60000)
  const seconds = Math.floor((remaining % 60000) / 1000)
  return hours ? `${hours}h ${minutes}m` : `${minutes}m ${seconds}s`
}

function PoolCard({ pool, onJoin, joining, joined }) {
  const [now, setNow] = useState(0)
  const [open, setOpen] = useState(false)
  const [pickup, setPickup] = useState({ address: '', latitude: '', longitude: '' })
  const [recipient, setRecipient] = useState({ name: '', phone: '', description: '' })
  const [cargoTier, setCargoTier] = useState('STANDARD')
  const [locationError, setLocationError] = useState('')
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])
  const timeLeft = now ? countdown(pool.expires_at, now) : null
  const fee = pool.split_fee_ghs
  const rebate = fee == null ? null : Number(fee) * 0.25
  const expired = timeLeft === 'Closed' || String(pool.status).toLowerCase() !== 'open'

  async function useCurrentLocation() {
    setLocationError('')
    if (!navigator.geolocation) {
      setLocationError('Location access is not supported by this browser.')
      return
    }
    try {
      const position = await new Promise((resolve, reject) => navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 12000 }))
      setPickup((current) => ({ ...current, latitude: String(position.coords.latitude), longitude: String(position.coords.longitude) }))
    } catch {
      setLocationError('Could not read your location. You can enter the coordinates manually.')
    }
  }

  function submit(event) {
    event.preventDefault()
    onJoin(pool.id, {
      pickup_address: pickup.address,
      pickup_latitude: Number(pickup.latitude),
      pickup_longitude: Number(pickup.longitude),
      recipient_name: recipient.name,
      recipient_phone: recipient.phone,
      package_description: recipient.description,
      cargo_tier: cargoTier,
      ...(cargoTier === 'COLD_CHAIN' ? { max_temp_c: 8 } : {}),
    })
  }

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><h3 className="font-bold text-slate-900">{pool.zone_name || pool.name || `Campus pool ${pool.id}`}</h3><p className="mt-1 text-sm text-slate-500">Shared drop-off · {Number(pool.dropoff_lat).toFixed(4)}, {Number(pool.dropoff_lng).toFixed(4)}</p></div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700"><Users size={13} />{pool.participant_count} participants</span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Current participant fee</p><p className="mt-1 font-bold text-slate-900">{fee == null ? '—' : `GH₵ ${Number(fee).toFixed(2)}`}</p></div>
        <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Potential SLA rebate</p><p className="mt-1 font-bold text-slate-900">{rebate == null ? '—' : `Up to GH₵ ${rebate.toFixed(2)}`}</p></div>
      </div>
      <p className={`mt-3 flex items-center gap-2 text-xs font-semibold ${expired ? 'text-rose-700' : 'text-amber-700'}`}><Clock3 size={14} />{expired ? 'Pool is closed' : `Pool closes in ${timeLeft || '…'}`}</p>
      {joined ? <p className="mt-4 rounded-xl bg-emerald-50 px-4 py-2.5 text-center text-sm font-bold text-emerald-800">You joined this pool</p> : !open ? (
        <button className="mt-4 w-full rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50" disabled={joining || expired} onClick={() => setOpen(true)} type="button">Join campus pool</button>
      ) : (
        <form className="mt-4 space-y-3 border-t border-slate-100 pt-4" onSubmit={submit}>
          <label className="block text-xs font-semibold text-slate-600">Pickup address<input className="form-input mt-1" minLength={3} onChange={(event) => setPickup((current) => ({ ...current, address: event.target.value }))} required value={pickup.address} /></label>
          <div className="grid grid-cols-2 gap-2">
            <label className="block text-xs font-semibold text-slate-600">Pickup latitude<input className="form-input mt-1" max="90" min="-90" onChange={(event) => setPickup((current) => ({ ...current, latitude: event.target.value }))} required step="any" type="number" value={pickup.latitude} /></label>
            <label className="block text-xs font-semibold text-slate-600">Pickup longitude<input className="form-input mt-1" max="180" min="-180" onChange={(event) => setPickup((current) => ({ ...current, longitude: event.target.value }))} required step="any" type="number" value={pickup.longitude} /></label>
          </div>
          <button className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-700" onClick={useCurrentLocation} type="button"><MapPin size={14} /> Use my current location</button>
          {locationError && <p className="text-xs text-rose-700" role="alert">{locationError}</p>}
          <div className="grid grid-cols-2 gap-2">
            <label className="block text-xs font-semibold text-slate-600">Recipient name<input className="form-input mt-1" maxLength={120} minLength={1} onChange={(event) => setRecipient((current) => ({ ...current, name: event.target.value }))} required value={recipient.name} /></label>
            <label className="block text-xs font-semibold text-slate-600">Recipient phone<input className="form-input mt-1" maxLength={30} minLength={5} onChange={(event) => setRecipient((current) => ({ ...current, phone: event.target.value }))} required value={recipient.phone} /></label>
          </div>
          <label className="block text-xs font-semibold text-slate-600">Package description<textarea className="form-input mt-1" maxLength={2000} minLength={1} onChange={(event) => setRecipient((current) => ({ ...current, description: event.target.value }))} required value={recipient.description} /></label>
          <label className="block text-xs font-semibold text-slate-600">Cargo tier<select className="form-input mt-1" onChange={(event) => setCargoTier(event.target.value)} value={cargoTier}><option value="STANDARD">Standard</option><option value="COLD_CHAIN">Cold chain</option><option value="FRAGILE">Fragile</option></select></label>
          <div className="flex gap-2"><button className="flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600" onClick={() => setOpen(false)} type="button">Cancel</button><button className="flex-1 rounded-xl bg-blue-600 px-3 py-2 text-sm font-bold text-white disabled:opacity-50" disabled={joining || expired} type="submit">{joining ? 'Joining…' : `Join · GH₵ ${fee == null ? '—' : Number(fee).toFixed(2)}`}</button></div>
        </form>
      )}
    </article>
  )
}

export function CampusPools() {
  const client = useQueryClient()
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [joinedOrder, setJoinedOrder] = useState(null)
  const [joinedPoolId, setJoinedPoolId] = useState(null)
  const query = useQuery({
    queryKey: ['campus-pools'],
    queryFn: async () => (await api.get('/pools')).data,
    refetchInterval: 30000,
    retry: false,
  })
  const join = useMutation({
    mutationFn: async ({ poolId, payload }) => (await api.post(`/pools/${poolId}/join`, payload)).data,
    onSuccess: async (result, variables) => {
      setError('')
      setJoinedOrder(result)
      setJoinedPoolId(variables.poolId)
      setMessage(`Joined the pool. Your participant fee is GH₵ ${Number(result.split_fee_ghs).toFixed(2)}. Delivery OTP: ${result.verification_otp}.`)
      await Promise.all([
        client.invalidateQueries({ queryKey: ['campus-pools'] }),
        client.invalidateQueries({ queryKey: ['customer-orders'] }),
      ])
    },
    onError: (requestError) => {
      setMessage('')
      setError(apiErrorMessage(requestError, 'Could not join this pool. Please refresh and try again.'))
    },
  })
  const pools = poolItems(query.data).filter((pool) => String(pool.status).toLowerCase() === 'open')

  return (
    <section className="mt-7 rounded-3xl border border-slate-200 bg-slate-50 p-5 sm:p-6">
      <div className="mb-4"><p className="text-xs font-bold uppercase tracking-widest text-blue-700">Share a route</p><h2 className="mt-1 text-xl font-black text-slate-950">Active Campus Drop-Pools (Split Fee)</h2><p className="mt-1 text-sm text-slate-500">Join a group delivery to split the fee. The potential rebate is 25% of your share if the SLA is missed.</p></div>
      {message && <p className="mb-3 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800" role="status">{message}{joinedOrder && <> · <Link className="font-bold underline" to={`/customer/track/${joinedOrder.order_id}`}>Track {joinedOrder.tracking_number}</Link></>}</p>}
      {error && <p className="mb-3 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">{error}</p>}
      {query.isError ? <p className="rounded-xl bg-white p-4 text-sm text-slate-500">Campus pools are unavailable right now.</p> : query.isLoading ? <p className="text-sm text-slate-500">Loading active campus pools…</p> : pools.length ? (
        <div className="grid gap-3 md:grid-cols-2">{pools.map((pool) => <PoolCard joined={joinedPoolId === pool.id} joining={join.isPending} key={pool.id} onJoin={(poolId, payload) => join.mutate({ poolId, payload })} pool={pool} />)}</div>
      ) : <p className="rounded-xl bg-white p-4 text-sm text-slate-500">No active campus pools at the moment.</p>}
    </section>
  )
}
