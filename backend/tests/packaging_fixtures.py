"""Synthetic packaging ruleset fixtures for Batch J1 tests.

These fixtures are test-only. They are never imported by ``backend.main`` or any
production wiring path, and every ruleset is marked ``synthetic_only``. They must
not be described as real packaging specifications, real material stock or real
packing validation.

The physical values below are invented for deterministic testing only. They are
deliberately unrelated to the product weights and dimensions in
``backend/data/skus.json`` so that any accidental dependence on product data
would be visible.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from backend.models import (
    Customer,
    Dimensions,
    Order,
    OrderItem,
    PackageDimensions,
    PackageMaterialSpec,
    PackagingRuleSet,
    PackingPolicy,
    Product,
    ShippingAddress,
    SkuPackagingSpec,
)

NOW = datetime(2026, 11, 8, 1, 2, tzinfo=UTC)

SKU_ALPHA = "SYNTH-SKU-ALPHA"
SKU_BETA = "SYNTH-SKU-BETA"
BOX_SMALL = "SYNTH-BOX-S"
BOX_LARGE = "SYNTH-BOX-L"


def dimensions(length: str, width: str, height: str) -> PackageDimensions:
    """Build dimensions with the exact derived volume."""

    length_decimal = Decimal(length)
    width_decimal = Decimal(width)
    height_decimal = Decimal(height)
    return PackageDimensions(
        length_mm=length_decimal,
        width_mm=width_decimal,
        height_mm=height_decimal,
        volume_mm3=length_decimal * width_decimal * height_decimal,
    )


def small_box() -> PackageMaterialSpec:
    """Synthetic small carton: 3,000,000 mm3 inner capacity, 50 g tare."""

    return PackageMaterialSpec(
        material_id=BOX_SMALL,
        inner_dimensions_mm=dimensions("200", "150", "100"),
        outer_dimensions_mm=dimensions("210", "160", "110"),
        tare_weight_g=Decimal("50"),
        max_gross_weight_g=Decimal("5000"),
    )


def large_box() -> PackageMaterialSpec:
    """Synthetic large carton: 24,000,000 mm3 inner capacity, 120 g tare."""

    return PackageMaterialSpec(
        material_id=BOX_LARGE,
        inner_dimensions_mm=dimensions("400", "300", "200"),
        outer_dimensions_mm=dimensions("410", "310", "210"),
        tare_weight_g=Decimal("120"),
        max_gross_weight_g=Decimal("20000"),
    )


def alpha_spec(materials: tuple[str, ...] = (BOX_SMALL, BOX_LARGE)) -> SkuPackagingSpec:
    """Synthetic packaged-unit spec for ``SYNTH-SKU-ALPHA``."""

    return SkuPackagingSpec(
        sku=SKU_ALPHA,
        unit_weight_g=Decimal("250"),
        packed_unit_dimensions_mm=dimensions("100", "80", "60"),
        compatible_material_ids=materials,
        handling_class=None,
    )


def beta_spec(materials: tuple[str, ...] = (BOX_LARGE,)) -> SkuPackagingSpec:
    """Synthetic packaged-unit spec for ``SYNTH-SKU-BETA``."""

    return SkuPackagingSpec(
        sku=SKU_BETA,
        unit_weight_g=Decimal("400"),
        packed_unit_dimensions_mm=dimensions("120", "90", "70"),
        compatible_material_ids=materials,
        handling_class=None,
    )


def synthetic_ruleset(
    *,
    versions: tuple[SkuPackagingSpec, ...] | None = None,
    materials: tuple[PackageMaterialSpec, ...] | None = None,
    allow_mixed_sku: bool = False,
    allow_split: bool = True,
    version: str = "synthetic-v1",
    effective_from: datetime = NOW,
    effective_to: datetime | None = None,
    policy_id: str = "SYNTH-POLICY-1",
    priority: int = 0,
) -> PackagingRuleSet:
    """Build one explicitly synthetic-only packaging ruleset."""

    return PackagingRuleSet(
        ruleset_id="synthetic-ruleset-j1",
        version=version,
        effective_from=effective_from,
        effective_to=effective_to,
        source_revision="synthetic-source-revision-1",
        synthetic_only=True,
        sku_specs=versions or (alpha_spec(), beta_spec()),
        materials=materials or (small_box(), large_box()),
        policies=(
            PackingPolicy(
                policy_id=policy_id,
                priority=priority,
                allow_split=allow_split,
                allow_mixed_sku=allow_mixed_sku,
            ),
        ),
    )


def mixed_ruleset() -> PackagingRuleSet:
    """Both SKUs may only use the large box, and mixing is allowed."""

    return synthetic_ruleset(
        versions=(
            alpha_spec(materials=(BOX_LARGE,)),
            beta_spec(materials=(BOX_LARGE,)),
        ),
        allow_mixed_sku=True,
    )


def product_for(sku: str) -> Product:
    """Build a synthetic product whose physical data must never be used as packaging data.

    Its weight and dimensions are intentionally tiny and unrelated to the packaged
    unit specs above.
    """

    return Product(
        sku=sku,
        spu=f"SPU-{sku}",
        barcode="0000000000000",
        product_name=f"Synthetic product {sku}",
        description="Synthetic description for packaging tests",
        description_status="available",
        product_type="synthetic",
        size="synthetic",
        status="synthetic",
        schedule="synthetic",
        dosage_type="synthetic",
        plant_species="synthetic",
        strain_lineage="synthetic",
        spectrum="synthetic",
        route_of_administration="synthetic",
        tga_category="synthetic",
        eta_raw="1Days",
        eta_days=1,
        rrp_aud_incl_gst=Decimal("11.00"),
        weight_g=Decimal("7"),
        dimensions_mm=Dimensions(length=Decimal("1"), width=Decimal("1"), height=Decimal("1")),
        volume_mm3=Decimal("1"),
        volumetric_gross_weight_kg=Decimal("0.001"),
        max_storage_per_container=Decimal("1"),
        warning_threshold=Decimal("1"),
        source_date=NOW,
    )


def synthetic_order(items: tuple[tuple[str, int, str], ...]) -> Order:
    """Build a synthetic order from ``(sku, quantity, tracking_group_id)`` tuples."""

    return Order(
        order_no="SYNTH-ORDER-001",
        order_date=date(2026, 11, 8),
        company="Synthetic Company",
        customer=Customer(
            name="Synthetic Customer",
            phone="0000000000",
            email="synthetic@example.invalid",
        ),
        shipping_address=ShippingAddress(
            line1="1 Synthetic Street",
            suburb="Exampleville",
            state="NSW",
            postcode="2000",
            country="Australia",
        ),
        status="SYNTHETIC",
        currency="AUD",
        items=tuple(
            OrderItem(sku=sku, quantity=quantity, tracking_group_id=group_id)
            for sku, quantity, group_id in items
        ),
    )


def products_for(order: Order) -> tuple[Product, ...]:
    """Return one synthetic product per order line, in order."""

    return tuple(product_for(item.sku) for item in order.items)


def ruleset_for_skus(
    skus: tuple[str, ...],
    *,
    allow_mixed_sku: bool = False,
    version: str = "synthetic-v1",
) -> PackagingRuleSet:
    """Build a synthetic ruleset covering arbitrary SKU identifiers.

    The packaged-unit values are fixed synthetic constants; they are never read
    from the product records that share those SKU identifiers.
    """

    specs = tuple(
        SkuPackagingSpec(
            sku=sku,
            unit_weight_g=Decimal("300"),
            packed_unit_dimensions_mm=dimensions("100", "80", "60"),
            compatible_material_ids=(BOX_SMALL, BOX_LARGE),
            handling_class=None,
        )
        for sku in skus
    )
    return PackagingRuleSet(
        ruleset_id="synthetic-ruleset-j1",
        version=version,
        effective_from=NOW,
        effective_to=None,
        source_revision="synthetic-source-revision-1",
        synthetic_only=True,
        sku_specs=specs,
        materials=(small_box(), large_box()),
        policies=(
            PackingPolicy(
                policy_id="SYNTH-POLICY-1",
                priority=0,
                allow_split=True,
                allow_mixed_sku=allow_mixed_sku,
            ),
        ),
    )
