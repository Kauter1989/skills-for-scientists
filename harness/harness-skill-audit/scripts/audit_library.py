#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Аудит библиотеки навыков: структура, дубли, артефакты, ссылки, покрытие.

Использование:
    python audit_library.py --root /path/to/skills
    python audit_library.py --root . --domain harness
    python audit_library.py --root . --out docs/audits/2026-10-31.html

Только стандартная библиотека Python 3.9+. Read-only: ничего не исправляет.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

DOMAINS = ("dev", "sci", "harness", "reports")
PREFIX = {"dev": "dev-", "sci": "sci-", "harness": "harness-", "reports": ""}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
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
SEVERITY_RANK = {"minor": 1, "major": 2, "blocker": 3}
SEVERITY_LABEL = {"blocker": "BLOCKER", "major": "MAJOR", "minor": "MINOR"}
DUPLICATE_THRESHOLD = 0.70
PROJECT_RE = re.compile(r"RND\.Hub|rnd-hub|rnd_pms", re.IGNORECASE)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text

    data: dict = {}
    current = None
    block: list[str] = []
    nested = None

    def flush() -> None:
        nonlocal current, block, nested
        if current and block:
            data[current] = " ".join(part.strip() for part in block if part.strip())
        block = []
        current = None
        nested = None

    for raw in lines[1:end]:
        if not raw.strip():
            continue
        if raw.startswith(("  ", "\t")) and current:
            stripped = raw.strip()
            if nested == "metadata" and ":" in stripped:
                key, value = stripped.split(":", 1)
                data.setdefault("metadata", {})
                if isinstance(data["metadata"], dict):
                    data["metadata"][key.strip()] = value.strip().strip('"').strip("'")
            else:
                block.append(stripped)
            continue
        if ":" not in raw:
            continue
        flush()
        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip()
        current = key
        if key == "metadata":
            data["metadata"] = {}
            nested = "metadata"
            continue
        if value in (">-", ">", "|", "|-"):
            block = []
        else:
            data[key] = value.strip('"').strip("'")
    flush()
    return data, "\n".join(lines[end + 1:])


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zа-яё0-9]+", text.lower()) if len(w) > 2}


def jaccard(a: str, b: str) -> float:
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def add(findings: list[dict], severity: str, skill: str, rule: str, evidence: str, recommendation: str) -> None:
    findings.append({
        "severity": severity,
        "skill": skill,
        "rule": rule,
        "evidence": evidence,
        "recommendation": recommendation,
    })


def collect(root: Path, domain: str | None) -> list[dict]:
    skills: list[dict] = []
    domains = [domain] if domain else list(DOMAINS)
    for name in domains:
        base = root / name
        if not base.is_dir():
            continue
        for directory in sorted(p for p in base.iterdir() if p.is_dir()):
            skill_md = directory / "SKILL.md"
            if not skill_md.is_file():
                continue
            text = skill_md.read_text(encoding="utf-8")
            data, body = parse_frontmatter(text)
            metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
            skills.append({
                "path": directory,
                "rel": directory.relative_to(root).as_posix(),
                "domain": name,
                "folder": directory.name,
                "name": data.get("name") if isinstance(data.get("name"), str) else "",
                "description": data.get("description") if isinstance(data.get("description"), str) else "",
                "contract": metadata.get("contract"),
                "body": body,
                "text": text,
            })
    return skills


def audit_skill(skill: dict, root: Path, findings: list[dict]) -> None:
    rel = skill["rel"]
    name = skill["name"]
    description = skill["description"]
    contract = skill["contract"]

    if not name:
        add(findings, "major", rel, "frontmatter.name отсутствует", "SKILL.md", "добавить name и синхронизировать с каталогом")
    else:
        if not NAME_RE.match(name) or len(name) > 64:
            add(findings, "major", rel, "некорректный name", name, "использовать a-z, 0-9 и дефис")
        if name != skill["folder"]:
            add(findings, "major", rel, "name не совпадает с каталогом", f"{name} != {skill['folder']}", "синхронизировать имя")
        expected = PREFIX.get(skill["domain"], "")
        if expected and not name.startswith(expected):
            add(findings, "major", rel, f"name без префикса {expected}", name, "добавить префикс домена")

    if not description:
        add(findings, "major", rel, "пустое description", "SKILL.md", "описать что делает навык и когда применять")
    elif len(description) > 1024:
        add(findings, "major", rel, "description длиннее 1024", str(len(description)), "сократить описание")

    if contract != "harness-skill-template":
        add(findings, "minor", rel, "legacy: нет metadata.contract", "frontmatter", "перевести навык на контракт harness-skill-template")
        return

    headings = {h.strip().lower().rstrip(":") for h in HEADING_RE.findall(skill["body"])}
    for required in REQUIRED:
        if required not in headings:
            add(findings, "major", rel, f"нет раздела «{required}»", "SKILL.md", "добавить обязательный раздел")

    examples = skill["path"] / "examples"
    if not examples.is_dir():
        add(findings, "major", rel, "нет examples/", rel, "добавить хотя бы один пример")
    else:
        files = [p for p in examples.rglob("*") if p.is_file() and p.name != ".gitkeep"]
        if not files:
            add(findings, "major", rel, "examples/ пуст", rel, "добавить пример входа и выхода")

    for target in LINK_RE.findall(skill["body"]):
        target = target.strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = target.split("#", 1)[0].strip()
        if not target:
            continue
        if not (skill["path"] / target).resolve().exists():
            add(findings, "major", rel, "битая ссылка", target, "исправить путь или создать файл")

    scripts = skill["path"] / "scripts"
    if scripts.is_dir():
        for script in scripts.rglob("*.py"):
            try:
                compile(script.read_text(encoding="utf-8"), str(script), "exec")
            except SyntaxError as exc:
                add(findings, "major", rel, "синтаксис Python-скрипта", f"{script.name}: {exc}", "исправить скрипт")

    if "TODO" in skill["text"] or "{{" in skill["text"]:
        add(findings, "minor", rel, "незаполненный плейсхолдер", "SKILL.md", "удалить TODO/{{...}}")
    if PROJECT_RE.search(skill["text"]):
        add(findings, "minor", rel, "имя внутреннего проекта", "SKILL.md", "заменить на общий пример")


