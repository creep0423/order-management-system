import type { Money } from '../types/orders'

const ZERO_AMOUNT_PATTERN = /^-?0+(?:\.0+)?$/

export function formatMoney(money: Money): string {
  const amount = ZERO_AMOUNT_PATTERN.test(money.amount) ? '0.00' : money.amount
  return `A$${amount}`
}

export function formatOrderDate(isoDate: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate)
  if (!match) {
    return isoDate
  }

  const [, year, month, day] = match
  return `${day}/${month}/${year}`
}

export function formatCheckedAt(isoDateTime: string): string {
  const date = new Date(isoDateTime)
  if (Number.isNaN(date.getTime())) {
    return 'Unavailable'
  }

  return new Intl.DateTimeFormat('en-AU', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
    timeZoneName: 'short',
  }).format(date)
}

export function formatStatus(value: string): string {
  return value
    .trim()
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

/**
 * Render an ETA without inventing a delivery estimate.
 *
 * `eta_days === null` means the source has no usable ETA, so the UI says so
 * instead of echoing raw source markers such as `nullDays`. When a value exists
 * it is shown exactly as provided: `0Days` has no confirmed business meaning yet
 * (open question), so it is neither interpreted nor rewritten.
 */
export function formatEta(etaDays: number | null, etaRaw: string): string {
  if (etaDays === null) {
    return 'ETA unavailable'
  }

  return `ETA: ${etaRaw.trim() === '' ? `${etaDays} days` : etaRaw}`
}
