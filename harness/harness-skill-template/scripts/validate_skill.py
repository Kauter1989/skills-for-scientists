#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверить навык по контракту harness-skill-template.

Использование:
    python validate_skill.py dev/dev-example --root /path/to/skills
    python validate_skill.py --all --root /path/to/skills
    python validate_skill.py harness/harness-skill-template --json

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DOMAINS = ("dev", "sci", "harness", "reports")
PREFIX = {"dev": "dev-", "sci": "sci-", "harness": "harness-", "reports": ""}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
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
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
TRIGGER_RE = re.compile(r"use when|trigger on|использовать|применять|когда", re.IGNORECASE)
SECRET_RE = re.compile(r"(?i)\b(api[_-]?key|secret|password|token)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]")
PROJECT_RE = re.compile(r"RND\.Hub|rnd-hub|rnd_pms", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"<[А-Яа-яЁё][^>\n]*>|<[^>\n]*\.\.\.[^>\n]*>")


class Report:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def ok(self) -> bool:
        return not self.errors


def parse_frontmatter(text: str) -> tuple[dict, str, list[str]]:
    errors: list[str] = []
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text, ["SKILL.md должен начинаться с frontmatter (---)"]
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text, ["frontmatter не закрыт строкой ---"]

    data: dict = {}
    current = None
    block: list[str] = []
    nested_key = None

    def flush() -> None:
        nonlocal current, block, nested_key
        if current is None:
            block = []
            return
        if block:
            data[current] = " ".join(part.strip() for part in block if part.strip())
        block = []
        current = None
        nested_key = None

    for raw in lines[1:end]:
        if not raw.strip():
            continue
        if raw.startswith(("  ", "\t")) and current:
            stripped = raw.strip()
            if nested_key is not None and ":" in stripped:
                key, value = stripped.split(":", 1)
                data.setdefault(current, {})
                if isinstance(data[current], dict):
                    data[current][key.strip()] = value.strip().strip('"').strip("'")
            else:
                block.append(stripped)
            continue
        if ":" not in raw:
            errors.append(f"не разобрана строка frontmatter: {raw!r}")
            continue
        flush()
        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip()
        current = key
        if key == "metadata":
            data[key] = {}
            nested_key = key
            current = key
            continue
        nested_key = None
        if value in (">-", ">", "|", "|-"):
            block = []
        else:
            data[key] = value.strip('"').strip("'")
    flush()
    return data, "\n".join(lines[end + 1:]), errors


def validate_skill(path: Path) -> Report:
    report = Report(path)
    skill_md = path / "SKILL.md"
    if not path.is_dir():
        report.error(f"каталог не найден: {path}")
        return report
    if not skill_md.is_file():
        report.error("нет SKILL.md")
        return report

    text = skill_md.read_text(encoding="utf-8")
    data, body, fm_errors = parse_frontmatter(text)
    report.errors.extend(fm_errors)

    name = data.get("name")
    if not isinstance(name, str) or not name:
        report.error("frontmatter.name отсутствует")
        name = ""
    else:
        if len(name) > 64:
            report.error("name длиннее 64 символов")
        if not NAME_RE.match(name):
            report.error("name: только a-z, 0-9 и дефис, без -- и краёв")
        if name != path.name:
            report.error(f"name={name!r} не совпадает с каталогом {path.name!r}")
        domain = path.parent.name
        if domain in DOMAINS:
            expected = PREFIX[domain]
            if expected and not name.startswith(expected):
                report.error(f"name должен начинаться с {expected} для домена {domain}")
            if domain == "reports" and name.startswith(("dev-", "sci-", "harness-")):
                report.error("для reports не добавляйте доменный префикс")

    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        report.error("frontmatter.description отсутствует")
    else:
        if len(description) > 1024:
            report.error("description длиннее 1024 символов")
        if not TRIGGER_RE.search(description):
            report.warn("description не содержит условия применения (Use when / Trigger on / когда)")
        if len(description) < 40:
            report.warn("description короче 40 символов: проверьте, что условие применения понятно")

    metadata = data.get("metadata")
    contract = metadata.get("contract") if isinstance(metadata, dict) else None
    if contract != "harness-skill-template":
        report.warn("нет metadata.contract: harness-skill-template (legacy или другой контракт)")

    headings = {h.strip().lower().rstrip(":") for h in HEADING_RE.findall(body)}
    for required in REQUIRED:
        if required not in headings:
            report.error(f"нет обязательного раздела «{required}»")

    for token in ("TODO", "{{"):
        if token in text:
            report.error(f"в SKILL.md остался плейсхолдер {token!r}")
    if PLACEHOLDER_RE.search(body):
        report.error("в SKILL.md остались незаполненные подсказки в угловых скобках")

    for target in LINK_RE.findall(body):
        target = target.strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = target.split("#", 1)[0].strip()
        if not target:
            continue
        candidate = (path / target).resolve()
        if not candidate.exists():
            report.error(f"ссылка ведёт в несуществующий путь: {target}")

    examples = path / "examples"
    if not examples.is_dir():
        report.error("нет каталога examples/")
    else:
        files = [p for p in examples.rglob("*") if p.is_file() and p.name != ".gitkeep"]
        if not files:
            report.error("examples/ пуст: нужен хотя бы один пример")

    scripts = path / "scripts"
    if scripts.is_dir():
        for script in scripts.rglob("*.py"):
            try:
                compile(script.read_text(encoding="utf-8"), str(script), "exec")
            except SyntaxError as exc:
                report.error(f"синтаксис {script.name}: {exc}")

    if SECRET_RE.search(text):
        report.warn("похоже на секрет в тексте навыка")
    if PROJECT_RE.search(text):
        report.warn("в тексте есть имя внутреннего проекта")

    return report


