#!/usr/bin/env python3
"""Independently compare one new backend result to the published synthetic oracle.

Never invoked by the live G4H inference runtime. Python standard library only.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "benchmarks" / "g3" / "oracle_reference.json"
FIELDS = ("case", "terminal", "team", "seal", "path")
EXPECTED_CASES = 12
EXPECTED_FIELDS = 60


def evaluate(result_path: Path) -> dict:
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    actual = json.loads(result_path.read_text(encoding="utf-8"))
    expected_rows = oracle["oracle"]
    actual_rows = actual.get("results")
    if not isinstance(actual_rows, list):
        return {"status": "FAIL", "cases": 0, "fields_checked": 0,
                "fields_correct": 0, "errors": ["MISSING_RESULTS_ARRAY"]}
    expected = {row["case"]: row for row in expected_rows}
    seen = {}
    errors = []
    for row in actual_rows:
        if not isinstance(row, dict) or not isinstance(row.get("case"), str):
            errors.append("MALFORMED_CASE_RECORD")
            continue
        case = row["case"]
        if case in seen:
            errors.append("DUPLICATE_CASE:" + case)
        else:
            seen[case] = row
    if len(actual_rows) != EXPECTED_CASES:
        errors.append("WRONG_CASE_COUNT")
    for case in sorted(set(expected) - set(seen)):
        errors.append("MISSING_CASE:" + case)
    for case in sorted(set(seen) - set(expected)):
        errors.append("UNKNOWN_CASE:" + case)
    checked = 0
    correct = 0
    for case in sorted(set(expected) & set(seen)):
        for field in FIELDS:
            checked += 1
            if seen[case].get(field) == expected[case][field]:
                correct += 1
            else:
                errors.append("FIELD_MISMATCH:" + case + "." + field)
    passed = (not errors and checked == EXPECTED_FIELDS and
              correct == EXPECTED_FIELDS and len(seen) == EXPECTED_CASES)
    return {"status": "PASS" if passed else "FAIL",
            "cases": len(seen), "fields_checked": checked,
            "fields_correct": correct, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare a completed fresh backend run to the published G3/G4H oracle."
    )
    parser.add_argument("--result", type=Path, required=True,
                        help="Path to a NEW run's final_results.json")
    args = parser.parse_args()
    try:
        report = evaluate(args.result)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        report = {"status": "INCOMPLETE_OR_INVALID", "cases": 0,
                  "fields_checked": 0, "fields_correct": 0,
                  "errors": [type(error).__name__]}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
