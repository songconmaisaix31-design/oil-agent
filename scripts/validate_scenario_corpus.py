"""Check fixed scenario data only; never run the application or fetch payload URLs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

DEFAULT_CORPUS = Path(__file__).resolve().parents[1] / "fixtures/scenarios/v01.json"
CATEGORIES = {"automated_local", "automated_postgresql", "external_manual"}
POSTGRES_CASES = {4, 5, 8, 9, 13, 14, 15, 16, 17, 18, 19, 25, 27}
EXTERNAL_CASES = {11, 14, 16, 17, 20, 23, 24, 25, 26, 28}
KINDS = {
    "event",
    "source_page",
    "model_failure",
    "quote",
    "report",
    "failure",
    "delivery",
    "callback",
    "source_failure",
    "network_input",
    "file_input",
    "access",
    "phone",
    "restore",
    "log_input",
    "budget",
}
DECIMAL_KEYS = {"value", "expected_delta", "test_absolute_threshold", "test_cost_cap"}


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def read_corpus(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def resolve_pointer(payload: object, pointer: str) -> object:
    if not pointer.startswith("/"):
        raise ValueError("An evidence reference must select a payload field")
    current = payload
    for token in pointer[1:].split("/"):
        if re.search(r"~(?![01])", token):
            raise ValueError("Invalid JSON pointer escape")
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise ValueError("Invalid array index")
            current = current[int(token)]
        elif isinstance(current, dict):
            current = current[token]
        else:
            raise ValueError("Evidence path traverses a scalar")
    return current


def validate(corpus: dict) -> list[str]:
    errors: list[str] = []

    def require(condition: bool, location: str, message: str) -> None:
        if not condition:
            errors.append(f"{location}: {message}")

    def nonempty(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def check_values(value: object, location: str, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child in value.items():
                check_values(child, f"{location}/{child_key}", child_key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                check_values(child, f"{location}/{index}", key)
        elif key.endswith("_at") or key == "as_of":
            if value is None:
                return
            try:
                parsed = datetime.fromisoformat(value)
                valid = value.endswith("Z") and parsed.utcoffset() == timedelta(0)
            except (TypeError, ValueError, AttributeError):
                valid = False
            require(valid, location, "timestamp must be UTC with Z, or null")
        elif key in DECIMAL_KEYS or key == "quote_values":
            try:
                valid = isinstance(value, str) and bool(re.fullmatch(r"-?[0-9]+\.[0-9]+", value))
                valid = valid and Decimal(value).is_finite()
            except (InvalidOperation, TypeError):
                valid = False
            require(valid, location, "price/metric must be a finite decimal string")
        elif isinstance(value, float):
            require(False, location, "floating-point values are not allowed in this corpus")

    if not isinstance(corpus, dict):
        return ["corpus: expected JSON object"]
    require(nonempty(corpus.get("corpus_version")), "corpus", "missing version")
    require(corpus.get("is_fixture") is True, "corpus", "must be labeled is_fixture=true")
    provenance = corpus.get("provenance", {})
    if not isinstance(provenance, dict):
        return errors + ["provenance: expected object"]
    require(provenance.get("category") == "synthetic", "provenance", "baseline is synthetic only")
    for key in ("id", "rights", "description", "authored_on"):
        require(nonempty(provenance.get(key)), "provenance", f"missing {key}")
    require(
        provenance.get("external_requests") == 0,
        "provenance",
        "baseline must not request external data",
    )
    defaults = corpus.get("defaults", {})
    required_defaults = {
        "environment": "test",
        "delivery_mode": "dry_run",
        "production_sending": False,
        "product_model_calls": False,
        "repeat_reminders": False,
        "sms_enabled": False,
        "phone_enabled": False,
        "first_report_policy": None,
        "timezone": "Asia/Shanghai",
    }
    if not isinstance(defaults, dict):
        return errors + ["defaults: expected object"]
    for key, expected in required_defaults.items():
        actual = defaults.get(key)
        require(
            key in defaults and type(actual) is type(expected) and actual == expected,
            "defaults",
            f"unsafe or missing {key}",
        )

    cases = corpus.get("cases")
    if not isinstance(cases, list) or not all(isinstance(case, dict) for case in cases):
        return errors + ["cases: expected array of objects"]
    ids = [case.get("case_id") for case in cases]
    require(
        ids == [f"T{number:02d}" for number in range(1, 29)],
        "cases",
        "must contain T01-T28 exactly once, in order",
    )
    for case in cases:
        case_id = case.get("case_id", "invalid-case")
        require(nonempty(case.get("title")), case_id, "missing title")
        require(nonempty(case.get("clock_at")), case_id, "missing fixed clock")
        inputs = case.get("inputs", [])
        if (
            not isinstance(inputs, list)
            or not inputs
            or not all(isinstance(item, dict) for item in inputs)
        ):
            errors.append(f"{case_id}: missing concrete inputs")
            continue
        input_map = {}
        for item in inputs:
            item_id = item.get("id")
            if not nonempty(item_id):
                errors.append(f"{case_id}: missing input ID")
                continue
            require(item_id not in input_map, case_id, "duplicate input ID")
            input_map[item_id] = item
            require(
                item.get("is_fixture") is True, case_id, "input must be labeled is_fixture=true"
            )
            require(
                item.get("provenance_ref") == provenance.get("id"),
                case_id,
                "unknown input provenance",
            )
            require(item.get("kind") in KINDS, case_id, "unknown scenario input kind")
            require(
                isinstance(item.get("payload"), dict) and bool(item["payload"]),
                case_id,
                "input needs a concrete payload",
            )
        expectations = case.get("expectations", [])
        if not isinstance(expectations, list) or not expectations:
            errors.append(f"{case_id}: missing expectations")
            continue
        referenced = set()
        for expectation in expectations:
            if not isinstance(expectation, dict):
                errors.append(f"{case_id}: malformed expectation")
                continue
            require(nonempty(expectation.get("assertion")), case_id, "empty expectation")
            refs = expectation.get("evidence_refs", [])
            if not isinstance(refs, list) or not refs:
                errors.append(f"{case_id}: expectation has no evidence references")
                continue
            for ref in refs:
                try:
                    input_id, pointer = ref.split("#", 1)
                    resolve_pointer(input_map[input_id]["payload"], pointer)
                    referenced.add(input_id)
                except (AttributeError, ValueError, KeyError, IndexError, TypeError):
                    errors.append(f"{case_id}: unresolved evidence reference")
        require(referenced == set(input_map), case_id, "every input must support an expectation")
        acceptance = case.get("acceptance", [])
        if not isinstance(acceptance, list) or not acceptance:
            errors.append(f"{case_id}: missing acceptance classification")
            continue
        categories = []
        for gate in acceptance:
            if not isinstance(gate, dict):
                errors.append(f"{case_id}: malformed acceptance entry")
                continue
            category = gate.get("category")
            require(category in CATEGORIES, case_id, "unknown acceptance category")
            require(gate.get("status") == "NOT_EXECUTED", case_id, "corpus is not a runtime result")
            require(nonempty(gate.get("requires")), case_id, "acceptance prerequisites required")
            categories.append(category)
        require(len(categories) == len(set(categories)), case_id, "duplicate acceptance category")
        if case_id in {f"T{n:02d}" for n in POSTGRES_CASES}:
            require(
                "automated_postgresql" in categories, case_id, "requires real PostgreSQL acceptance"
            )
        if case_id in {f"T{n:02d}" for n in EXTERNAL_CASES}:
            require(
                "external_manual" in categories,
                case_id,
                "requires separate external/manual acceptance",
            )
    check_values(corpus, "corpus")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    args = parser.parse_args()
    try:
        corpus = read_corpus(args.corpus)
        errors = validate(corpus)
    except (OSError, ValueError, TypeError):
        # Avoid echoing arbitrary payload text or filesystem details into public logs.
        print("FAIL: unable to read valid corpus JSON", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    categories = Counter(
        gate["category"] for case in corpus["cases"] for gate in case["acceptance"]
    )
    print(f"PASS: corpus consistency only; {len(corpus['cases'])} fixed synthetic cases")
    print(
        "Acceptance categories: "
        + ", ".join(f"{key}={value}" for key, value in sorted(categories.items()))
    )
    print(
        "NOT EXECUTED: all 28 application cases; "
        "PostgreSQL, browser, Feishu, phone and operational gates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
