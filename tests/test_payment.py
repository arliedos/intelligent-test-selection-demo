"""T02 successful payment, T03 timeout/retry limit/config, T04 decline policy
(target), T05 duplicate-charge mandatory.

Target requirement (REQ-PAY-002, this branch): retry ONLY timeouts, up to
payment.max_retries (target value 2 via config/payment.json); declines are
never retried.
"""
import importlib.util
import json
from pathlib import Path

import pytest

from demoshop.config import PaymentConfig, load_payment_config
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


def test_target_decline_is_never_retried():
    """T04 (target) - target policy never retries a decline, even though
    max_retries > 0 would otherwise allow it."""
    gateway = InMemoryPaymentGateway(
        scripted_outcomes={"order-5": ["decline", "success"]}
    )
    processor = PaymentProcessor(
        gateway, PaymentConfig(max_retries=2, retry_on_decline=False)
    )

    result = processor.pay("order-5", amount_cents=1000)

    assert result.success is False
    assert result.attempts == 1
    assert gateway.call_count == 1


def test_default_loaded_config_reflects_target_policy():
    """T03/T04 (target) - config/payment.json on this branch must actually
    be loaded and drive behaviour: max_retries=2, decline never retried,
    timeout still retried. This proves the config isn't decorative."""
    config = load_payment_config()

    assert config.max_retries == 2
    assert config.retry_on_decline is False
    assert config.retry_on_timeout is True


def test_timeout_retried_up_to_target_max_retries_via_default_config():
    """T03 (target) - default (file-loaded) config now allows 2 retries."""
    gateway = InMemoryPaymentGateway(
        scripted_outcomes={"order-7": ["timeout", "timeout", "success"]}
    )
    processor = PaymentProcessor(gateway)  # no explicit config: loads from file

    result = processor.pay("order-7", amount_cents=1000)

    assert result.success is True
    assert result.attempts == 3  # 1 initial + 2 retries
    assert gateway.call_count == 3


def test_decline_via_default_config_is_never_retried():
    """T04 (target) - default (file-loaded) config never retries a decline,
    exercised end-to-end through PaymentProcessor's own config loading."""
    gateway = InMemoryPaymentGateway(scripted_outcomes={"order-8": ["decline"]})
    processor = PaymentProcessor(gateway)  # no explicit config: loads from file

    result = processor.pay("order-8", amount_cents=1000)

    assert result.success is False
    assert result.attempts == 1
    assert gateway.call_count == 1


def test_negative_max_retries_is_rejected():
    with pytest.raises(ValueError):
        PaymentConfig(max_retries=-1)


def test_load_payment_config_default_is_robust_to_install_layout(tmp_path):
    """T03 - default config discovery must not hardcode an exact number of
    parent directories between the module and the repo root. Reproduces
    the real failure mode of a non-editable/distributed install, where
    demoshop.config.py is not nested two levels below the directory that
    holds config/payment.json (e.g. site-packages/demoshop/config.py
    instead of <repo>/src/demoshop/config.py) - confirmed by installing
    this project non-editably into a scratch venv and observing
    `FileNotFoundError: ... .venv2\\Lib\\config\\payment.json`."""
    fake_root = tmp_path / "fake_site_packages"
    fake_demoshop_dir = fake_root / "demoshop"
    fake_demoshop_dir.mkdir(parents=True)

    real_config_src = Path(
        importlib.util.find_spec("demoshop.config").origin
    ).read_text(encoding="utf-8")
    (fake_demoshop_dir / "config.py").write_text(real_config_src, encoding="utf-8")

    # This is where a real (non-editable) install would place the package;
    # config/payment.json sits alongside it, not "two parents up".
    fake_config_dir = fake_root / "config"
    fake_config_dir.mkdir()
    fake_config_dir.joinpath("payment.json").write_text(
        json.dumps({"max_retries": 9, "retry_on_timeout": True, "retry_on_decline": True}),
        encoding="utf-8",
    )

    spec = importlib.util.spec_from_file_location(
        "demoshop_config_layout_probe", fake_demoshop_dir / "config.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    config = module.load_payment_config()

    assert config.max_retries == 9


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
