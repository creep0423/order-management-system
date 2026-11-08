import { useEffect, useRef, useState } from 'react'

import { ErrorState, LoadingState } from '../components/AsyncState'
import { InfoCard } from '../components/InfoCard'
import { OrderItemsTable } from '../components/OrderItemsTable'
import { PackagePanel } from '../components/PackagePanel'
import { PricingSummary } from '../components/PricingSummary'
import { ShippingQuotePanel } from '../components/ShippingQuotePanel'
import { StatusBadge } from '../components/StatusBadge'
import { TrackingPanel } from '../components/TrackingPanel'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { useOrderDetail } from '../hooks/useOrderDetail'
import { APP_NAME } from '../utils/appMetadata'
import { formatOrderDate } from '../utils/formatters'

interface OrderDetailPageProps {
  orderNumber: string
  focusRequest: number
  onBack: () => void
}

export function OrderDetailPage({
  orderNumber,
  focusRequest,
  onBack,
}: OrderDetailPageProps) {
  const [retryKey, setRetryKey] = useState(0)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const { order, loading, error } = useOrderDetail(orderNumber, retryKey)
  useDocumentTitle(`${order?.order_number ?? 'Order detail'} | ${APP_NAME}`)

  useEffect(() => {
    if (focusRequest > 0 && order !== null) {
      headingRef.current?.focus()
    }
  }, [focusRequest, order])

  if (loading) {
    return (
      <>
        <button className="back-link" type="button" onClick={onBack}>← Back to orders</button>
        <LoadingState label="Loading order details" />
      </>
    )
  }

  if (error) {
    return (
      <ErrorState
        error={error}
        onRetry={() => setRetryKey((key) => key + 1)}
        onBack={onBack}
      />
    )
  }

  if (!order) {
    return null
  }

  const address = order.shipping_address

  return (
    <>
      <button className="back-link" type="button" onClick={onBack}>← Back to orders</button>
      <section className="detail-hero">
        <div>
          <p className="eyebrow">Order detail</p>
          <h1 ref={headingRef} tabIndex={-1}>{order.order_number}</h1>
          <p>{order.company}</p>
        </div>
        <StatusBadge status={order.status} />
      </section>

      <section className="metadata-strip" aria-label="Order metadata">
        <div><span>Order date</span><strong>{formatOrderDate(order.order_date)}</strong></div>
        <div><span>Company</span><strong>{order.company}</strong></div>
        <div><span>Currency</span><strong>{order.currency}</strong></div>
        <div><span>Order status</span><strong>{order.status}</strong></div>
      </section>

      <div className="info-grid">
        <InfoCard title="Customer">
          <dl className="detail-list">
            <div><dt>Name</dt><dd>{order.customer.name}</dd></div>
            <div><dt>Phone</dt><dd>{order.customer.phone}</dd></div>
            <div><dt>Email</dt><dd>{order.customer.email}</dd></div>
          </dl>
        </InfoCard>
        <InfoCard title="Shipping address">
          <address>
            {address.line1}<br />
            {address.suburb} {address.state} {address.postcode}<br />
            {address.country}
          </address>
        </InfoCard>
      </div>

      <OrderItemsTable items={order.items} />

      <PackagePanel estimation={order.package_estimation} />

      <TrackingPanel results={order.tracking_results} />

      <div className="summary-grid">
        <ShippingQuotePanel quote={order.shipping_quote} />
        <PricingSummary order={order} />
      </div>
    </>
  )
}
