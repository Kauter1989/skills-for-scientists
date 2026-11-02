#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверить bootstrap нового репозитория.

Использование:
    python check_bootstrap.py --root /path/to/repo
    python check_bootstrap.py --root . --json

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED_FILES = (
    "profile.yml",
    "AGENTS.md",
    "docs/rules/registry.yml",
    ".pre-commit-config.yaml",
)
REQUIRED_DIRS = (
    "docs/research",
    "docs/reviews",
    "docs/audits",
)


def parse_profile(path: Path) -> tuple[dict, list[str]]:
    data: dict = {"commands": {}, "skills": []}
    errors: list[str] = []
    current = None
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        if indent == 0:
            if ":" not in content:
                errors.append(f"profile.yml:{number}: ожидалось key: value")
                continue
            key, value = content.split(":", 1)
            current = key.strip()
            value = value.strip().strip('"').strip("'")
            if current in ("commands", "skills"):
                if current == "skills" and value == "[]":
                    data["skills"] = []
                continue
            data[current] = value
        elif indent == 2:
            if current == "commands" and ":" in content:
                key, value = content.split(":", 1)
                data["commands"][key.strip()] = value.strip().strip('"').strip("'")
            elif current == "skills" and content.startswith("- "):
                data["skills"].append(content[2:].strip())
            else:
                errors.append(f"profile.yml:{number}: неожиданная строка")
        else:
            errors.append(f"profile.yml:{number}: неожиданный отступ")
    return data, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверить bootstrap")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    if not root.is_dir():
        print(f"error: корень не найден: {root}", file=sys.stderr)
        return 2

    for name in REQUIRED_FILES:
        if not (root / name).is_file():
            errors.append(f"нет файла {name}")
    for name in REQUIRED_DIRS:
        if not (root / name).is_dir():
            errors.append(f"нет каталога {name}/")

    profile_path = root / "profile.yml"
    profile: dict = {}
    if profile_path.is_file():
        profile, parse_errors = parse_profile(profile_path)
        errors.extend(parse_errors)
        if not profile.get("project"):
            errors.append("profile.yml: пустой project")
        if not profile.get("domain"):
            errors.append("profile.yml: пустой domain")
        if not profile.get("commands", {}).get("test"):
            warnings.append("profile.yml: не задана команда tests")
        if not profile.get("commands", {}).get("lint"):
            warnings.append("profile.yml: не задана команда lint")
        for key in ("project_mode", "science_work", "science_outputs", "sdd"):
            if not profile.get(key):
                warnings.append(f"profile.yml: не заполнено поле {key}")
        if not profile.get("skills"):
            errors.append("profile.yml: пустой список skills")
        if profile.get("ci") == "github" and not (root / ".github" / "workflows" / "ci.yml").is_file():
            errors.append("profile.yml: ci=github, но нет .github/workflows/ci.yml")

    registry = root / "docs" / "rules" / "registry.yml"
    if registry.is_file() and "version: 1" not in registry.read_text(encoding="utf-8"):
        errors.append("docs/rules/registry.yml: нет version: 1")

    for path in list(root.glob("*.md")) + [root / "profile.yml"]:
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            if "{{" in text or "TODO" in text:
                errors.append(f"{path.name}: остались плейсхолдеры")

    result = {
        "root": str(root),
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "project": profile.get("project", ""),
        "domain": profile.get("domain", ""),
        "skills": profile.get("skills", []),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"bootstrap: {root}")
        for error in errors:
            print(f"  error: {error}")
        for warning in warnings:
            print(f"  warn: {warning}")
        print("ok" if not errors else "failed")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())