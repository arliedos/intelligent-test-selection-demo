"""Deterministic in-memory payment gateway.

Outcomes are scripted per idempotency key up front (never randomised), so
the same inputs always produce the same sequence of results. This models
a real payment network's failure modes without any network I/O:

- "success": charge succeeds and is recorded.
- "decline": charge is rejected; nothing is recorded.
- "timeout": the call fails before the gateway processed anything.
- "timeout_after_charge": the gateway recorded the charge, but the caller
  never received the acknowledgement (simulates a response that timed out
  after the write already happened). Idempotency keys ensure a retry does
  not create a second charge.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional


class DeclineError(Exception):
    """Raised when the gateway declines a charge."""


class GatewayTimeoutError(Exception):
    """Raised when the gateway call times out (with or without a recorded charge)."""


@dataclass(frozen=True)
class Charge:
    idempotency_key: str
    amount_cents: int
    status: str


class InMemoryPaymentGateway:
    """No randomness: outcomes are scripted per idempotency key."""

    def __init__(self, scripted_outcomes: Optional[Dict[str, List[str]]] = None) -> None:
        self._scripts: Dict[str, List[str]] = {
            key: list(outcomes) for key, outcomes in (scripted_outcomes or {}).items()
        }
        self._charges: Dict[str, Charge] = {}
        self.call_count = 0

    def charge(self, idempotency_key: str, amount_cents: int) -> Charge:
        self.call_count += 1

        existing = self._charges.get(idempotency_key)
        if existing is not None:
            return existing

        script = self._scripts.get(idempotency_key)
        outcome = script.pop(0) if script else "success"

        if outcome == "success":
            recorded = Charge(idempotency_key, amount_cents, status="success")
            self._charges[idempotency_key] = recorded
            return recorded

        if outcome == "decline":
            raise DeclineError(f"gateway declined charge for '{idempotency_key}'")

        if outcome == "timeout":
            raise GatewayTimeoutError(f"gateway timed out for '{idempotency_key}'")

        if outcome == "timeout_after_charge":
            recorded = Charge(idempotency_key, amount_cents, status="success")
            self._charges[idempotency_key] = recorded
            raise GatewayTimeoutError(
                f"gateway timed out for '{idempotency_key}' after recording charge"
            )

        raise ValueError(f"unknown scripted outcome '{outcome}'")

    def charge_count_for(self, idempotency_key: str) -> int:
        return 1 if idempotency_key in self._charges else 0
