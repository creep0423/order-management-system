import type { ShippingQuote } from '../types/orders'
import { formatCheckedAt } from '../utils/formatters'
import { MoneyDisplay } from './MoneyDisplay'
import { StatusBadge } from './StatusBadge'

interface ShippingQuotePanelProps {
  quote: ShippingQuote
}

export function ShippingQuotePanel({ quote }: ShippingQuotePanelProps) {
  return (
    <section className="shipping-panel" aria-labelledby="shipping-quote-heading">
      <div className="shipping-panel__header">
        <div>
          <p className="section-kicker">Shipping quote</p>
          <h2 id="shipping-quote-heading">Shipping quote integration not implemented</h2>
        </div>
        <StatusBadge status={quote.status} />
      </div>
      <div className="shipping-panel__body">
        <div>
          <span>Quoted fee</span>
          <strong>{quote.quoted_fee ? <MoneyDisplay money={quote.quoted_fee} /> : 'Not available'}</strong>
        </div>
        <div>
          <span>Applied to order</span>
          <strong><MoneyDisplay money={quote.applied_fee} /></strong>
        </div>
        <div>
          <span>System check</span>
          <strong>{formatCheckedAt(quote.checked_at)}</strong>
        </div>
      </div>
      <div className="shipping-warning" role="note">
        <strong>Real shipping quotes are not implemented yet.</strong>
        <p>
          A$0.00 is the fallback amount used for this order calculation. It does not mean
          a carrier offered free shipping. Carrier integration is planned for Phase 6.
        </p>
        <span>Reason: {quote.reason_code}</span>
      </div>
    </section>
  )
}
