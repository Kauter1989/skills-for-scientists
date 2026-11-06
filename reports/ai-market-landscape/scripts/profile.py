#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Профиль анализа рынка: когорты, таксономия и период в MD.

Профиль обязателен до сбора: таксономия объявляется заранее, а не подгоняется
под результат. Файл правится человеком, скрипт его читает и проверяет.

Использование:
    python profile.py --file .ai-market-landscape/landscape.md show --json
    python profile.py --file .ai-market-landscape/landscape.md init --name "ИИ-рынок 2026"
    python profile.py --file .ai-market-landscape/landscape.md check
    python profile.py --file .ai-market-landscape/landscape.md confirm
    python profile.py --file .ai-market-landscape/landscape.md set-period --period 2022-2026

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REQUIRED_SECTIONS = ("Cohorts", "Taxonomy", "Preferences")
REQUIRED_PREFERENCES = ("Period", "Cohort focus", "Report language")

TEMPLATE = """# AI market landscape — профиль

## Profile
- Name: {name}
- Created at: {today}
- Last confirmed: not confirmed

## Cohorts
| id | Label | Registry | Include |
|---|---|---|---|
| RF | Российская Федерация | ЕГРЮЛ / ФИПС | компании со штаб-квартирой в РФ |
| WORLD | Мир (без РФ) | открытые каталоги | компании вне РФ |

## Taxonomy
| axis | values |
|---|---|
| roles | developer, integrator |
| domains | med, fin, industrial, security, education, media, agro, public, mobility |
| services | consulting, integration, development, licensing, mlops, data_services, support, training, hardware |
| pak | none, ai_component, ai_system, ai_software_package |
| delivery | api, on_prem, saas, pak, none |

## Preferences
- Period: 2022-2026
- Cohort focus: RF; WORLD
- Sources: openrouter; company_site
- Gap threshold: 0 in RF and 3 or more in WORLD
- Report language: ru
"""


def today() -> str:
    return dt.date.today().isoformat()


def parse(path: Path) -> dict:
    data: dict[str, dict] = {}
    section = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            section = line[3:].strip()
            data[section] = {}
        elif section and line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            data[section][key.strip()] = value.strip()
        elif section and line.startswith("|"):
            data[section].setdefault("_rows", []).append(line)
    return data


def cmd_init(args) -> int:
    path = Path(args.file)
    if path.exists() and not args.force:
        print(f"error: {path} уже существует; используйте --force", file=sys.stderr)
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE.format(name=args.name, today=today()), encoding="utf-8")
    print(f"ok: создан профиль {path}")
    return 0


def cmd_show(args) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f"error: нет профиля {path}", file=sys.stderr)
        return 2
    data = parse(path)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    profile = data.get("Profile", {})
    prefs = data.get("Preferences", {})
    print(f"профиль: {profile.get('Name', '—')}")
    print(f"период: {prefs.get('Period', '—')}")
    print(f"когорты: {prefs.get('Cohort focus', '—')}")
    print(f"подтверждён: {profile.get('Last confirmed', '—')}")
    return 0


def cmd_check(args) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f"error: нет профиля {path}", file=sys.stderr)
        return 2
    data = parse(path)
    problems = [f"нет раздела {name}" for name in REQUIRED_SECTIONS if name not in data]
    prefs = data.get("Preferences", {})
    problems += [f"нет поля Preferences: {key}" for key in REQUIRED_PREFERENCES if key not in prefs]
    for axis in ("roles", "domains", "services", "pak"):
        rows = data.get("Taxonomy", {}).get("_rows") or []
        if not any(row.strip().startswith(f"| {axis} ") for row in rows):
            problems.append(f"нет оси таксономии {axis}")
    period = prefs.get("Period", "")
    if period and not any(ch.isdigit() for ch in period):
        problems.append("период должен содержать годы")
    confirmed = data.get("Profile", {}).get("Last confirmed")
    if not confirmed or "not confirmed" in confirmed:
        print("warn: профиль не подтверждён; перед сбором выполните `confirm`")
    if problems:
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1
    print(f"ok: профиль {path} корректен")
    return 0


def cmd_confirm(args) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f"error: нет профиля {path}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8")
    lines = []
    replaced = False
    for line in text.splitlines():
        if line.startswith("- Last confirmed:"):
            lines.append(f"- Last confirmed: {today()}")
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        lines.append(f"- Last confirmed: {today()}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"ok: профиль подтверждён {today()}")
    return 0


def cmd_set_period(args) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f"error: нет профиля {path}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        if line.startswith("- Period:"):
            lines.append(f"- Period: {args.period}")
        else:
            lines.append(line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"ok: период {args.period}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Профиль анализа рынка")
    parser.add_argument("--file", default=".ai-market-landscape/landscape.md")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="создать профиль")
    p_init.add_argument("--name", default="ИИ-рынок")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_show = sub.add_parser("show", help="показать профиль")
    p_show.add_argument("--json", action="store_true")
    p_show.set_defaults(func=cmd_show)

    sub.add_parser("check", help="проверить профиль").set_defaults(func=cmd_check)
    sub.add_parser("confirm", help="подтвердить профиль").set_defaults(func=cmd_confirm)

    p_period = sub.add_parser("set-period", help="задать период")
    p_period.add_argument("--period", required=True)
    p_period.set_defaults(func=cmd_set_period)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())