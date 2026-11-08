import { apiRequest } from './api'
import type {
  ApiErrorCode,
  CarrierProvider,
  ErrorEnvelope,
  Money,
  OrderDetail,
  OrderItem,
  OrderSummary,
  Package,
  PackageDimensions,
  PackageEstimation,
  PackageItem,
  PackageItemReference,
  PackageWeight,
  Product,
  TrackingEvent,
  TrackingResult,
} from '../types/orders'

type ApiFailureKind = 'disconnected' | 'http' | 'invalid-response'

const API_ERROR_CODES: ReadonlySet<string> = new Set([
  'ORDER_NOT_FOUND',
  'REQUEST_VALIDATION_ERROR',
  'DATA_SOURCE_ERROR',
  'INTERNAL_SERVER_ERROR',
])
const TRACKING_PROVIDERS: ReadonlySet<string> = new Set([
  'australia_post',
  'startrack',
  'tnt',
])
const TRACKING_STATUSES: ReadonlySet<string> = new Set([
  'available',
  'unavailable',
  'unsupported',
])
const NORMALIZED_TRACKING_STATUSES: ReadonlySet<string> = new Set([
  'pending',
  'ready_for_pickup',
  'in_transit',
  'out_for_delivery',
  'awaiting_collection',
  'delivered',
  'delivery_exception',
  'cancelled',
  'unknown',
])
const TRACKING_REASON_CODES: ReadonlySet<string> = new Set([
  'CARRIER_NOT_IMPLEMENTED',
  'PROVIDER_CONFIGURATION_MISSING',
  'CARRIER_MAPPING_UNRESOLVED',
  'PROVIDER_AUTHENTICATION_FAILED',
  'PROVIDER_TIMEOUT',
  'PROVIDER_NETWORK_ERROR',
  'PROVIDER_RATE_LIMITED',
  'TRACKING_ID_INVALID',
  'PRODUCT_NOT_TRACKABLE',
  'PROVIDER_RESPONSE_INVALID',
  'PROVIDER_ERROR',
])
const PACKAGE_SOURCES: ReadonlySet<string> = new Set(['actual', 'rules'])
const PACKAGE_ESTIMATION_STATUSES: ReadonlySet<string> = new Set([
  'available',
  'unavailable',
])
const PACKAGE_REASON_CODES: ReadonlySet<string> = new Set([
  'PACKAGE_RULES_NOT_CONFIGURED',
  'PACKAGE_DATA_INCOMPLETE',
])
/**
 * Physical measurements are decimal strings. They are never parsed into
 * JavaScript numbers, so no packaging fact is silently rounded.
 */
const MEASURE_STRING_PATTERN = /^\d+(\.\d+)?$/
const UTC_DATE_TIME_PATTERN =
  /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.\d{1,6})?(?:Z|\+00:00)$/

export class OrderApiError extends Error {
  readonly kind: ApiFailureKind
  readonly status: number | null

  constructor(message: string, kind: ApiFailureKind, status: number | null = null) {
    super(message)
    this.name = 'OrderApiError'
    this.kind = kind
    this.status = status
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isString(value: unknown): value is string {
  return typeof value === 'string'
}

function isNonNegativeInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0
}

function isPositiveInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value > 0
}

function isApiErrorCode(value: unknown): value is ApiErrorCode {
  return isString(value) && API_ERROR_CODES.has(value)
}

function isUtcDateTime(value: unknown): value is string {
  if (!isString(value)) {
    return false
  }

  const match = UTC_DATE_TIME_PATTERN.exec(value)
  if (!match) {
    return false
  }

  const date = new Date(value)
  return (
    !Number.isNaN(date.getTime()) &&
    date.toISOString().slice(0, 19) === match[1]
  )
}

function isMoney(value: unknown): value is Money {
  return (
    isRecord(value) &&
    typeof value.amount === 'string' &&
    /^\d+\.\d{2}$/.test(value.amount) &&
    value.currency === 'AUD'
  )
}

