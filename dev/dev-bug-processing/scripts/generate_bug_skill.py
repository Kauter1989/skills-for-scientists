#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сгенерировать навык обработки дефектов под конкретный репозиторий.

Команды:
    python generate_bug_skill.py survey --out answers.json
    python generate_bug_skill.py plan --root . --answers answers.json
    python generate_bug_skill.py approve --plan bug-processing-plan.html --json bug-processing-plan.json
    python generate_bug_skill.py apply --root . --plan-json bug-processing-plan.json

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
REFERENCES = ROOT / "references"
GENERATED_SKILL = "dev-bug-process"
APPROACHES = (
    "test-first",
    "container-first",
    "incident-first",
    "benchmark-first",
    "lightweight",
)

STACK_DEFAULTS = {
    "python": ("pytest", "python -m pytest", "tests/"),
    "javascript": ("jest", "npm test", "tests/"),
    "typescript": ("vitest", "npm test", "tests/"),
    "java": ("junit", "mvn test", "src/test/java/"),
    "go": ("go test", "go test ./...", "."),
    "rust": ("cargo test", "cargo test", "."),
    "other": ("custom", "<команда тестов>", "tests/"),
}

APPROACH_INFO = {
    "test-first": (
        "локальный тестовый фреймворк и быстрые тесты",
        "red test, минимальный вход, git bisect",
    ),
    "container-first": (
        "дефект зависит от окружения или сервисов",
        "закреплённый образ, compose, детерминированные данные",
    ),
    "incident-first": (
        "production-инцидент или живая система",
        "timeline, логи и трейсы, rollback, затем локальное воспроизведение",
    ),
    "benchmark-first": (
        "много дефектов или исследовательский стенд",
        "пакетная обработка, метаданные, сравнение ревизий",
    ),
    "lightweight": (
        "малая команда и простой процесс",
        "минимальный отчёт без тяжёлого трекера",
    ),
}

INVARIANTS = [
    ("I1", "Подробное описание: expected / actual, окружение, версия, шаги, входы, логи", "поля repro.json"),
    ("I2", "Воспроизводимость: не менее 3 прогонов с одинаковым результатом", "probe.json"),
    ("I3", "Минимальный вход, каждый остаток обоснован", "minimal_case, removed"),
    ("I4", "Падающий автотест до фикса", "test.path, test.name, red_output"),
    ("I5", "Падение соответствует заявленному symptom", "failure_matches_symptom"),
    ("I6", "Диагноз: гипотезы с evidence, confidence и следующим probe", "diagnosis.hypotheses"),
    ("I7", "Фикс не начинается до красного гейта", "status и порядок шагов"),
    ("I8", "Артефакты в docs/bugs/<id>/", "манифест и файлы"),
    ("I9", "Недоверенные команды не запускаются автоматически", "явное решение пользователя"),
]

PROFILE_FIELDS = [
    ("Репозиторий", "repo"),
    ("Стек", "stack"),
    ("Тестовый фреймворк", "test_framework"),
    ("Команда тестов", "test_command"),
    ("Каталог тестов", "test_root"),
    ("Трекер", "tracker"),
    ("Окружение", "environment"),
    ("Команда", "team"),
    ("Compliance", "compliance"),
    ("Политика флейков", "flake_policy"),
    ("Глубина", "repro_depth"),
    ("Approval", "approval"),
]

