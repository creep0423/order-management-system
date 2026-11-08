import { describe, expect, it, vi } from 'vitest'

import { getOrder, getOrders, OrderApiError } from '../src/services/orders'
import {
  jsonResponse,
  orderDetail,
  orderSummaries,
  syntheticAvailableEstimation,
} from './fixtures'

function mockFetchResponse(body: unknown, status = 200) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(body, status)))
}

describe('orders API service', () => {
  it('accepts Money amounts only as two-decimal strings', async () => {
    const invalidOrder = {
      ...orderSummaries[0],
      order_total: { amount: 120, currency: 'AUD' },
    }
    mockFetchResponse({ data: [invalidOrder] })

    await expect(getOrders(new AbortController().signal)).rejects.toMatchObject({
      kind: 'invalid-response',
    } satisfies Partial<OrderApiError>)
  })

  it('does not substitute records when the backend is disconnected', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network unavailable')))

    await expect(getOrders(new AbortController().signal)).rejects.toMatchObject({
      kind: 'disconnected',
    } satisfies Partial<OrderApiError>)
  })

  it('passes AbortController cancellation through to fetch', async () => {
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      const requestSignal = init?.signal
      return new Promise<Response>((_resolve, reject) => {
        requestSignal?.addEventListener('abort', () => {
          reject(new DOMException('The operation was aborted', 'AbortError'))
        })
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    const controller = new AbortController()

    const request = getOrders(controller.signal)
    const requestSignal = fetchMock.mock.calls[0]?.[1]?.signal
    controller.abort()

    await expect(request).rejects.toMatchObject({ name: 'AbortError' })
    expect(requestSignal?.aborted).toBe(true)
  })

  it.each([
    [404, 'ORDER_NOT_FOUND'],
    [422, 'REQUEST_VALIDATION_ERROR'],
    [500, 'INTERNAL_SERVER_ERROR'],
  ] as const)('preserves safe error envelopes for HTTP %i', async (status, code) => {
    mockFetchResponse({ error: { code, message: 'Safe API error' } }, status)

    await expect(getOrder('TEST-ORDER-001', new AbortController().signal)).rejects.toMatchObject({
      kind: 'http',
      status,
      message: 'Safe API error',
    } satisfies Partial<OrderApiError>)
  })

  it('uses a generic message for an invalid error envelope', async () => {
    mockFetchResponse({ error: { code: 'UNKNOWN_CODE', message: 'Do not trust this' } }, 500)

    await expect(getOrders(new AbortController().signal)).rejects.toMatchObject({
      kind: 'http',
      message: 'The order service could not complete the request.',
    } satisfies Partial<OrderApiError>)
  })

  it('rejects a non-JSON response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response('not-json', {
          status: 200,
          headers: { 'Content-Type': 'text/plain' },
        }),
      ),
    )

    await expect(getOrders(new AbortController().signal)).rejects.toMatchObject({
      kind: 'invalid-response',
    } satisfies Partial<OrderApiError>)
  })

  it('rejects an invalid order detail response', async () => {
    mockFetchResponse({ data: { order_number: 'TEST-ORDER-001' } })

    await expect(getOrder('TEST-ORDER-001', new AbortController().signal)).rejects.toMatchObject({
      kind: 'invalid-response',
    } satisfies Partial<OrderApiError>)
  })

  it.each([
    ['99.99', '2026-11-07T00:00:00Z'],
    ['-1.00', '2026-11-07T00:00:00Z'],
    ['0.0', '2026-11-07T00:00:00Z'],
    ['0.00', 'not-a-date'],
    ['0.00', '2026-11-07T00:00:00'],
    ['0.00', '2026-11-07T10:00:00+10:00'],
    ['0.00', '2026-02-30T00:00:00Z'],
  ])(
    'rejects an invalid D-015 quote with fee %s and checked_at %s',
    async (amount, checkedAt) => {
      mockFetchResponse({
        data: {
          ...orderDetail,
          shipping_quote: {
            ...orderDetail.shipping_quote,
            checked_at: checkedAt,
            applied_fee: { amount, currency: 'AUD' },
          },
        },
      })

      await expect(
        getOrder('TEST-ORDER-001', new AbortController().signal),
      ).rejects.toMatchObject({ kind: 'invalid-response' } satisfies Partial<OrderApiError>)
    },
  )

  it.each([
    '2026-11-07T00:00:00Z',
    '2026-11-07T00:00:00.123456Z',
    '2026-11-07T00:00:00+00:00',
  ])('accepts a zero-fee D-015 quote with UTC checked_at %s', async (checkedAt) => {
    const expected = {
      ...orderDetail,
      shipping_quote: { ...orderDetail.shipping_quote, checked_at: checkedAt },
    }
    mockFetchResponse({ data: expected })

    await expect(
      getOrder('TEST-ORDER-001', new AbortController().signal),
    ).resolves.toEqual(expected)
  })

  it('accepts raw and unknown tracking status with real UTC events', async () => {
    const expected = {
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
      ],
    }
    mockFetchResponse({ data: expected })

    await expect(
      getOrder('TEST-ORDER-001', new AbortController().signal),
    ).resolves.toEqual(expected)
  })

  it('accepts the D-031 provider-null mapping unresolved result', async () => {
    const expected = {
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
      ],
    }
    mockFetchResponse({ data: expected })

    await expect(
      getOrder('TEST-ORDER-001', new AbortController().signal),
    ).resolves.toEqual(expected)
  })

  const illegalTrackingStates: Record<string, unknown>[] = [
    { provider: null, status: 'available', reason_code: null },
    { provider: null, status: 'unsupported', reason_code: 'CARRIER_NOT_IMPLEMENTED' },
    { provider: null, status: 'unavailable', reason_code: 'PROVIDER_TIMEOUT' },
    { provider: null, status: 'unavailable', reason_code: 'PROVIDER_ERROR' },
    { provider: null, status: 'unavailable', reason_code: null },
    {
      provider: 'australia_post',
      status: 'unavailable',
      reason_code: 'CARRIER_MAPPING_UNRESOLVED',
    },
    { provider: 'unapproved_carrier', status: 'available', reason_code: null },
  ]

  it.each(illegalTrackingStates)(
    'rejects an illegal D-031 provider combination %#',
    async (tracking) => {
      mockFetchResponse({
        data: {
          ...orderDetail,
          tracking_results: [
            {
              tracking_group_id: 'TEST-GROUP-001',
              checked_at: '2026-11-08T01:00:00Z',
              provider_status: null,
              current_status: null,
              latest_event_at: null,
              events: [],
              ...tracking,
            },
          ],
        },
      })

      await expect(
        getOrder('TEST-ORDER-001', new AbortController().signal),
      ).rejects.toMatchObject({ kind: 'invalid-response' } satisfies Partial<OrderApiError>)
    },
  )

  it.each([
    {
      status: 'unavailable',
      reason_code: null,
      provider_status: null,
      current_status: null,
      latest_event_at: null,
      events: [],
    },
    {
      status: 'unsupported',
      reason_code: 'PROVIDER_TIMEOUT',
      provider_status: null,
      current_status: null,
      latest_event_at: null,
      events: [],
    },
    {
      status: 'available',
      reason_code: null,
      provider_status: 'Delivered',
      current_status: 'delivered',
      latest_event_at: null,
      events: [
        {
          event_time: 'not-utc',
          location: null,
          description: 'Synthetic provider event',
          provider_status: null,
          normalized_status: 'delivered',
        },
      ],
    },
  ])('rejects malformed tracking state matrices', async (tracking) => {
    mockFetchResponse({
      data: {
        ...orderDetail,
        tracking_results: [
          {
            tracking_group_id: 'TEST-GROUP-001',
            provider: 'australia_post',
            checked_at: '2026-11-08T01:00:00Z',
            ...tracking,
          },
        ],
      },
    })

    await expect(
      getOrder('TEST-ORDER-001', new AbortController().signal),
    ).rejects.toMatchObject({ kind: 'invalid-response' } satisfies Partial<OrderApiError>)
  })

