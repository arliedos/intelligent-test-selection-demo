"""A01 - metadata integrity self-check (REQ-META-001, additional/not primary).

Verifies scripts/verify_metadata.py both against synthetic fixtures (to
prove it actually detects drift) and against the real repository metadata
(to prove the repository is currently consistent).
"""
from pathlib import Path

from scripts.verify_metadata import (
    REPO_ROOT,
    collect_catalog_test_ids,
    collect_critical_journey_test_ids,
    collect_pytest_node_ids,
    collect_referenced_requirements,
    diff_selectors,
    extract_requirement_ids,
    find_unknown_critical_journey_refs,
    find_unknown_requirements,
    flatten_catalog_selectors,
    load_json,
    run_all_checks,
)


def test_catalog_selectors_match_real_pytest_collection():
    catalog = load_json(REPO_ROOT / "test-metadata" / "test-catalog.json")
    catalog_selectors = flatten_catalog_selectors(catalog)
    collected = collect_pytest_node_ids(REPO_ROOT)

    diff = diff_selectors(catalog_selectors, collected)

    assert diff.missing_in_catalog == set(), diff.missing_in_catalog
    assert diff.missing_in_collection == set(), diff.missing_in_collection
    assert diff.duplicates == set(), diff.duplicates


def test_detects_selector_missing_from_catalog():
    catalog_selectors = ["tests/test_a.py::test_one"]
    collected = ["tests/test_a.py::test_one", "tests/test_a.py::test_two"]

    diff = diff_selectors(catalog_selectors, collected)

    assert diff.missing_in_catalog == {"tests/test_a.py::test_two"}
    assert diff.missing_in_collection == set()
    assert diff.duplicates == set()


def test_detects_selector_missing_from_collection():
    catalog_selectors = ["tests/test_a.py::test_one", "tests/test_a.py::test_gone"]
    collected = ["tests/test_a.py::test_one"]

    diff = diff_selectors(catalog_selectors, collected)

    assert diff.missing_in_collection == {"tests/test_a.py::test_gone"}
    assert diff.missing_in_catalog == set()


def test_detects_duplicate_selector_in_catalog():
    catalog_selectors = ["tests/test_a.py::test_one", "tests/test_a.py::test_one"]
    collected = ["tests/test_a.py::test_one"]

    diff = diff_selectors(catalog_selectors, collected)

    assert diff.duplicates == {"tests/test_a.py::test_one"}


def test_traceability_requirement_refs_exist_in_requirements_doc():
    catalog = load_json(REPO_ROOT / "test-metadata" / "test-catalog.json")
    traceability = load_json(REPO_ROOT / "test-metadata" / "traceability.json")
    requirements_text = (REPO_ROOT / "docs" / "requirements.md").read_text(encoding="utf-8")

    known = extract_requirement_ids(requirements_text)
    referenced = collect_referenced_requirements(catalog, traceability)
    unknown = find_unknown_requirements(referenced, known)

    assert unknown == set(), unknown


def test_detects_unknown_requirement_ref():
    known = {"REQ-AUTH-001"}
    referenced = {"REQ-AUTH-001", "REQ-DOES-NOT-EXIST"}

    unknown = find_unknown_requirements(referenced, known)

    assert unknown == {"REQ-DOES-NOT-EXIST"}


def test_critical_journey_test_ids_exist_in_catalog():
    catalog = load_json(REPO_ROOT / "test-metadata" / "test-catalog.json")
    critical_journeys = load_json(REPO_ROOT / "test-metadata" / "critical-journeys.json")

    catalog_ids = collect_catalog_test_ids(catalog)
    journey_ids = collect_critical_journey_test_ids(critical_journeys)
    unknown = find_unknown_critical_journey_refs(journey_ids, catalog_ids)

    assert unknown == set(), unknown
    assert {"T01", "T05", "T10"}.issubset(journey_ids)


def test_run_all_checks_passes_on_real_repo():
    report = run_all_checks(REPO_ROOT)

    assert report.ok, report.issues
