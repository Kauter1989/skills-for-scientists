#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снимок компаний -> analysis.json: динамика по осям и пробелы РФ.

Детерминированный расчёт без сети. Все метрики получают метку качества:
`measured`, `derived`, `estimated`, `expert` или `missing`.

Динамика между снимками считается только для пар снимков, у которых совпадает
таксономия (schemaVersion и набор осей). Если дат основания нет, «прирост по
годам» не выдумывается: метрика получает `missing`.

Использование:
    python analyze.py companies-2026-11-06.json -o analysis.json --strict
    python analyze.py now.json --previous earlier.json -o analysis.json
    python analyze.py --example -o examples/example-analysis.json --strict

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROLES = ("developer", "integrator")
DOMAINS = ("med", "fin", "industrial", "security", "education", "media", "agro", "public", "mobility")
SERVICES = (
    "consulting", "integration", "development", "licensing", "mlops",
    "data_services", "support", "training", "hardware",
)
PAK = ("none", "ai_component", "ai_system", "ai_software_package")
DELIVERY = ("api", "on_prem", "saas", "pak", "none")
QUALITY = ("measured", "derived", "estimated", "expert", "missing")
COHORTS = ("RF", "WORLD")
GAP_MIN_COHORT = 10
GAP_MIN_GLOBAL = 3
HERE = Path(__file__).resolve().parent


def metric(name: str, value, unit: str, level: str, note: str, evidence: list[str] | None = None) -> dict:
    return {
        "id": name,
        "value": value,
        "unit": unit,
        "quality": level,
        "note": note,
        "evidence": evidence or [],
    }


