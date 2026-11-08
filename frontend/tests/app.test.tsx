import { StrictMode } from 'react'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../src/App'
import type { OrderDetail, OrderSummary } from '../src/types/orders'
import {
  jsonResponse,
  orderDetail,
  orderSummaries,
  syntheticAvailableEstimation,
} from './fixtures'

interface Deferred<T> {
  promise: Promise<T>
  resolve: (value: T) => void
}

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve
  })
  return { promise, resolve }
}

function detailFor(orderNumber: string): OrderDetail {
  const summary = orderSummaries.find((order) => order.order_number === orderNumber)
  return {
    ...orderDetail,
    order_number: orderNumber,
    company: summary?.company ?? orderDetail.company,
    status: summary?.status ?? orderDetail.status,
    pricing: {
      ...orderDetail.pricing,
      order_total: summary?.order_total ?? orderDetail.pricing.order_total,
    },
  }
}

function installApiMock() {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/api/v1/orders')) {
      return Promise.resolve(jsonResponse({ data: orderSummaries }))
    }

    const orderNumber = decodeURIComponent(url.slice(url.lastIndexOf('/') + 1))
    return Promise.resolve(jsonResponse({ data: detailFor(orderNumber) }))
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('order management application', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/')
  })

  it('loads a mocked API list and combines order, company, case, whitespace, and status filters', async () => {
    const fetchMock = installApiMock()
    const user = userEvent.setup()

    render(<App />)
    expect(screen.getByRole('heading', { name: 'Loading orders' })).toBeTruthy()

    expect(await screen.findByText('TEST-ORDER-001')).toBeTruthy()
    expect(screen.getByText('TEST-ORDER-002')).toBeTruthy()
    expect(fetchMock).toHaveBeenCalledTimes(1)

    const search = screen.getByRole('searchbox', { name: 'Search orders' })
    await user.type(search, '  test-order-002  ')
    await user.selectOptions(
      screen.getByRole('combobox', { name: 'Order status' }),
      'Completed',
    )
    expect(screen.queryByText('TEST-ORDER-001')).toBeNull()
    expect(screen.getByText('TEST-ORDER-002')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    await user.type(search, 'bEtA tEsT')
    expect(screen.queryByText('TEST-ORDER-001')).toBeNull()
    expect(screen.getByText('TEST-ORDER-002')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(screen.getByText('TEST-ORDER-001')).toBeTruthy()
    expect(screen.getByText('TEST-ORDER-002')).toBeTruthy()
  })

  it('shows search empty state and clears the criteria', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<App />)

    await screen.findByText('TEST-ORDER-001')
    await user.type(screen.getByRole('searchbox', { name: 'Search orders' }), 'not-present')
    expect(screen.getByRole('heading', { name: 'No matching orders' })).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(screen.getByText('TEST-ORDER-001')).toBeTruthy()
  })

  it('shows an empty state when the API returns no orders', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ data: [] })))
    render(<App />)

    expect(await screen.findByRole('heading', { name: 'No orders available' })).toBeTruthy()
    expect(screen.queryByRole('table')).toBeNull()
  })

  it('loads detail Money strings and explains unsupported shipping without a false quote', async () => {
    window.history.replaceState(null, '', '/orders/TEST-ORDER-001')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ data: orderDetail })))
    render(<App />)

    expect(await screen.findByRole('heading', { name: 'TEST-ORDER-001' })).toBeTruthy()
    expect(screen.getByText('Description unavailable')).toBeTruthy()
    expect(
      screen.getByRole('img', { name: 'Medicine bottle product image placeholder' }),
    ).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'RRP (incl. GST)' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Quantity' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Unit price ex. GST' })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Line subtotal ex. GST' })).toBeTruthy()
    expect(screen.getByText(/ETA unavailable/)).toBeTruthy()
    expect(screen.queryByText(/nullDays/)).toBeNull()
    expect(
      screen.getByRole('heading', { name: 'Shipping quote integration not implemented' }),
    ).toBeTruthy()
    expect(screen.getByText(/does not mean a carrier offered free shipping/i)).toBeTruthy()
    expect(screen.getAllByText('A$0.00').length).toBeGreaterThan(0)
    expect(screen.getAllByText('A$55.00').length).toBeGreaterThan(0)
    expect(screen.getByText('A$110.00')).toBeTruthy()
    expect(screen.getByText(/not carrier tracking events/i)).toBeTruthy()
    expect(screen.getByText('No tracking groups')).toBeTruthy()
    expect(screen.queryByText('Tracking not requested')).toBeNull()
  })

  it('flags a possibly truncated description and shows the provided 0Days ETA verbatim', async () => {
    const partialDescriptionDetail: OrderDetail = {
      ...orderDetail,
      items: [
        {
          ...orderDetail.items[0],
          product: {
            ...orderDetail.items[0].product,
            description: 'Partial source description',
            description_status: 'partial_needs_requery',
            eta_raw: '0Days',
            eta_days: 0,
          },
        },
      ],
    }
    window.history.replaceState(null, '', '/orders/TEST-ORDER-001')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ data: partialDescriptionDetail })),
    )
    render(<App />)

    expect(await screen.findByText('Partial source description')).toBeTruthy()
    expect(screen.getByText(/possibly truncated and needs re-query/i)).toBeTruthy()
    expect(screen.getByText(/ETA: 0Days/)).toBeTruthy()
    expect(screen.queryByText('Description unavailable')).toBeNull()
  })

  it('shows successful, unknown, empty, and failed tracking states independently', async () => {
    const trackingDetail: OrderDetail = {
      ...orderDetail,
      tracking_results: [
        {
          tracking_group_id: 'TEST-GROUP-001',
          provider: 'australia_post',
          status: 'available',
          reason_code: null,
          checked_at: '2026-11-08T01:00:00Z',
          provider_status: 'New provider status',
          current_status: 'unknown',
          latest_event_at: '2026-11-08T00:30:00Z',
          events: [
            {
              event_time: '2026-11-08T00:30:00Z',
              location: null,
              description: 'Synthetic provider event',
              provider_status: null,
              normalized_status: 'unknown',
            },
          ],
        },
        {
          tracking_group_id: 'TEST-GROUP-002',
          provider: 'startrack',
          status: 'available',
          reason_code: null,
          checked_at: '2026-11-08T01:00:00Z',
          provider_status: null,
          current_status: null,
          latest_event_at: null,
          events: [],
        },
        {
          tracking_group_id: 'TEST-GROUP-003',
          provider: 'tnt',
          status: 'unsupported',
          reason_code: 'CARRIER_NOT_IMPLEMENTED',
          checked_at: '2026-11-08T01:00:00Z',
          provider_status: null,
          current_status: null,
          latest_event_at: null,
          events: [],
        },
      ],
    }
    window.history.replaceState(null, '', '/orders/TEST-ORDER-001')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ data: trackingDetail })))
    render(<App />)

    expect(await screen.findByText('Synthetic provider event')).toBeTruthy()
    expect(screen.getByText('New provider status')).toBeTruthy()
    expect(screen.getByText(/no approved normalized mapping exists/i)).toBeTruthy()
    expect(screen.getByText(/no real tracking events were returned/i)).toBeTruthy()
    expect(screen.getByText(/tracking for this carrier is not implemented/i)).toBeTruthy()
    expect(screen.getByText('Shipping quote integration not implemented')).toBeTruthy()
    expect(screen.queryByText('Tracking not requested')).toBeNull()
  })

  it('shows a mapping unresolved group as unavailable instead of not requested', async () => {
    const mappingDetail: OrderDetail = {
      ...orderDetail,
      tracking_results: [
        {
          tracking_group_id: 'TEST-GROUP-001',
          provider: null,
          status: 'unavailable',
          reason_code: 'CARRIER_MAPPING_UNRESOLVED',
          checked_at: '2026-11-08T01:00:00Z',
          provider_status: null,
          current_status: null,
          latest_event_at: null,
          events: [],
        },
        {
          tracking_group_id: 'TEST-GROUP-002',
          provider: 'tnt',
          status: 'unsupported',
          reason_code: 'CARRIER_NOT_IMPLEMENTED',
          checked_at: '2026-11-08T01:00:00Z',
          provider_status: null,
          current_status: null,
          latest_event_at: null,
          events: [],
        },
      ],
    }
    window.history.replaceState(null, '', '/orders/TEST-ORDER-001')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ data: mappingDetail })))
    render(<App />)

    expect(
      await screen.findByText(/Tracking unavailable — carrier mapping could not be resolved/i),
    ).toBeTruthy()
    expect(screen.getByText('Carrier not resolved')).toBeTruthy()
    expect(screen.getAllByText('TEST-GROUP-001').length).toBeGreaterThan(0)
    expect(screen.getAllByText('TEST-GROUP-002').length).toBeGreaterThan(0)
    expect(screen.getByText('Reason: CARRIER_MAPPING_UNRESOLVED')).toBeTruthy()
    expect(screen.queryByText('Tracking not requested')).toBeNull()
    expect(screen.queryByText('No tracking groups')).toBeNull()
  })

  it('shows a disconnected state, no fabricated records, and supports retry', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('network unavailable'))
      .mockResolvedValueOnce(jsonResponse({ data: orderSummaries }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Backend disconnected' })).toBeTruthy()
    expect(screen.queryByText('TEST-ORDER-001')).toBeNull()

    await user.click(screen.getByRole('button', { name: 'Retry' }))
    await screen.findByText('TEST-ORDER-001')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('uses push, back, and forward without creating a list-detail history loop', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<App />)

    const orderLink = await screen.findByRole('link', { name: 'Open order TEST-ORDER-001' })
    const initialHistoryLength = window.history.length
    await user.click(orderLink)

    const detailHeading = await screen.findByRole('heading', { name: 'TEST-ORDER-001' })
    await waitFor(() => expect(document.activeElement).toBe(detailHeading))
    expect(window.location.pathname).toBe('/orders/TEST-ORDER-001')
    expect(window.history.length).toBe(initialHistoryLength + 1)

    await user.click(screen.getByRole('button', { name: /Back to orders/ }))
    const listHeading = await screen.findByRole('heading', { name: 'Orders' })
    await waitFor(() => expect(window.location.pathname).toBe('/'))
    expect(document.activeElement).toBe(listHeading)

    act(() => window.history.forward())
    const forwardHeading = await screen.findByRole('heading', { name: 'TEST-ORDER-001' })
    await waitFor(() => expect(document.activeElement).toBe(forwardHeading))

    act(() => window.history.back())
    const backHeading = await screen.findByRole('heading', { name: 'Orders' })
    await waitFor(() => expect(document.activeElement).toBe(backHeading))
    expect(window.history.length).toBe(initialHistoryLength + 1)
  })

  it('preserves list navigation after a detail route is remounted with the same history state', async () => {
    installApiMock()
    const user = userEvent.setup()
    const firstView = render(<App />)

    const orderLink = await screen.findByRole('link', { name: 'Open order TEST-ORDER-001' })
    await user.click(orderLink)
    await screen.findByRole('heading', { name: 'TEST-ORDER-001' })
    const detailHistoryLength = window.history.length

    const detailUrl = window.location.href
    const detailState = window.history.state
    firstView.unmount()
    window.history.replaceState(detailState, '', detailUrl)

    render(<App />)
    await screen.findByRole('heading', { name: 'TEST-ORDER-001' })
    expect(window.history.length).toBe(detailHistoryLength)
    await user.click(screen.getByRole('button', { name: /Back to orders/ }))

    await screen.findByRole('heading', { name: 'Orders' })
    await waitFor(() => expect(window.location.pathname).toBe('/'))
  })

  it('replaces a directly opened detail entry when returning and preserves external state', async () => {
    window.history.replaceState(
      { externalState: 'preserved' },
      '',
      '/orders/TEST-ORDER-001',
    )
    installApiMock()
    const user = userEvent.setup()
    const initialHistoryLength = window.history.length
    render(<App />)

    await screen.findByRole('heading', { name: 'TEST-ORDER-001' })
    await user.click(screen.getByRole('button', { name: /Back to orders/ }))

    const listHeading = await screen.findByRole('heading', { name: 'Orders' })
    expect(window.location.pathname).toBe('/')
    expect(window.history.length).toBe(initialHistoryLength)
    expect(document.activeElement).toBe(listHeading)
    expect(window.history.state.externalState).toBe('preserved')
  })

  it('does not add history entries when the brand is repeatedly selected on the list', async () => {
    window.history.replaceState({ externalState: 'preserved' }, '', '/')
    installApiMock()
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText('TEST-ORDER-001')
    const initialHistoryLength = window.history.length

    const brand = screen.getByRole('button', { name: 'Order Management System' })
    await user.click(brand)
    await user.click(brand)

    expect(window.history.length).toBe(initialHistoryLength)
    expect(window.history.state.externalState).toBe('preserved')
  })

  it('aborts the active request when the component unmounts', async () => {
    const pendingResponse = deferred<Response>()
    const fetchMock = vi.fn((_input: RequestInfo | URL, _init?: RequestInit) =>
      pendingResponse.promise,
    )
    vi.stubGlobal('fetch', fetchMock)
    const view = render(<App />)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    const requestInit = fetchMock.mock.calls[0]?.[1]
    expect(requestInit?.signal?.aborted).toBe(false)

    view.unmount()
    expect(requestInit?.signal?.aborted).toBe(true)
  })

  it('prevents a stale detail response from replacing a newer route result', async () => {
    window.history.replaceState(null, '', '/orders/TEST-ORDER-001')
    const firstResponse = deferred<Response>()
    const secondResponse = deferred<Response>()
    const signals: AbortSignal[] = []
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.signal) {
        signals.push(init.signal)
      }
      return fetchMock.mock.calls.length === 1
        ? firstResponse.promise
        : secondResponse.promise
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))

    act(() => {
      window.history.pushState(null, '', '/orders/TEST-ORDER-002')
      window.dispatchEvent(new PopStateEvent('popstate', { state: window.history.state }))
    })
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(signals[0]?.aborted).toBe(true)

    secondResponse.resolve(jsonResponse({ data: detailFor('TEST-ORDER-002') }))
    const latestHeading = await screen.findByRole('heading', { name: 'TEST-ORDER-002' })
    expect(document.activeElement).toBe(latestHeading)

    firstResponse.resolve(jsonResponse({ data: detailFor('TEST-ORDER-001') }))
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'TEST-ORDER-001' })).toBeNull()
    })
  })

  it('keeps StrictMode effect replay isolated and aborts the obsolete request', async () => {
    const firstResponse = deferred<Response>()
    const secondResponse = deferred<Response>()
    const signals: AbortSignal[] = []
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.signal) {
        signals.push(init.signal)
      }
      return fetchMock.mock.calls.length === 1
        ? firstResponse.promise
        : secondResponse.promise
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <StrictMode>
        <App />
      </StrictMode>,
    )
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(signals[0]?.aborted).toBe(true)

    secondResponse.resolve(jsonResponse({ data: orderSummaries }))
    await screen.findByText('TEST-ORDER-001')

    const staleOrder: OrderSummary = {
      ...orderSummaries[0],
      order_number: 'STALE-ORDER',
    }
    firstResponse.resolve(jsonResponse({ data: [staleOrder] }))
    await waitFor(() => expect(screen.queryByText('STALE-ORDER')).toBeNull())
  })
})