function isOrderSummary(value: unknown): value is OrderSummary {
  return (
    isRecord(value) &&
    isString(value.order_number) &&
    isString(value.order_date) &&
    isString(value.company) &&
    isString(value.status) &&
    isNonNegativeInteger(value.item_count) &&
    isNonNegativeInteger(value.unit_count) &&
    isMoney(value.order_total) &&
    value.quote_request_state === 'not_requested' &&
    value.shipping_quote_status === null &&
    value.shipping_quote_reason_code === null
  )
}

function isNormalizedTrackingStatus(value: unknown): boolean {
  return isString(value) && NORMALIZED_TRACKING_STATUSES.has(value)
}

function isCarrierProvider(value: unknown): value is CarrierProvider {
  return isString(value) && TRACKING_PROVIDERS.has(value)
}

function isTrackingEvent(value: unknown): value is TrackingEvent {
  return (
    isRecord(value) &&
    isUtcDateTime(value.event_time) &&
    (value.location === null || isString(value.location)) &&
    isString(value.description) &&
    value.description.trim().length > 0 &&
    (value.provider_status === null || isString(value.provider_status)) &&
    isNormalizedTrackingStatus(value.normalized_status)
  )
}

function isTrackingResult(value: unknown): value is TrackingResult {
  if (
    !isRecord(value) ||
    !isString(value.tracking_group_id) ||
    value.tracking_group_id.length === 0 ||
    !(value.provider === null || isCarrierProvider(value.provider)) ||
    !isString(value.status) ||
    !TRACKING_STATUSES.has(value.status) ||
    !isUtcDateTime(value.checked_at) ||
    !Array.isArray(value.events) ||
    !value.events.every(isTrackingEvent)
  ) {
    return false
  }

  // D-031: a null provider is only legal with unavailable + mapping unresolved,
  // and mapping unresolved is never allowed to name a carrier provider.
  const mappingUnresolved =
    value.status === 'unavailable' && value.reason_code === 'CARRIER_MAPPING_UNRESOLVED'
  if (value.provider === null && !mappingUnresolved) {
    return false
  }
  if (value.provider !== null && mappingUnresolved) {
    return false
  }

  if (value.status === 'available') {
    if (
      value.reason_code !== null ||
      (value.provider_status !== null && !isString(value.provider_status)) ||
      (value.current_status !== null && !isNormalizedTrackingStatus(value.current_status)) ||
      (value.latest_event_at !== null && !isUtcDateTime(value.latest_event_at))
    ) {
      return false
    }
    if (value.events.length === 0) {
      return value.latest_event_at === null
    }
    if (value.latest_event_at === null) {
      return false
    }
    const times = value.events.map((event) => new Date(event.event_time).getTime())
    return (
      new Date(value.latest_event_at).getTime() === Math.max(...times) &&
      times.every((time, index) => index === 0 || times[index - 1] >= time)
    )
  }

  return (
    isString(value.reason_code) &&
    TRACKING_REASON_CODES.has(value.reason_code) &&
    value.provider_status === null &&
    value.current_status === null &&
    value.latest_event_at === null &&
    value.events.length === 0 &&
    ((value.status === 'unsupported' && value.reason_code === 'CARRIER_NOT_IMPLEMENTED') ||
      (value.status === 'unavailable' && value.reason_code !== 'CARRIER_NOT_IMPLEMENTED'))
  )
}

function isProduct(value: unknown): value is Product {
  if (!isRecord(value)) {
    return false
  }

  const stringFields = [
    'sku',
    'spu',
    'barcode',
    'product_name',
    'description_status',
    'product_type',
    'size',
    'status',
    'schedule',
    'dosage_type',
    'plant_species',
    'strain_lineage',
    'spectrum',
    'route_of_administration',
    'tga_category',
    'eta_raw',
  ]

  return (
    stringFields.every((field) => isString(value[field])) &&
    (value.description === null || isString(value.description)) &&
    (value.eta_days === null || isNonNegativeInteger(value.eta_days))
  )
}

