import { useEffect, useState } from 'react'

import { getOrders, OrderApiError } from '../services/orders'
import type { OrderSummary } from '../types/orders'

interface OrdersResult {
  orders: OrderSummary[]
  loading: boolean
  error: OrderApiError | null
}

interface OrdersRequestState {
  requestKey: number
  orders: OrderSummary[]
  error: OrderApiError | null
}

const initialState: OrdersRequestState = {
  requestKey: -1,
  orders: [],
  error: null,
}

export function useOrders(retryKey: number): OrdersResult {
  const [state, setState] = useState<OrdersRequestState>(initialState)

  useEffect(() => {
    const controller = new AbortController()
    let active = true

    void getOrders(controller.signal)
      .then((orders) => {
        if (active) {
          setState({ requestKey: retryKey, orders, error: null })
        }
      })
      .catch((error: unknown) => {
        if (!active || controller.signal.aborted) {
          return
        }

        const apiError =
          error instanceof OrderApiError
            ? error
            : new OrderApiError(
                'The orders could not be loaded. Please try again.',
                'invalid-response',
              )
        setState({ requestKey: retryKey, orders: [], error: apiError })
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [retryKey])

  if (state.requestKey !== retryKey) {
    return { orders: [], loading: true, error: null }
  }

  return { orders: state.orders, loading: false, error: state.error }
}