describe('package estimation panel', () => {
  function renderDetail(detail: OrderDetail) {
    window.history.replaceState(null, '', '/orders/TEST-ORDER-001')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ data: detail })))
    render(<App />)
  }

  it('shows multiple packages with dimensions, weights and provenance', async () => {
    renderDetail({ ...orderDetail, package_estimation: syntheticAvailableEstimation })

    expect(await screen.findByText('PKG-001')).toBeTruthy()
    expect(screen.getByText('Available')).toBeTruthy()
    expect(screen.getByText('PKG-002')).toBeTruthy()
    expect(screen.getAllByText('210 mm × 160 mm × 110 mm')).toHaveLength(2)
    expect(screen.getByText('650 g')).toBeTruthy()
    expect(screen.getByText('350 g')).toBeTruthy()
    // Provenance is rendered as "id v version"; match on the rendered content.
    expect(screen.getAllByText(/synthetic-ruleset-j1/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/synthetic-v1/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Synthetic estimation rules/i)).toBeTruthy()
    expect(screen.getByText('Qty 2')).toBeTruthy()
    expect(screen.getByText('Qty 1')).toBeTruthy()
  })

  it('explains a missing packaging ruleset without inventing packages', async () => {
    renderDetail(orderDetail)

    expect(
      await screen.findByText(/Packaging rules are not configured/i),
    ).toBeTruthy()
    expect(screen.getByText('Unavailable')).toBeTruthy()
    expect(screen.getByText('Reason: PACKAGE_RULES_NOT_CONFIGURED')).toBeTruthy()
    expect(screen.queryByText('PKG-001')).toBeNull()
  })

  it('explains incomplete packaging data distinctly', async () => {
    renderDetail({
      ...orderDetail,
      package_estimation: {
        ...orderDetail.package_estimation,
        reason_code: 'PACKAGE_DATA_INCOMPLETE',
      },
    })

    expect(await screen.findByText(/Packaging data is incomplete/i)).toBeTruthy()
    expect(screen.getByText('Reason: PACKAGE_DATA_INCOMPLETE')).toBeTruthy()
    expect(screen.queryByText(/Packaging rules are not configured/i)).toBeNull()
  })

  it('keeps package and tracking states independent', async () => {
    renderDetail({
      ...orderDetail,
      package_estimation: syntheticAvailableEstimation,
      tracking_results: [
        {
          tracking_group_id: 'TEST-GROUP-001',
          provider: null,
          status: 'unavailable',
          reason_code: 'CARRIER_MAPPING_UNRESOLVED',
          checked_at: '2026-11-08T01:00:00Z',
          provider_status: null,
          current_status: null,
          latest_event_at: null,
          events: [],
        },
      ],
    })

    expect(await screen.findByText('PKG-001')).toBeTruthy()
    expect(
      screen.getByText(/Tracking unavailable — carrier mapping could not be resolved/i),
    ).toBeTruthy()
    expect(screen.queryByText('Tracking not requested')).toBeNull()
  })
})