function isOrderItem(value: unknown): value is OrderItem {
  return (
    isRecord(value) &&
    isString(value.sku) &&
    isPositiveInteger(value.quantity) &&
    isString(value.tracking_group_id) &&
    isProduct(value.product) &&
    isMoney(value.unit_price_incl_gst) &&
    isMoney(value.unit_price_ex_gst) &&
    isMoney(value.line_subtotal)
  )
}

function isOrderDetail(value: unknown): value is OrderDetail {
  if (!isRecord(value)) {
    return false
  }

  const customer = value.customer
  const address = value.shipping_address
  const pricing = value.pricing
  const quote = value.shipping_quote

  return (
    isString(value.order_number) &&
    isString(value.order_date) &&
    isString(value.company) &&
    isString(value.status) &&
    value.currency === 'AUD' &&
    isRecord(customer) &&
    isString(customer.name) &&
    isString(customer.phone) &&
    isString(customer.email) &&
    isRecord(address) &&
    isString(address.line1) &&
    isString(address.suburb) &&
    isString(address.state) &&
    isString(address.postcode) &&
    isString(address.country) &&
    Array.isArray(value.items) &&
    value.items.every(isOrderItem) &&
    isRecord(pricing) &&
    isMoney(pricing.order_subtotal) &&
    isMoney(pricing.gst_amount) &&
    isMoney(pricing.order_total) &&
    value.quote_request_state === 'requested' &&
    isRecord(quote) &&
    quote.status === 'unsupported' &&
    quote.reason_code === 'SHIPPING_QUOTE_NOT_IMPLEMENTED' &&
    isUtcDateTime(quote.checked_at) &&
    quote.quoted_fee === null &&
    isMoney(quote.applied_fee) &&
    quote.applied_fee.amount === '0.00' &&
    isPackageEstimation(value.package_estimation) &&
    packagesBelongToOrder(value) &&
    Array.isArray(value.tracking_results) &&
    value.tracking_results.every(isTrackingResult)
  )
}

function isMeasureString(value: unknown): value is string {
  return isString(value) && MEASURE_STRING_PATTERN.test(value)
}

function isPositiveMeasure(value: unknown): value is string {
  return isMeasureString(value) && /[1-9]/.test(value.replace('.', ''))
}

function isPackageItemReference(value: unknown): value is PackageItemReference {
  return (
    isRecord(value) &&
    isString(value.order_number) &&
    value.order_number.length > 0 &&
    isNonNegativeInteger(value.line_index)
  )
}

function isPackageItem(value: unknown): value is PackageItem {
  return (
    isRecord(value) &&
    isPackageItemReference(value.order_item_ref) &&
    isString(value.sku) &&
    value.sku.length > 0 &&
    isPositiveInteger(value.quantity)
  )
}

function isPackageDimensions(value: unknown): value is PackageDimensions {
  return (
    isRecord(value) &&
    isPositiveMeasure(value.length_mm) &&
    isPositiveMeasure(value.width_mm) &&
    isPositiveMeasure(value.height_mm) &&
    isPositiveMeasure(value.volume_mm3)
  )
}

function isPackageWeight(value: unknown): value is PackageWeight {
  return (
    isRecord(value) &&
    isMeasureString(value.item_weight_g) &&
    isMeasureString(value.packaging_weight_g) &&
    isPositiveMeasure(value.gross_weight_g)
  )
}

function isPackage(value: unknown): value is Package {
  if (
    !isRecord(value) ||
    !isString(value.package_id) ||
    value.package_id.length === 0 ||
    !isString(value.source) ||
    !PACKAGE_SOURCES.has(value.source) ||
    !Array.isArray(value.items) ||
    value.items.length === 0 ||
    !value.items.every(isPackageItem) ||
    !isPackageDimensions(value.dimensions) ||
    !isPackageWeight(value.weight) ||
    !(value.ruleset_id === null || isString(value.ruleset_id)) ||
    !(value.ruleset_version === null || isString(value.ruleset_version))
  ) {
    return false
  }

  // Public provenance subset: a rules-sourced package must name its ruleset.
  if (value.source === 'rules') {
    return isString(value.ruleset_id) && isString(value.ruleset_version)
  }

  return true
}

