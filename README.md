# DemoShop (intelligent-test-selection-demo)

A small, **synthetic** Python application used to evaluate a read-only
regression-suite-selection agent. It is not a real product: there are no
network integrations, no external services, and no randomness anywhere —
the payment gateway is a deterministic in-memory stand-in with scripted
outcomes.

Auth is an explicit **demo-only smoke layer**, not production
authentication (plaintext in-memory credential check, used only to gate
the checkout journey in this sandbox).

## Journeys covered

- Login (demo-only auth smoke) — `demoshop.auth`
- Catalogue search — `demoshop.catalogue` (independent)
- Profile update — `demoshop.profile` (independent)
- Checkout -> payments -> gateway (directed dependency chain) —
  `demoshop.checkout` -> `demoshop.payments` -> `demoshop.gateway`,
  configured by `config/payment.json` via `demoshop.config`.

See `docs/architecture.md` for the module map and dependency graph, and
`docs/requirements.md` for requirement IDs (`REQ-*`).

## Requirements

- Python 3.11+ (native Windows path example below uses `python`; on this
  machine `python3` is not available — use `python`).
- Git Bash / PowerShell.

## Setup

From `C:/Users/arlie/qe-sandbox/intelligent-test-selection-demo`:

```
python -m venv .venv
.venv/Scripts/python -m pip install --upgrade pip
.venv/Scripts/python -m pip install -e ".[dev]"
```

## Running tests

```
.venv/Scripts/python -m pytest -q
```

### Generating run reports (JUnit + coverage)

This is the exact command CI (`.github/workflows/ci.yml`) also runs:

```
.venv/Scripts/python -m pytest --junitxml=reports/junit.xml --cov=demoshop --cov-report=xml:reports/coverage.xml --cov-report=term
```

Report/output directories (`reports/`, `htmlcov/`, `.pytest_cache/`,
`*.egg-info/`, `.venv/`) are all git-ignored — see `.gitignore`.

### Metadata integrity check

Confirms the test catalog's selectors exactly match real pytest
collection, and that requirement/critical-journey references resolve:

```
.venv/Scripts/python scripts/verify_metadata.py
```

## Test catalog

Exactly ten primary catalog test IDs (T01-T10) plus one additional
metadata self-check entry (A01) are defined in
`test-metadata/test-catalog.json`, with exact pytest selectors,
components, requirement refs, and `mandatory` flags. `T01`, `T05`, and
`T10` are mandatory/protected (see `test-metadata/critical-journeys.json`).

| ID  | Title                                              |
|-----|-----------------------------------------------------|
| T01 | Login mandatory                                      |
| T02 | Successful payment                                   |
| T03 | Timeout / retry limit / config                       |
| T04 | Decline policy (baseline allows retry, target forbids) |
| T05 | Duplicate-charge prevention (mandatory)              |
| T06 | Checkout result                                      |
| T07 | Catalogue search                                     |
| T08 | Profile edit                                         |
| T09 | Gateway timeout contract                             |
| T10 | Checkout critical journey (mandatory)                |

## Baseline vs. target retry policy

- **Baseline** (`main`, tag `demo-baseline`, `config/payment.json`
  `max_retries=1`): retries **any** failure (timeout or decline) up to
  `payment.max_retries`.
- **Target** (`feature/payment-retry-policy`, `config/payment.json`
  `max_retries=2`): retries **only** timeouts; declines are never
  retried.
- Idempotency (`demoshop.gateway`) prevents duplicate charges on retry in
  both baseline and target, including when a timeout occurs *after* the
  gateway already recorded the charge.
- `PaymentConfig(max_retries=-1)` raises `ValueError` in both branches.

Both branches have a fully passing test suite according to their own
requirements — they are not meant to be merged as part of this build.

## What is synthetic vs. measured vs. unavailable

- `test-metadata/synthetic-test-history.json` is **fabricated** example
  flaky-history metadata, explicitly labelled `"synthetic": true`. It does
  not reflect any observed run.
- Local run output (pytest pass/fail counts, coverage %, `reports/junit.xml`,
  `reports/coverage.xml`) referenced in this README and in
  `evaluator/tdd-evidence.md` (outside this repo) is **measured** — it was
  produced by actually running the commands above.
- `.github/workflows/ci.yml` exists and has been validated by running its
  exact pytest command locally, but this repository has not been pushed
  anywhere, so **no CI run has actually executed it yet**. Treat CI as
  unavailable/unverified until a parent process publishes this repository
  and a workflow run completes.

## Repository layout

```
src/demoshop/            application code (src layout)
tests/                   pytest test suite
config/payment.json      payment retry policy config (loaded at runtime)
docs/                    requirements, architecture, dependency map, selection policy
test-metadata/           test catalog, traceability, critical journeys, synthetic history
scripts/verify_metadata.py  metadata integrity checker
.github/workflows/ci.yml CI (push + pull_request), not yet run (not published)
```
