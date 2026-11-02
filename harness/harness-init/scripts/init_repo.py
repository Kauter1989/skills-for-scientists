#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Init: опрос, HTML-план, утверждение и scaffold.

Команды:
    python init_repo.py survey --out answers.json
    python init_repo.py plan --root . --answers answers.json --out bootstrap-plan.html
    python init_repo.py approve --plan bootstrap-plan.html --json bootstrap-plan.json
    python init_repo.py apply --root . --plan-json bootstrap-plan.json

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

SKILL_INFO = {
    "harness-skill-template": "контракт и проверка нового навыка",
    "harness-rule-to-mechanism": "правило → проверка и registry",
    "harness-skill-audit": "аудит структуры и дублей библиотеки",
    "dev-pr-report-html": "HTML-отчёт об изменениях фичи",
    "pptx-report": "презентации и отчёты PPTX",
    "sci-literature-news": "научный дайджест: Q1/A*/Q2, темы, датасеты, HTML",
}
SDD_COMMAND = "/dev-spec-chain"
DEFAULT_BRANCH = "main"
TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def ask(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def survey(out: Path) -> int:
    print("Опрос для bootstrap. Enter — значение по умолчанию.\n")

    print("Блок 1/3: научные данные и отчёты.")
    science_work = csv_list(
        ask(
            "Научная работа (analysis,experiment,literature,dataset,visualization,none)",
            "none",
        )
    )
    science_data = ask("Данные: формат, объём, чувствительность", "не задано")
    science_outputs = csv_list(
        ask("Результаты (article,html-report,pptx,dashboard,dataset,none)", "none")
    )
    reproducibility = ask("Воспроизводимость (code,data,env,license,none)", "code")

    print("\nБлок 2/3: разработка.")
    project_mode = ask("Режим разработки (greenfield,brownfield,none)", "none")
    dev_specifics = ask(
        "Специфика разработки (web,ml,cli,library,critical,integrations)",
        "не задано",
    )
    sdd_setup = ask(
        f"Настроить SDD отдельно командой {SDD_COMMAND}? (yes/no/later)",
        "later",
    )

    print("\nБлок 3/3: библиотека навыков.")
    library_contribution = ask(
        "Дополнить библиотеку навыков? (none,new-skill,improve-existing)",
        "none",
    )

    print("\nОбщие вопросы.")
    answers = {
        "project": ask("Имя проекта", Path.cwd().name),
        "domain": ask("Домен (dev/science/integrations/reports/mixed)", "dev"),
        "stack": ask("Стек", "python"),
        "default_branch": ask("Основная ветка", DEFAULT_BRANCH),
        "workflow": ask("Workflow (minimal/extended)", "minimal"),
        "ci": ask("CI (github/none)", "github"),
        "commands": {
            "test": ask("Команда тестов", "pytest -q"),
            "lint": ask("Команда линтера", "ruff check ."),
            "build": ask("Команда сборки", ""),
        },
        "roles": csv_list(ask("Роли через запятую", "developer, reviewer")),
        "tasks": csv_list(
            ask(
                "Стартовые задачи (feature,bugfix,release,report,audit,rules,presentation,literature,dataset)",
                "feature, bugfix, report",
            )
        ),
        "constraints": csv_list(ask("Ограничения через запятую", "private")),
        "skills": [],
        "science_work": science_work,
        "science_data": science_data,
        "science_outputs": science_outputs,
        "reproducibility": reproducibility,
        "project_mode": project_mode,
        "dev_specifics": dev_specifics,
        "sdd_setup": sdd_setup,
        "library_contribution": library_contribution,
    }
    out.write_text(json.dumps(answers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nok: {out}")
    return 0


def recommend(answers: dict) -> list[str]:
    explicit = [x for x in answers.get("skills", []) if x in SKILL_INFO]
    if explicit:
        return explicit
    tasks = {str(x).lower() for x in answers.get("tasks", [])}
    science_work = {str(x).lower() for x in answers.get("science_work", [])}
    outputs = {str(x).lower() for x in answers.get("science_outputs", [])}
    skills = ["harness-skill-template", "harness-skill-audit"]
    if tasks & {"rules", "quality", "feature", "bugfix"}:
        skills.append("harness-rule-to-mechanism")
    if tasks & {"report", "release", "audit"} or "html-report" in outputs:
        skills.append("dev-pr-report-html")
    if "presentation" in tasks or "pptx" in outputs:
        skills.append("pptx-report")
    if (
        science_work & {"literature", "digest"}
        or outputs & {"literature-digest", "article"}
        or "literature" in tasks
    ):
        skills.append("sci-literature-news")
    return list(dict.fromkeys(skills))


def stages(answers: dict, skills: list[str]) -> list[dict]:
    def present(items: list[str]) -> str:
        return ", ".join(item for item in items if item in skills) or "—"

    science_work = {str(x).lower() for x in answers.get("science_work", [])} - {"none"}
    outputs = {str(x).lower() for x in answers.get("science_outputs", [])} - {"none"}
    result = [
        {"stage": "Старт", "what": "Открыть репозиторий и выбрать первый шаг", "skills": present(["harness-skill-template"])},
    ]
    if science_work or outputs:
        result.append(
            {
                "stage": "Научные данные",
                "what": "Зафиксировать данные, лицензии и воспроизводимость",
                "skills": present(["sci-literature-news", "dev-pr-report-html"]),
            }
        )
        result.append(
            {
                "stage": "Научный результат",
                "what": "Собрать дайджест, отчёт, презентацию или датасет",
                "skills": present(["sci-literature-news", "dev-pr-report-html", "pptx-report"]),
            }
        )
    result.append(
        {"stage": "Правила", "what": "Проверить, что правила имеют механизм", "skills": present(["harness-rule-to-mechanism"])}
    )
    if str(answers.get("project_mode", "none")).lower() in {"greenfield", "brownfield"}:
        result.append(
            {
                "stage": "Разработка и SDD",
                "what": f"Настроить spec-driven workflow отдельной командой {SDD_COMMAND}",
                "skills": SDD_COMMAND,
            }
        )
    else:
        result.append(
            {"stage": "Работа", "what": "Выполнить стартовую задачу", "skills": present(["dev-pr-report-html"])}
        )
    if str(answers.get("library_contribution", "none")).lower() != "none":
        result.append(
            {
                "stage": "Библиотека",
                "what": "Добавить или улучшить навык по гейтам research → review → PR",
                "skills": present(["harness-skill-template", "harness-skill-audit"]),
            }
        )
    result.append(
        {"stage": "Проверка", "what": "Проверить структуру и дубли", "skills": present(["harness-skill-audit"])}
    )
    result.append(
        {"stage": "Отчёт", "what": "Собрать результат для ревью", "skills": present(["dev-pr-report-html", "pptx-report"])}
    )
    return result


def skill_rows(skills: list[str]) -> str:
    rows = []
    for skill in skills:
        rows.append(
            "<tr>"
            f'<td class="mono">{html.escape(skill)}</td>'
            f"<td>{html.escape(SKILL_INFO.get(skill, ''))}</td>"
            "<td>реализован</td>"
            "</tr>"
        )
    return "\n".join(rows)


def stage_rows(items: list[dict]) -> str:
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f'<td>{html.escape(item["stage"])}</td>'
            f'<td>{html.escape(item["what"])}</td>'
            f'<td class="mono">{html.escape(item["skills"])}</td>'
            "</tr>"
        )
    return "\n".join(rows)


def command_rows(answers: dict) -> str:
    rows = []
    for name, label in (("test", "тесты"), ("lint", "линтер"), ("build", "сборка")):
        command = answers.get("commands", {}).get(name, "")
        rows.append(
            "<tr>"
            f'<td>{label}</td>'
            f'<td class="mono">{html.escape(command or "не задана")}</td>'
            "</tr>"
        )
    return "\n".join(rows)


def file_rows(answers: dict) -> str:
    files = [
        ("profile.yml", "профиль проекта"),
        ("AGENTS.md", "правила и команды"),
        ("docs/research/", "research ledger"),
        ("docs/reviews/", "HTML-ревью"),
        ("docs/audits/", "отчёты аудита"),
        ("docs/rules/registry.yml", "реестр правил"),
        (".pre-commit-config.yaml", "локальные хуки"),
    ]
    if answers.get("ci") == "github":
        files.append((".github/workflows/ci.yml", "CI"))
    return "\n".join(
        f'<tr><td class="mono">{html.escape(path)}</td><td>{html.escape(desc)}</td></tr>'
        for path, desc in files
    )


def value_text(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "не задано"
    return str(value or "не задано")


def science_rows(answers: dict) -> str:
    rows = [
        ("Научная работа", answers.get("science_work")),
        ("Данные", answers.get("science_data")),
        ("Результаты", answers.get("science_outputs")),
        ("Воспроизводимость", answers.get("reproducibility")),
    ]
    return "\n".join(
        f'<tr><td>{html.escape(label)}</td><td>{html.escape(value_text(value))}</td></tr>'
        for label, value in rows
    )


def dev_rows(answers: dict) -> str:
    rows = [
        ("Режим проекта", answers.get("project_mode")),
        ("Специфика", answers.get("dev_specifics")),
        ("SDD", answers.get("sdd_setup")),
        ("Команда SDD", SDD_COMMAND),
    ]
    return "\n".join(
        f'<tr><td>{html.escape(label)}</td><td>{html.escape(value_text(value))}</td></tr>'
        for label, value in rows
    )


def library_note(answers: dict) -> str:
    contribution = str(answers.get("library_contribution", "none")).lower()
    if contribution == "new-skill":
        return (
            "Новый навык: `harness-skill-audit` (проверить дубли) → "
            "`docs/research/<skill>.md` → `docs/reviews/<skill>.html` со статусом "
            "`approved` → `harness-skill-template` → пример и валидатор → PR."
        )
    if contribution == "improve-existing":
        return (
            "Улучшение навыка: прочитать `SKILL.md`, `references/` и `examples/`, "
            "проверить триггеры через `harness-skill-audit`, обновить research/review "
            "и открыть PR."
        )
    return (
        "Не планируется. Если появится новый навык, начинать с "
        "`harness-skill-template` и проходить research/review до реализации."
    )


def route_rows(answers: dict) -> str:
    mode = str(answers.get("project_mode", "none")).lower()
    if mode in {"greenfield", "brownfield"}:
        sdd = f'<code>{SDD_COMMAND}</code> — отдельная команда, bootstrap её не запускает'
    else:
        sdd = "не требуется"
    contribution = str(answers.get("library_contribution", "none")).lower()
    library = {
        "new-skill": "<code>harness-skill-template</code> → research/review → <code>harness-skill-audit</code> → PR",
        "improve-existing": "<code>harness-skill-audit</code> → правка навыка → research/review → PR",
    }.get(contribution, "не требуется")
    rows = [
        ("Научные данные и отчёты", "<code>harness-init</code> → рекомендованные научные и отчётные навыки"),
        ("Разработка и SDD", sdd),
        ("Пополнение библиотеки", library),
    ]
    return "\n".join(
        f"<tr><td>{html.escape(label)}</td><td>{value}</td></tr>" for label, value in rows
    )


def plan(answers: dict, out_html: Path, out_json: Path, status: str = "draft") -> dict:
    skills = recommend(answers)
    data = {
        "status": status,
        "created": dt.date.today().isoformat(),
        "answers": answers,
        "skills": skills,
        "stages": stages(answers, skills),
        "route": {
            "entry": "harness-init",
            "sdd": SDD_COMMAND,
            "library": "harness-skill-template → research/review → harness-skill-audit → PR",
        },
        "files": [
            "profile.yml", "AGENTS.md", "docs/research/", "docs/reviews/",
            "docs/audits/", "docs/rules/registry.yml", ".pre-commit-config.yaml",
        ] + ([".github/workflows/ci.yml"] if answers.get("ci") == "github" else []),
    }
    template = (TEMPLATES / "bootstrap-plan.html").read_text(encoding="utf-8")
    values = {
        "PROJECT": answers.get("project", "project"),
        "DOMAIN": answers.get("domain", "dev"),
        "STACK": answers.get("stack", ""),
        "WORKFLOW": answers.get("workflow", "minimal"),
        "DATE": data["created"],
        "STATUS": status,
        "SDD_COMMAND": SDD_COMMAND,
        "SCIENCE_ROWS": science_rows(answers),
        "DEV_ROWS": dev_rows(answers),
        "ROUTE_ROWS": route_rows(answers),
        "SKILL_ROWS": skill_rows(skills),
        "STAGE_ROWS": stage_rows(data["stages"]),
        "COMMAND_ROWS": command_rows(answers),
        "FILE_ROWS": file_rows(answers),
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
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


def write_file(path: Path, content: str, force: bool, dry: bool) -> str:
    if path.exists() and not force:
        return f"skip {path} (exists)"
    if dry:
        return f"would write {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"write {path}"


def render(template_name: str, values: dict[str, str]) -> str:
    text = (TEMPLATES / template_name).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def apply(root: Path, plan_json: Path, force: bool, dry: bool) -> int:
    if not plan_json.is_file():
        fail(f"план не найден: {plan_json}")
    data = json.loads(plan_json.read_text(encoding="utf-8"))
    if data.get("status") != "approved":
        fail("план не утверждён: статус должен быть approved")
    answers = data["answers"]
    skills = data["skills"]
    files: list[tuple[Path, str]] = [
        (root / "profile.yml", render("profile.yml", {
            "PROJECT": answers.get("project", ""),
            "DOMAIN": answers.get("domain", ""),
            "STACK": answers.get("stack", ""),
            "WORKFLOW": answers.get("workflow", ""),
            "CI": answers.get("ci", ""),
            "TEST_COMMAND": answers.get("commands", {}).get("test", ""),
            "LINT_COMMAND": answers.get("commands", {}).get("lint", ""),
            "BUILD_COMMAND": answers.get("commands", {}).get("build", ""),
            "PROJECT_MODE": value_text(answers.get("project_mode")),
            "SCIENCE_WORK": value_text(answers.get("science_work")),
            "SCIENCE_OUTPUTS": value_text(answers.get("science_outputs")),
            "SDD_SETUP": value_text(answers.get("sdd_setup")),
            "SKILLS_YAML": "\n".join(f"  - {s}" for s in skills) or "  []",
        })),
        (root / "AGENTS.md", render("AGENTS.md", {
            "PROJECT": answers.get("project", ""),
            "DOMAIN": answers.get("domain", ""),
            "STACK": answers.get("stack", ""),
            "WORKFLOW": answers.get("workflow", ""),
            "DATE": data.get("created", ""),
            "TEST_COMMAND": answers.get("commands", {}).get("test", ""),
            "LINT_COMMAND": answers.get("commands", {}).get("lint", ""),
            "BUILD_COMMAND": answers.get("commands", {}).get("build", ""),
            "DEFAULT_BRANCH": answers.get("default_branch", DEFAULT_BRANCH),
            "SCIENCE_WORK": value_text(answers.get("science_work")),
            "SCIENCE_DATA": value_text(answers.get("science_data")),
            "SCIENCE_OUTPUTS": value_text(answers.get("science_outputs")),
            "REPRODUCIBILITY": value_text(answers.get("reproducibility")),
            "PROJECT_MODE": value_text(answers.get("project_mode")),
            "DEV_SPECIFICS": value_text(answers.get("dev_specifics")),
            "SDD_SETUP": value_text(answers.get("sdd_setup")),
            "SDD_COMMAND": SDD_COMMAND,
            "LIBRARY_NOTE": library_note(answers),
            "SKILLS_MD": "\n".join(f"- `{s}` — {SKILL_INFO.get(s, '')}" for s in skills),
        })),
        (root / "docs" / "rules" / "registry.yml", "version: 1\nrules: []\n"),
        (root / ".pre-commit-config.yaml", (TEMPLATES / "pre-commit-config.yaml").read_text(encoding="utf-8")),
    ]
    for directory in ("docs/research", "docs/reviews", "docs/audits"):
        files.append((root / directory / ".gitkeep", ""))
    if answers.get("ci") == "github":
        files.append((root / ".github" / "workflows" / "ci.yml", render("ci.yml", {
            "TEST_COMMAND": answers.get("commands", {}).get("test") or 'echo "no test command"',
            "LINT_COMMAND": answers.get("commands", {}).get("lint") or 'echo "no lint command"',
        })))

    report = []
    for path, content in files:
        report.append(write_file(path, content, force, dry))
    lines = "\n".join(f"- {line}" for line in report)
    root.joinpath("bootstrap-report.md").write_text(
        f"# Bootstrap report\n\nДата: {dt.date.today().isoformat()}\n\n{lines}\n",
        encoding="utf-8",
    ) if not dry else None
    for line in report:
        print(line)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap с опросом и HTML-утверждением")
    sub = parser.add_subparsers(dest="command", required=True)

    p_survey = sub.add_parser("survey")
    p_survey.add_argument("--out", type=Path, default=Path("answers.json"))

    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--root", type=Path, default=Path("."))
    p_plan.add_argument("--answers", type=Path, required=True)
    p_plan.add_argument("--out", type=Path, default=Path("bootstrap-plan.html"))
    p_plan.add_argument("--json", type=Path, default=Path("bootstrap-plan.json"))

    p_approve = sub.add_parser("approve")
    p_approve.add_argument("--plan", type=Path, default=Path("bootstrap-plan.html"))
    p_approve.add_argument("--json", type=Path, default=Path("bootstrap-plan.json"))

    p_apply = sub.add_parser("apply")
    p_apply.add_argument("--root", type=Path, default=Path("."))
    p_apply.add_argument("--plan-json", type=Path, default=Path("bootstrap-plan.json"))
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
        print(f"status: {data['status']}; skills: {', '.join(data['skills'])}")
        return 0
    if args.command == "approve":
        return approve(args.plan, args.json)
    if args.command == "apply":
        return apply(args.root.resolve(), args.plan_json, args.force, args.dry_run)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())