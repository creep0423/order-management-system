import type { OrderApiError } from '../services/orders'

interface LoadingStateProps {
  label: string
}

export function LoadingState({ label }: LoadingStateProps) {
  return (
    <section className="state-panel" aria-live="polite" aria-busy="true">
      <span className="loading-indicator" aria-hidden="true" />
      <h2>{label}</h2>
      <p>Retrieving current data from the order service.</p>
    </section>
  )
}

interface ErrorStateProps {
  error: OrderApiError
  onRetry: () => void
  onBack?: () => void
}

export function ErrorState({ error, onRetry, onBack }: ErrorStateProps) {
  const notFound = error.status === 404
  const title = notFound
    ? 'Order not found'
    : error.kind === 'disconnected'
      ? 'Backend disconnected'
      : 'Unable to load order data'

  return (
    <section className="state-panel state-panel--error" role="alert">
      <div className="state-icon" aria-hidden="true">!</div>
      <h2>{title}</h2>
      <p>{error.message}</p>
      <div className="state-actions">
        <button className="button button--primary" type="button" onClick={onRetry}>
          Retry
        </button>
        {onBack ? (
          <button className="button button--secondary" type="button" onClick={onBack}>
            Back to orders
          </button>
        ) : null}
      </div>
    </section>
  )
}

interface EmptyStateProps {
  filtered: boolean
  onClear?: () => void
}

export function EmptyState({ filtered, onClear }: EmptyStateProps) {
  return (
    <section className="state-panel" aria-live="polite">
      <div className="state-icon state-icon--neutral" aria-hidden="true">0</div>
      <h2>{filtered ? 'No matching orders' : 'No orders available'}</h2>
      <p>
        {filtered
          ? 'No orders match the current search and status filters.'
          : 'The order service returned an empty order list.'}
      </p>
      {filtered && onClear ? (
        <button className="button button--secondary" type="button" onClick={onClear}>
          Clear filters
        </button>
      ) : null}
    </section>
  )
}
