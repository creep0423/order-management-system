import { useEffect, useState } from 'react'

import { getOrder, OrderApiError } from '../services/orders'
import type { OrderDetail } from '../types/orders'

interface OrderDetailResult {
  order: OrderDetail | null
  loading: boolean
  error: OrderApiError | null
}

interface OrderDetailRequestState {
  requestId: string
  order: OrderDetail | null
  error: OrderApiError | null
}

export function useOrderDetail(
  orderNumber: string,
  retryKey: number,
): OrderDetailResult {
  const requestId = `${orderNumber}:${retryKey}`
  const [state, setState] = useState<OrderDetailRequestState>({
    requestId: '',
    order: null,
    error: null,
  })

  useEffect(() => {
    const controller = new AbortController()
    let active = true

    void getOrder(orderNumber, controller.signal)
      .then((order) => {
        if (active) {
          setState({ requestId, order, error: null })
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
                'The order could not be loaded. Please try again.',
                'invalid-response',
              )
        setState({ requestId, order: null, error: apiError })
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [orderNumber, requestId])

  if (state.requestId !== requestId) {
    return { order: null, loading: true, error: null }
  }

  return { order: state.order, loading: false, error: state.error }
}