describe('package estimation runtime validation', () => {
  it('accepts a rules estimation with multiple packages', async () => {
    const expected = { ...orderDetail, package_estimation: syntheticAvailableEstimation }
    mockFetchResponse({ data: expected })

    await expect(
      getOrder('TEST-ORDER-001', new AbortController().signal),
    ).resolves.toEqual(expected)
  })

  it('accepts a fail-closed estimation without packages', async () => {
    mockFetchResponse({ data: orderDetail })

    await expect(
      getOrder('TEST-ORDER-001', new AbortController().signal),
    ).resolves.toEqual(orderDetail)
  })

  const illegalEstimations: Record<string, unknown>[] = [
    // available but no packages
    { status: 'available', packages: [] },
    // available but carries a reason code
    { reason_code: 'PACKAGE_DATA_INCOMPLETE' },
    // unavailable but still claims packages
    { status: 'unavailable', reason_code: 'PACKAGE_RULES_NOT_CONFIGURED' },
    // unavailable without a reason code
    { status: 'unavailable', reason_code: null },
    // unavailable but claims a source
    { status: 'unavailable', reason_code: 'PACKAGE_DATA_INCOMPLETE', source: 'rules' },
    // unknown public reason code
    { status: 'unavailable', reason_code: 'SOMETHING_ELSE' },
    // non-UTC check time
    { checked_at: '2026-11-08T01:00:00+10:00' },
    // synthetic flag is not a boolean
    { synthetic_ruleset: 'yes' },
  ]

  it.each(illegalEstimations)(
    'rejects an illegal package estimation matrix %#',
    async (patch) => {
      mockFetchResponse({
        data: {
          ...orderDetail,
          package_estimation: { ...syntheticAvailableEstimation, ...patch },
        },
      })

      await expect(
        getOrder('TEST-ORDER-001', new AbortController().signal),
      ).rejects.toMatchObject({ kind: 'invalid-response' } satisfies Partial<OrderApiError>)
    },
  )

  const illegalPackages: Record<string, unknown>[] = [
    { items: [] },
    { items: [{ ...syntheticAvailableEstimation.packages[0].items[0], quantity: 0 }] },
    {
      items: [
        { ...syntheticAvailableEstimation.packages[0].items[0], quantity: -2 },
      ],
    },
    {
      items: [
        { ...syntheticAvailableEstimation.packages[0].items[0], quantity: 1.5 },
      ],
    },
    { ruleset_id: null, ruleset_version: null },
    { dimensions: { ...syntheticAvailableEstimation.packages[0].dimensions, length_mm: '-1' } },
    { dimensions: { ...syntheticAvailableEstimation.packages[0].dimensions, width_mm: 'wide' } },
    { dimensions: { ...syntheticAvailableEstimation.packages[0].dimensions, height_mm: 0 } },
    { weight: { ...syntheticAvailableEstimation.packages[0].weight, gross_weight_g: '0' } },
    { weight: { ...syntheticAvailableEstimation.packages[0].weight, item_weight_g: 600 } },
  ]

  it.each(illegalPackages)('rejects an illegal package payload %#', async (patch) => {
    mockFetchResponse({
      data: {
        ...orderDetail,
        package_estimation: {
          ...syntheticAvailableEstimation,
          packages: [{ ...syntheticAvailableEstimation.packages[0], ...patch }],
        },
      },
    })

    await expect(
      getOrder('TEST-ORDER-001', new AbortController().signal),
    ).rejects.toMatchObject({ kind: 'invalid-response' } satisfies Partial<OrderApiError>)
  })

  it('rejects duplicate package identifiers', async () => {
    const duplicate = syntheticAvailableEstimation.packages[0]
    mockFetchResponse({
      data: {
        ...orderDetail,
        package_estimation: {
          ...syntheticAvailableEstimation,
          packages: [duplicate, duplicate],
        },
      },
    })

    await expect(
      getOrder('TEST-ORDER-001', new AbortController().signal),
    ).rejects.toMatchObject({ kind: 'invalid-response' } satisfies Partial<OrderApiError>)
  })

  it('rejects a package whose source disagrees with the estimation', async () => {
    mockFetchResponse({
      data: {
        ...orderDetail,
        package_estimation: {
          ...syntheticAvailableEstimation,
          packages: [
            { ...syntheticAvailableEstimation.packages[0], source: 'actual' },
          ],
        },
      },
    })

    await expect(
      getOrder('TEST-ORDER-001', new AbortController().signal),
    ).rejects.toMatchObject({ kind: 'invalid-response' } satisfies Partial<OrderApiError>)
  })
})
})