function isPackageEstimation(value: unknown): value is PackageEstimation {
  if (
    !isRecord(value) ||
    !isString(value.status) ||
    !PACKAGE_ESTIMATION_STATUSES.has(value.status) ||
    !isUtcDateTime(value.checked_at) ||
    !(value.source === null || (isString(value.source) && PACKAGE_SOURCES.has(value.source))) ||
    !(value.ruleset_id === null || isString(value.ruleset_id)) ||
    !(value.ruleset_version === null || isString(value.ruleset_version)) ||
    typeof value.synthetic_ruleset !== 'boolean' ||
    !Array.isArray(value.packages) ||
    !value.packages.every(isPackage)
  ) {
    return false
  }

  if (value.status === 'available') {
    if (
      value.reason_code !== null ||
      value.packages.length === 0 ||
      value.source === null
    ) {
      return false
    }
    if (
      value.source === 'rules' &&
      (!isString(value.ruleset_id) || !isString(value.ruleset_version))
    ) {
      return false
    }
    const ids = value.packages.map((item) => item.package_id)
    if (new Set(ids).size !== ids.length) {
      return false
    }
    return value.packages.every(
      (item) =>
        item.source === value.source &&
        (value.source !== 'rules' ||
          (item.ruleset_id === value.ruleset_id &&
            item.ruleset_version === value.ruleset_version)),
    )
  }

  return (
    isString(value.reason_code) &&
    PACKAGE_REASON_CODES.has(value.reason_code) &&
    value.packages.length === 0 &&
    value.source === null
  )
}

function packagesBelongToOrder(detail: Record<string, unknown>): boolean {
  const orderNumber = detail.order_number
  const estimation = detail.package_estimation
  if (!isString(orderNumber) || !isPackageEstimation(estimation)) {
    return false
  }

  return estimation.packages.every((packageItem) =>
    packageItem.items.every(
      (item) => item.order_item_ref.order_number === orderNumber,
    ),
  )
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  return (
    isRecord(value) &&
    isRecord(value.error) &&
    isApiErrorCode(value.error.code) &&
    isString(value.error.message)
  )
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    throw new OrderApiError(
      'The server returned a response that could not be read.',
      'invalid-response',
      response.status,
    )
  }
}

async function request(path: string, signal: AbortSignal): Promise<unknown> {
  let response: Response

  try {
    response = await apiRequest(path, { method: 'GET', signal })
  } catch (error) {
    if (signal.aborted) {
      throw error
    }

    throw new OrderApiError(
      'The order service could not be reached. Check that the backend is running and try again.',
      'disconnected',
    )
  }

  const body = await readJson(response)
  if (!response.ok) {
    const message = isErrorEnvelope(body)
      ? body.error.message
      : 'The order service could not complete the request.'
    throw new OrderApiError(message, 'http', response.status)
  }

  return body
}

export async function getOrders(signal: AbortSignal): Promise<OrderSummary[]> {
  const body = await request('/api/v1/orders', signal)
  if (
    !isRecord(body) ||
    !Array.isArray(body.data) ||
    !body.data.every(isOrderSummary)
  ) {
    throw new OrderApiError(
      'The order service returned an unexpected list response.',
      'invalid-response',
    )
  }

  return body.data
}

export async function getOrder(
  orderNumber: string,
  signal: AbortSignal,
): Promise<OrderDetail> {
  const body = await request(
    `/api/v1/orders/${encodeURIComponent(orderNumber)}`,
    signal,
  )
  if (!isRecord(body) || !isOrderDetail(body.data)) {
    throw new OrderApiError(
      'The order service returned an unexpected detail response.',
      'invalid-response',
    )
  }

  return body.data
}
