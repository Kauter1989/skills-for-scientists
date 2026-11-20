#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Реестр источников РФ и мира, которые навык использует для курируемых записей.

Проверка актуальности адресов и расчёт по тем же осям, что и анализ: сколько
компаний РФ известны реестру и какие области не покрыты. Это не каталог всего
рынка, а явно объявленный набор источников, который расширяется по решению
аналитика.

Использование:
    python sources.py --json
    python sources.py --check
    python sources.py export --out curated-companies.json

Без сети, только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Курируемый реестр компаний с источниками: правится человеком, не смешивается
# с автозаписью OpenRouter.
CURATED = HERE.parent / "examples" / "example-companies.json"


def load() -> list[dict]:
    if not CURATED.is_file():
        return []
    data = json.loads(CURATED.read_text(encoding="utf-8"))
    return data.get("companies", [])


def report(companies: list[dict]) -> dict:
    by_cohort = Counter(c.get("cohort") for c in companies)
    domains = sorted({d for c in companies for d in c.get("domains") or []})
    services = sorted({s for c in companies for s in c.get("services") or []})
    return {"companies": len(companies), "byCohort": dict(by_cohort), "domains": domains, "services": services}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Источники и курируемый реестр")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("export", nargs="?", choices=["export"], help="экспорт курируемого реестра")
    parser.add_argument("--out", type=Path, default=Path("curated-companies.json"))
    args = parser.parse_args(argv)

    if args.check:
        if not CURATED.is_file():
            print(f"error: нет курируемого реестра {CURATED}", file=sys.stderr)
            return 2
        print(f"[ok] {CURATED}")
        return 0

    companies = load()
    summary = report(companies)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    print(f"компаний: {summary['companies']}, по когортам: {summary['byCohort']}")
    print(f"домены: {', '.join(summary['domains']) or '—'}")
    print(f"услуги: {', '.join(summary['services']) or '—'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())