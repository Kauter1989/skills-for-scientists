#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Офлайн-самопроверка навыка на примере: без сети и без внешних библиотек.

Прогоняет анализ и отчёт на `examples/example-companies.json`, проверяет
инварианты методики и печатает итог. Используется в Verification Gate и в CI.

Использование:
    python scripts/test_example.py

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXAMPLES = ROOT / "examples"
FAILED: list[str] = []


def check(condition: bool, message: str) -> None:
    print(("  ok   " if condition else "  FAIL ") + message)
    if not condition:
        FAILED.append(message)


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")


def main() -> int:
    companies_path = EXAMPLES / "example-companies.json"
    profile_path = EXAMPLES / "example-profile.md"
    check(companies_path.is_file(), "снимок примера существует")
    if FAILED:
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        analysis_path = Path(tmp) / "analysis.json"
        report_path = Path(tmp) / "report.html"
        result = run("scripts/analyze.py", str(companies_path),
                     "--profile", str(profile_path), "-o", str(analysis_path), "--strict")
        check(result.returncode == 0, "analyze.py --strict без ошибок")
        if result.returncode != 0:
            print(result.stderr)
            return 1

        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        rf = analysis["cohorts"]["RF"]
        world = analysis["cohorts"]["WORLD"]

        check(rf["companies"] > 0 and world["companies"] > 0, "в обеих когортах есть проверенные компании")
        check(all(m["quality"] in {"measured", "derived", "estimated", "expert", "missing"}
                  for m in rf["metrics"] + world["metrics"]), "у каждой метрики есть метка качества")
        check(analysis["taxonomy"]["domains"], "таксономия зафиксирована в анализе")

        pending_ids = {p["id"] for p in rf["pending"] + world["pending"]}
        snapshot = json.loads(companies_path.read_text(encoding="utf-8"))
        counted = {c["id"] for c in snapshot["companies"] if c.get("cohort") in ("RF", "WORLD")
                   and not c.get("needsReview")}
        check(not (pending_ids & counted), "записи needsReview не попали в доли")

        gapped = [g for g in analysis["gaps"] if g["rfCount"] == 0 and g["worldCount"] >= 3]
        check(all(g["missingInRf"] for g in gapped), "пробелы отмечены при 0 в РФ и не менее 3 в мире")
        check(all(g["gapQuality"] in {"derived", "missing"} for g in analysis["gaps"]),
              "у разницы долей есть метка качества")

        result = run("scripts/build_report.py", "--analysis", str(analysis_path),
                     "--companies", str(companies_path), "-o", str(report_path), "--strict")
        check(result.returncode == 0, "build_report.py --strict без ошибок")

        result = run("scripts/check_report.py", str(report_path))
        check(result.returncode == 0, "check_report.py зелёный")
        if result.returncode != 0:
            print(result.stdout, result.stderr)

        html = report_path.read_text(encoding="utf-8")
        for marker in ("Россия", "Мир (без РФ)", "Разница рынков", "Методика"):
            check(marker in html, f"блок «{marker}» присутствует")
        check("<script src" not in html and "@import" not in html, "нет внешних скриптов и импортов")

    print()
    if FAILED:
        print(f"FAILED: {len(FAILED)}")
        return 1
    print("ok: все офлайн-проверки пройдены")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())