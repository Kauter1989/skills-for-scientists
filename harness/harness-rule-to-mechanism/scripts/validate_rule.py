#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверить реестр правил docs/rules/registry.yml.

Использование:
    python validate_rule.py --registry docs/rules/registry.yml --repo .
    python validate_rule.py --registry examples/registry-good.yml --repo . --json

Поддерживается подмножество YAML, описанное в references/registry-format.md.
Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,15}-[0-9]{3}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LEVELS = {"editor", "pre-commit", "CI", "runtime"}
STATUSES = {"proposed", "active", "deprecated"}
MECHANISMS = {"hook", "lint", "test", "policy", "scanner", "ci", "script"}
REQUIRED = ("id", "rule", "trigger", "mechanism", "level", "owner", "cost", "bypass", "evidence", "status")


def strip_comment(raw: str) -> str:
    quote = None
    for i, char in enumerate(raw):
        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
        elif char == "#" and quote is None and (i == 0 or raw[i - 1].isspace()):
            return raw[:i]
    return raw


def scalar(value: str):
    value = value.strip()
    if value == "[]":
        return []
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if value in ("true", "false"):
        return value == "true"
    return value


def split_pair(text: str) -> tuple[str, str] | None:
    if ":" not in text:
        return None
    key, value = text.split(":", 1)
    return key.strip(), value.strip()


def parse_registry(path: Path) -> tuple[dict, list[str]]:
    errors: list[str] = []
    lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    data: dict = {"rules": []}
    current_rule = None
    current_section = None
    seen_rules = False

    for number, raw in enumerate(lines, 1):
        line = strip_comment(raw).rstrip()
        if not line.strip():
            continue
        if "\t" in line[: len(line) - len(line.lstrip())]:
            errors.append(f"строка {number}: табуляция в отступе")
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()

        if indent == 0:
            pair = split_pair(content)
            if not pair:
                errors.append(f"строка {number}: ожидалось key: value")
                continue
            key, value = pair
            if key == "version":
                data["version"] = scalar(value)
            elif key == "rules":
                seen_rules = True
                if value.strip() == "[]":
                    data["rules"] = []
                elif value.strip():
                    errors.append(f"строка {number}: rules должен быть списком")
                current_rule = None
                current_section = None
            else:
                errors.append(f"строка {number}: неизвестный ключ {key!r}")
            continue

        if indent == 2 and content.startswith("- "):
            if not seen_rules:
                errors.append(f"строка {number}: элемент списка вне rules")
                continue
            current_rule = {}
            current_section = None
            data["rules"].append(current_rule)
            pair = split_pair(content[2:])
            if not pair:
                errors.append(f"строка {number}: ожидалось - key: value")
                continue
            key, value = pair
            current_rule[key] = scalar(value)
            continue

        if indent == 4 and current_rule is not None:
            pair = split_pair(content)
            if not pair:
                errors.append(f"строка {number}: ожидалось key: value")
                continue
            key, value = pair
            if key == "mechanism" and not value:
                current_section = {}
                current_rule["mechanism"] = current_section
            else:
                current_section = None
                current_rule[key] = scalar(value)
            continue

        if indent >= 6 and current_rule is not None and current_section is not None:
            pair = split_pair(content)
            if not pair:
                errors.append(f"строка {number}: ожидалось key: value в mechanism")
                continue
            key, value = pair
            current_section[key] = scalar(value)
            continue

        errors.append(f"строка {number}: неожиданный отступ {indent}")

    return data, errors


def validate(data: dict, repo: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    version = data.get("version")
    if version != 1:
        errors.append("version должен быть 1")
    rules = data.get("rules")
    if not isinstance(rules, list):
        errors.append("rules должен быть списком")
        return errors, warnings
    if not rules:
        warnings.append("registry пуст: правил нет")

    seen: set[str] = set()
    for index, rule in enumerate(rules, 1):
        prefix = f"rules[{index}]"
        if not isinstance(rule, dict):
            errors.append(f"{prefix}: должен быть объектом")
            continue
        for field in REQUIRED:
            if field not in rule or rule[field] in (None, ""):
                errors.append(f"{prefix}: отсутствует {field}")

        rule_id = rule.get("id")
        if isinstance(rule_id, str):
            if not ID_RE.match(rule_id):
                errors.append(f"{prefix}: id должен быть вида PREFIX-001")
            if rule_id in seen:
                errors.append(f"{prefix}: повтор id {rule_id}")
            seen.add(rule_id)

        status = rule.get("status")
        if status not in STATUSES:
            errors.append(f"{prefix}: status={status!r}, допустимо {sorted(STATUSES)}")
        level = rule.get("level")
        if level not in LEVELS:
            errors.append(f"{prefix}: level={level!r}, допустимо {sorted(LEVELS)}")

        mechanism = rule.get("mechanism")
        if not isinstance(mechanism, dict):
            errors.append(f"{prefix}: mechanism должен быть объектом")
        else:
            mtype = mechanism.get("type")
            if mtype not in MECHANISMS:
                errors.append(f"{prefix}: mechanism.type={mtype!r}, допустимо {sorted(MECHANISMS)}")
            if not any(mechanism.get(key) for key in ("command", "config", "contract")):
                errors.append(f"{prefix}: нужен command, config или contract")

        evidence = rule.get("evidence")
        if isinstance(evidence, str) and evidence:
            candidate = (repo / evidence).resolve()
            if repo not in candidate.parents and candidate != repo:
                errors.append(f"{prefix}: evidence выходит за пределы --repo: {evidence}")
            elif not candidate.is_file():
                errors.append(f"{prefix}: evidence не найден: {evidence}")
            elif status == "active":
                warnings.append(f"{prefix}: evidence существует, но тест не запускался валидатором")

        since = rule.get("since")
        if since is not None and (not isinstance(since, str) or not DATE_RE.match(since)):
            warnings.append(f"{prefix}: since должен быть YYYY-MM-DD")

        if status == "active" and not evidence:
            errors.append(f"{prefix}: active без evidence")
        if status == "deprecated" and not rule.get("notes"):
            warnings.append(f"{prefix}: deprecated без notes")

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверить registry правил")
    parser.add_argument("--registry", type=Path, default=Path("docs/rules/registry.yml"))
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="предупреждения считать ошибками")
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    registry = args.registry if args.registry.is_absolute() else repo / args.registry
    if not registry.is_file():
        print(f"error: registry не найден: {registry}", file=sys.stderr)
        return 2

    try:
        data, parse_errors = parse_registry(registry)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    errors, warnings = validate(data, repo)
    errors = parse_errors + errors
    if args.strict:
        errors += warnings
        warnings = []

    count = len(data.get("rules") or [])
    if args.json:
        print(json.dumps({
            "registry": str(registry),
            "rules": count,
            "ok": not errors,
            "errors": errors,
            "warnings": warnings,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"registry: {registry}")
        print(f"rules: {count}")
        for error in errors:
            print(f"  error: {error}")
        for warning in warnings:
            print(f"  warn: {warning}")
        print("ok" if not errors else "failed")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())