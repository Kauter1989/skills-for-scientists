#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверить сгенерированную spec-chain.

Использование:
    python check_spec_chain.py --root /path/to/repo
    python check_spec_chain.py --root . --json

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

APPROACHES = {"spec-kit", "openspec", "bmad", "lightweight"}
REQUIRED = (
    "когда применять",
    "когда не применять",
    "вход",
    "процедура",
    "выход",
    "доказательства",
    "границы",
    "типовые ошибки",
    "qa",
)
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def parse_manifest(path: Path) -> tuple[dict, list[str]]:
    data: dict = {"stages": []}
    errors: list[str] = []
    current = None
    in_stages = False
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        if indent == 0:
            if content.startswith("version:"):
                data["version"] = content.split(":", 1)[1].strip()
            elif content.startswith("approach:"):
                data["approach"] = content.split(":", 1)[1].strip()
            elif content == "stages:":
                in_stages = True
            elif content.startswith("gates:"):
                in_stages = False
            continue
        if in_stages and indent == 2 and content.startswith("- "):
            current = {}
            data["stages"].append(current)
            key, value = content[2:].split(":", 1)
            current[key.strip()] = value.strip()
        elif in_stages and indent == 4 and current is not None and ":" in content:
            key, value = content.split(":", 1)
            current[key.strip()] = value.strip()
        elif content.startswith("tests_first:"):
            data["tests_first"] = content.split(":", 1)[1].strip()
    return data, errors


def frontmatter_name(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^name:\s*(\S+)", text, re.MULTILINE)
    return match.group(1).strip('"').strip("'") if match else ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверить spec-chain")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    manifest = root / ".opencode" / "spec-chain.yml"
    if not manifest.is_file():
        errors.append("нет .opencode/spec-chain.yml")
        data = {"stages": []}
    else:
        data, parse_errors = parse_manifest(manifest)
        errors.extend(parse_errors)
        if data.get("version") != "1":
            errors.append("manifest: version должен быть 1")
        if data.get("approach") not in APPROACHES:
            errors.append(f"manifest: approach={data.get('approach')!r}")
        if data.get("tests_first") != "true":
            errors.append("manifest: gates.tests_first должен быть true")

    stages = data.get("stages", [])
    if not stages:
        errors.append("manifest: нет stages")
    ids = [stage.get("id") for stage in stages]
    if len(ids) != len(set(ids)):
        errors.append("manifest: повтор stage id")
    for stage in stages:
        for field in ("id", "skill", "input", "output", "gate"):
            if not stage.get(field):
                errors.append(f"stage {stage.get('id', '?')}: нет {field}")
        skill = stage.get("skill", "")
        skill_dir = root / ".opencode" / "skill" / skill
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{skill}: нет SKILL.md")
            continue
        if frontmatter_name(skill_md) != skill:
            errors.append(f"{skill}: name не совпадает с каталогом")
        text = skill_md.read_text(encoding="utf-8")
        headings = {h.strip().lower().rstrip(":") for h in HEADING_RE.findall(text)}
        for required in REQUIRED:
            if required not in headings:
                errors.append(f"{skill}: нет раздела «{required}»")
        if not (skill_dir / "examples").is_dir():
            warnings.append(f"{skill}: нет examples/")

    if "implement" in ids:
        for required in ("tasks", "analyze"):
            if required in ids and ids.index(required) > ids.index("implement"):
                errors.append(f"порядок: {required} должен быть раньше implement")
    if "tasks" in ids and "plan" in ids and ids.index("plan") > ids.index("tasks"):
        errors.append("порядок: plan должен быть раньше tasks")

    result = {
        "root": str(root),
        "ok": not errors,
        "approach": data.get("approach", ""),
        "stages": ids,
        "errors": errors,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"spec-chain: {root}")
        print(f"approach: {result['approach']}; stages: {', '.join(ids) or '—'}")
        for error in errors:
            print(f"  error: {error}")
        for warning in warnings:
            print(f"  warn: {warning}")
        print("ok" if not errors else "failed")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())