def collect(root: Path) -> list[Path]:
    found: list[Path] = []
    for domain in DOMAINS:
        base = root / domain
        if not base.is_dir():
            continue
        found.extend(sorted(p for p in base.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверить навык по контракту")
    parser.add_argument("path", nargs="?", help="каталог навыка или domain/name")
    parser.add_argument("--root", type=Path, default=Path("."), help="корень библиотеки")
    parser.add_argument("--all", action="store_true", help="проверить все навыки домена")
    parser.add_argument("--json", action="store_true", help="вывод в JSON")
    parser.add_argument("--strict", action="store_true", help="предупреждения считать ошибками")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        print(f"error: корень не найден: {root}", file=sys.stderr)
        return 2

    if args.all:
        all_targets = collect(root)
        targets = []
        skipped = []
        for candidate in all_targets:
            text = (candidate / "SKILL.md").read_text(encoding="utf-8")
            data, _, _ = parse_frontmatter(text)
            metadata = data.get("metadata")
            contract = metadata.get("contract") if isinstance(metadata, dict) else None
            if contract == "harness-skill-template":
                targets.append(candidate)
            else:
                skipped.append(candidate)
    else:
        skipped = []
        if not args.path:
            print("error: укажите путь или --all", file=sys.stderr)
            return 2
        path = Path(args.path)
        if not path.is_absolute():
            if "/" in args.path or "\\" in args.path:
                path = root / path
            else:
                path = (root / path)
        targets = [path.resolve()]

    reports = [validate_skill(path) for path in targets]
    if args.strict:
        for report in reports:
            report.errors.extend(report.warnings)
            report.warnings.clear()

    if args.json:
        print(json.dumps({
            "reports": [
                {
                    "path": str(r.path),
                    "ok": r.ok,
                    "errors": r.errors,
                    "warnings": r.warnings,
                }
                for r in reports
            ],
            "skipped": [str(p) for p in skipped],
        }, ensure_ascii=False, indent=2))
    else:
        for path in skipped:
            print(f"[skip] {path} (нет metadata.contract: harness-skill-template)")
        for report in reports:
            status = "ok" if report.ok else "FAIL"
            print(f"[{status}] {report.path}")
            for error in report.errors:
                print(f"  error: {error}")
            for warning in report.warnings:
                print(f"  warn: {warning}")
        failed = sum(1 for r in reports if not r.ok)
        print(f"\n{len(reports) - failed} ok, {failed} failed, {len(skipped)} skipped")

    return 0 if all(r.ok for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())