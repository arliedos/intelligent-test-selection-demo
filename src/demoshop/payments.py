"""Payment processing: retry orchestration on top of the gateway.

Depends on demoshop.gateway (checkout -> payments -> gateway).
"""
from dataclasses import dataclass
from typing import Optional

from demoshop.config import PaymentConfig, load_payment_config
from demoshop.gateway import Charge, DeclineError, GatewayTimeoutError, InMemoryPaymentGateway


@dataclass(frozen=True)
class PaymentResult:
    success: bool
    attempts: int
    charge: Optional[Charge] = None
    error: Optional[str] = None


class PaymentProcessor:
    def __init__(self, gateway: InMemoryPaymentGateway, config: Optional[PaymentConfig] = None) -> None:
        self.gateway = gateway
        self.config = config if config is not None else load_payment_config()

    def pay(self, idempotency_key: str, amount_cents: int) -> PaymentResult:
        max_attempts = self.config.max_retries + 1
        attempts = 0
        last_error: Optional[str] = None

        while attempts < max_attempts:
            attempts += 1
            try:
                charge = self.gateway.charge(idempotency_key, amount_cents)
                return PaymentResult(success=True, attempts=attempts, charge=charge)
            except GatewayTimeoutError as exc:
                last_error = str(exc)
                if not self.config.retry_on_timeout:
                    break
            except DeclineError as exc:
                last_error = str(exc)
                if not self.config.retry_on_decline:
                    break

        return PaymentResult(success=False, attempts=attempts, error=last_error)
