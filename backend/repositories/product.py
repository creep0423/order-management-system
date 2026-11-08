"""Read-only product repository backed only by normalized skus.json."""

from pathlib import Path

from backend.models import Dimensions, Product
from backend.models.source import ProductsFileSource, ProductSource
from backend.repositories.exceptions import DuplicateIdentifierError, RecordNotFoundError
from backend.repositories.loader import load_json_model


class ProductRepository:
    """Load, cache and query normalized products by SKU."""

    def __init__(self, path: Path) -> None:
        source = load_json_model(path, ProductsFileSource)
        products = tuple(self._to_domain(record) for record in source.products)
        by_sku = {product.sku: product for product in products}
        if len(by_sku) != len(products):
            raise DuplicateIdentifierError("SKU")
        self._products = products
        self._by_sku = by_sku

    @staticmethod
    def _to_domain(record: ProductSource) -> Product:
        data = record.model_dump()
        data["dimensions_mm"] = Dimensions(**record.dimensions_mm.model_dump())
        return Product(**data)

    def list_products(self) -> tuple[Product, ...]:
        return self._products

    def get_by_sku(self, sku: str) -> Product:
        try:
            return self._by_sku[sku]
        except KeyError:
            raise RecordNotFoundError("product") from None
