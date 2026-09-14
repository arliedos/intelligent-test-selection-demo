"""T09 - gateway timeout contract.

The gateway is a deterministic in-memory stand-in for a real payment
network: outcomes are scripted per idempotency key, never randomised.
"""
import pytest

from demoshop.gateway import (
    DeclineError,
    GatewayTimeoutError,
    InMemoryPaymentGateway,
)


def test_charge_success_returns_recorded_charge():
    gateway = InMemoryPaymentGateway(scripted_outcomes={"order-1": ["success"]})

    charge = gateway.charge("order-1", amount_cents=1000)

    assert charge.status == "success"
    assert charge.idempotency_key == "order-1"
    assert charge.amount_cents == 1000


def test_charge_timeout_raises_gateway_timeout_error():
    gateway = InMemoryPaymentGateway(scripted_outcomes={"order-2": ["timeout"]})

    with pytest.raises(GatewayTimeoutError):
        gateway.charge("order-2", amount_cents=500)


def test_charge_decline_raises_decline_error():
    gateway = InMemoryPaymentGateway(scripted_outcomes={"order-3": ["decline"]})

    with pytest.raises(DeclineError):
        gateway.charge("order-3", amount_cents=500)


def test_timeout_after_charge_still_records_exactly_one_charge():
    """Contract: a timeout can occur AFTER the gateway has recorded a charge
    (the client never saw the acknowledgement). The gateway must still only
    have recorded a single charge for that idempotency key."""
    gateway = InMemoryPaymentGateway(
        scripted_outcomes={"order-4": ["timeout_after_charge"]}
    )

    with pytest.raises(GatewayTimeoutError):
        gateway.charge("order-4", amount_cents=750)

    assert gateway.charge_count_for("order-4") == 1


def test_repeat_charge_with_same_idempotency_key_does_not_duplicate():
    gateway = InMemoryPaymentGateway(
        scripted_outcomes={"order-5": ["timeout_after_charge", "success"]}
    )

    with pytest.raises(GatewayTimeoutError):
        gateway.charge("order-5", amount_cents=750)

    # Retry with the same idempotency key must return the already-recorded
    # charge rather than creating a new one, even though "success" is next
    # in the script.
    charge = gateway.charge("order-5", amount_cents=750)

    assert charge.status == "success"
    assert gateway.charge_count_for("order-5") == 1
