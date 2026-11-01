#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверить отчёт о дефекте и его evidence.

Использование:
    python check_bug_report.py --root . --report docs/bugs/<id>/repro.json
    python check_bug_report.py --root . --report docs/bugs/<id>/repro.json --strict --json

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STATUSES = {"reproduced", "not-reproduced", "flaky", "blocked"}
CONFIDENCE = {"measured", "derived", "estimated", "expert", "missing"}
GOOD_CONFIDENCE = {"measured", "derived"}


def read_min_runs(root: Path) -> int:
    manifest = root / ".opencode" / "bug-processing.yml"
    if not manifest.is_file():
        return 3
    for raw in manifest.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("min_runs:"):
            value = line.split(":", 1)[1].strip()
            try:
                return max(1, int(value))
            except ValueError:
                return 3
    return 3


def load_json(path: Path, errors: list[str], label: str) -> dict:
    if not path.is_file():
        errors.append(f"нет {label}: {path}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{label}: невалидный JSON: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append(f"{label}: ожидался объект")
        return {}
    return data


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверить отчёт о дефекте")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    report_path = args.report if args.report.is_absolute() else root / args.report
    errors: list[str] = []
    warnings: list[str] = []

    data = load_json(report_path, errors, "repro.json")
    min_runs = read_min_runs(root)

    if data:
        if data.get("version") != 1:
            errors.append("version должен быть 1")
        bug_id = data.get("id")
        if not non_empty(bug_id):
            errors.append("id не заполнен")
        elif report_path.parent.name != bug_id:
            errors.append(f"id={bug_id!r} не совпадает с каталогом {report_path.parent.name!r}")

        status = data.get("status")
        if status not in STATUSES:
            errors.append(f"status={status!r}, ожидается одно из {sorted(STATUSES)}")

        for field in ("symptom", "expected", "actual", "environment", "command"):
            if not non_empty(data.get(field)):
                errors.append(f"{field} не заполнен")

        runs = data.get("runs")
        if not isinstance(runs, int) or isinstance(runs, bool):
            errors.append("runs должен быть целым числом")
            runs = 0
        if status != "blocked" and runs < min_runs:
            errors.append(f"runs={runs}, нужно минимум {min_runs}")
        if runs < 0:
            errors.append("runs не может быть отрицательным")

        results = data.get("results")
        failed = passed = 0
        if not isinstance(results, dict):
            errors.append("results должен быть объектом")
        else:
            failed = results.get("failed")
            passed = results.get("passed")
            if not isinstance(failed, int) or isinstance(failed, bool):
                errors.append("results.failed должен быть целым числом")
                failed = 0
            if not isinstance(passed, int) or isinstance(passed, bool):
                errors.append("results.passed должен быть целым числом")
                passed = 0
            if failed < 0 or passed < 0:
                errors.append("results не может быть отрицательным")
            if runs and failed + passed != runs:
                errors.append(f"results.failed + results.passed = {failed + passed}, runs = {runs}")

        if status == "reproduced":
            if runs and failed != runs:
                errors.append("reproduced требует failed == runs")
            if not non_empty(data.get("minimal_case")):
                errors.append("reproduced требует minimal_case")
            removed = data.get("removed")
            if not isinstance(removed, list) or not removed:
                errors.append("reproduced требует непустой removed")
        elif status == "flaky":
            if not (failed > 0 and passed > 0):
                errors.append("flaky требует и failed, и passed")
            if not non_empty(data.get("minimal_case")):
                warnings.append("flaky без minimal_case")
            if not data.get("next_steps"):
                errors.append("flaky требует next_steps")
            if args.strict:
                errors.append("strict: flaky не проходит гейт; нужен стабильный red test")
        elif status == "not-reproduced":
            if runs and failed != 0:
                errors.append("not-reproduced требует failed == 0")
            if not data.get("next_steps"):
                errors.append("not-reproduced требует next_steps")
        elif status == "blocked":
            if not non_empty(data.get("blocked_reason")):
                errors.append("blocked требует blocked_reason")

        test = data.get("test")
        if not isinstance(test, dict):
            errors.append("test должен быть объектом")
            test = {}
        if status == "reproduced":
            test_path = test.get("path")
            if not non_empty(test_path):
                errors.append("reproduced требует test.path")
            else:
                candidate = Path(test_path)
                if not candidate.is_absolute():
                    candidate = root / candidate
                if not candidate.is_file():
                    errors.append(f"test.path не существует: {candidate}")
            if not non_empty(test.get("name")):
                errors.append("reproduced требует test.name")
            if not non_empty(test.get("red_output")):
                errors.append("reproduced требует test.red_output")
            if test.get("failure_matches_symptom") is not True:
                errors.append("reproduced требует failure_matches_symptom: true")

        diagnosis = data.get("diagnosis")
        hypotheses = diagnosis.get("hypotheses") if isinstance(diagnosis, dict) else None
        if not isinstance(hypotheses, list):
            errors.append("diagnosis.hypotheses должен быть списком")
            hypotheses = []
        if status == "reproduced":
            if not hypotheses:
                errors.append("reproduced требует хотя бы одну гипотезу")
            good = 0
            for index, item in enumerate(hypotheses, 1):
                if not isinstance(item, dict):
                    errors.append(f"hypothesis {index}: ожидался объект")
                    continue
                for field in ("claim", "evidence", "next_probe"):
                    if not non_empty(item.get(field)):
                        errors.append(f"hypothesis {index}: {field} не заполнен")
                confidence = item.get("confidence")
                if confidence not in CONFIDENCE:
                    errors.append(f"hypothesis {index}: confidence={confidence!r}")
                elif confidence in GOOD_CONFIDENCE:
                    good += 1
                elif confidence in {"expert", "missing"}:
                    warnings.append(f"hypothesis {index}: confidence={confidence} не является доказательством")
            if hypotheses and good == 0:
                errors.append("нужна хотя бы одна гипотеза с confidence measured или derived")

        probe_path = data.get("probe_path")
        if status == "blocked":
            probe_path = None
        if non_empty(probe_path):
            candidate = Path(probe_path)
            if not candidate.is_absolute():
                candidate = root / candidate
            probe = load_json(candidate, errors, "probe.json")
            if probe:
                classification = probe.get("classification")
                expected = {
                    "reproduced": "deterministic-fail",
                    "flaky": "flaky",
                    "not-reproduced": "deterministic-pass",
                }.get(status)
                if expected and classification != expected:
                    errors.append(
                        f"probe.classification={classification!r}, для {status} ожидается {expected!r}"
                    )
                if probe.get("runs") != runs:
                    errors.append(f"probe.runs={probe.get('runs')}, repro.runs={runs}")
        elif status in {"reproduced", "flaky", "not-reproduced"}:
            errors.append(f"{status} требует probe_path")

    if args.strict:
        strict_errors = [f"strict: {item}" for item in warnings]
        errors.extend(strict_errors)
        warnings = []

    result = {
        "root": str(root),
        "report": str(report_path),
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "min_runs": min_runs,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"bug report: {report_path}")
        print(f"min_runs: {min_runs}")
        for error in errors:
            print(f"  error: {error}")
        for warning in warnings:
            print(f"  warn: {warning}")
        print("ok" if not errors else "failed")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())