describe('package projection cross-consistency', () => {
  it('rejects a package whose ruleset disagrees with the estimation', async () => {
    mockFetchResponse({
      data: {
        ...orderDetail,
        package_estimation: {
          ...syntheticAvailableEstimation,
          packages: [
            {
              ...syntheticAvailableEstimation.packages[0],
              ruleset_version: 'synthetic-v9',
            },
          ],
        },
      },
    })

    await expect(
      getOrder('TEST-ORDER-001', new AbortController().signal),
    ).rejects.toMatchObject({ kind: 'invalid-response' } satisfies Partial<OrderApiError>)
  })

  it('rejects package items that reference another order', async () => {
    mockFetchResponse({
      data: {
        ...orderDetail,
        package_estimation: {
          ...syntheticAvailableEstimation,
          packages: [
            {
              ...syntheticAvailableEstimation.packages[0],
              items: [
                {
                  ...syntheticAvailableEstimation.packages[0].items[0],
                  order_item_ref: {
                    order_number: 'OTHER-ORDER',
                    line_index: 0,
                  },
                },
              ],
            },
          ],
        },
      },
    })

    await expect(
      getOrder('TEST-ORDER-001', new AbortController().signal),
    ).rejects.toMatchObject({ kind: 'invalid-response' } satisfies Partial<OrderApiError>)
  })
})
