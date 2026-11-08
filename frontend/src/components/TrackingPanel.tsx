import type { TrackingReasonCode, TrackingResult } from '../types/orders'
import { formatCheckedAt, formatStatus } from '../utils/formatters'
import { StatusBadge } from './StatusBadge'

interface TrackingPanelProps {
  results: TrackingResult[]
}

const REASON_MESSAGES: Record<TrackingReasonCode, string> = {
  CARRIER_NOT_IMPLEMENTED: 'Tracking for this carrier is not implemented.',
  PROVIDER_CONFIGURATION_MISSING: 'The approved provider configuration is unavailable.',
  CARRIER_MAPPING_UNRESOLVED:
    'Tracking unavailable — carrier mapping could not be resolved.',
  PROVIDER_AUTHENTICATION_FAILED: 'The carrier rejected the tracking credentials.',
  PROVIDER_TIMEOUT: 'The carrier did not respond before the timeout.',
  PROVIDER_NETWORK_ERROR: 'The carrier tracking service could not be reached.',
  PROVIDER_RATE_LIMITED: 'The carrier tracking request was rate limited.',
  TRACKING_ID_INVALID: 'The carrier did not accept the tracking identifier.',
  PRODUCT_NOT_TRACKABLE: 'The carrier reports that this product cannot be tracked.',
  PROVIDER_RESPONSE_INVALID: 'The carrier returned an invalid tracking response.',
  PROVIDER_ERROR: 'The carrier could not complete the tracking request.',
}

function providerName(provider: TrackingResult['provider']): string {
  if (provider === null) {
    // D-031: no carrier may be named or inferred for an unresolved mapping.
    return 'Carrier not resolved'
  }
  return provider === 'australia_post'
    ? 'Australia Post'
    : provider === 'startrack'
      ? 'StarTrack'
      : 'TNT'
}

export function TrackingPanel({ results }: TrackingPanelProps) {
  return (
    <section className="tracking-panel" aria-labelledby="tracking-heading">
      <div className="panel-heading panel-heading--simple">
        <div>
          <p className="section-kicker">Tracking</p>
          <h2 id="tracking-heading">Carrier tracking</h2>
        </div>
      </div>
      {results.length === 0 ? (
        <div className="tracking-empty" role="note">
          <strong>No tracking groups</strong>
          <p>
            This order has no unique tracking group, so there is nothing to query. No
            carrier request was made.
          </p>
        </div>
      ) : (
        <div className="tracking-groups">
          {results.map((result) => (
            <article className="tracking-card" key={result.tracking_group_id}>
              <header>
                <div>
                  <span>{providerName(result.provider)}</span>
                  <h3>Shipment tracking</h3>
                </div>
                <StatusBadge status={result.status} />
              </header>
              <dl className="tracking-metadata">
                <div><dt>Tracking group</dt><dd>{result.tracking_group_id}</dd></div>
                <div><dt>System check</dt><dd>{formatCheckedAt(result.checked_at)}</dd></div>
                {result.provider_status ? (
                  <div><dt>Carrier status</dt><dd>{result.provider_status}</dd></div>
                ) : null}
                {result.current_status ? (
                  <div><dt>Normalized status</dt><dd>{formatStatus(result.current_status)}</dd></div>
                ) : null}
              </dl>
              {result.status !== 'available' && result.reason_code ? (
                <div className="tracking-warning" role="note">
                  <p>{REASON_MESSAGES[result.reason_code]}</p>
                  <span>Reason: {result.reason_code}</span>
                </div>
              ) : null}
              {result.status === 'available' && result.current_status === 'unknown' ? (
                <div className="tracking-warning" role="note">
                  The carrier status is preserved, but no approved normalized mapping exists.
                </div>
              ) : null}
              {result.status === 'available' && result.events.length === 0 ? (
                <div className="tracking-empty" role="note">
                  Carrier query succeeded. No real tracking events were returned.
                </div>
              ) : null}
              {result.events.length > 0 ? (
                <ol className="tracking-events">
                  {result.events.map((event, index) => (
                    <li key={`${event.event_time}-${index}`}>
                      <time dateTime={event.event_time}>{formatCheckedAt(event.event_time)}</time>
                      <strong>{event.description}</strong>
                      {event.location ? <span>{event.location}</span> : null}
                      <small>Status: {formatStatus(event.normalized_status)}</small>
                    </li>
                  ))}
                </ol>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
