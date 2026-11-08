import type { OrderDetail, OrderSummary } from '../src/types/orders'

export const orderSummaries: OrderSummary[] = [
  {
    order_number: 'TEST-ORDER-001',
    order_date: '2025-12-02',
    company: 'Alpha Test Company',
    status: 'Processing',
    item_count: 1,
    unit_count: 2,
    order_total: { amount: '110.00', currency: 'AUD' },
    quote_request_state: 'not_requested',
    shipping_quote_status: null,
    shipping_quote_reason_code: null,
  },
  {
    order_number: 'TEST-ORDER-002',
    order_date: '2025-12-03',
    company: 'Beta Test Company',
    status: 'Completed',
    item_count: 1,
    unit_count: 1,
    order_total: { amount: '55.00', currency: 'AUD' },
    quote_request_state: 'not_requested',
    shipping_quote_status: null,
    shipping_quote_reason_code: null,
  },
]

export const orderDetail: OrderDetail = {
  order_number: 'TEST-ORDER-001',
  order_date: '2025-12-02',
  company: 'Alpha Test Company',
  customer: {
    name: 'Test Customer',
    phone: '0000 000 000',
    email: 'customer@example.invalid',
  },
  shipping_address: {
    line1: '1 Test Street',
    suburb: 'Testville',
    state: 'NSW',
    postcode: '2000',
    country: 'Australia',
  },
  status: 'Processing',
  currency: 'AUD',
  items: [
    {
      sku: 'TEST-SKU-001',
      quantity: 2,
      tracking_group_id: 'TEST-GROUP-001',
      product: {
        sku: 'TEST-SKU-001',
        spu: 'TEST-SPU-001',
        barcode: '0000000000000',
        product_name: 'Test Product',
        description: null,
        description_status: 'missing',
        product_type: 'Test type',
        size: '1 unit',
        status: 'available',
        schedule: 'Test schedule',
        dosage_type: 'Test dosage',
        plant_species: 'Test species',
        strain_lineage: 'Test lineage',
        spectrum: 'Test spectrum',
        route_of_administration: 'Test route',
        tga_category: 'Test category',
        eta_raw: 'Unavailable',
        eta_days: null,
      },
      unit_price_incl_gst: { amount: '55.00', currency: 'AUD' },
      unit_price_ex_gst: { amount: '50.00', currency: 'AUD' },
      line_subtotal: { amount: '100.00', currency: 'AUD' },
    },
  ],
  pricing: {
    order_subtotal: { amount: '100.00', currency: 'AUD' },
    gst_amount: { amount: '10.00', currency: 'AUD' },
    order_total: { amount: '110.00', currency: 'AUD' },
  },
  quote_request_state: 'requested',
  shipping_quote: {
    status: 'unsupported',
    reason_code: 'SHIPPING_QUOTE_NOT_IMPLEMENTED',
    checked_at: '2026-11-07T00:00:00Z',
    quoted_fee: null,
    applied_fee: { amount: '0.00', currency: 'AUD' },
  },
  // D-031: an empty array is only used here to exercise the "no tracking
  // groups" UI state; the API returns one result per unique tracking group.
  tracking_results: [],
  // Batch J1: the default runtime has no approved packaging ruleset, so the
  // order detail reports a fail-closed estimation with zero packages.
  package_estimation: {
    status: 'unavailable',
    reason_code: 'PACKAGE_RULES_NOT_CONFIGURED',
    checked_at: '2026-11-08T01:00:00Z',
    source: null,
    ruleset_id: null,
    ruleset_version: null,
    synthetic_ruleset: false,
    packages: [],
  },
}

export const syntheticAvailableEstimation: OrderDetail['package_estimation'] = {
  status: 'available',
  reason_code: null,
  checked_at: '2026-11-08T01:00:00Z',
  source: 'rules',
  ruleset_id: 'synthetic-ruleset-j1',
  ruleset_version: 'synthetic-v1',
  synthetic_ruleset: true,
  packages: [
    {
      package_id: 'PKG-001',
      source: 'rules',
      items: [
        {
          order_item_ref: { order_number: 'TEST-ORDER-001', line_index: 0 },
          sku: 'TEST-SKU-001',
          quantity: 2,
        },
      ],
      dimensions: {
        length_mm: '210',
        width_mm: '160',
        height_mm: '110',
        volume_mm3: '3696000',
      },
      weight: {
        item_weight_g: '600',
        packaging_weight_g: '50',
        gross_weight_g: '650',
      },
      ruleset_id: 'synthetic-ruleset-j1',
      ruleset_version: 'synthetic-v1',
    },
    {
      package_id: 'PKG-002',
      source: 'rules',
      items: [
        {
          order_item_ref: { order_number: 'TEST-ORDER-001', line_index: 0 },
          sku: 'TEST-SKU-001',
          quantity: 1,
        },
      ],
      dimensions: {
        length_mm: '210',
        width_mm: '160',
        height_mm: '110',
        volume_mm3: '3696000',
      },
      weight: {
        item_weight_g: '300',
        packaging_weight_g: '50',
        gross_weight_g: '350',
      },
      ruleset_id: 'synthetic-ruleset-j1',
      ruleset_version: 'synthetic-v1',
    },
  ],
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}
