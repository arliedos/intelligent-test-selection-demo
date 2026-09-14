"""Metadata integrity verification (REQ-META-001).

Checks that:
  1. test-metadata/test-catalog.json selectors exactly match real pytest
     collection - no selector collected-but-not-catalogued, none
     catalogued-but-not-collected, and no duplicate selectors.
  2. every requirement ID referenced from test-catalog.json or
     traceability.json is actually documented in docs/requirements.md.
  3. every test ID referenced from critical-journeys.json exists in the
     test catalog.

Run directly: `python scripts/verify_metadata.py` (exit 0 = OK, 1 = FAILED).
"""
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Set

REPO_ROOT = Path(__file__).resolve().parents[1]

REQ_ID_PATTERN = re.compile(r"REQ-[A-Z]+-\d+")
NODE_ID_PATTERN = re.compile(r"^tests/[\w./\\-]+\.py::[\w\[\]\-.:]+$")


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def collect_pytest_node_ids(repo_root: Path) -> List[str]:
    """Runs real pytest collection (no fabrication) and parses node IDs."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    return [
        line.strip()
        for line in result.stdout.splitlines()
        if NODE_ID_PATTERN.match(line.strip())
    ]


def flatten_catalog_selectors(catalog: dict) -> List[str]:
    selectors: List[str] = []
    for section in ("primary_tests", "additional_tests"):
        for entry in catalog.get(section, []):
            selectors.extend(entry.get("selectors", []))
    return selectors


@dataclass(frozen=True)
class SelectorDiff:
    missing_in_catalog: Set[str]
    missing_in_collection: Set[str]
    duplicates: Set[str]


def diff_selectors(catalog_selectors: Iterable[str], collected: Iterable[str]) -> SelectorDiff:
    catalog_list = list(catalog_selectors)
    catalog_set = set(catalog_list)
    collected_set = set(collected)

    duplicates = {s for s in catalog_set if catalog_list.count(s) > 1}
    missing_in_catalog = collected_set - catalog_set
    missing_in_collection = catalog_set - collected_set

    return SelectorDiff(
        missing_in_catalog=missing_in_catalog,
        missing_in_collection=missing_in_collection,
        duplicates=duplicates,
    )


def extract_requirement_ids(text: str) -> Set[str]:
    return set(REQ_ID_PATTERN.findall(text))


def collect_referenced_requirements(catalog: dict, traceability: dict) -> Set[str]:
    referenced: Set[str] = set()
    for section in ("primary_tests", "additional_tests"):
        for entry in catalog.get(section, []):
            referenced.update(entry.get("requirements", []))
    referenced.update(traceability.get("requirements", {}).keys())
    return referenced


def find_unknown_requirements(referenced: Set[str], known: Set[str]) -> Set[str]:
    return referenced - known


def collect_catalog_test_ids(catalog: dict) -> Set[str]:
    ids: Set[str] = set()
    for section in ("primary_tests", "additional_tests"):
        for entry in catalog.get(section, []):
            ids.add(entry["id"])
    return ids


def collect_critical_journey_test_ids(critical_journeys: dict) -> Set[str]:
    ids: Set[str] = set(critical_journeys.get("protected_test_ids", []))
    for journey in critical_journeys.get("journeys", []):
        ids.update(journey.get("protected_test_ids", []))
        if "primary_test_id" in journey:
            ids.add(journey["primary_test_id"])
    return ids


def find_unknown_critical_journey_refs(journey_ids: Set[str], catalog_ids: Set[str]) -> Set[str]:
    return journey_ids - catalog_ids


@dataclass
class VerificationReport:
    ok: bool
    issues: List[str] = field(default_factory=list)


def run_all_checks(repo_root: Path) -> VerificationReport:
    issues: List[str] = []

    catalog = load_json(repo_root / "test-metadata" / "test-catalog.json")
    traceability = load_json(repo_root / "test-metadata" / "traceability.json")
    critical_journeys = load_json(repo_root / "test-metadata" / "critical-journeys.json")
    requirements_text = (repo_root / "docs" / "requirements.md").read_text(encoding="utf-8")

    catalog_selectors = flatten_catalog_selectors(catalog)
    collected = collect_pytest_node_ids(repo_root)
    selector_diff = diff_selectors(catalog_selectors, collected)
    if selector_diff.missing_in_catalog:
        issues.append(
            f"selectors collected but not catalogued: {sorted(selector_diff.missing_in_catalog)}"
        )
    if selector_diff.missing_in_collection:
        issues.append(
            f"catalogued selectors not collected by pytest: {sorted(selector_diff.missing_in_collection)}"
        )
    if selector_diff.duplicates:
        issues.append(f"duplicate selectors in catalog: {sorted(selector_diff.duplicates)}")

    known_requirements = extract_requirement_ids(requirements_text)
    referenced_requirements = collect_referenced_requirements(catalog, traceability)
    unknown_requirements = find_unknown_requirements(referenced_requirements, known_requirements)
    if unknown_requirements:
        issues.append(
            f"requirement IDs referenced but not documented in docs/requirements.md: "
            f"{sorted(unknown_requirements)}"
        )

    catalog_ids = collect_catalog_test_ids(catalog)
    journey_ids = collect_critical_journey_test_ids(critical_journeys)
    unknown_journey_refs = find_unknown_critical_journey_refs(journey_ids, catalog_ids)
    if unknown_journey_refs:
        issues.append(
            f"critical-journeys.json references test IDs missing from the catalog: "
            f"{sorted(unknown_journey_refs)}"
        )

    return VerificationReport(ok=not issues, issues=issues)


def main(argv=None) -> int:
    report = run_all_checks(REPO_ROOT)
    if report.ok:
        print(
            "verify_metadata: OK - catalog selectors, pytest collection, "
            "requirement refs, and critical-journey refs are all consistent."
        )
        return 0

    print("verify_metadata: FAILED")
    for issue in report.issues:
        print(f"  - {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