FILE_SPECS = [
    (".opencode/bug-processing.yml", "манифест профиля и гейтов"),
    (".opencode/skill/dev-bug-process/SKILL.md", "операционный навык"),
    (".opencode/skill/dev-bug-process/references/bug-contract.md", "контракт и инварианты"),
    (".opencode/skill/dev-bug-process/templates/bug-report.md", "человекочитаемый отчёт"),
    (".opencode/skill/dev-bug-process/templates/repro.json", "машиночитаемый отчёт"),
    (".opencode/skill/dev-bug-process/scripts/probe_bug.py", "прогоны и классификация"),
    (".opencode/skill/dev-bug-process/scripts/check_bug_report.py", "проверка отчёта"),
    (".opencode/skill/dev-bug-process/examples/README.md", "пример заполнения"),
    ("docs/bugs/README.md", "правила каталога дефектов"),
]


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def ask(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def normalize_answers(answers: dict) -> dict:
    data = dict(answers)
    data.setdefault("repo", Path.cwd().name)
    data.setdefault("stack", "python")
    defaults = STACK_DEFAULTS.get(str(data["stack"]), STACK_DEFAULTS["other"])
    data.setdefault("test_framework", defaults[0])
    data.setdefault("test_command", defaults[1])
    data.setdefault("test_root", defaults[2])
    data.setdefault("tracker", "github")
    data.setdefault("environment", "local")
    data.setdefault("team", "small")
    data.setdefault("compliance", "none")
    data.setdefault("flake_policy", "strict")
    data.setdefault("repro_depth", "standard")
    data.setdefault("approval", "user")
    data.setdefault("approach", "auto")
    data.setdefault("issue_template", "none")
    for key, value in list(data.items()):
        if isinstance(value, str):
            data[key] = value.strip()
    return data


def survey(out: Path) -> int:
    print("Опрос для обработки дефектов. Enter — значение по умолчанию.\n")
    repo = ask("Имя репозитория", Path.cwd().name)
    stack = ask("Стек (python/javascript/typescript/java/go/rust/other)", "python")
    defaults = STACK_DEFAULTS.get(stack, STACK_DEFAULTS["other"])
    test_framework = ask("Тестовый фреймворк", defaults[0])
    test_command = ask("Команда тестов", defaults[1])
    test_root = ask("Каталог тестов", defaults[2])
    tracker = ask("Трекер (github/jira/none)", "github")
    environment = ask("Окружение (local/container/production/benchmark)", "local")
    team = ask("Команда (small/enterprise)", "small")
    compliance = ask("Compliance (none/audit)", "none")
    flake_policy = ask("Политика флейков (strict/retry)", "strict")
    repro_depth = ask("Глубина воспроизведения (light/standard/deep)", "standard")
    approval = ask("Режим утверждения (user/autonomous)", "user")
    approach = ask(
        "Подход (auto/test-first/container-first/incident-first/benchmark-first/lightweight)",
        "auto",
    )
    issue_template = ask("Шаблон issue (none/github/jira)", "none")
    answers = {
        "repo": repo,
        "stack": stack,
        "test_framework": test_framework,
        "test_command": test_command,
        "test_root": test_root,
        "tracker": tracker,
        "environment": environment,
        "team": team,
        "compliance": compliance,
        "flake_policy": flake_policy,
        "repro_depth": repro_depth,
        "approval": approval,
        "approach": approach,
        "issue_template": issue_template,
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

    environment = str(answers.get("environment", "local")).lower()
    if environment in {"production", "incident"}:
        return "incident-first"
    if environment in {"benchmark", "research"}:
        return "benchmark-first"
    if environment in {"container", "docker"}:
        return "container-first"
    if (
        answers.get("team") == "small"
        and answers.get("compliance") == "none"
        and answers.get("repro_depth") == "light"
    ):
        return "lightweight"
    return "test-first"


def min_runs(answers: dict) -> int:
    if answers.get("flake_policy") == "retry" or answers.get("repro_depth") == "deep":
        return 5
    return 3


def approach_notes(approach: str, answers: dict) -> str:
    if approach == "test-first":
        return (
            "Основной путь — локальный тестовый фреймворк. Red test пишется в "
            f"`{answers.get('test_root', 'tests/')}` и запускается командой "
            f"`{answers.get('test_command', '<команда тестов>')}`. Минимальный вход "
            "уменьшается вручную или delta debugging; `git bisect` предлагается как "
            "следующий probe, но не запускается автоматически."
        )
    if approach == "container-first":
        return (
            "Сначала зафиксируйте образ, диджест, переменные окружения и данные. "
            "Тест запускается внутри контейнера; локальный запуск без контейнера не "
            "считается воспроизведением. Если контейнер не воспроизводит дефект, "
            "статус `not-reproduced`, а не «исправлено»."
        )
    if approach == "incident-first":
        return (
            "Сначала timeline, impact, логи и трейсы. Mitigation и rollback разрешены "
            "до red test, но фикс запрещён до локального воспроизведения и падающего "
            "теста. После инцидента артефакты остаются в `docs/bugs/<id>/`."
        )
    if approach == "benchmark-first":
        return (
            "Один `bug-id` — один набор артефактов. Фиксируйте ревизии и метаданные, "
            "не смешивайте дефекты и сравнивайте поведение «до / после» на одной и "
            "той же команде."
        )
    return (
        "Можно не заводить issue и не использовать тяжёлый трекер, но отчёт всё "
        "равно содержит expected / actual, окружение и red test. Все 9 инвариантов "
        "сохраняются."
    )


def profile_rows(answers: dict, approach: str) -> str:
    rows = []
    for label, key in PROFILE_FIELDS:
        rows.append(
            f'<tr><td>{html.escape(label)}</td>'
            f'<td class="mono">{html.escape(str(answers.get(key, "")))}</td></tr>'
        )
    rows.append(
        '<tr><td>Подход</td>'
        f'<td class="mono">{html.escape(approach)}</td></tr>'
    )
    return "\n".join(rows)


def approach_rows(selected: str) -> str:
    rows = []
    for key, (when, adds) in APPROACH_INFO.items():
        css = ' class="selected"' if key == selected else ""
        rows.append(
            f"<tr{css}><td class=\"mono\">{html.escape(key)}</td>"
            f"<td>{html.escape(when)}</td><td>{html.escape(adds)}</td></tr>"
        )
    return "\n".join(rows)


def invariant_rows() -> str:
    rows = []
    for number, text, check in INVARIANTS:
        rows.append(
            f"<tr><td class=\"mono\">{number}</td><td>{html.escape(text)}</td>"
            f"<td class=\"mono\">{html.escape(check)}</td></tr>"
        )
    return "\n".join(rows)


def file_rows() -> str:
    return "\n".join(
        f'<tr><td class="mono">{html.escape(path)}</td><td>{html.escape(purpose)}</td></tr>'
        for path, purpose in FILE_SPECS
    )


def plan(answers: dict, out_html: Path, out_json: Path) -> dict:
    answers = normalize_answers(answers)
    approach = choose_approach(answers)
    data = {
        "status": "draft",
        "created": dt.date.today().isoformat(),
        "repo": answers["repo"],
        "approach": approach,
        "generated_skill": GENERATED_SKILL,
        "profile": answers,
        "min_runs": min_runs(answers),
        "invariants": [number for number, _, _ in INVARIANTS],
        "files": [{"path": path, "purpose": purpose} for path, purpose in FILE_SPECS],
    }
    template = (TEMPLATES / "bug-processing-plan.html").read_text(encoding="utf-8")
    values = {
        "REPO": data["repo"],
        "APPROACH": approach,
        "DATE": data["created"],
        "STATUS": "draft",
        "PROFILE_ROWS": profile_rows(answers, approach),
        "APPROACH_ROWS": approach_rows(approach),
        "INVARIANT_ROWS": invariant_rows(),
        "FILE_ROWS": file_rows(),
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
        text = text.replace(
            '<span id="approval" class="status draft">draft</span>',
            '<span id="approval" class="status approved">approved</span>',
        )
        plan_html.write_text(text, encoding="utf-8")
    print(f"ok: approved {plan_json}")
    return 0


def generated_skill_md(data: dict) -> str:
    template = (TEMPLATES / "generated-SKILL.md").read_text(encoding="utf-8")
    profile = data["profile"]
    values = {
        "GENERATED_SKILL": GENERATED_SKILL,
        "REPO": data["repo"],
        "APPROACH": data["approach"],
        "APPROACH_NOTES": approach_notes(data["approach"], profile),
        "STACK": profile.get("stack", ""),
        "TEST_FRAMEWORK": profile.get("test_framework", ""),
        "TEST_COMMAND": profile.get("test_command", ""),
        "TEST_ROOT": profile.get("test_root", ""),
        "TRACKER": profile.get("tracker", ""),
        "TRACKER_LINE": (
            "ссылка на issue не требуется"
            if profile.get("tracker") in {"", "none"}
            else f"ссылка на issue в `{profile.get('tracker')}`, если есть"
        ),
        "ENVIRONMENT": profile.get("environment", ""),
        "TEAM": profile.get("team", ""),
        "COMPLIANCE": profile.get("compliance", ""),
        "FLAKE_POLICY": profile.get("flake_policy", ""),
        "REPRO_DEPTH": profile.get("repro_depth", ""),
        "APPROVAL": profile.get("approval", ""),
        "MIN_RUNS": data.get("min_runs", 3),
        "ISSUE_TEMPLATE": profile.get("issue_template", "none"),
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def manifest(data: dict) -> str:
    template = (TEMPLATES / "bug-processing.yml").read_text(encoding="utf-8")
    profile = data["profile"]
    values = {
        "REPO": data["repo"],
        "STACK": profile.get("stack", ""),
        "TEST_FRAMEWORK": profile.get("test_framework", ""),
        "TEST_COMMAND": profile.get("test_command", ""),
        "TEST_ROOT": profile.get("test_root", ""),
        "TRACKER": profile.get("tracker", ""),
        "ENVIRONMENT": profile.get("environment", ""),
        "TEAM": profile.get("team", ""),
        "COMPLIANCE": profile.get("compliance", ""),
        "FLAKE_POLICY": profile.get("flake_policy", ""),
        "REPRO_DEPTH": profile.get("repro_depth", ""),
        "APPROVAL": profile.get("approval", ""),
        "APPROACH": data["approach"],
        "MIN_RUNS": data.get("min_runs", 3),
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def examples_readme(data: dict) -> str:
    profile = data["profile"]
    return (
        f"# Пример обработки дефекта — {data['repo']}\n\n"
        f"Подход: `{data['approach']}`. Команда тестов: "
        f"`{profile.get('test_command', '')}`.\n\n"
        "1. Создайте `docs/bugs/<id>/repro.md` и `repro.json` из шаблонов.\n"
        "2. Запустите прогоны:\n\n"
        "   ```bash\n"
        "   python .opencode/skill/dev-bug-process/scripts/probe_bug.py \\\n"
        f"     --runs {data.get('min_runs', 3)} --out docs/bugs/<id>/probe.json -- \\\n"
        f"     {profile.get('test_command', '<команда тестов>')}\n"
        "   ```\n\n"
        "3. Заполните red test и гипотезы.\n"
        "4. Проверьте отчёт:\n\n"
        "   ```bash\n"
        "   python .opencode/skill/dev-bug-process/scripts/check_bug_report.py \\\n"
        "     --root . --report docs/bugs/<id>/repro.json --strict\n"
        "   ```\n"
    )


def docs_bugs_readme(data: dict) -> str:
    return (
        "# Каталог дефектов\n\n"
        "Один дефект — один каталог `docs/bugs/<id>/`.\n\n"
        "| Файл | Назначение |\n|---|---|\n"
        "| `repro.md` | подробное описание, шаги, логи |\n"
        "| `repro.json` | машиночитаемый отчёт |\n"
        "| `probe.json` | прогоны и классификация |\n\n"
        f"Подход: `{data['approach']}`. Минимум прогонов: {data.get('min_runs', 3)}.\n"
        "Проверка: `python .opencode/skill/dev-bug-process/scripts/check_bug_report.py "
        "--root . --report docs/bugs/<id>/repro.json --strict`.\n"
    )


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

    skill_dir = root / ".opencode" / "skill" / GENERATED_SKILL
    copies = [
        (REFERENCES / "bug-contract.md", skill_dir / "references" / "bug-contract.md"),
        (TEMPLATES / "bug-report.md", skill_dir / "templates" / "bug-report.md"),
        (TEMPLATES / "repro.json", skill_dir / "templates" / "repro.json"),
        (TEMPLATES / "probe_bug.py", skill_dir / "scripts" / "probe_bug.py"),
        (TEMPLATES / "check_bug_report.py", skill_dir / "scripts" / "check_bug_report.py"),
    ]

    report = []
    report.append(write_file(root / ".opencode" / "bug-processing.yml", manifest(data), force, dry))
    report.append(write_file(skill_dir / "SKILL.md", generated_skill_md(data), force, dry))
    for source, target in copies:
        report.append(write_file(target, source.read_text(encoding="utf-8"), force, dry))
    report.append(write_file(skill_dir / "examples" / "README.md", examples_readme(data), force, dry))
    report.append(write_file(root / "docs" / "bugs" / "README.md", docs_bugs_readme(data), force, dry))

    if not dry:
        (root / "bug-processing-report.md").write_text(
            "# Bug processing report\n\n"
            f"Дата: {dt.date.today().isoformat()}\n\n"
            f"Подход: `{data['approach']}`\n\n"
            + "\n".join(f"- {line}" for line in report)
            + "\n",
            encoding="utf-8",
        )
    for line in report:
        print(line)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Генерация навыка обработки дефектов")
    sub = parser.add_subparsers(dest="command", required=True)

    p_survey = sub.add_parser("survey")
    p_survey.add_argument("--out", type=Path, default=Path("answers.json"))

    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--root", type=Path, default=Path("."))
    p_plan.add_argument("--answers", type=Path, required=True)
    p_plan.add_argument("--out", type=Path, default=Path("bug-processing-plan.html"))
    p_plan.add_argument("--json", type=Path, default=Path("bug-processing-plan.json"))

    p_approve = sub.add_parser("approve")
    p_approve.add_argument("--plan", type=Path, default=Path("bug-processing-plan.html"))
    p_approve.add_argument("--json", type=Path, default=Path("bug-processing-plan.json"))

    p_apply = sub.add_parser("apply")
    p_apply.add_argument("--root", type=Path, default=Path("."))
    p_apply.add_argument("--plan-json", type=Path, default=Path("bug-processing-plan.json"))
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
        print(f"approach: {data['approach']}; generated: {data['generated_skill']}; runs: {data['min_runs']}")
        return 0
    if args.command == "approve":
        return approve(args.plan, args.json)
    if args.command == "apply":
        return apply(args.root.resolve(), args.plan_json, args.force, args.dry_run)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())