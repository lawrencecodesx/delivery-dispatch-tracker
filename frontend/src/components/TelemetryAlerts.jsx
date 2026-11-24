import { useQueries, useQuery } from '@tanstack/react-query'
import { AlertTriangle, Activity } from 'lucide-react'
import api from '../services/api.js'

const ACTIVE_STATUSES = new Set(['assigned', 'accepted', 'picked_up', 'in_transit'])

export function TelemetryAlerts({ orders: providedOrders }) {
  const ordersQuery = useQuery({
    queryKey: ['telemetry-orders'],
    queryFn: async () => (await api.get('/orders', { params: { limit: 100 } })).data,
    enabled: !Array.isArray(providedOrders),
    refetchInterval: 30000,
    retry: false,
  })
  const orders = Array.isArray(providedOrders) ? providedOrders : ordersQuery.data || []
  const activeOrders = orders.filter((order) => ACTIVE_STATUSES.has(order.current_status)).slice(0, 30)
  const locations = useQueries({
    queries: activeOrders.map((order) => ({
      queryKey: ['order-tracking', order.id],
      queryFn: async () => (await api.get(`/tracking/${order.id}`)).data,
      refetchInterval: 30000,
      retry: false,
    })),
  })
  const alerts = locations.flatMap((locationQuery, index) => {
    const telemetry = locationQuery.data
    if (!telemetry) return []
    const order = activeOrders[index]
    const orderName = order.tracking_number || `Order ${order.id}`
    const messages = []
    if (telemetry.is_off_route) {
      messages.push({ id: `${order.id}-route`, text: `${orderName} is off route (${Math.round(telemetry.deviation_meters || 0)} m deviation).` })
    }
    if (order.is_compromised) {
      messages.push({ id: `${order.id}-temperature`, text: `${orderName} has a recorded cold-chain thermal breach.` })
    } else if (order.cargo_tier === 'COLD_CHAIN' && telemetry.temperature_c != null && order.max_temp_c != null && Number(telemetry.temperature_c) > Number(order.max_temp_c)) {
      messages.push({ id: `${order.id}-temperature`, text: `${orderName} temperature is ${telemetry.temperature_c}°C, above its ${order.max_temp_c}°C cargo limit.` })
    }
    return messages
  })

  if (!alerts.length) return null

  return (
    <section aria-label="Telemetry anomaly alerts" className="mb-5 rounded-2xl border border-rose-300 bg-rose-50 p-4">
      <div className="flex items-start gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-rose-100 text-rose-700"><AlertTriangle size={18} /></span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2"><h2 className="font-bold text-rose-950">Telemetry & anomaly alerts</h2><Activity size={15} className="text-rose-700" /></div>
          <ul className="mt-2 space-y-2">{alerts.map((alert) => <li className="text-sm font-medium text-rose-900" key={alert.id}>{alert.text}</li>)}</ul>
        </div>
      </div>
    </section>
  )
}
