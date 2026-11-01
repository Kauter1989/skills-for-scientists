#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверить сгенерированный навык обработки дефектов.

Использование:
    python check_bug_skill.py --root /path/to/repo
    python check_bug_skill.py --root . --json

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

GENERATED_SKILL = "dev-bug-process"
APPROACHES = {
    "test-first",
    "container-first",
    "incident-first",
    "benchmark-first",
    "lightweight",
}
INVARIANT_KEYS = (
    "detailed_description",
    "reproducibility",
    "minimal_case",
    "red_test",
    "failure_matches_symptom",
    "evidence_based_diagnosis",
    "no_fix_before_red",
    "repo_artifacts",
    "no_auto_run",
)
PROFILE_KEYS = (
    "stack",
    "test_framework",
    "test_command",
    "test_root",
    "tracker",
    "environment",
    "team",
    "compliance",
    "flake_policy",
    "repro_depth",
    "approval",
)
ARTIFACT_KEYS = ("bug_dir", "report", "manifest", "probe", "test_root")
REQUIRED_HEADINGS = (
    "когда применять",
    "когда не применять",
    "вход",
    "процедура",
    "выход",
    "доказательства",
    "границы",
    "типовые ошибки",
    "qa",
    "файлы",
)
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def parse_manifest(path: Path) -> dict:
    data: dict = {}
    section = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        if ":" not in content:
            continue
        key, value = content.split(":", 1)
        key = key.strip()
        value = value.strip()
        if indent == 0:
            if value:
                data[key] = value
                section = None
            else:
                section = key
                data.setdefault(key, {})
        elif section and indent >= 2:
            data.setdefault(section, {})[key] = value
    return data


def frontmatter_name(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^name:\s*(\S+)", text, re.MULTILINE)
    return match.group(1).strip('"').strip("'") if match else ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверить сгенерированный dev-bug-process")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    manifest_path = root / ".opencode" / "bug-processing.yml"
    if not manifest_path.is_file():
        errors.append("нет .opencode/bug-processing.yml")
        data: dict = {}
    else:
        data = parse_manifest(manifest_path)
        text = manifest_path.read_text(encoding="utf-8")
        if "{{" in text:
            errors.append("manifest: остались незаполненные {{...}}")
        if data.get("version") != "1":
            errors.append("manifest: version должен быть 1")
        if data.get("generated_skill") != GENERATED_SKILL:
            errors.append(f"manifest: generated_skill={data.get('generated_skill')!r}")
        approach = data.get("approach")
        if approach not in APPROACHES:
            errors.append(f"manifest: approach={approach!r}")

        profile = data.get("profile", {})
        if not isinstance(profile, dict):
            errors.append("manifest: profile должен быть объектом")
            profile = {}
        for key in PROFILE_KEYS:
            if not profile.get(key):
                errors.append(f"manifest: profile.{key} не заполнен")

        invariants = data.get("invariants", {})
        if not isinstance(invariants, dict):
            errors.append("manifest: invariants должен быть объектом")
            invariants = {}
        for key in INVARIANT_KEYS:
            if invariants.get(key) != "true":
                errors.append(f"manifest: invariants.{key} должен быть true")

        gates = data.get("gates", {})
        if not isinstance(gates, dict):
            errors.append("manifest: gates должен быть объектом")
            gates = {}
        try:
            runs = int(gates.get("min_runs", "0"))
        except ValueError:
            runs = 0
        if runs < 3:
            errors.append("manifest: gates.min_runs должен быть >= 3")
        for key in ("require_minimal", "require_failure_match", "require_hypotheses"):
            if gates.get(key) != "true":
                errors.append(f"manifest: gates.{key} должен быть true")

        artifacts = data.get("artifacts", {})
        if not isinstance(artifacts, dict):
            errors.append("manifest: artifacts должен быть объектом")
            artifacts = {}
        for key in ARTIFACT_KEYS:
            if not artifacts.get(key):
                errors.append(f"manifest: artifacts.{key} не заполнен")
        if artifacts.get("test_root") and profile.get("test_root"):
            if artifacts["test_root"] != profile["test_root"]:
                errors.append(
                    "manifest: artifacts.test_root не совпадает с profile.test_root"
                )

        environment = str(profile.get("environment", "")).lower()
        expected = None
        if environment in {"production", "incident"}:
            expected = "incident-first"
        elif environment in {"benchmark", "research"}:
            expected = "benchmark-first"
        elif environment in {"container", "docker"}:
            expected = "container-first"
        if expected and approach != expected:
            errors.append(
                f"manifest: для environment={environment} ожидается approach={expected}"
            )

    skill_dir = root / ".opencode" / "skill" / GENERATED_SKILL
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        errors.append(f"нет .opencode/skill/{GENERATED_SKILL}/SKILL.md")
    else:
        text = skill_md.read_text(encoding="utf-8")
        if "{{" in text:
            errors.append("SKILL.md: остались незаполненные {{...}}")
        if frontmatter_name(skill_md) != GENERATED_SKILL:
            errors.append(f"SKILL.md: name не совпадает с {GENERATED_SKILL}")
        headings = {h.strip().lower().rstrip(":") for h in HEADING_RE.findall(text)}
        for heading in REQUIRED_HEADINGS:
            if heading not in headings:
                errors.append(f"SKILL.md: нет раздела «{heading}»")

    required_files = (
        "references/bug-contract.md",
        "templates/bug-report.md",
        "templates/repro.json",
        "scripts/probe_bug.py",
        "scripts/check_bug_report.py",
        "examples/README.md",
    )
    for relative in required_files:
        if not (skill_dir / relative).is_file():
            errors.append(f"нет {skill_dir / relative}")
    if not (root / "docs" / "bugs" / "README.md").is_file():
        warnings.append("нет docs/bugs/README.md")

    result = {
        "root": str(root),
        "ok": not errors,
        "generated_skill": GENERATED_SKILL,
        "approach": data.get("approach", ""),
        "errors": errors,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"bug processing: {root}")
        print(f"approach: {result['approach'] or '—'}; generated: {GENERATED_SKILL}")
        for error in errors:
            print(f"  error: {error}")
        for warning in warnings:
            print(f"  warn: {warning}")
        print("ok" if not errors else "failed")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())