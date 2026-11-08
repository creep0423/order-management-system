import type { OrderItem } from '../types/orders'
import { formatEta } from '../utils/formatters'
import { MoneyDisplay } from './MoneyDisplay'
import { ProductPlaceholder } from './ProductPlaceholder'

interface OrderItemsTableProps {
  items: OrderItem[]
}

function descriptionCaveat(status: string): string | null {
  if (status === 'partial_needs_requery') {
    return 'Source description is possibly truncated and needs re-query'
  }

  return null
}

export function OrderItemsTable({ items }: OrderItemsTableProps) {
  return (
    <section className="detail-section" aria-labelledby="items-heading">
      <div className="section-heading">
        <div>
          <p className="section-kicker">Order contents</p>
          <h2 id="items-heading">Items</h2>
        </div>
        <p>{items.length} line {items.length === 1 ? 'item' : 'items'}</p>
      </div>
      <div className="table-card">
        <div
          className="table-scroll"
          role="region"
          aria-label="Order items table"
          tabIndex={0}
        >
          <table className="items-table">
            <caption className="sr-only">
              Order item pricing supplied by the API. RRP is GST-inclusive.
            </caption>
            <colgroup>
              <col className="items-table__product-column" />
              <col className="items-table__sku-column" />
              <col className="items-table__tracking-column" />
              <col className="items-table__quantity-column" />
              <col className="items-table__money-column" />
              <col className="items-table__money-column" />
              <col className="items-table__money-column" />
            </colgroup>
            <thead>
              <tr>
                <th scope="col">Product</th>
                <th scope="col">SKU</th>
                <th scope="col">Tracking group</th>
                <th scope="col" className="number-cell">Quantity</th>
                <th scope="col" className="money-cell">RRP (incl. GST)</th>
                <th scope="col" className="money-cell">Unit price ex. GST</th>
                <th scope="col" className="money-cell">Line subtotal ex. GST</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => {
                const caveat = descriptionCaveat(item.product.description_status)

                return (
                  <tr key={`${item.sku}-${item.tracking_group_id}-${index}`}>
                    <td className="product-cell">
                      <div className="product-info">
                        <ProductPlaceholder />
                        <div className="product-info__content">
                          <strong>{item.product.product_name}</strong>
                          <span>{item.product.description ?? 'Description unavailable'}</span>
                          {caveat ? <span className="product-caveat">{caveat}</span> : null}
                          <span className="product-meta">
                            {item.product.size} · {formatEta(item.product.eta_days, item.product.eta_raw)}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="sku-cell"><code>{item.sku}</code></td>
                    <td className="tracking-group-cell">
                      <code>{item.tracking_group_id}</code>
                      <span className="cell-note">Internal group only</span>
                    </td>
                    <td className="number-cell">{item.quantity}</td>
                    <td className="money-cell">
                      <MoneyDisplay money={item.unit_price_incl_gst} />
                    </td>
                    <td className="money-cell">
                      <MoneyDisplay money={item.unit_price_ex_gst} />
                    </td>
                    <td className="money-cell">
                      <MoneyDisplay money={item.line_subtotal} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
      <p className="context-note">
        RRP includes GST. The ex-GST unit price and line subtotal are calculated by the
        backend; this page only displays the API amounts. Tracking group IDs organise
        fulfilment records and are not carrier tracking events.
      </p>
    </section>
  )
}
