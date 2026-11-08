# Backend Services

This directory contains the business service layer. Dependencies point inwards:
`API -> Service -> Repository / Integration`. Services never read JSON directly,
never serialize API payloads and never own HTTP request/response objects.

## Contents

| Module | Responsibility |
|---|---|
| `pricing.py` | Pure Decimal pricing rules (D-004). No I/O, no cross-order state. |
| `order.py` | Order list/detail orchestration, capability isolation and injection. |
| `exceptions.py` | Classified, non-sensitive service errors. |
| `tracking.py` | Tracking orchestration: mapping preflight, batching, D-031 projection. |
| `tracking_configuration.py` | Append-only immutable Revision/Release catalog. |
| `packaging_rules.py` | Read-only packaging rules reader protocol (D-021). |
| `package_estimation.py` | Deterministic rules-based package estimation (Batch J1). |

## Package estimation boundary (Batch J1)

Data flow:

```text
OrderService.get_order()
  -> PackageEstimationService.estimate_for_order(order, products)
       -> PackagingRuleSetReader.get_active(checked_at)
       -> PackageEstimationService.estimate(order, products, ruleset)
            -> SkuPackagingSpec / PackageMaterialSpec lookups
            -> sequential first-fit allocation over packaged-unit volume + gross weight
            -> quantity conservation + split policy verification
            -> Package / PackageProvenance construction
  -> PackageEstimationResult
       -> OrderDetailResult.packages / OrderDetailResult.package_estimation
       -> API PackageEstimationResponse / PackageResponse
```

Enforced rules:

- Product physical data (`weight_g`, `dimensions_mm`, `volume_mm3`,
  `volumetric_gross_weight_kg`, `max_storage_per_container`) is **never** read as
  packaging data. Package dimensions, unit weights and packaging weights come
  only from the ruleset (D-019, contract §4.4).
- Every `OrderItem` quantity must be allocated exactly once across packages
  (D-020). Allocation that cannot be conserved fails closed.
- Every rules package records `ruleset_id`, `ruleset_version`, `source_revision`
  and an irreversible `input_fingerprint` in its provenance (D-021).
- Only two public reason codes exist: `PACKAGE_RULES_NOT_CONFIGURED` and
  `PACKAGE_DATA_INCOMPLETE`. Finer causes stay in internal diagnostics
  (`sku_spec_missing`, `material_missing`, `capacity_exceeded`,
  `quantity_conservation`, `invalid_input`, `internal_error`).
- Estimation failures never raise into the order detail request and never affect
  Tracking, the D-015 Shipping Quote or Pricing.

### Synthetic-only boundary

No production packaging ruleset exists, and DEC-1 (full `PackingPolicy` schema),
DEC-2 (orientation / fragile / stacking / dangerous-goods placement), DEC-3
(production allocation algorithm) and DEC-4 (material selection strategy) are
still open business decisions. Therefore:

- `PackingPolicy` is a deliberately narrow synthetic shape with **no**
  match-criteria fields and no orientation or handling-class routing.
- `PackagingRuleSet.synthetic_only` is typed `Literal[True]`: a non-synthetic
  ruleset cannot be constructed, so synthetic rules can never be mixed into
  production behaviour.
- `POST /shipping/v1/prices/shipments` and every other provider call remain out of
  scope; this module computes no freight and no money.
- The allocation strategy is a deterministic sequential first-fit over packaged
  unit volume and gross weight. It is **not** a production three-dimensional bin
  packing algorithm.
- Synthetic fixtures live only under `backend/tests/packaging_fixtures.py` and are
  never imported by `backend.main`.

### Default application behaviour

`backend.main.build_package_estimation_service()` wires a
`StaticPackagingRuleSetReader(None)`. With no approved ruleset the default
runtime returns `unavailable / PACKAGE_RULES_NOT_CONFIGURED` with zero packages
for every order detail. It never falls back to synthetic fixtures and never
fabricates a default dimension, weight, material or capacity.

### Not in scope for Batch J1

Real packaging specifications, real material stock, production packing
algorithms, Package API for lists, Shipping Quote, PAC, TNT, quote history and
cross-request caching.
