#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Открыть фичу: ветка, feature brief и гейты.

Использование:
    python start_feature.py demo-feature --root /path/to/repo --plan-item P1
    python start_feature.py demo-feature --root . --justification "срочный фикс"
    python start_feature.py demo-feature --root . --plan-item P1 --dry-run

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "overview.md"


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        fail(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result


def human_title(slug: str) -> str:
    return slug.replace("-", " ").strip().capitalize()


def render(template: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Открыть фичу")
    parser.add_argument("slug")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--base", default="main")
    parser.add_argument("--owner", default="owner")
    parser.add_argument("--plan-item", help="пункт плана или цели")
    parser.add_argument("--justification", help="обоснование, если фичи нет в плане")
    parser.add_argument("--approval-mode", choices=("user", "autonomous"), default="user")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--force", action="store_true", help="перезаписать overview.md")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir() or not (root / ".git").exists():
        fail(f"не git-репозиторий: {root}")
    if not SLUG_RE.match(args.slug):
        fail("slug: только a-z, 0-9 и дефис, без -- и краёв")
    if not args.plan_item and not args.justification:
        fail("укажите --plan-item или --justification: фича должна быть привязана к цели")

    branch = f"feature/{args.slug}"
    overview = root / "docs" / "features" / args.slug / "overview.md"
    if overview.exists() and not args.force:
        fail(f"brief уже существует: {overview} (используйте --force)")

    dirty = git(root, "status", "--porcelain").stdout.strip()
    if dirty and not args.allow_dirty:
        fail("рабочее дерево не чистое; закоммитьте изменения или используйте --allow-dirty")

    if git(root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode == 0:
        fail(f"ветка уже существует: {branch}")

    base_ref = args.base
    if not args.no_fetch:
        remotes = git(root, "remote").stdout.split()
        if "origin" in remotes:
            fetch = git(root, "fetch", "origin", check=False)
            if fetch.returncode != 0:
                print(f"warn: git fetch origin failed: {fetch.stderr.strip()}", file=sys.stderr)
            if git(root, "rev-parse", "--verify", f"origin/{args.base}", check=False).returncode == 0:
                base_ref = f"origin/{args.base}"
        else:
            print("warn: remote origin не найден; использую локальную базу", file=sys.stderr)

    if git(root, "rev-parse", "--verify", base_ref, check=False).returncode != 0:
        fail(f"база не найдена: {base_ref}")

    plan_item = args.plan_item or f"вне плана: {args.justification}"
    print(f"branch: {branch}")
    print(f"base: {base_ref}")
    print(f"brief: {overview}")
    if args.dry_run:
        print("dry-run: изменения не внесены")
        return 0

    git(root, "checkout", "-b", branch, base_ref)
    values = {
        "FEATURE": human_title(args.slug),
        "SLUG": args.slug,
        "OWNER": args.owner,
        "BASE": args.base,
        "PLAN_ITEM": plan_item,
        "APPROVAL_MODE": args.approval_mode,
        "DATE": dt.date.today().isoformat(),
    }
    overview.parent.mkdir(parents=True, exist_ok=True)
    overview.write_text(render(TEMPLATE.read_text(encoding="utf-8"), values), encoding="utf-8")

    print(f"ok: {overview}")
    print("дальше:")
    print("  1. заполнить US-* и утвердить stories")
    print("  2. заполнить B-* и утвердить поведенческие тесты")
    print("  3. заполнить F-* и утвердить функциональные тесты")
    print("  4. реализовать тесты и зафиксировать красный гейт")
    print("  5. реализовать задачи до зелёного полного прогона")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())