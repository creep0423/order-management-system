export type Currency = 'AUD'

export interface Money {
  amount: string
  currency: Currency
}

export type ShippingQuoteStatus = 'unsupported'
export type ShippingQuoteReasonCode = 'SHIPPING_QUOTE_NOT_IMPLEMENTED'

export interface OrderSummary {
  order_number: string
  order_date: string
  company: string
  status: string
  item_count: number
  unit_count: number
  order_total: Money
  quote_request_state: 'not_requested'
  shipping_quote_status: null
  shipping_quote_reason_code: null
}

export interface Customer {
  name: string
  phone: string
  email: string
}

export interface ShippingAddress {
  line1: string
  suburb: string
  state: string
  postcode: string
  country: string
}

export interface Product {
  sku: string
  spu: string
  barcode: string
  product_name: string
  description: string | null
  description_status: string
  product_type: string
  size: string
  status: string
  schedule: string
  dosage_type: string
  plant_species: string
  strain_lineage: string
  spectrum: string
  route_of_administration: string
  tga_category: string
  eta_raw: string
  eta_days: number | null
}

export interface OrderItem {
  sku: string
  quantity: number
  tracking_group_id: string
  product: Product
  unit_price_incl_gst: Money
  unit_price_ex_gst: Money
  line_subtotal: Money
}

export interface OrderPricing {
  order_subtotal: Money
  gst_amount: Money
  order_total: Money
}

export interface ShippingQuote {
  status: ShippingQuoteStatus
  reason_code: ShippingQuoteReasonCode
  checked_at: string
  quoted_fee: Money | null
  applied_fee: Money
}

export type CarrierProvider = 'australia_post' | 'startrack' | 'tnt'
export type TrackingStatus = 'available' | 'unavailable' | 'unsupported'
export type NormalizedTrackingStatus =
  | 'pending'
  | 'ready_for_pickup'
  | 'in_transit'
  | 'out_for_delivery'
  | 'awaiting_collection'
  | 'delivered'
  | 'delivery_exception'
  | 'cancelled'
  | 'unknown'
export type TrackingReasonCode =
  | 'CARRIER_NOT_IMPLEMENTED'
  | 'PROVIDER_CONFIGURATION_MISSING'
  | 'CARRIER_MAPPING_UNRESOLVED'
  | 'PROVIDER_AUTHENTICATION_FAILED'
  | 'PROVIDER_TIMEOUT'
  | 'PROVIDER_NETWORK_ERROR'
  | 'PROVIDER_RATE_LIMITED'
  | 'TRACKING_ID_INVALID'
  | 'PRODUCT_NOT_TRACKABLE'
  | 'PROVIDER_RESPONSE_INVALID'
  | 'PROVIDER_ERROR'

export interface TrackingEvent {
  event_time: string
  location: string | null
  description: string
  provider_status: string | null
  normalized_status: NormalizedTrackingStatus
}

export interface TrackingResult {
  tracking_group_id: string
  /**
   * D-031: nullable only for `status: 'unavailable'` with
   * `reason_code: 'CARRIER_MAPPING_UNRESOLVED'`. Every other result names a
   * concrete carrier provider. The runtime validator enforces the combination.
   */
  provider: CarrierProvider | null
  status: TrackingStatus
  reason_code: TrackingReasonCode | null
  checked_at: string
  provider_status: string | null
  current_status: NormalizedTrackingStatus | null
  latest_event_at: string | null
  events: TrackingEvent[]
}

export type PackageSource = 'actual' | 'rules'
export type PackageEstimationStatus = 'available' | 'unavailable'
export type PackageReasonCode =
  | 'PACKAGE_RULES_NOT_CONFIGURED'
  | 'PACKAGE_DATA_INCOMPLETE'

export interface PackageItemReference {
  order_number: string
  line_index: number
}

export interface PackageItem {
  order_item_ref: PackageItemReference
  sku: string
  quantity: number
}

/**
 * Physical measurements arrive as decimal strings so the browser never has to
 * round or re-compute a packaging fact through binary floating point.
 */
export interface PackageDimensions {
  length_mm: string
  width_mm: string
  height_mm: string
  volume_mm3: string
}

export interface PackageWeight {
  item_weight_g: string
  packaging_weight_g: string
  gross_weight_g: string
}

export interface Package {
  package_id: string
  source: PackageSource
  items: PackageItem[]
  dimensions: PackageDimensions
  weight: PackageWeight
  /** Public provenance subset: required for a rules-sourced package. */
  ruleset_id: string | null
  ruleset_version: string | null
}

export interface PackageEstimation {
  status: PackageEstimationStatus
  reason_code: PackageReasonCode | null
  checked_at: string
  source: PackageSource | null
  ruleset_id: string | null
  ruleset_version: string | null
  /**
   * True when the estimation used synthetic-only rules. Batch J1 ships no
   * approved production ruleset, so a synthetic result is never production data.
   */
  synthetic_ruleset: boolean
  packages: Package[]
}

export interface OrderDetail {
  order_number: string
  order_date: string
  company: string
  customer: Customer
  shipping_address: ShippingAddress
  status: string
  currency: Currency
  items: OrderItem[]
  pricing: OrderPricing
  quote_request_state: 'requested'
  shipping_quote: ShippingQuote
  package_estimation: PackageEstimation
  tracking_results: TrackingResult[]
}

export interface OrderListEnvelope {
  data: OrderSummary[]
}

export interface OrderDetailEnvelope {
  data: OrderDetail
}

export type ApiErrorCode =
  | 'ORDER_NOT_FOUND'
  | 'REQUEST_VALIDATION_ERROR'
  | 'DATA_SOURCE_ERROR'
  | 'INTERNAL_SERVER_ERROR'

export interface ErrorEnvelope {
  error: {
    code: ApiErrorCode
    message: string
  }
}
