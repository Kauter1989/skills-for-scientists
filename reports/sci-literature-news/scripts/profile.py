#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read, validate and update the literature-news Markdown profile.

The profile is deliberately human-editable. It stores the scientific profile,
research directions, period and report preferences.

Usage:
    python profile.py show --file .sci-literature-news/profile.md --json
    python profile.py check --file .sci-literature-news/profile.md
    python profile.py confirm --file .sci-literature-news/profile.md
    python profile.py set-period --file .sci-literature-news/profile.md --months 6
    python profile.py init --file ... --name "..." --direction "..." --query "..."
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

DEFAULT_FILE = Path(".sci-literature-news/profile.md")
DEFAULT_MONTHS = 6
DEFAULT_CATEGORIES = ["Q1 journals", "A* conferences", "Q2 journals"]


def today() -> date:
    return date.today()


def month_shift(day: date, months: int) -> date:
    month = day.month - months
    year = day.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, min(day.day, 28))


def add_months(day: date, months: int) -> date:
    month = day.month + months
    year = day.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, min(day.day, 28))


def default_profile(name: str = "", directions: list[dict] | None = None) -> dict:
    end = today()
    start = month_shift(end, DEFAULT_MONTHS)
    return {
        "profile": {
            "name": name,
            "affiliation": "",
            "orcid": "",
            "google_scholar": "",
            "scopus": "",
            "researchgate": "",
            "personal_site": "",
            "profile_source": "",
            "profile_fetched_at": "",
        },
        "directions": directions
        or [{"id": "D1", "direction": "", "query": "", "notes": ""}],
        "preferences": {
            "period_months": DEFAULT_MONTHS,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "categories": list(DEFAULT_CATEGORIES),
            "languages": ["en"],
            "include_preprints": False,
            "max_results_per_direction": 100,
            "ranking_source": "SJR 2025; ICORE2026",
            "report_language": "ru",
            "last_confirmed": "",
        },
    }


def _parse_bullets(lines: list[str]) -> dict:
    result = {}
    for line in lines:
        match = re.match(r"^\s*-\s*([^:]+):\s*(.*)$", line)
        if match:
            result[match.group(1).strip().lower().replace(" ", "_")] = match.group(2).strip()
    return result


def _parse_directions(lines: list[str]) -> list[dict]:
    rows = []
    header = None
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if header is None:
            header = [cell.lower() for cell in cells]
            continue
        if all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
            continue
        if len(cells) < 2:
            continue
        rows.append(
            {
                "id": cells[0],
                "direction": cells[1] if len(cells) > 1 else "",
                "query": cells[2] if len(cells) > 2 else "",
                "notes": cells[3] if len(cells) > 3 else "",
            }
        )
    return rows


