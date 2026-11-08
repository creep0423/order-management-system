import { useEffect, useState } from 'react'

import './App.css'
import { OrderDetailPage } from './pages/OrderDetailPage'
import { OrdersPage } from './pages/OrdersPage'
import { APP_NAME } from './utils/appMetadata'

interface Route {
  page: 'orders' | 'detail'
  orderNumber?: string
}

interface NavigationState {
  route: Route
  focusRequest: number
}

interface AppHistoryMarker {
  page: Route['page']
  enteredFromList: boolean
}

const APP_HISTORY_STATE_KEY = '__orderManagementSystem'
const PRESERVED_HISTORY_STATE_KEY = '__orderManagementSystemPreservedState'

function isStateRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function readHistoryMarker(): AppHistoryMarker | null {
  const state = window.history.state as unknown
  if (!isStateRecord(state)) {
    return null
  }

  const marker = state[APP_HISTORY_STATE_KEY]
  if (
    !isStateRecord(marker) ||
    (marker.page !== 'orders' && marker.page !== 'detail') ||
    typeof marker.enteredFromList !== 'boolean'
  ) {
    return null
  }

  return {
    page: marker.page,
    enteredFromList: marker.enteredFromList,
  }
}

function withHistoryMarker(marker: AppHistoryMarker): Record<string, unknown> {
  const state = window.history.state as unknown
  if (isStateRecord(state)) {
    return { ...state, [APP_HISTORY_STATE_KEY]: marker }
  }

  return {
    ...(state === null ? {} : { [PRESERVED_HISTORY_STATE_KEY]: state }),
    [APP_HISTORY_STATE_KEY]: marker,
  }
}

function readRoute(): Route {
  const match = /^\/orders\/([^/]+)\/?$/.exec(window.location.pathname)
  if (!match) {
    return { page: 'orders' }
  }

  try {
    return { page: 'detail', orderNumber: decodeURIComponent(match[1]) }
  } catch {
    return { page: 'orders' }
  }
}

function App() {
  const [navigation, setNavigation] = useState<NavigationState>(() => ({
    route: readRoute(),
    focusRequest: 0,
  }))
  const { route, focusRequest } = navigation

  useEffect(() => {
    if (readHistoryMarker() === null) {
      const initialRoute = readRoute()
      window.history.replaceState(
        withHistoryMarker({
          page: initialRoute.page,
          enteredFromList: false,
        }),
        '',
        window.location.href,
      )
    }

    const handlePopState = () => {
      setNavigation((current) => ({
        route: readRoute(),
        focusRequest: current.focusRequest + 1,
      }))
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  function updateRouteAfterHistoryChange() {
    setNavigation((current) => ({
      route: readRoute(),
      focusRequest: current.focusRequest + 1,
    }))
    window.scrollTo({ top: 0, behavior: 'auto' })
  }

  function openOrder(orderNumber: string) {
    const path = `/orders/${encodeURIComponent(orderNumber)}`
    if (route.page === 'detail' && window.location.pathname === path) {
      return
    }

    window.history.pushState(
      withHistoryMarker({ page: 'detail', enteredFromList: true }),
      '',
      path,
    )
    updateRouteAfterHistoryChange()
  }

  function returnToOrders() {
    const marker = readHistoryMarker()
    if (route.page === 'detail' && marker?.enteredFromList === true) {
      window.history.back()
      return
    }

    if (route.page === 'orders' && window.location.pathname === '/') {
      return
    }

    window.history.replaceState(
      withHistoryMarker({ page: 'orders', enteredFromList: false }),
      '',
      '/',
    )
    updateRouteAfterHistoryChange()
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <button className="brand" type="button" onClick={returnToOrders}>
          <span className="brand-mark" aria-hidden="true">OM</span>
          <span>{APP_NAME}</span>
        </button>
        <p className="environment-label"><span aria-hidden="true" /> Read-only workspace</p>
      </header>
      <main>
        {route.page === 'detail' && route.orderNumber ? (
          <OrderDetailPage
            orderNumber={route.orderNumber}
            focusRequest={focusRequest}
            onBack={returnToOrders}
          />
        ) : (
          <OrdersPage
            focusRequest={focusRequest}
            onOpenOrder={openOrder}
          />
        )}
      </main>
      <footer className="app-footer">
        <span>{APP_NAME}</span>
        <span>Read-only order data · AUD</span>
      </footer>
    </div>
  )
}

export default App
