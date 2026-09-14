"""Checkout journey: catalogue selection -> payments -> gateway.

Directed dependency: checkout depends on payments, which depends on the
gateway. Catalogue search and profile update are independent of this chain.
"""
from dataclasses import dataclass
from typing import List, Optional

from demoshop.auth import AuthSession
from demoshop.payments import PaymentProcessor, PaymentResult


class CheckoutError(Exception):
    """Raised when checkout preconditions are not met."""


def require_authenticated(session: Optional[AuthSession]) -> None:
    if session is None or not getattr(session, "is_authenticated", False):
        raise CheckoutError("checkout requires an authenticated session")


@dataclass(frozen=True)
class CartItem:
    sku: str
    quantity: int
    unit_price_cents: int


@dataclass(frozen=True)
class CheckoutResult:
    status: str  # "success" or "failed"
    order_id: Optional[str]
    total_cents: int
    payment_result: PaymentResult


class CheckoutService:
    """Orchestrates the checkout -> payments -> gateway chain."""

    def __init__(self, payment_processor: PaymentProcessor) -> None:
        self.payment_processor = payment_processor

    def checkout(self, session: Optional[AuthSession], order_id: str,
                 items: List[CartItem]) -> CheckoutResult:
        require_authenticated(session)

        total_cents = sum(item.quantity * item.unit_price_cents for item in items)
        payment_result = self.payment_processor.pay(order_id, total_cents)

        return CheckoutResult(
            status="success" if payment_result.success else "failed",
            order_id=order_id if payment_result.success else None,
            total_cents=total_cents,
            payment_result=payment_result,
        )
