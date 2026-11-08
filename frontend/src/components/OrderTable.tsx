import type { MouseEvent } from 'react'

import type { OrderSummary } from '../types/orders'
import { formatOrderDate } from '../utils/formatters'
import { MoneyDisplay } from './MoneyDisplay'
import { StatusBadge } from './StatusBadge'

interface OrderTableProps {
  orders: OrderSummary[]
  onOpenOrder: (orderNumber: string) => void
}

export function OrderTable({ orders, onOpenOrder }: OrderTableProps) {
  function openOrder(event: MouseEvent<HTMLAnchorElement>, orderNumber: string) {
    if (
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return
    }

    event.preventDefault()
    onOpenOrder(orderNumber)
  }

  return (
    <div className="table-card">
      <div
        className="table-scroll"
        role="region"
        aria-label="Orders table"
        tabIndex={0}
      >
        <table>
          <caption className="sr-only">Current orders</caption>
          <thead>
            <tr>
              <th scope="col">Order number</th>
              <th scope="col">Order date</th>
              <th scope="col">Company</th>
              <th scope="col">Status</th>
              <th scope="col" className="number-cell">Items</th>
              <th scope="col" className="number-cell">Units</th>
              <th scope="col" className="money-cell">Total before shipping</th>
              <th scope="col">Shipping quote</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.order_number}>
                <td>
                  <a
                    className="order-link"
                    href={`/orders/${encodeURIComponent(order.order_number)}`}
                    onClick={(event) => openOrder(event, order.order_number)}
                    aria-label={`Open order ${order.order_number}`}
                  >
                    {order.order_number}
                  </a>
                </td>
                <td>{formatOrderDate(order.order_date)}</td>
                <td>{order.company}</td>
                <td><StatusBadge status={order.status} /></td>
                <td className="number-cell">{order.item_count}</td>
                <td className="number-cell">{order.unit_count}</td>
                <td className="money-cell"><MoneyDisplay money={order.order_total} /></td>
                <td>Shipping quote not requested</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
