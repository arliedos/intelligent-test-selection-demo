"""In-memory product catalogue. Independent of checkout/payments/gateway."""
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    price_cents: int


class InMemoryCatalogue:
    """Deterministic in-memory product list. No network calls."""

    _PRODUCTS = [
        Product(sku="WID-BLU", name="Blue Widget", price_cents=1299),
        Product(sku="WID-RED", name="Red Widget", price_cents=1499),
        Product(sku="GAD-001", name="Gadget", price_cents=2599),
    ]

    def list_all(self) -> List[Product]:
        return list(self._PRODUCTS)

    def search(self, query: str) -> List[Product]:
        needle = query.strip().lower()
        if not needle:
            return self.list_all()
        return [p for p in self._PRODUCTS if needle in p.name.lower()]
