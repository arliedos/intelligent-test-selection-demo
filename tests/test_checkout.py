"""T06 checkout result, T10 checkout critical journey (mandatory).

T10 is an integration test: it exercises real interaction between auth,
catalogue, checkout, payments, and the gateway modules (checkout -> payments
-> gateway), not mocks.
"""
import pytest

from demoshop.auth import InMemoryAuthGateway
from demoshop.catalogue import InMemoryCatalogue
from demoshop.checkout import CartItem, CheckoutError, CheckoutService
from demoshop.config import PaymentConfig
from demoshop.gateway import InMemoryPaymentGateway
from demoshop.payments import PaymentProcessor


def test_checkout_result_success_reports_order_id_and_total():
    """T06 - checkout result reflects a successful payment."""
    gateway = InMemoryPaymentGateway(scripted_outcomes={"order-100": ["success"]})
    processor = PaymentProcessor(gateway, PaymentConfig(max_retries=1))
    service = CheckoutService(processor)
    session = InMemoryAuthGateway().login("alice", "wonderland")

    result = service.checkout(
        session,
        order_id="order-100",
        items=[CartItem(sku="WID-BLU", quantity=2, unit_price_cents=1299)],
    )

    assert result.status == "success"
    assert result.order_id == "order-100"
    assert result.total_cents == 2598
    assert result.payment_result.success is True


def test_checkout_result_failed_when_payment_exhausts_retries():
    """T06 - checkout result reflects a failed payment, with no order id."""
    gateway = InMemoryPaymentGateway(
        scripted_outcomes={"order-101": ["timeout", "timeout"]}
    )
    processor = PaymentProcessor(gateway, PaymentConfig(max_retries=1))
    service = CheckoutService(processor)
    session = InMemoryAuthGateway().login("alice", "wonderland")

    result = service.checkout(
        session,
        order_id="order-101",
        items=[CartItem(sku="GAD-001", quantity=1, unit_price_cents=2599)],
    )

    assert result.status == "failed"
    assert result.order_id is None
    assert result.payment_result.success is False


def test_checkout_rejects_unauthenticated_session():
    gateway = InMemoryPaymentGateway()
    processor = PaymentProcessor(gateway, PaymentConfig(max_retries=1))
    service = CheckoutService(processor)

    with pytest.raises(CheckoutError):
        service.checkout(None, order_id="order-102", items=[])


def test_critical_journey_login_search_checkout_pay_gateway():
    """T10 (mandatory) - end-to-end journey using real modules throughout:
    auth -> catalogue -> checkout -> payments -> gateway."""
    auth_gateway = InMemoryAuthGateway()
    catalogue = InMemoryCatalogue()
    payment_gateway = InMemoryPaymentGateway(
        scripted_outcomes={"order-critical-1": ["success"]}
    )
    processor = PaymentProcessor(payment_gateway, PaymentConfig(max_retries=1))
    checkout_service = CheckoutService(processor)

    session = auth_gateway.login("alice", "wonderland")
    matches = catalogue.search("widget")
    assert len(matches) >= 1

    chosen = matches[0]
    result = checkout_service.checkout(
        session,
        order_id="order-critical-1",
        items=[CartItem(sku=chosen.sku, quantity=1, unit_price_cents=chosen.price_cents)],
    )

    assert result.status == "success"
    assert result.order_id == "order-critical-1"
    assert result.total_cents == chosen.price_cents
    assert payment_gateway.charge_count_for("order-critical-1") == 1