def audit(root: Path, domain: str | None) -> dict:
    skills = collect(root, domain)
    findings: list[dict] = []
    for skill in skills:
        audit_skill(skill, root, findings)

    duplicates = []
    for i, left in enumerate(skills):
        if not left["description"]:
            continue
        for right in skills[i + 1:]:
            if not right["description"]:
                continue
            score = 1.0 if left["description"].strip() == right["description"].strip() else jaccard(left["description"], right["description"])
            if score >= DUPLICATE_THRESHOLD:
                duplicates.append({
                    "a": left["rel"],
                    "b": right["rel"],
                    "score": round(score, 2),
                    "kind": "exact" if score == 1.0 else "near",
                })
                severity = "blocker" if score == 1.0 else "major"
                add(
                    findings,
                    severity,
                    left["rel"],
                    "дубль триггеров" if score == 1.0 else "возможный дубль триггеров",
                    f"{left['rel']} ↔ {right['rel']} ({score:.2f})",
                    "уточнить у пользователя: объединить, развести или оставить исключение",
                )

    coverage = {name: 0 for name in DOMAINS}
    for skill in skills:
        coverage[skill["domain"]] = coverage.get(skill["domain"], 0) + 1

    summary = {"blocker": 0, "major": 0, "minor": 0}
    for finding in findings:
        summary[finding["severity"]] += 1

    return {
        "date": dt.date.today().isoformat(),
        "scope": domain or "all",
        "root": "." if root == Path.cwd().resolve() else str(root),
        "skills": len(skills),
        "summary": summary,
        "duplicates": duplicates,
        "coverage": coverage,
        "findings": findings,
    }


def render(template: str, data: dict) -> str:
    def esc(value) -> str:
        return html.escape(str(value), quote=False)

    findings_rows = []
    for finding in sorted(data["findings"], key=lambda f: (-SEVERITY_RANK[f["severity"]], f["skill"], f["rule"])):
        severity = SEVERITY_LABEL[finding["severity"]]
        findings_rows.append(
            "<tr>"
            f'<td><span class="sev {finding["severity"]}">{severity}</span></td>'
            f'<td class="mono">{esc(finding["skill"])}</td>'
            f'<td>{esc(finding["rule"])}</td>'
            f'<td class="mono">{esc(finding["evidence"])}</td>'
            f'<td>{esc(finding["recommendation"])}</td>'
            "</tr>"
        )
    if not findings_rows:
        findings_rows.append('<tr><td colspan="5" class="empty">Находок нет.</td></tr>')

    coverage_rows = []
    for name in DOMAINS:
        coverage_rows.append(
            f'<tr><td class="mono">{name}</td><td>{data["coverage"].get(name, 0)}</td>'
            f'<td>{"есть" if data["coverage"].get(name, 0) else "пусто"}</td></tr>'
        )

    duplicates = data["duplicates"]
    dup_text = "нет" if not duplicates else ", ".join(
        f'{d["a"]} ↔ {d["b"]} ({d["score"]})' for d in duplicates
    )
    values = {
        "DATE": data["date"],
        "SCOPE": data["scope"],
        "ROOT": data["root"],
        "SKILL_COUNT": data["skills"],
        "BLOCKERS": data["summary"]["blocker"],
        "MAJORS": data["summary"]["major"],
        "MINORS": data["summary"]["minor"],
        "DUPLICATES": dup_text,
        "FINDINGS_ROWS": "\n".join(findings_rows),
        "COVERAGE_ROWS": "\n".join(coverage_rows),
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", esc(value))
    return template


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Аудит библиотеки навыков")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--domain", choices=DOMAINS)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on", choices=("none", "blocker", "major", "minor"), default="blocker")
    parser.add_argument("--json", action="store_true", help="напечатать JSON вместо записи HTML")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        print(f"error: корень не найден: {root}", file=sys.stderr)
        return 2

    data = audit(root, args.domain)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        date = data["date"]
        out = args.out or (root / "docs" / "audits" / f"{date}.html")
        json_out = args.json_out or out.with_suffix(".json")
        template_path = Path(__file__).resolve().parent.parent / "templates" / "audit-report.html"
        if not template_path.is_file():
            print(f"error: шаблон не найден: {template_path}", file=sys.stderr)
            return 2
        out.parent.mkdir(parents=True, exist_ok=True)
        json_out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(template_path.read_text(encoding="utf-8"), data), encoding="utf-8")
        json_out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"ok: {out}")
        print(f"ok: {json_out}")
        print(f"skills={data['skills']} blocker={data['summary']['blocker']} major={data['summary']['major']} minor={data['summary']['minor']}")

    if args.fail_on == "none":
        return 0
    threshold = SEVERITY_RANK[args.fail_on]
    failed = any(SEVERITY_RANK[f["severity"]] >= threshold for f in data["findings"])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())