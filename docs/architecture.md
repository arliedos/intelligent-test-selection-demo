# DemoShop Architecture

DemoShop is a synthetic, single-process Python application built to give a
read-only regression-suite-selection agent something real to reason about.
There are no network integrations, no external services, and no
randomness anywhere in the application: the "gateway" is an in-memory
stand-in that returns pre-scripted outcomes.

## Modules (`src/demoshop/`)

| Module        | Responsibility                                              |
|---------------|--------------------------------------------------------------|
| `auth.py`     | Demo-only login smoke layer (explicitly **not** production auth). |
| `catalogue.py`| In-memory product catalogue and search.                     |
| `profile.py`  | In-memory user profile store and update/validation.         |
| `checkout.py` | Orchestrates a checkout: requires an authenticated session, computes totals, calls payments. |
| `payments.py` | Retry orchestration on top of the gateway, driven by `PaymentConfig`. |
| `gateway.py`  | Deterministic in-memory payment gateway with scripted outcomes and idempotency-key deduplication. |
| `config.py`   | Loads `config/payment.json` into a validated `PaymentConfig`. |

## Dependency graph

```
checkout.py --> payments.py --> gateway.py
                    ^
                    |
              config.py (config/payment.json)

catalogue.py   (independent)
profile.py     (independent)
auth.py        (used by checkout.py to gate the journey; otherwise independent)
```

The machine-readable form of this graph lives in
`docs/dependency-map.json` and is what a selection agent should use to
reason about blast radius: a change to `gateway.py` or `config/payment.json`
can affect `payments.py` and `checkout.py`; a change to `catalogue.py` or
`profile.py` cannot affect the checkout chain.

## Config, not decoration

`payment.max_retries`, `retry_on_timeout`, and `retry_on_decline` are read
from `config/payment.json` by `demoshop.config.load_payment_config()` at
`PaymentProcessor` construction time (unless a `PaymentConfig` is passed
explicitly, which is what unit tests do for determinism). The **baseline**
and **target** git refs differ in both this config file's committed
content and in `payments.py`'s retry-decision logic — the retry-policy
change described in `docs/requirements.md` (REQ-PAY-002) is a real,
loaded, behavioural change, not metadata.

## Test layout

Tests live under `tests/` and map to primary catalog IDs T01-T10 as
described in `test-metadata/test-catalog.json`. Some catalog IDs cover
multiple pytest cases (e.g. parametrized-style variations written as
separate `test_*` functions for readability); every collected pytest test
is catalogued under exactly one ID — see
`test-metadata/traceability.json` and `scripts/verify_metadata.py`.

## What is synthetic vs. measured

- `test-metadata/synthetic-test-history.json` is **fabricated** example
  history metadata (e.g. an illustrative flaky-test scenario for T05) used
  only to give a selection agent something to reason about. It is
  explicitly labelled synthetic and does not reflect any real observed
  run. T05 itself is deterministic in this repository.
- Local run reports (`reports/junit.xml`, `reports/coverage.xml`,
  `htmlcov/`) are **measured** — produced by actually running pytest
  locally, per `README.md`.
- CI (`.github/workflows/ci.yml`) has not run yet in this repository
  (it is not published/pushed anywhere) — no CI-produced artifacts exist
  yet. Do not treat this repo as having CI-verified results until the
  parent process publishes it and a workflow run actually completes.
