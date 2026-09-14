"""T02 successful payment, T03 timeout/retry limit/config, T04 decline policy
(baseline), T05 duplicate-charge mandatory.

Baseline requirement (REQ-PAY-002): retry any failure (timeout or decline)
up to payment.max_retries (default 1).
"""
import pytest

from demoshop.config import PaymentConfig
from demoshop.gateway import InMemoryPaymentGateway
from demoshop.payments import PaymentProcessor


def test_successful_payment_charges_once():
    """T02 - a successful payment charges exactly once and reports success."""
    gateway = InMemoryPaymentGateway(scripted_outcomes={"order-1": ["success"]})
    processor = PaymentProcessor(gateway, PaymentConfig(max_retries=1))

    result = processor.pay("order-1", amount_cents=1000)

    assert result.success is True
    assert result.attempts == 1
    assert gateway.call_count == 1


def test_timeout_is_retried_up_to_max_retries_then_fails():
    """T03 - baseline retries a timeout, but stops at the configured limit."""
    gateway = InMemoryPaymentGateway(
        scripted_outcomes={"order-2": ["timeout", "timeout"]}
    )
    processor = PaymentProcessor(gateway, PaymentConfig(max_retries=1))

    result = processor.pay("order-2", amount_cents=1000)

    assert result.success is False
    assert result.attempts == 2  # 1 initial attempt + 1 retry
    assert gateway.call_count == 2


def test_timeout_retry_respects_config_max_retries_of_zero():
    """T03 - max_retries=0 means no retry at all."""
    gateway = InMemoryPaymentGateway(scripted_outcomes={"order-3": ["timeout"]})
    processor = PaymentProcessor(gateway, PaymentConfig(max_retries=0))

    result = processor.pay("order-3", amount_cents=1000)

    assert result.success is False
    assert result.attempts == 1
    assert gateway.call_count == 1


def test_timeout_eventually_succeeds_within_retry_budget():
    """T03 - a timeout followed by success within budget reports success."""
    gateway = InMemoryPaymentGateway(
        scripted_outcomes={"order-4": ["timeout", "success"]}
    )
    processor = PaymentProcessor(gateway, PaymentConfig(max_retries=1))

    result = processor.pay("order-4", amount_cents=1000)

    assert result.success is True
    assert result.attempts == 2


def test_baseline_decline_is_retried_up_to_max_retries():
    """T04 (baseline) - baseline policy retries declines too."""
    gateway = InMemoryPaymentGateway(
        scripted_outcomes={"order-5": ["decline", "success"]}
    )
    processor = PaymentProcessor(gateway, PaymentConfig(max_retries=1))

    result = processor.pay("order-5", amount_cents=1000)

    assert result.success is True
    assert result.attempts == 2
    assert gateway.call_count == 2


def test_negative_max_retries_is_rejected():
    with pytest.raises(ValueError):
        PaymentConfig(max_retries=-1)


def test_duplicate_charge_prevented_after_timeout_following_recorded_charge():
    """T05 (mandatory) - a timeout that occurs AFTER the gateway recorded a
    charge must not result in a duplicate charge when the processor retries."""
    gateway = InMemoryPaymentGateway(
        scripted_outcomes={"order-6": ["timeout_after_charge", "success"]}
    )
    processor = PaymentProcessor(gateway, PaymentConfig(max_retries=1))

    result = processor.pay("order-6", amount_cents=1000)

    assert result.success is True
    assert result.attempts == 2
    assert gateway.charge_count_for("order-6") == 1
