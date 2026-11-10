const STATUS_STYLES = {
  pending: 'status-pending',
  confirmed: 'status-confirmed',
  assigned: 'status-assigned',
  accepted: 'status-accepted',
  picked_up: 'status-picked-up',
  in_transit: 'status-in-transit',
  delivered: 'status-delivered',
  failed: 'status-failed',
  returned: 'status-returned',
  cancelled: 'status-cancelled',
  rejected: 'status-rejected',
}

export function StatusBadge({ status }) {
  const normalized = String(status || 'unknown').toLowerCase()
  const label = normalized.replaceAll('_', ' ')
  const styles = STATUS_STYLES[normalized] || 'status-unknown'

  return (
    <span className={`status-badge inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${styles}`}>
      {label}
    </span>
  )
}
