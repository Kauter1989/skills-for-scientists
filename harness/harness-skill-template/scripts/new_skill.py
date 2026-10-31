#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Создать каталог навыка и SKILL.md по контракту harness-skill-template.

Использование:
    python new_skill.py harness/harness-example --root /path/to/skills
    python new_skill.py dev/dev-example --root . --title "Пример" --dry-run
    python new_skill.py harness-example --domain harness --root .

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

DOMAINS = ("dev", "sci", "harness", "reports")
PREFIX = {"dev": "dev-", "sci": "sci-", "harness": "harness-", "reports": ""}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def human_title(name: str) -> str:
    for prefix in ("dev-", "sci-", "harness-"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name.replace("-", " ").strip().capitalize()


def parse_target(target: str, domain_arg: str | None) -> tuple[str, str]:
    if "/" in target:
        parts = [p for p in target.replace("\\", "/").split("/") if p]
        if len(parts) != 2:
            fail("укажите target как <domain>/<name>, например harness/harness-example")
        domain, name = parts
    else:
        if not domain_arg:
            fail("без <domain>/<name> нужен --domain dev|sci|harness|reports")
        domain, name = domain_arg, target

    if domain not in DOMAINS:
        fail(f"неизвестный домен {domain!r}; допустимо: {', '.join(DOMAINS)}")
    if not NAME_RE.match(name) or len(name) > 64:
        fail("имя: 1-64 символа, только a-z, 0-9 и дефис, без -- в начале/конце")
    expected = PREFIX[domain]
    if expected and not name.startswith(expected):
        fail(f"для домена {domain} имя должно начинаться с {expected}")
    if domain == "reports" and name.startswith(("dev-", "sci-", "harness-")):
        fail("для reports не добавляйте доменный префикс")
    return domain, name


def render(template: str, values: dict[str, str]) -> str:
    text = template
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Создать навык по контракту")
    parser.add_argument("target", help="<domain>/<name> или <name> с --domain")
    parser.add_argument("--domain", choices=DOMAINS, help="домен, если target без папки")
    parser.add_argument("--root", type=Path, default=Path("."), help="корень библиотеки")
    parser.add_argument("--title", help="человеческое название для заголовка")
    parser.add_argument("--description", help="что делает навык и когда применять")
    parser.add_argument("--force", action="store_true", help="перезаписать SKILL.md")
    parser.add_argument("--dry-run", action="store_true", help="только показать план")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        fail(f"корень не найден: {root}")

    domain, name = parse_target(args.target, args.domain)
    target = (root / domain / name).resolve()
    if root not in target.parents and target != root:
        fail("target выходит за пределы --root")

    template_path = Path(__file__).resolve().parent.parent / "templates" / "SKILL.md"
    if not template_path.is_file():
        fail(f"шаблон не найден: {template_path}")

    description = (args.description or "Опишите, что делает навык и когда его применять. Use when ...").strip()
    description = " ".join(description.split())
    if len(description) > 1024:
        fail("description длиннее 1024 символов")

    values = {
        "name": name,
        "domain": domain,
        "title": args.title or human_title(name),
        "description": description,
        "date": dt.date.today().isoformat(),
    }
    skill_md = render(template_path.read_text(encoding="utf-8"), values)

    if target.exists() and not args.force:
        fail(f"каталог уже существует: {target} (используйте --force)")
    if target.exists() and not target.is_dir():
        fail(f"target существует и не является каталогом: {target}")

    actions = [
        f"создать {target}",
        f"записать {target / 'SKILL.md'}",
        f"создать {target / 'references'}",
        f"создать {target / 'scripts'}",
        f"создать {target / 'templates'}",
        f"создать {target / 'examples'}",
    ]
    if args.dry_run:
        print("dry-run:")
        for action in actions:
            print("  " + action)
        return 0

    target.mkdir(parents=True, exist_ok=True)
    for sub in ("references", "scripts", "templates", "examples"):
        (target / sub).mkdir(exist_ok=True)
    (target / "SKILL.md").write_text(skill_md, encoding="utf-8")

    print(f"ok: {target}")
    print("дальше:")
    print(f"  1. заполните {target / 'SKILL.md'}")
    print(f"  2. добавьте пример в {target / 'examples'}")
    print(f"  3. python scripts/validate_skill.py {domain}/{name} --root {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())