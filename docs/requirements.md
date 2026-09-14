# DemoShop Requirements

These requirement IDs are referenced from `test-metadata/test-catalog.json`
and `test-metadata/traceability.json`. This is a **synthetic demo
application**; nothing here reflects a real production system.

## Auth (demo-only smoke, not production auth)

- **REQ-AUTH-001**: A user must have an authenticated session before
  checkout can proceed. Login validates username/password against an
  in-memory demo user store and raises `AuthError` on failure.

## Catalogue (independent of checkout -> payments -> gateway)

- **REQ-CATALOGUE-001**: Catalogue search returns products whose name
  contains the (case-insensitive) query substring; an empty query returns
  the full catalogue; no match returns an empty list.

## Profile (independent of checkout -> payments -> gateway)

- **REQ-PROFILE-001**: A user's profile (email, display name) can be
  updated. Email updates are validated against a basic email shape;
  updating an unknown profile raises `ProfileError`.

## Payments

- **REQ-PAY-001**: A successful charge attempt charges exactly once and
  the payment result reports success with the recorded charge.

- **REQ-PAY-002**: Payment retry policy (config-driven via
  `config/payment.json`, loaded by `demoshop.config.load_payment_config`).
  **Baseline** (branch `main`, tag `demo-baseline`): retry any failure —
  timeout or decline — up to `payment.max_retries` (baseline value: `1`).
  **Target** (branch `feature/payment-retry-policy`): retry **only**
  timeouts; declines are never retried; `payment.max_retries` raised to
  `2`.

- **REQ-PAY-004**: Idempotency. A retry using the same idempotency key as
  a prior attempt must never create a second charge, including when the
  gateway recorded the charge but the caller received a timeout for that
  same call (`timeout_after_charge`).

- **REQ-PAY-005**: `payment.max_retries` must be a non-negative integer;
  constructing a `PaymentConfig` with a negative value raises `ValueError`.

## Gateway

- **REQ-GATEWAY-001**: The in-memory gateway is deterministic (scripted
  outcomes per idempotency key, never randomised) and honours the
  timeout contract: `timeout` raises before any charge is recorded,
  `timeout_after_charge` raises after a charge is recorded, and a repeat
  call with an already-charged idempotency key returns the existing
  charge rather than creating a new one.

## Checkout (directed dependency: checkout -> payments -> gateway)

- **REQ-CHECKOUT-001**: The checkout result reports `status` (`success`
  or `failed`), an `order_id` (present only on success), the computed
  `total_cents`, and the underlying `PaymentResult`.

- **REQ-CHECKOUT-002** (critical journey, mandatory): The full journey —
  login, catalogue search, checkout, payment, gateway charge — must
  succeed end-to-end for a valid order using real module interaction
  (no mocked collaborators).

## Test metadata integrity (additional, not part of T01-T10)

- **REQ-META-001**: The test catalog's selectors must exactly match real
  pytest collection (no duplicates, no omissions), and every requirement
  ID referenced from `test-metadata/test-catalog.json` and
  `test-metadata/traceability.json` must exist in this document. Enforced
  by `scripts/verify_metadata.py` and `tests/test_metadata_integrity.py`.