def validate_snapshot(snapshot: dict, strict: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if snapshot.get("schemaVersion") != 1:
        errors.append("schemaVersion должен быть 1")
    if not snapshot.get("snapshotDate"):
        errors.append("нет snapshotDate")
    companies = snapshot.get("companies")
    if not isinstance(companies, list) or not companies:
        errors.append("companies пуст: анализ без компаний не имеет смысла")
        return errors, warnings

    seen: set[str] = set()
    for index, company in enumerate(companies):
        label = company.get("id") or f"#{index}"
        if not company.get("id"):
            errors.append(f"{label}: нет id")
        elif company["id"] in seen:
            errors.append(f"{label}: повторяющийся id")
        seen.add(company.get("id"))
        if company.get("cohort") not in COHORTS:
            errors.append(f"{label}: cohort должен быть одним из {COHORTS}")
        roles = company.get("roles") or []
        if not roles and not company.get("needsReview"):
            errors.append(f"{label}: нет roles")
        for role in roles:
            if role not in ROLES:
                errors.append(f"{label}: роль {role!r} вне таксономии {ROLES}")
        for axis, allowed in (("domains", DOMAINS), ("services", SERVICES)):
            for value in company.get(axis) or []:
                if value not in allowed:
                    errors.append(f"{label}: {axis} {value!r} вне таксономии")
        pak = company.get("pak", "none")
        if pak not in PAK:
            errors.append(f"{label}: pak {pak!r} вне таксономии {PAK}")
        delivery = company.get("delivery")
        if delivery is not None and delivery not in DELIVERY:
            errors.append(f"{label}: delivery {delivery!r} вне таксономии {DELIVERY}")
        if company.get("quality") not in QUALITY:
            errors.append(f"{label}: quality должен быть одним из {QUALITY}")
        evidence = company.get("evidence") or []
        if strict:
            if not evidence:
                errors.append(f"{label}: нет evidence (URL и дата)")
            for item in evidence:
                if not str(item.get("url", "")).startswith(("http://", "https://")):
                    errors.append(f"{label}: evidence.url должен быть http(s)")
                if not item.get("retrievedAt"):
                    errors.append(f"{label}: evidence.retrievedAt обязателен")
            if company.get("cohort") == "RF" and not company.get("site") and not company.get("needsReview"):
                warnings.append(f"{label}: у компании РФ нет site")
        elif not (company.get("domains") or []):
            warnings.append(f"{label}: домен не указан -> missing")
    return errors, warnings


def share(counter: Counter, total: int) -> float | None:
    if total <= 0:
        return None
    return round(100.0 * counter / total, 1)


def gini(values: list[int]) -> float | None:
    if not values or sum(values) == 0:
        return None
    ordered = sorted(values)
    n = len(ordered)
    cumulative = sum((i + 1) * v for i, v in enumerate(ordered))
    total = sum(ordered)
    return round((2 * cumulative) / (n * total) - (n + 1) / n, 3)


def cohort_block(companies: list[dict], cohort: str) -> dict:
    all_members = [c for c in companies if c.get("cohort") == cohort]
    pending = [c for c in all_members if c.get("needsReview")]
    # Записи, требующие ручной проверки, не участвуют в долях: иначе публикация
    # одного сообщения превращала бы компанию в «игрока рынка».
    members = [c for c in all_members if not c.get("needsReview")]
    total = len(members)
    domain_counts = Counter(d for c in members for d in set(c.get("domains") or []))
    service_counts = Counter(s for c in members for s in set(c.get("services") or []))
    pak_counts = Counter(c.get("pak", "none") for c in members)
    role_counts = Counter(r for c in members for r in set(c.get("roles") or []))
    country_counts = Counter(c.get("country") for c in members if c.get("country"))
    year_counts = Counter(c["founded"] for c in members if isinstance(c.get("founded"), int))
    undated = total - sum(year_counts.values())
    with_pak = total - pak_counts.get("none", 0)
    by_quality = Counter(c.get("quality", "missing") for c in members)
    defaulted = sum(1 for c in members if c.get("source", "").startswith("collect.py"))
    other = total - defaulted

    return {
        "cohort": cohort,
        "companies": total,
        "verified": total,
        "needsReview": len(pending),
        "metrics": [
            metric("AIC", total, "компаний", "measured" if total else "missing",
                   f"активные компании когорты на дату снимка; ещё {len(pending)} записей ждут проверки"),
            metric("PSS", share(with_pak, total), "%", "derived" if total else "missing",
                   f"доля компаний с ПАК ({with_pak} из {total})"),
            metric("UDI", share(len(domain_counts), total), "%", "derived",
                   f"покрыто {len(domain_counts)} доменов из {len(DOMAINS)}"),
            metric("UID", share(len(service_counts), total), "%", "derived",
                   f"покрыто {len(service_counts)} услуг из {len(SERVICES)}; "
                   f"{defaulted} записей из {total} собраны автоматически, их услуги — "
                   f"значение по умолчанию сборщика, а не подтверждённый факт"),
            metric("GINI", gini([role_counts.get(r, 0) for r in ROLES]), "коеф.", "derived",
                   "концентрация ролей внутри когорты"),
            metric("FOUNDED_COV", share(total - undated, total), "%", "derived" if total else "missing",
                   f"год основания известен у {total - undated} из {total}; без него динамика не считается"),
        ],
        "pending": [{"id": c.get("id"), "name": c.get("name"), "quality": c.get("quality", "missing")}
                    for c in pending],
        "pendingBySource": dict(Counter(c.get("source", "?") for c in pending)),
        "roles": {r: role_counts.get(r, 0) for r in ROLES},
        "domains": {d: {"count": domain_counts.get(d, 0), "share": share(domain_counts.get(d, 0), total)}
                    for d in DOMAINS},
        "services": {s: {"count": service_counts.get(s, 0), "share": share(service_counts.get(s, 0), total)}
                     for s in SERVICES},
        "pak": {p: {"count": pak_counts.get(p, 0), "share": share(pak_counts.get(p, 0), total)} for p in PAK},
        "countries": dict(country_counts.most_common(12)),
        "foundedByYear": dict(sorted(year_counts.items())),
        "quality": dict(by_quality),
        "autoCollected": defaulted,
        "curated": other,
        "undated": undated,
    }


def yearly_growth(cohort: dict) -> dict:
    by_year = {int(k): v for k, v in cohort["foundedByYear"].items()}
    if len(by_year) < 3 or cohort["companies"] < GAP_MIN_COHORT:
        return metric("DD_YEAR", None, "компаний/год", "missing",
                      "ряд по годам основания короче трёх точек или когорта меньше порога")
    years = sorted(by_year)
    counts = [0]
    running = 0
    for year in years:
        running += by_year[year]
        counts.append(running)
    deltas = [counts[i + 1] - counts[i] for i in range(len(counts) - 1)]
    avg = round(sum(deltas) / len(deltas), 2)
    return metric("DD_YEAR", avg, "компаний/год", "estimated",
                  f"осреднённый прирост по годам основания {years[0]}–{years[-1]}; "
                  f"не является данными о выходе компаний на рынок")


def gap_block(rf: dict, world: dict) -> list[dict]:
    gaps = []
    for axis in ("domains", "services"):
        for key, rf_value in rf[axis].items():
            world_value = world[axis][key]
            if rf["companies"] >= GAP_MIN_COHORT and world["companies"] >= GAP_MIN_COHORT:
                gap = round((world_value["share"] or 0) - (rf_value["share"] or 0), 1)
                level = "derived"
                note = "разница долей (мир минус РФ), не разница компаний"
            else:
                gap = None
                level = "missing"
                note = f"доля не считается: нужно минимум {GAP_MIN_COHORT} компаний в когорте"
            gaps.append({
                "axis": axis,
                "key": key,
                "rfCount": rf_value["count"],
                "rfShare": rf_value["share"],
                "worldCount": world_value["count"],
                "worldShare": world_value["share"],
                "gapShare": gap,
                "gapQuality": level,
                "note": note,
                "missingInRf": rf_value["count"] == 0 and world_value["count"] >= GAP_MIN_GLOBAL,
            })
    gaps.sort(key=lambda item: (item["gapShare"] is None, -(item["gapShare"] or 0)))
    return gaps


def build_analysis(snapshot: dict, previous: dict | None = None, profile: dict | None = None) -> dict:
    companies = snapshot["companies"]
    rf = cohort_block(companies, "RF")
    world = cohort_block(companies, "WORLD")

    rf_roles = set()
    world_roles = set()
    for company in companies:
        roles = set(company.get("roles") or [])
        if company.get("cohort") == "RF":
            rf_roles |= roles
        else:
            world_roles |= roles
    role_gap = sorted(world_roles - rf_roles)

    analysis = {
        "schemaVersion": 1,
        "snapshotDate": snapshot.get("snapshotDate"),
        "generatedFrom": snapshot.get("snapshotDate"),
        "taxonomy": {
            "roles": list(ROLES),
            "domains": list(DOMAINS),
            "services": list(SERVICES),
            "pak": list(PAK),
            "delivery": list(DELIVERY),
        },
        "thresholds": {"gapMinCohort": GAP_MIN_COHORT, "gapMinGlobal": GAP_MIN_GLOBAL},
        "cohorts": {"RF": rf, "WORLD": world},
        "growth": {
            "RF": yearly_growth(rf),
            "WORLD": yearly_growth(world),
        },
        "gaps": gap_block(rf, world),
        "roleGap": role_gap,
        "missingInRf": [g for g in gap_block(rf, world) if g["missingInRf"]],
        "caveats": list(snapshot.get("warnings") or []),
    }

    if previous:
        analysis["changes"] = {
            "from": previous.get("snapshotDate"),
            "to": snapshot.get("snapshotDate"),
            "note": "сравнение снимков одной методологии; новый снимок не пересчитывает прошлый",
            "newCompanies": sorted(set(c["id"] for c in companies) - set(c["id"] for c in previous.get("companies", []))),
            "droppedCompanies": sorted(set(c["id"] for c in previous.get("companies", [])) - set(c["id"] for c in companies)),
        }
    else:
        analysis["changes"] = {
            "from": None, "to": snapshot.get("snapshotDate"),
            "note": "один снимок: динамика между снимками недоступна, помечена missing",
            "newCompanies": [], "droppedCompanies": [],
        }

    if profile:
        analysis["profile"] = profile
    return analysis


def profile_from_md(path: Path) -> dict:
    """Минимальное чтение MD-профиля: заголовки ## и строки `- key: value`."""
    data: dict[str, dict] = {}
    section = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            section = line[3:].strip()
            data[section] = {}
        elif section and line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            data[section][key.strip()] = value.strip()
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Снимок -> анализ рынка")
    parser.add_argument("snapshot", nargs="?")
    parser.add_argument("--previous", type=Path, help="предыдущий снимок для динамики")
    parser.add_argument("--profile", type=Path, help="MD-профиль")
    parser.add_argument("--merge", type=Path, action="append", default=[],
                        help="дополнительный снимок (например, курируемая когорта РФ); "
                             "совпадающие id не перезаписываются")
    parser.add_argument("--example", action="store_true", help="взять пример из examples/")
    parser.add_argument("-o", "--out", type=Path, required=True)
    parser.add_argument("--strict", action="store_true", help="обязательны evidence и URL")
    args = parser.parse_args(argv)

    snapshot_path = Path(args.snapshot) if args.snapshot else HERE.parent / "examples" / "example-companies.json"
    if args.example and not args.snapshot:
        snapshot_path = HERE.parent / "examples" / "example-companies.json"
    if not snapshot_path.is_file():
        print(f"error: нет снимка {snapshot_path}", file=sys.stderr)
        return 2

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    for extra_path in args.merge:
        extra = json.loads(extra_path.read_text(encoding="utf-8"))
        known = {c.get("id") for c in snapshot.get("companies", [])}
        added = 0
        for company in extra.get("companies", []):
            if company.get("id") in known:
                continue
            snapshot.setdefault("companies", []).append(company)
            known.add(company.get("id"))
            added += 1
        snapshot.setdefault("warnings", []).append(
            f"добавлено {added} записей из {extra_path.name} (курируемые, не перезаписываются сбором)")
    errors, warnings = validate_snapshot(snapshot, args.strict)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    previous = json.loads(args.previous.read_text(encoding="utf-8")) if args.previous else None
    profile = profile_from_md(args.profile) if args.profile else None
    analysis = build_analysis(snapshot, previous, profile)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    rf, world = analysis["cohorts"]["RF"], analysis["cohorts"]["WORLD"]
    print(f"ok: {args.out}")
    print(f"  RF: {rf['companies']} компаний, доменов {sum(1 for d in rf['domains'].values() if d['count'])}")
    print(f"  WORLD: {world['companies']} компаний, доменов {sum(1 for d in world['domains'].values() if d['count'])}")
    print(f"  пробелов в РФ: {len(analysis['missingInRf'])}")
    for warning in warnings:
        print(f"  warn: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())