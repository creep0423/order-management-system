import { useEffect, useMemo, useRef, useState } from 'react'

import { EmptyState, ErrorState, LoadingState } from '../components/AsyncState'
import { OrderFilters } from '../components/OrderFilters'
import { OrderTable } from '../components/OrderTable'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { useOrders } from '../hooks/useOrders'
import { APP_NAME } from '../utils/appMetadata'

interface OrdersPageProps {
  focusRequest: number
  onOpenOrder: (orderNumber: string) => void
}

export function OrdersPage({ focusRequest, onOpenOrder }: OrdersPageProps) {
  useDocumentTitle(`Orders | ${APP_NAME}`)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const [retryKey, setRetryKey] = useState(0)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('')
  const { orders, loading, error } = useOrders(retryKey)

  useEffect(() => {
    if (focusRequest > 0) {
      headingRef.current?.focus()
    }
  }, [focusRequest])

  const statuses = useMemo(
    () => [...new Set(orders.map((order) => order.status))].sort(),
    [orders],
  )
  const filteredOrders = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase('en-AU')
    return orders.filter((order) => {
      const matchesQuery =
        normalizedQuery.length === 0 ||
        order.order_number.toLocaleLowerCase('en-AU').includes(normalizedQuery) ||
        order.company.toLocaleLowerCase('en-AU').includes(normalizedQuery)
      const matchesStatus = status.length === 0 || order.status === status
      return matchesQuery && matchesStatus
    })
  }, [orders, query, status])

  function clearFilters() {
    setQuery('')
    setStatus('')
  }

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="eyebrow">Order operations</p>
          <h1 ref={headingRef} tabIndex={-1}>Orders</h1>
          <p>Review current orders, pricing, and shipping quote availability.</p>
        </div>
        {!loading && !error ? (
          <div className="record-count" aria-live="polite">
            <strong>{filteredOrders.length}</strong>
            <span>of {orders.length} orders</span>
          </div>
        ) : null}
      </section>

      {loading ? <LoadingState label="Loading orders" /> : null}
      {!loading && error ? (
        <ErrorState error={error} onRetry={() => setRetryKey((key) => key + 1)} />
      ) : null}
      {!loading && !error && orders.length === 0 ? <EmptyState filtered={false} /> : null}
      {!loading && !error && orders.length > 0 ? (
        <>
          <OrderFilters
            query={query}
            status={status}
            statuses={statuses}
            onQueryChange={setQuery}
            onStatusChange={setStatus}
            onClear={clearFilters}
          />
          {filteredOrders.length > 0 ? (
            <OrderTable orders={filteredOrders} onOpenOrder={onOpenOrder} />
          ) : (
            <EmptyState filtered />
          )}
        </>
      ) : null}
    </>
  )
}
