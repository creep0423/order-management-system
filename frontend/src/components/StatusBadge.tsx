import { formatStatus } from '../utils/formatters'

interface StatusBadgeProps {
  status: string
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalizedStatus = status.toLowerCase().replaceAll('_', '-')

  return (
    <span className={`status-badge status-badge--${normalizedStatus}`}>
      {formatStatus(status)}
    </span>
  )
}
