import type { OrderDetail } from '../types/orders'
import { MoneyDisplay } from './MoneyDisplay'

interface PricingSummaryProps {
  order: OrderDetail
}

export function PricingSummary({ order }: PricingSummaryProps) {
  return (
    <section className="pricing-card" aria-labelledby="pricing-heading">
      <div className="section-heading section-heading--compact">
        <div>
          <p className="section-kicker">API-calculated</p>
          <h2 id="pricing-heading">Order summary</h2>
        </div>
      </div>
      <dl className="pricing-list">
        <div>
          <dt>Order subtotal <span>ex. GST</span></dt>
          <dd><MoneyDisplay money={order.pricing.order_subtotal} /></dd>
        </div>
        <div>
          <dt>GST amount</dt>
          <dd><MoneyDisplay money={order.pricing.gst_amount} /></dd>
        </div>
        <div>
          <dt>Shipment fee <span>degraded amount</span></dt>
          <dd><MoneyDisplay money={order.shipping_quote.applied_fee} /></dd>
        </div>
        <div className="pricing-total">
          <dt>Order total</dt>
          <dd><MoneyDisplay money={order.pricing.order_total} emphasis /></dd>
        </div>
      </dl>
      <p className="context-note">
        Prices are displayed exactly as supplied by the backend. The frontend does not
        recalculate item prices, GST, shipment fees, or the order total.
      </p>
    </section>
  )
}
