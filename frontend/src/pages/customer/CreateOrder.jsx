import { useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, MapPin, Package, Route } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { DeliveryMap } from '../../components/DeliveryMap.jsx'
import api, { apiErrorMessage } from '../../services/api.js'

const BASE_FEE = 5
const RATE_PER_KM = 1.5

function distanceInKm(start, end) {
  if (!start || !end) return 0
  const radians = (degrees) => degrees * Math.PI / 180
  const latitudeDelta = radians(end.latitude - start.latitude)
  const longitudeDelta = radians(end.longitude - start.longitude)
  const a = Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(radians(start.latitude)) * Math.cos(radians(end.latitude))
    * Math.sin(longitudeDelta / 2) ** 2
  return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

export function CreateOrder() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activePoint, setActivePoint] = useState('pickup')
  const [coordinates, setCoordinates] = useState({ pickup: null, destination: null })
  const [form, setForm] = useState({
    pickup_address: '',
    destination_address: '',
    recipient_name: '',
    recipient_phone: '',
    package_description: '',
  })
  const [error, setError] = useState('')
  const distance = useMemo(() => distanceInKm(coordinates.pickup, coordinates.destination), [coordinates])
  const deliveryFee = coordinates.pickup && coordinates.destination
    ? (BASE_FEE + distance * RATE_PER_KM).toFixed(2)
    : ''

  const createOrder = useMutation({
    mutationFn: async (payload) => (await api.post('/orders', payload)).data,
    onSuccess: async (order) => {
      await queryClient.invalidateQueries({ queryKey: ['customer-orders'] })
      navigate(`/customer/track/${order.id}`, { replace: true })
    },
    onError: (requestError) => {
      setError(apiErrorMessage(requestError, 'We could not create your delivery. Please try again.'))
    },
  })

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  function selectMapPoint(point) {
    setCoordinates((current) => ({ ...current, [activePoint]: point }))
  }

  function submit(event) {
    event.preventDefault()
    setError('')
    if (!coordinates.pickup || !coordinates.destination) {
      setError('Select both pickup and destination points on the map.')
      return
    }
    createOrder.mutate({
      ...form,
      pickup_latitude: coordinates.pickup.latitude,
      pickup_longitude: coordinates.pickup.longitude,
      destination_latitude: coordinates.destination.latitude,
      destination_longitude: coordinates.destination.longitude,
    })
  }

  const markers = [
    ...(coordinates.pickup ? [{ id: 'pickup', type: 'pickup', position: [coordinates.pickup.latitude, coordinates.pickup.longitude], label: 'Pickup point' }] : []),
    ...(coordinates.destination ? [{ id: 'destination', type: 'destination', position: [coordinates.destination.latitude, coordinates.destination.longitude], label: 'Delivery destination' }] : []),
  ]

  return (
    <section className="mx-auto max-w-6xl">
      <Link className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-700" to="/customer">
        <ArrowLeft size={16} /> Back to deliveries
      </Link>
      <div className="mb-7 mt-5">
        <p className="text-sm font-semibold text-blue-700">New delivery</p>
        <h1 className="mt-1 text-3xl font-black tracking-tight text-slate-950">Where are we going?</h1>
        <p className="mt-2 text-slate-500">Add the package details and choose both stops on the map.</p>
      </div>

      <form className="grid gap-6 xl:grid-cols-[1fr_0.95fr]" onSubmit={submit}>
        <div className="space-y-5">
          <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="mb-5 flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl bg-blue-50 text-blue-700"><MapPin size={19} /></span>
              <div><h2 className="font-bold text-slate-900">Route details</h2><p className="text-sm text-slate-500">Enter addresses, then pinpoint each stop.</p></div>
            </div>
            <div className="space-y-4">
              <label className="block text-sm font-semibold text-slate-700">
                Pickup address
                <input className="form-input" name="pickup_address" onChange={updateField} placeholder="Street, neighborhood, city" required value={form.pickup_address} />
              </label>
              <label className="block text-sm font-semibold text-slate-700">
                Destination address
                <input className="form-input" name="destination_address" onChange={updateField} placeholder="Street, neighborhood, city" required value={form.destination_address} />
              </label>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              {[
                { id: 'pickup', text: 'Set pickup on map' },
                { id: 'destination', text: 'Set destination on map' },
              ].map(({ id, text }) => (
                <button className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${activePoint === id ? 'border-blue-600 bg-blue-600 text-white' : 'border-slate-200 bg-white text-slate-600 hover:border-blue-300'}`} key={id} onClick={() => setActivePoint(id)} type="button">
                  {text}
                </button>
              ))}
            </div>
            <p className="mt-3 text-xs text-slate-500">
              {coordinates[activePoint] ? `${activePoint === 'pickup' ? 'Pickup' : 'Destination'} pinned. Click to adjust.` : `Click the map to place the ${activePoint === 'pickup' ? 'pickup' : 'destination'} pin.`}
            </p>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="mb-5 flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl bg-amber-50 text-amber-700"><Package size={19} /></span>
              <div><h2 className="font-bold text-slate-900">Package & recipient</h2><p className="text-sm text-slate-500">Help the rider complete a smooth handoff.</p></div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-sm font-semibold text-slate-700">
                Recipient name
                <input className="form-input" maxLength={120} name="recipient_name" onChange={updateField} required value={form.recipient_name} />
              </label>
              <label className="block text-sm font-semibold text-slate-700">
                Recipient phone
                <input className="form-input" maxLength={30} name="recipient_phone" onChange={updateField} required type="tel" value={form.recipient_phone} />
              </label>
            </div>
            <label className="mt-4 block text-sm font-semibold text-slate-700">
              Package description
              <textarea className="form-input min-h-24 resize-y" maxLength={2000} name="package_description" onChange={updateField} placeholder="What are we delivering?" required value={form.package_description} />
            </label>
          </div>
        </div>

        <div className="space-y-5">
          <div className="rounded-3xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
            <div className="flex items-center justify-between px-2 pb-3 pt-1">
              <div><h2 className="font-bold text-slate-900">Choose your stops</h2><p className="mt-1 text-xs text-slate-500">Map centered on Accra · click to pin</p></div>
              <Route className="text-blue-600" size={20} />
            </div>
            <DeliveryMap markers={markers} onMapClick={selectMapPoint} className="h-[360px]" />
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 px-2 text-xs font-medium text-slate-600">
              <span className="inline-flex items-center gap-2"><i className="size-2.5 rounded-full bg-emerald-500" /> Pickup</span>
              <span className="inline-flex items-center gap-2"><i className="size-2.5 rounded-full bg-rose-500" /> Destination</span>
            </div>
          </div>
          <div className="rounded-3xl bg-slate-950 p-6 text-white shadow-lg">
            <div className="flex items-center justify-between">
              <div><p className="text-sm text-slate-400">Estimated delivery fee</p><p className="mt-2 text-3xl font-black">{deliveryFee ? `GH₵ ${deliveryFee}` : '—'}</p></div>
              <span className="grid size-12 place-items-center rounded-2xl bg-white/10 text-blue-300"><ArrowRight size={22} /></span>
            </div>
            <p className="mt-3 text-xs leading-5 text-slate-400">
              {deliveryFee ? `Approx. ${distance.toFixed(1)} km direct distance. Estimate: GH₵ ${BASE_FEE.toFixed(2)} base + GH₵ ${RATE_PER_KM.toFixed(2)}/km; the server calculates the final fee.` : 'Pin both locations to calculate a distance-based estimate.'}
            </p>
            {error && <p className="mt-4 rounded-xl bg-rose-500/15 px-3 py-2 text-sm text-rose-200">{error}</p>}
            <button className="mt-5 w-full rounded-xl bg-blue-500 px-5 py-3.5 font-bold text-white transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-50" disabled={createOrder.isPending} type="submit">
              {createOrder.isPending ? 'Creating delivery…' : 'Confirm delivery request'}
            </button>
          </div>
        </div>
      </form>
      <p className="mx-auto mt-5 max-w-5xl text-center text-xs text-slate-400">The displayed amount is an estimate based on straight-line distance. The server independently calculates the final delivery fee when you submit.</p>
    </section>
  )
}