def load_profile(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    sections: dict[str, list[str]] = {}
    current = None
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections[current] = []
            continue
        if current:
            sections[current].append(line)

    profile = _parse_bullets(sections.get("profile", []))
    prefs = _parse_bullets(sections.get("preferences", []))
    directions = _parse_directions(sections.get("directions", []))

    def as_int(key: str, fallback: int) -> int:
        try:
            return int(str(prefs.get(key, fallback)).strip())
        except (TypeError, ValueError):
            return fallback

    def as_bool(key: str, fallback: bool) -> bool:
        value = str(prefs.get(key, str(fallback))).strip().lower()
        return value in {"true", "yes", "1", "да"}

    categories = [
        item.strip()
        for item in str(prefs.get("categories", ";".join(DEFAULT_CATEGORIES))).replace(",", ";").split(";")
        if item.strip()
    ]
    languages = [
        item.strip()
        for item in str(prefs.get("languages", "en")).replace(",", ";").split(";")
        if item.strip()
    ]
    return {
        "profile": {
            "name": profile.get("name", ""),
            "affiliation": profile.get("affiliation", ""),
            "orcid": profile.get("orcid", ""),
            "google_scholar": profile.get("google_scholar", ""),
            "scopus": profile.get("scopus", ""),
            "researchgate": profile.get("researchgate", ""),
            "personal_site": profile.get("personal_site", ""),
            "profile_source": profile.get("profile_source", ""),
            "profile_fetched_at": profile.get("profile_fetched_at", ""),
        },
        "directions": directions,
        "preferences": {
            "period_months": as_int("period_months", DEFAULT_MONTHS),
            "from": prefs.get("from", ""),
            "to": prefs.get("to", ""),
            "categories": categories or list(DEFAULT_CATEGORIES),
            "languages": languages or ["en"],
            "include_preprints": as_bool("include_preprints", False),
            "max_results_per_direction": as_int("max_results_per_direction", 100),
            "ranking_source": prefs.get("ranking_source", "SJR 2025; ICORE2026"),
            "report_language": prefs.get("report_language", "ru"),
            "last_confirmed": prefs.get("last_confirmed", ""),
        },
    }


def render_profile(profile: dict) -> str:
    p = profile["profile"]
    prefs = profile["preferences"]
    lines = [
        "# Scientific profile — literature news",
        "",
        "Этот файл хранит научный профиль, направления и период. Правьте его",
        "вручную или через `scripts/profile.py`; после правок выполните `confirm`.",
        "",
        "## Profile",
        "",
        f"- Name: {p.get('name', '')}",
        f"- Affiliation: {p.get('affiliation', '')}",
        f"- ORCID: {p.get('orcid', '')}",
        f"- Google Scholar: {p.get('google_scholar', '')}",
        f"- Scopus: {p.get('scopus', '')}",
        f"- ResearchGate: {p.get('researchgate', '')}",
        f"- Personal site: {p.get('personal_site', '')}",
        f"- Profile source: {p.get('profile_source', '')}",
        f"- Profile fetched at: {p.get('profile_fetched_at', '')}",
        "",
        "## Directions",
        "",
        "| id | Direction | Query terms (EN) | Notes |",
        "|---|---|---|---|",
    ]
    for direction in profile.get("directions", []):
        lines.append(
            f"| {direction.get('id', '')} | {direction.get('direction', '')} | "
            f"{direction.get('query', '')} | {direction.get('notes', '')} |"
        )
    lines += [
        "",
        "## Preferences",
        "",
        f"- Period months: {prefs.get('period_months', DEFAULT_MONTHS)}",
        f"- From: {prefs.get('from', '')}",
        f"- To: {prefs.get('to', '')}",
        f"- Categories: {'; '.join(prefs.get('categories', DEFAULT_CATEGORIES))}",
        f"- Languages: {'; '.join(prefs.get('languages', ['en']))}",
        f"- Include preprints: {str(prefs.get('include_preprints', False)).lower()}",
        f"- Max results per direction: {prefs.get('max_results_per_direction', 100)}",
        f"- Ranking source: {prefs.get('ranking_source', 'SJR 2025; ICORE2026')}",
        f"- Report language: {prefs.get('report_language', 'ru')}",
        f"- Last confirmed: {prefs.get('last_confirmed', '')}",
        "",
    ]
    return "\n".join(lines)


def validate(profile: dict, require_confirm: bool = False) -> list[str]:
    errors: list[str] = []
    directions = [d for d in profile.get("directions", []) if d.get("direction", "").strip()]
    if not directions:
        errors.append("Directions: нужен хотя бы одно направление")
    for direction in directions:
        if not direction.get("query", "").strip():
            errors.append(
                f"Directions/{direction.get('id', '?')}: заполните Query terms (EN) для поиска"
            )
    prefs = profile.get("preferences", {})
    months = prefs.get("period_months")
    if not isinstance(months, int) or not (1 <= months <= 60):
        errors.append("Preferences/Period months: нужно целое число от 1 до 60")
    if prefs.get("from") and prefs.get("to") and prefs["from"] > prefs["to"]:
        errors.append("Preferences: From больше To")
    if require_confirm and not prefs.get("last_confirmed"):
        errors.append("Preferences/Last confirmed: подтвердите направления и период")
    return errors


def save_profile(path: Path, profile: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_profile(profile), encoding="utf-8")


def _cmd_show(args: argparse.Namespace) -> int:
    profile = load_profile(Path(args.file))
    if args.json:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    else:
        prefs = profile["preferences"]
        print(f"Профиль: {profile['profile'].get('name') or '—'}")
        print(f"Период: {prefs.get('from')} — {prefs.get('to')} ({prefs.get('period_months')} мес.)")
        print("Направления:")
        for d in profile["directions"]:
            print(f"- {d['id']}: {d['direction']} | {d['query']}")
        print(f"Последнее подтверждение: {prefs.get('last_confirmed') or 'нет'}")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    profile = load_profile(Path(args.file))
    errors = validate(profile, require_confirm=args.require_confirm)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"ok: {len(profile['directions'])} directions, period {profile['preferences']['period_months']} months")
    return 0


def _cmd_confirm(args: argparse.Namespace) -> int:
    path = Path(args.file)
    profile = load_profile(path)
    errors = validate(profile, require_confirm=False)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    profile["preferences"]["last_confirmed"] = args.at or today().isoformat()
    save_profile(path, profile)
    print(f"confirmed: {profile['preferences']['last_confirmed']}")
    return 0


def _cmd_set_period(args: argparse.Namespace) -> int:
    path = Path(args.file)
    profile = load_profile(path)
    profile["preferences"]["period_months"] = args.months
    end = date.fromisoformat(args.to) if args.to else today()
    start = date.fromisoformat(args.from_) if args.from_ else month_shift(end, args.months)
    profile["preferences"]["from"] = start.isoformat()
    profile["preferences"]["to"] = end.isoformat()
    profile["preferences"]["last_confirmed"] = ""
    save_profile(path, profile)
    print(f"period: {start} — {end}")
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if path.exists() and not args.force:
        print(f"error: файл уже существует: {path}", file=sys.stderr)
        return 1
    directions = []
    for index, direction in enumerate(args.direction or [], start=1):
        query = args.query[index - 1] if args.query and index <= len(args.query) else direction
        directions.append({"id": f"D{index}", "direction": direction, "query": query, "notes": ""})
    profile = default_profile(args.name, directions or None)
    profile["preferences"]["period_months"] = args.months
    profile["preferences"]["from"] = month_shift(today(), args.months).isoformat()
    profile["preferences"]["to"] = today().isoformat()
    save_profile(path, profile)
    print(f"created: {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MD-профиль для sci-literature-news")
    parser.add_argument("--file", default=str(DEFAULT_FILE))
    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show")
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=_cmd_show)

    check = sub.add_parser("check")
    check.add_argument("--require-confirm", action="store_true")
    check.set_defaults(func=_cmd_check)

    confirm = sub.add_parser("confirm")
    confirm.add_argument("--at", default="")
    confirm.set_defaults(func=_cmd_confirm)

    period = sub.add_parser("set-period")
    period.add_argument("--months", type=int, default=DEFAULT_MONTHS)
    period.add_argument("--from", dest="from_", default="")
    period.add_argument("--to", default="")
    period.set_defaults(func=_cmd_set_period)

    init = sub.add_parser("init")
    init.add_argument("--name", default="")
    init.add_argument("--direction", action="append", default=[])
    init.add_argument("--query", action="append", default=[])
    init.add_argument("--months", type=int, default=DEFAULT_MONTHS)
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=_cmd_init)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"error: файл не найден: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())