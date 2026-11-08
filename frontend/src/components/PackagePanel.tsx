import type { PackageEstimation, PackageReasonCode } from '../types/orders'
import { formatCheckedAt } from '../utils/formatters'
import { StatusBadge } from './StatusBadge'

interface PackagePanelProps {
  estimation: PackageEstimation
}

const REASON_MESSAGES: Record<PackageReasonCode, string> = {
  PACKAGE_RULES_NOT_CONFIGURED:
    'Packaging rules are not configured, so no packages could be estimated.',
  PACKAGE_DATA_INCOMPLETE:
    'Packaging data is incomplete or could not satisfy the packaging rules.',
}

function measurement(value: string, unit: string): string {
  // The API sends decimal strings; the UI only appends a unit suffix and never
  // converts the value to a JavaScript number.
  return `${value} ${unit}`
}

export function PackagePanel({ estimation }: PackagePanelProps) {
  return (
    <section className="package-panel" aria-labelledby="package-heading">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Packaging</p>
          <h2 id="package-heading">Package estimation</h2>
        </div>
        <StatusBadge status={estimation.status} />
      </div>

      {estimation.status === 'available' ? (
        <div className="package-groups">
          <dl className="package-metadata">
            <div>
              <dt>Packages</dt>
              <dd>{estimation.packages.length}</dd>
            </div>
            <div>
              <dt>System check</dt>
              <dd>{formatCheckedAt(estimation.checked_at)}</dd>
            </div>
            <div>
              <dt>Ruleset</dt>
              <dd>
                {estimation.ruleset_id} v{estimation.ruleset_version}
              </dd>
            </div>
          </dl>

          {estimation.synthetic_ruleset ? (
            <div className="package-synthetic-note" role="note">
              <strong>Synthetic estimation rules</strong>
              <p>
                These packages come from synthetic-only test rules. They are not
                real packaging specifications, real material stock or a real
                packing validation.
              </p>
            </div>
          ) : null}

          {estimation.packages.map((packageItem) => (
            <article className="package-card" key={packageItem.package_id}>
              <header>
                <div>
                  <span>{packageItem.source === 'rules' ? 'Rules estimate' : 'Actual'}</span>
                  <h3>{packageItem.package_id}</h3>
                </div>
              </header>
              <dl className="package-metadata">
                <div>
                  <dt>Dimensions (L × W × H)</dt>
                  <dd>
                    {measurement(packageItem.dimensions.length_mm, 'mm')} ×{' '}
                    {measurement(packageItem.dimensions.width_mm, 'mm')} ×{' '}
                    {measurement(packageItem.dimensions.height_mm, 'mm')}
                  </dd>
                </div>
                <div>
                  <dt>Package weight</dt>
                  <dd>{measurement(packageItem.weight.gross_weight_g, 'g')}</dd>
                </div>
                <div>
                  <dt>Packaging weight</dt>
                  <dd>{measurement(packageItem.weight.packaging_weight_g, 'g')}</dd>
                </div>
                <div>
                  <dt>Ruleset</dt>
                  <dd>
                    {packageItem.ruleset_id} v{packageItem.ruleset_version}
                  </dd>
                </div>
              </dl>
              <ul className="package-items">
                {packageItem.items.map((item) => (
                  <li key={`${item.order_item_ref.line_index}-${item.sku}`}>
                    <strong>{item.sku}</strong>
                    <span>Qty {item.quantity}</span>
                    <small>
                      Order line {item.order_item_ref.line_index + 1}
                    </small>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      ) : (
        <div className="package-warning" role="note">
          <p>
            {estimation.reason_code
              ? REASON_MESSAGES[estimation.reason_code]
              : REASON_MESSAGES.PACKAGE_DATA_INCOMPLETE}
          </p>
          {estimation.reason_code ? (
            <span>Reason: {estimation.reason_code}</span>
          ) : null}
          <span>No package was constructed and no shipping cost was derived.</span>
        </div>
      )}
    </section>
  )
}
