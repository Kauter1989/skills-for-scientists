#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сгенерировать spec-chain под конкретный репозиторий.

Команды:
    python generate_chain.py survey --out answers.json
    python generate_chain.py plan --root . --answers answers.json
    python generate_chain.py approve --plan spec-chain-plan.html --json spec-chain-plan.json
    python generate_chain.py apply --root . --plan-json spec-chain-plan.json

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
APPROACHES = ("spec-kit", "openspec", "bmad", "lightweight")
STAGE_SPECS = {
    "specify": {
        "title": "Specify",
        "trigger": "specify, requirements, spec.md",
        "input": "docs/features/<slug>/overview.md",
        "output": "docs/features/<slug>/spec.md",
        "gate": "spec approved",
    },
    "clarify": {
        "title": "Clarify",
        "trigger": "clarify, ambiguity, clarification",
        "input": "docs/features/<slug>/spec.md",
        "output": "docs/features/<slug>/spec.md (clarified)",
        "gate": "clarification closed",
    },
    "plan": {
        "title": "Plan",
        "trigger": "plan, architecture, constitution check",
        "input": "docs/features/<slug>/spec.md",
        "output": "docs/features/<slug>/plan.md",
        "gate": "plan approved",
    },
    "tasks": {
        "title": "Tasks",
        "trigger": "tasks, decomposition, T-TEST, T-IMPL",
        "input": "docs/features/<slug>/plan.md",
        "output": "docs/features/<slug>/tasks.md",
        "gate": "traceability complete",
    },
    "analyze": {
        "title": "Analyze",
        "trigger": "analyze, consistency, traceability",
        "input": "spec, plan and tasks",
        "output": "docs/features/<slug>/analysis-report.json",
        "gate": "analysis clean",
    },
    "implement": {
        "title": "Implement",
        "trigger": "implement, code, red green",
        "input": "docs/features/<slug>/tasks.md",
        "output": "code and green test run",
        "gate": "tests green",
    },
}


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def ask(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def survey(out: Path) -> int:
    print("Опрос для spec-chain. Enter — значение по умолчанию.\n")
    answers = {
        "repo": ask("Имя репозитория", Path.cwd().name),
        "mode": ask("Профиль (greenfield/brownfield)", "greenfield"),
        "change_size": ask("Размер изменений (small/medium/large)", "medium"),
        "roles": ask("Роли (small/enterprise)", "small"),
        "compliance": ask("Compliance (none/audit)", "none"),
        "stack": ask("Стек", "python"),
        "approval": ask("Режим утверждения (user/autonomous)", "user"),
        "strict": ask("Строгость гейтов (light/standard/strict)", "standard"),
        "approach": ask("Подход (auto/spec-kit/openspec/bmad/lightweight)", "auto"),
    }
    out.write_text(json.dumps(answers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nok: {out}")
    return 0


def choose_approach(answers: dict) -> str:
    explicit = answers.get("approach", "auto")
    if explicit != "auto":
        if explicit not in APPROACHES:
            fail(f"неизвестный подход: {explicit}")
        return explicit
    if answers.get("mode") == "brownfield":
        return "openspec"
    if answers.get("roles") == "enterprise" or answers.get("compliance") == "audit":
        return "bmad"
    if answers.get("change_size") == "small":
        return "lightweight"
    return "spec-kit"


def choose_stages(answers: dict, approach: str) -> list[str]:
    if approach == "lightweight":
        stages = ["specify", "plan", "tasks", "analyze"]
    elif approach == "openspec":
        stages = ["specify", "clarify", "plan", "tasks", "analyze"]
    elif approach == "bmad":
        stages = ["specify", "clarify", "plan", "tasks", "analyze", "implement"]
    else:
        stages = ["specify", "clarify", "plan", "tasks", "analyze", "implement"]

    if answers.get("strict") == "light":
        stages = ["specify", "plan", "tasks"]
    elif answers.get("strict") == "strict" and "implement" not in stages:
        stages.append("implement")
    return stages


def stage_rows(stages: list[str]) -> str:
    rows = []
    for index, key in enumerate(stages, 1):
        spec = STAGE_SPECS[key]
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{html.escape(spec['title'])}</td>"
            f"<td class=\"mono\">{html.escape(spec['input'])}</td>"
            f"<td class=\"mono\">{html.escape(spec['output'])}</td>"
            f"<td>{html.escape(spec['gate'])}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def profile_rows(answers: dict, approach: str) -> str:
    fields = {
        "Репозиторий": answers.get("repo", ""),
        "Профиль": answers.get("mode", ""),
        "Размер изменений": answers.get("change_size", ""),
        "Роли": answers.get("roles", ""),
        "Compliance": answers.get("compliance", ""),
        "Стек": answers.get("stack", ""),
        "Approval": answers.get("approval", ""),
        "Строгость": answers.get("strict", ""),
        "Подход": approach,
    }
    return "\n".join(
        f'<tr><td>{html.escape(str(k))}</td><td class="mono">{html.escape(str(v))}</td></tr>'
        for k, v in fields.items()
    )


def file_rows(stages: list[str]) -> str:
    rows = ['<tr><td class="mono">.opencode/spec-chain.yml</td><td>манифест цепочки</td></tr>']
    for key in stages:
        skill = f"dev-{key}"
        rows.append(
            f'<tr><td class="mono">.opencode/skill/{skill}/SKILL.md</td>'
            f'<td>сгенерированный stage-навык</td></tr>'
        )
    return "\n".join(rows)


def plan(answers: dict, out_html: Path, out_json: Path) -> dict:
    approach = choose_approach(answers)
    stages = choose_stages(answers, approach)
    data = {
        "status": "draft",
        "created": dt.date.today().isoformat(),
        "repo": answers.get("repo", "repo"),
        "approach": approach,
        "profile": answers,
        "stages": [
            {"id": key, "skill": f"dev-{key}", **STAGE_SPECS[key]}
            for key in stages
        ],
        "files": [".opencode/spec-chain.yml"] + [
            f".opencode/skill/dev-{key}/SKILL.md" for key in stages
        ],
    }
    template = (TEMPLATES / "spec-chain-plan.html").read_text(encoding="utf-8")
    values = {
        "REPO": data["repo"],
        "MODE": answers.get("mode", ""),
        "APPROACH": approach,
        "DATE": data["created"],
        "STATUS": "draft",
        "PROFILE_ROWS": profile_rows(answers, approach),
        "STAGE_ROWS": stage_rows(stages),
        "FILE_ROWS": file_rows(stages),
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(template, encoding="utf-8")
    out_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def approve(plan_html: Path, plan_json: Path) -> int:
    if not plan_json.is_file():
        fail(f"план не найден: {plan_json}")
    data = json.loads(plan_json.read_text(encoding="utf-8"))
    data["status"] = "approved"
    plan_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if plan_html.is_file():
        text = plan_html.read_text(encoding="utf-8")
        text = text.replace('data-status="draft"', 'data-status="approved"')
        text = text.replace('<span id="approval" class="status draft">draft</span>', '<span id="approval" class="status approved">approved</span>')
        plan_html.write_text(text, encoding="utf-8")
    print(f"ok: approved {plan_json}")
    return 0


def stage_skill_md(data: dict, stage: dict) -> str:
    template = (TEMPLATES / "stage-SKILL.md").read_text(encoding="utf-8")
    values = {
        "STAGE_SKILL": stage["skill"],
        "STAGE_TITLE": stage["title"],
        "REPO": data["repo"],
        "APPROACH": data["approach"],
        "STAGE_TRIGGER": stage["trigger"],
        "INPUT": stage["input"],
        "OUTPUT": stage["output"],
        "GATE": stage["gate"],
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def manifest(data: dict) -> str:
    template = (TEMPLATES / "spec-chain.yml").read_text(encoding="utf-8")
    profile = data["profile"]
    stages = []
    for stage in data["stages"]:
        stages.append(
            f"  - id: {stage['id']}\n"
            f"    title: {stage['title']}\n"
            f"    skill: {stage['skill']}\n"
            f"    input: {stage['input']}\n"
            f"    output: {stage['output']}\n"
            f"    gate: {stage['gate']}"
        )
    values = {
        "REPO": data["repo"],
        "MODE": profile.get("mode", ""),
        "CHANGE_SIZE": profile.get("change_size", ""),
        "ROLES": profile.get("roles", ""),
        "COMPLIANCE": profile.get("compliance", ""),
        "STACK": profile.get("stack", ""),
        "APPROVAL": profile.get("approval", ""),
        "APPROACH": data["approach"],
        "STRICT": profile.get("strict", ""),
        "STAGES_YAML": "\n".join(stages),
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def write_file(path: Path, content: str, force: bool, dry: bool) -> str:
    if path.exists() and not force:
        return f"skip {path} (exists)"
    if dry:
        return f"would write {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"write {path}"


def apply(root: Path, plan_json: Path, force: bool, dry: bool) -> int:
    if not plan_json.is_file():
        fail(f"план не найден: {plan_json}")
    data = json.loads(plan_json.read_text(encoding="utf-8"))
    if data.get("status") != "approved":
        fail("план не утверждён: статус должен быть approved")

    report = []
    report.append(write_file(root / ".opencode" / "spec-chain.yml", manifest(data), force, dry))
    for stage in data["stages"]:
        skill_dir = root / ".opencode" / "skill" / stage["skill"]
        report.append(write_file(skill_dir / "SKILL.md", stage_skill_md(data, stage), force, dry))
        example = (
            f"# Пример стадии {stage['title']}\n\n"
            f"Вход: {stage['input']}\n\n"
            f"Выход: {stage['output']}\n\n"
            f"Гейт: {stage['gate']}\n"
        )
        report.append(write_file(skill_dir / "examples" / "README.md", example, force, dry))
    if not dry:
        (root / "spec-chain-report.md").write_text(
            "# Spec chain report\n\nДата: " + dt.date.today().isoformat() + "\n\n" +
            "\n".join(f"- {line}" for line in report) + "\n",
            encoding="utf-8",
        )
    for line in report:
        print(line)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Генерация spec-chain под репозиторий")
    sub = parser.add_subparsers(dest="command", required=True)

    p_survey = sub.add_parser("survey")
    p_survey.add_argument("--out", type=Path, default=Path("answers.json"))

    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--root", type=Path, default=Path("."))
    p_plan.add_argument("--answers", type=Path, required=True)
    p_plan.add_argument("--out", type=Path, default=Path("spec-chain-plan.html"))
    p_plan.add_argument("--json", type=Path, default=Path("spec-chain-plan.json"))

    p_approve = sub.add_parser("approve")
    p_approve.add_argument("--plan", type=Path, default=Path("spec-chain-plan.html"))
    p_approve.add_argument("--json", type=Path, default=Path("spec-chain-plan.json"))

    p_apply = sub.add_parser("apply")
    p_apply.add_argument("--root", type=Path, default=Path("."))
    p_apply.add_argument("--plan-json", type=Path, default=Path("spec-chain-plan.json"))
    p_apply.add_argument("--force", action="store_true")
    p_apply.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "survey":
        return survey(args.out)
    if args.command == "plan":
        answers = json.loads(args.answers.read_text(encoding="utf-8"))
        root = args.root.resolve()
        out = args.out if args.out.is_absolute() else root / args.out
        meta = args.json if args.json.is_absolute() else root / args.json
        data = plan(answers, out, meta)
        print(f"ok: {out}")
        print(f"ok: {meta}")
        print(f"approach: {data['approach']}; stages: {', '.join(s['id'] for s in data['stages'])}")
        return 0
    if args.command == "approve":
        return approve(args.plan, args.json)
    if args.command == "apply":
        return apply(args.root.resolve(), args.plan_json, args.force, args.dry_run)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())