# Test Selection Policy

This document describes the **behavior** a read-only regression-suite-selection
agent is expected to exhibit against this repository. It intentionally does
**not** state which specific test IDs it would pick for any given diff —
that expected-selection answer key is kept outside this repository (see
`docs/architecture.md`'s note on evaluator materials).

## Inputs available to a selection agent

- `test-metadata/test-catalog.json` — exact pytest selectors per test ID,
  component, requirement refs, and `mandatory` flag.
- `test-metadata/traceability.json` — requirement -> test ID mapping.
- `test-metadata/critical-journeys.json` — protected/mandatory test IDs
  and the critical-journey component chain.
- `docs/dependency-map.json` — directed module dependency graph.
- `docs/requirements.md` — human-readable requirement definitions.
- `test-metadata/synthetic-test-history.json` — **synthetic, fabricated**
  illustrative flakiness metadata (see its own `synthetic: true` field and
  disclaimer). Never treat this as an observed/measured result.

## Selection principles

1. **Protected tests are never excluded.** `T01`, `T05`, and `T10` are
   marked `"mandatory": true` in the test catalog and listed in
   `protected_test_ids` in `critical-journeys.json`. Any selected subset
   must include all protected tests regardless of which files changed.

2. **Dependency-aware inclusion.** The dependency graph is directed:
   `checkout -> payments -> gateway` (`docs/dependency-map.json`). A change
   to `gateway.py` or `config/payment.json` should pull in tests for
   `payments` and `checkout` (their downstream dependents), not just the
   gateway's own tests. `catalogue.py` and `profile.py` are independent of
   this chain and of each other.

3. **Config changes are code changes.** `config/payment.json` is loaded
   and used by `demoshop.config.load_payment_config()` — a change to that
   file must be treated the same as a change to the Python module that
   reads it (i.e. it should pull in the payments/checkout test IDs), not
   dismissed as inert metadata.

4. **Requirement-driven inclusion.** Where a change is scoped to a
   requirement rather than a file (e.g. "implement REQ-PAY-002 target
   behavior"), use `test-metadata/traceability.json` to resolve the
   requirement to its covering test IDs.

5. **Synthetic history is a hint, never a veto.** `synthetic-test-history.json`
   is fabricated for evaluation purposes. A selection agent may use it to
   reason about *retaining* a uniquely-covering flaky test rather than
   dropping it, but must never use it to justify *excluding* a mandatory
   or otherwise in-scope test, and must never present it as measured data.

6. **Read-only.** A selection agent operating against this repository must
   not write to the repository, modify metadata, or execute unauthorized
   commands — it reads the catalog/graph/docs above and returns a
   selection decision.

7. **Unsupported scope is reported, not guessed.** If a diff touches a
   component with no catalog entry, or a revision/ref that doesn't exist,
   or metadata is missing/stale relative to the actual pytest collection
   (see `scripts/verify_metadata.py`), the agent should report that
   explicitly rather than silently guessing a selection.

## Verifying the catalog itself

`scripts/verify_metadata.py` (exercised by `tests/test_metadata_integrity.py`,
catalog ID `A01`) checks that:

- Every pytest-collected test selector appears in
  `test-metadata/test-catalog.json` exactly once (no omissions, no
  duplicates).
- Every requirement ID referenced from the catalog or from
  `traceability.json` is documented in `docs/requirements.md`.
- Every test ID referenced from `critical-journeys.json` exists in the
  catalog.

Run it locally with:

```
python scripts/verify_metadata.py
```
