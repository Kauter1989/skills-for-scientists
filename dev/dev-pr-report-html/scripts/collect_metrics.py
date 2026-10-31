#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собрать метрики изменения из Git и кода в metrics.json.

Что выводится автоматически:
  * Cognitive Load Index (сырой балл, сущности, blast radius);
  * Hallucination Risk (неразрешённые внутренние импорты и ссылки на файлы);
  * метаданные изменения (коммиты, LOC, файлы).

Что требует телеметрии (--telemetry):
  * Feature Token Budget, Agent Iteration Rate, Context Window Utilization.

Architecture Drift Score не вычисляется автоматически: нужен архитектурный
контракт. Скрипт оставляет секцию пустой и напоминает, что проверить.

Использование:
    python collect_metrics.py --repo . --from v1.4.0 --to HEAD --out metrics.json
    python collect_metrics.py --repo . --from HEAD~20 --telemetry telemetry.json

Только стандартная библиотека. Python 3.9+.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache",
    "site-packages", "dist", "build", ".tox", ".nox",
}

SOURCE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go",
              ".rs", ".java", ".kt", ".cs", ".cpp", ".cc", ".c", ".h", ".hpp"}
DOC_EXT = {".md", ".rst", ".adoc", ".txt"}
CONFIG_EXT = {".yml", ".yaml", ".toml", ".ini", ".cfg", ".json"}
DEP_FILES = {
    "pyproject.toml", "requirements.txt", "requirements-dev.txt", "uv.lock",
    "poetry.lock", "pipfile", "pipfile.lock", "package.json",
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "go.mod", "go.sum",
    "cargo.toml", "cargo.lock", "pom.xml", "build.gradle", "build.gradle.kts",
}
PATH_RE = re.compile(
    r"(?<![\w/.-])((?:[\w.-]+/)+[\w.-]+\.(?:py|ts|tsx|js|jsx|md|json|ya?ml|toml|sql|css|html))"
)
JS_IMPORT_RE = re.compile(
    r"""(?:from\s*|require\s*\(\s*|import\s*\(\s*)['"]([^'"]+)['"]"""
)


def run_git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout


def rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_test(path: str) -> bool:
    low = path.lower()
    name = low.rsplit("/", 1)[-1]
    return (
        "/tests/" in low or low.startswith("tests/") or "/test/" in low
        or name.startswith("test_") or name.endswith("_test.py")
        or ".test." in name or ".spec." in name
    )


def is_migration(path: str) -> bool:
    low = path.lower()
    return "/alembic/versions/" in low or "/migrations/" in low


def classify(path: str) -> str:
    low = path.lower()
    name = low.rsplit("/", 1)[-1]
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if is_test(path):
        return "tests"
    if is_migration(path):
        return "migrations"
    if name in DEP_FILES:
        return "deps"
    if ext in DOC_EXT:
        return "docs"
    if ext in SOURCE_EXT:
        return "source"
    if ext in CONFIG_EXT or name.startswith("dockerfile"):
        return "config"
    return "other"


def parse_numstat(text: str) -> tuple[list[dict], list[str]]:
    files, warnings = [], []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            warnings.append(f"не разобрана строка numstat: {line!r}")
            continue
        added, deleted, path = parts
        if added == "-" or deleted == "-":
            warnings.append(f"бинарный файл пропущен: {path}")
            continue
        if "=>" in path:
            path = path.split("=>")[-1].strip().strip("{}").strip()
        files.append({
            "path": path,
            "added": int(added),
            "deleted": int(deleted),
            "kind": classify(path),
        })
    return files, warnings


def added_ranges(repo: Path, rev_from: str, rev_to: str, path: str) -> list[tuple[int, int]]:
    try:
        diff = run_git(repo, "diff", "-U0", f"{rev_from}..{rev_to}", "--", path)
    except RuntimeError:
        return []
    ranges: list[tuple[int, int]] = []
    for line in diff.splitlines():
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
        if m:
            start = int(m.group(1))
            count = int(m.group(2) or 1)
            if count > 0:
                ranges.append((start, start + count - 1))
    return ranges


def in_ranges(line: int, ranges: list[tuple[int, int]]) -> bool:
    return any(a <= line <= b for a, b in ranges)


def git_show(repo: Path, rev: str, path: str) -> str | None:
    try:
        return run_git(repo, "show", f"{rev}:{path}")
    except RuntimeError:
        return None


@dataclass
class ImportIndex:
    modules: dict[str, str] = field(default_factory=dict)
    top_packages: set[str] = field(default_factory=set)


def build_import_index(repo: Path, max_files: int) -> ImportIndex:
    index = ImportIndex()
    count = 0
    for path in repo.rglob("*.py"):
        if count >= max_files:
            break
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        rel = path.relative_to(repo)
        parts = list(rel.with_suffix("").parts)
        if parts and parts[0] in {"src", "lib"}:
            parts = parts[1:]
        if not parts:
            continue
        module = ".".join(parts)
        index.modules.setdefault(module, rel.as_posix())
        index.top_packages.add(parts[0])
        count += 1
    return index


def resolve_relative(file_path: str, level: int, module: str | None) -> str | None:
    parts = file_path.split("/")[:-1]
    if level > 1:
        parts = parts[: len(parts) - (level - 1)]
    if module:
        parts.extend(module.split("."))
    return ".".join(parts) if parts else None


def check_python_imports(
    index: ImportIndex,
    path: str,
    source: str,
) -> tuple[list[dict], list[dict]]:
    """Вернуть (внутренние_проверки, подтверждённые_пропуски)."""
    checks, missing = [], []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return checks, missing

    def exists(module: str) -> bool:
        if module in index.modules:
            return True
        prefix = module + "."
        return any(key.startswith(prefix) for key in index.modules)

    for node in ast.walk(tree):
        targets: list[str] = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = resolve_relative(path, node.level, node.module)
                if base:
                    targets.append(base)
                for alias in node.names:
                    if alias.name != "*" and base:
                        targets.append(f"{base}.{alias.name}")
            elif node.module:
                targets.append(node.module)

        for target in targets:
            top = target.split(".")[0]
            internal = top in index.top_packages
            if not internal:
                checks.append({"module": target, "kind": "external", "status": "unverified"})
                continue
            if exists(target):
                checks.append({"module": target, "kind": "internal", "status": "ok"})
            else:
                checks.append({"module": target, "kind": "internal", "status": "missing"})
                missing.append({
                    "type": "missing_import",
                    "symbol": target,
                    "location": path,
                    "evidence": "модуль не найден в индексе репозитория",
                })
    return checks, missing


def check_js_imports(repo: Path, path: str, source: str) -> tuple[list[dict], list[dict]]:
    checks, missing = [], []
    base = (repo / path).parent
    exts = ["", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json", ".css",
            "/index.ts", "/index.tsx", "/index.js", "/index.jsx"]
    for m in JS_IMPORT_RE.finditer(source):
        spec = m.group(1)
        if not spec.startswith("."):
            checks.append({"module": spec, "kind": "external", "status": "unverified"})
            continue
        target = (base / spec).resolve()
        ok = any((Path(str(target) + ext)).exists() for ext in exts)
        if ok:
            checks.append({"module": spec, "kind": "internal", "status": "ok"})
        else:
            checks.append({"module": spec, "kind": "internal", "status": "missing"})
            missing.append({
                "type": "missing_import",
                "symbol": spec,
                "location": path,
                "evidence": "относительный импорт не разрешается в файл",
            })
    return checks, missing


def python_entities(source: str, ranges: list[tuple[int, int]]) -> dict:
    result = {"classes": 0, "public_functions": 0, "private_functions": 0,
              "routes": 0, "models": 0}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return result
    for node in ast.walk(tree):
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not in_ranges(getattr(node, "lineno", -1), ranges):
            continue
        if isinstance(node, ast.ClassDef):
            result["classes"] += 1
            bases = []
            for base in node.bases:
                try:
                    bases.append(ast.unparse(base))
                except Exception:
                    pass
            if any(("Base" in b or "Model" in b or "Declarative" in b) for b in bases):
                result["models"] += 1
            continue
        is_route = False
        for dec in node.decorator_list:
            try:
                text = ast.unparse(dec)
            except Exception:
                text = ""
            if any(token in text for token in (".callback", ".route", ".get(", ".post(", ".put(", ".delete(")):
                is_route = True
        if is_route:
            result["routes"] += 1
        elif node.name.startswith("_"):
            result["private_functions"] += 1
        else:
            result["public_functions"] += 1
    return result


def build_reverse_graph(repo: Path, index: ImportIndex, max_files: int) -> dict[str, set[str]]:
    reverse: dict[str, set[str]] = defaultdict(set)
    count = 0
    for path in repo.rglob("*.py"):
        if count >= max_files:
            break
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        count += 1
        rel = path.relative_to(repo).as_posix()
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except Exception:
            continue
        for node in ast.walk(tree):
            target = None
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    target = resolve_relative(rel, node.level, node.module)
                elif node.module:
                    target = node.module
            elif isinstance(node, ast.Import) and node.names:
                target = node.names[0].name
            if not target:
                continue
            resolved = index.modules.get(target)
            if not resolved:
                prefix = target + "."
                for key, value in index.modules.items():
                    if key.startswith(prefix):
                        resolved = value
                        break
            if resolved and resolved != rel:
                reverse[resolved].add(rel)
    return reverse


def blast_radius(changed: list[str], reverse: dict[str, set[str]]) -> int:
    seen: set[str] = set()
    frontier = set(changed)
    for _ in range(2):
        nxt: set[str] = set()
        for item in frontier:
            for importer in reverse.get(item, set()):
                if importer not in seen and importer not in changed:
                    seen.add(importer)
                    nxt.add(importer)
        frontier = nxt
        if not frontier:
            break
    return len(seen)


def stale_references(repo: Path, path: str, added_lines: list[str]) -> list[dict]:
    findings = []
    base = (repo / path).parent
    for line in added_lines:
        for m in PATH_RE.finditer(line):
            ref = m.group(1)
            if ref.startswith(("http", "www", "node_modules/", ".venv/")):
                continue
            if any(ch in ref for ch in ("{", "}", "<", ">", "*", "$")):
                continue
            if (repo / ref).exists() or (base / ref).exists():
                continue
            findings.append({
                "type": "stale_reference",
                "symbol": ref,
                "location": path,
                "evidence": "ссылка на несуществующий файл",
            })
    return findings


def load_telemetry(path: Path | None) -> dict:
    if not path:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"warn: telemetry не найден: {path}", file=sys.stderr)
        return {}
    except json.JSONDecodeError as exc:
        print(f"warn: telemetry не разобран: {exc}", file=sys.stderr)
        return {}
    return data if isinstance(data, dict) else {}


def status_air(failure_rate: float, thrash: int | None) -> str:
    if thrash is not None and thrash >= 3:
        return "red"
    if failure_rate < 15:
        return "green"
    if failure_rate <= 30:
        return "amber"
    return "red"


def build(args: argparse.Namespace) -> dict:
    repo = args.repo.resolve()
    if not (repo / ".git").exists() and run_git(repo, "rev-parse", "--is-inside-work-tree").strip() != "true":
        raise SystemExit(f"error: не git-репозиторий: {repo}")

    warnings: list[str] = []
    rev_to = args.to or "HEAD"
    numstat = run_git(repo, "diff", "--numstat", f"{args.from_rev}..{rev_to}")
    files, w = parse_numstat(numstat)
    warnings.extend(w)
    changed_loc = sum(f["added"] + f["deleted"] for f in files)
    commits = [line for line in run_git(repo, "log", "--format=%H", f"{args.from_rev}..{rev_to}").splitlines() if line]
    branch = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()

    index = build_import_index(repo, args.max_files)
    reverse = build_reverse_graph(repo, index, args.max_files) if not args.no_blast_radius else {}

    entities = Counter()
    missing: list[dict] = []
    import_checks: list[dict] = []
    all_added_lines: dict[str, list[str]] = {}
    changed_sources: list[str] = []

    for item in files:
        path = item["path"]
        kind = item["kind"]
        if kind == "source":
            changed_sources.append(path)
        if kind not in {"source", "tests", "migrations"}:
            continue
        source = git_show(repo, rev_to, path)
        if source is None:
            warnings.append(f"не удалось прочитать {path}@{rev_to}")
            continue
        if path.endswith(".py") and kind != "tests":
            ranges = added_ranges(repo, args.from_rev, rev_to, path)
            found = python_entities(source, ranges)
            for key, value in found.items():
                entities[key] += value
            checks, miss = check_python_imports(index, path, source)
            import_checks.extend(checks)
            missing.extend(miss)
        elif path.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")) and kind != "tests":
            checks, miss = check_js_imports(repo, path, source)
            import_checks.extend(checks)
            missing.extend(miss)

        diff = ""
        try:
            diff = run_git(repo, "diff", "-U0", f"{args.from_rev}..{rev_to}", "--", path)
        except RuntimeError:
            pass
        all_added_lines[path] = [ln[1:] for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++")]

    for path, lines in all_added_lines.items():
        missing.extend(stale_references(repo, path, lines))

    # --- Cognitive Load ---
    modules = sum(1 for f in files if f["kind"] == "source")
    test_files = sum(1 for f in files if f["kind"] == "tests")
    doc_files = sum(1 for f in files if f["kind"] == "docs")
    migration_files = sum(1 for f in files if f["kind"] == "migrations")
    dep_files = sum(1 for f in files if f["kind"] == "deps")

    layers = set()
    for f in files:
        parts = f["path"].split("/")
        if parts[0] in {"src", "lib", "packages"} and len(parts) > 2:
            layers.add("/".join(parts[:2]))
        elif len(parts) > 1:
            layers.add(parts[0])

    weights = {
        "modules": modules * 1,
        "public_functions": entities["public_functions"] * 2,
        "classes": entities["classes"] * 2,
        "routes": entities["routes"] * 2,
        "models": entities["models"] * 3,
        "migrations": migration_files * 3,
        "dependencies": dep_files * 2,
        "layers": len(layers) * 3,
        "test_files": test_files * 0.5,
        "docs": doc_files * 0.5,
    }
    cli_raw = round(sum(weights.values()), 1)
    blast = blast_radius(changed_sources, reverse) if reverse else None
    cli_value = round(cli_raw + (0.2 * blast if blast is not None else 0), 1)

    # --- Hallucination Risk ---
    confirmed = missing
    weighted = sum({"phantom_api": 5, "wrong_signature": 3,
                    "missing_import": 2, "stale_reference": 1}.get(x["type"], 1) for x in confirmed)
    hr_value = round(1000 * weighted / max(changed_loc, 1), 2)
    hr_status = "red" if any(x["type"] == "phantom_api" for x in confirmed) or hr_value > 1 else ("amber" if confirmed else "green")

    internal_checks = [c for c in import_checks if c["kind"] == "internal"]
    ok_imports = sum(1 for c in internal_checks if c["status"] == "ok")
    bad_imports = sum(1 for c in internal_checks if c["status"] == "missing")
    ext_imports = sum(1 for c in import_checks if c["kind"] == "external")

    # --- Telemetry ---
    tel = load_telemetry(args.telemetry)
    tokens = tel.get("tokens") or {}
    total_tokens = None
    if tokens:
        total_tokens = sum(int(tokens.get(k) or 0) for k in ("input", "output", "cache_read", "cache_write"))
        if total_tokens == 0:
            total_tokens = None
    ftb_value = total_tokens
    ftb_quality = "measured" if total_tokens else "missing"
    ftb_status = "unknown"
    if total_tokens and args.budget_tokens:
        if total_tokens <= args.budget_tokens:
            ftb_status = "green"
        elif total_tokens <= args.budget_tokens * 1.5:
            ftb_status = "amber"
        else:
            ftb_status = "red"

    iterations = tel.get("iterations") or {}
    attempts = int(iterations.get("verification_attempts") or 0)
    failed = int(iterations.get("verification_failed") or 0)
    air_value = round(100 * failed / attempts, 1) if attempts else None
    air_status = status_air(air_value, iterations.get("max_repeat_failure")) if air_value is not None else "unknown"

    context = tel.get("context") or {}
    coverage = None
    if context.get("relevant_files"):
        coverage = round(100 * int(context.get("read_before_first_edit") or 0) / int(context["relevant_files"]), 1)
    window_util = None
    if context.get("window_tokens"):
        window_util = round(100 * int(context.get("peak_window_tokens") or 0) / int(context["window_tokens"]), 1)
    cwu_value = coverage
    cwu_status = "unknown" if coverage is None else ("green" if coverage >= 70 else "amber" if coverage >= 40 else "red")

    tel_hall = (tel.get("hallucinations") or {}).get("confirmed") or []
    for item in tel_hall:
        confirmed.append(item)
    if tel_hall:
        weighted = sum({"phantom_api": 5, "wrong_signature": 3,
                        "missing_import": 2, "stale_reference": 1}.get(x.get("type"), 1) for x in confirmed)
        hr_value = round(1000 * weighted / max(changed_loc, 1), 2)
        hr_status = "red" if any(x.get("type") == "phantom_api" for x in confirmed) or hr_value > 1 else "amber"

    agent = tel.get("agent") or {}
    title = args.title or repo.name
    subtitle = args.subtitle or run_git(repo, "log", "-1", "--format=%s", rev_to).strip()
    today = dt.date.today().isoformat()

    def per_100(value: float | None) -> str:
        return "—" if value is None else f"{round(100 * value / max(changed_loc, 1)):,}".replace(",", " ")

    data = {
        "schema_version": 1,
        "meta": {
            "title": title,
            "subtitle": subtitle,
            "scope": args.scope,
            "range": f"{args.from_rev}..{rev_to}",
            "date": today,
            "repo": repo.name,
            "branch": branch,
            "agent": agent.get("model") or agent.get("name") or "",
            "commits": len(commits),
            "changed_loc": changed_loc,
            "files": len(files),
            "quality": "derived",
            "notes": "Автоматический снимок. ADS и процессные метрики требуют ревью и телеметрии.",
        },
        "verdict": {
            "status": "unknown",
            "headline": "Автоматический снимок: архитектура и процесс ещё не оценены.",
            "text": "Заполните ADS по архитектурному контракту, подмешайте телеметрию и пересоберите отчёт.",
        },
        "metrics": {
            "ftb": {
                "value": ftb_value,
                "unit": "tokens",
                "quality": ftb_quality,
                "status": ftb_status,
                "summary": (
                    f"Бюджет {total_tokens:,} tokens по телеметрии.".replace(",", " ")
                    if total_tokens else
                    "Телеметрия токенов не передана. Укажите --telemetry с usage сессий."
                ),
                "drivers": [
                    f"{len(commits)} коммитов, {changed_loc} изменённых LOC.",
                ] + ([f"input {int(tokens.get('input') or 0):,}".replace(",", " "),
                      f"output {int(tokens.get('output') or 0):,}".replace(",", " ")] if total_tokens else []),
                "evidence": ([{"claim": "usage из телеметрии", "source": str(args.telemetry)}] if total_tokens else []),
                "verdict": "Стоимость не оценена без телеметрии." if not total_tokens else "Сравните с медианой последних фич.",
                "actions": [] if total_tokens else ["Экспортировать usage сессий в telemetry.json."],
                "parts": ([{"label": "input", "value": int(tokens.get("input") or 0)},
                           {"label": "output", "value": int(tokens.get("output") or 0)},
                           {"label": "cache read", "value": int(tokens.get("cache_read") or 0)},
                           {"label": "cache write", "value": int(tokens.get("cache_write") or 0)}] if total_tokens else []),
                "normalized": ([{"label": "tokens / 100 LOC", "value": per_100(total_tokens)},
                                {"label": "tokens / сущность", "value": str(round(total_tokens / max(cli_value, 1)))}] if total_tokens else []),
                "series": [],
            },
            "ads": {
                "value": None,
                "unit": "%",
                "quality": "missing",
                "status": "unknown",
                "summary": "ADS не вычисляется без архитектурного контракта. Проверьте решения вручную по docs/adr и границам слоёв.",
                "drivers": [
                    f"Изменено слоёв/пакетов: {len(layers)}.",
                    "Новые внешние зависимости: " + str(dep_files) + " файлов зависимостей.",
                ],
                "evidence": [],
                "verdict": "Без контракта число было бы выдумкой.",
                "actions": ["Зафиксировать контракт и подтвердить нарушения файлом и строкой."],
                "contract": {"name": "", "source": "", "assumed": True},
                "violations": [],
                "compliant": [],
            },
            "cli": {
                "value": cli_value,
                "unit": "балла",
                "quality": "derived",
                "status": "unknown",
                "summary": f"Затронуто {modules} модулей, {entities['public_functions']} публичных функций, {entities['classes']} классов; blast radius {blast if blast is not None else '—'}.",
                "drivers": [
                    f"Слоёв/пакетов: {len(layers)}.",
                    f"Миграций: {migration_files}; тестов: {test_files}; документов: {doc_files}.",
                ],
                "evidence": [{"claim": "diff и AST изменённых файлов", "source": f"git diff {args.from_rev}..{rev_to}"}],
                "verdict": "Нормируйте к медиане последних 5–10 фич, иначе число не интерпретируется.",
                "actions": ["Добавить baseline CLI для нормировки."],
                "entities": [
                    {"kind": "modules", "count": modules, "weight": 1, "total": weights["modules"]},
                    {"kind": "public functions", "count": entities["public_functions"], "weight": 2, "total": weights["public_functions"]},
                    {"kind": "classes", "count": entities["classes"], "weight": 2, "total": weights["classes"]},
                    {"kind": "routes", "count": entities["routes"], "weight": 2, "total": weights["routes"]},
                    {"kind": "models", "count": entities["models"], "weight": 3, "total": weights["models"]},
                    {"kind": "migrations", "count": migration_files, "weight": 3, "total": weights["migrations"]},
                    {"kind": "dependencies", "count": dep_files, "weight": 2, "total": weights["dependencies"]},
                    {"kind": "layers", "count": len(layers), "weight": 3, "total": weights["layers"]},
                    {"kind": "test files", "count": test_files, "weight": 0.5, "total": weights["test_files"]},
                    {"kind": "docs", "count": doc_files, "weight": 0.5, "total": weights["docs"]},
                ],
                "blast_radius": blast,
                "top_modules": [],
            },
            "air": {
                "value": air_value,
                "unit": "%",
                "quality": "measured" if air_value is not None else "missing",
                "status": air_status,
                "summary": (
                    f"{failed} неудачных из {attempts} проверок; циклов {iterations.get('cycles', '—')}."
                    if air_value is not None else "Логи проверок не переданы. Нужны tool-call лог или история CI."
                ),
                "drivers": ([f"max повторов одной ошибки: {iterations.get('max_repeat_failure', '—')}",
                             f"ручных вмешательств: {iterations.get('manual_interventions', '—')}"] if air_value is not None else []),
                "evidence": ([{"claim": "журнал проверок", "source": str(args.telemetry)}] if air_value is not None else []),
                "verdict": ("Есть зацикливание." if (iterations.get("max_repeat_failure") or 0) >= 3 else "Оценка по среднему; проверьте thrash."),
                "actions": [],
                "attempts": attempts or None,
                "failed": failed or None,
                "cycles": iterations.get("cycles"),
                "loops": iterations.get("loops"),
                "thrash": iterations.get("max_repeat_failure"),
                "interventions": iterations.get("manual_interventions"),
                "series": iterations.get("history") or [],
            },
            "hr": {
                "value": hr_value,
                "unit": "на 1000 LOC",
                "quality": "derived",
                "status": hr_status,
                "summary": f"Подтверждено {len(confirmed)} случаев; проверено {ok_imports + bad_imports} внутренних импортов, {ext_imports} внешних — не проверялись.",
                "drivers": [
                    f"Неразрешённых внутренних импортов: {bad_imports}.",
                    f"Ссылок на несуществующие файлы: {sum(1 for x in confirmed if x['type'] == 'stale_reference')}.",
                ],
                "evidence": [{"claim": "резолвинг импортов по индексу репозитория", "source": "collect_metrics.py"}],
                "verdict": "Внешние импорты помечены unverified: проверьте их в venv проекта.",
                "actions": [] if not confirmed else ["Исправить подтверждённые случаи и пересобрать отчёт."],
                "confirmed": confirmed[:50],
                "unconfirmed": [],
                "checks": [
                    {"name": "internal imports", "result": f"{ok_imports} / {ok_imports + bad_imports}", "note": "резолвинг по индексу репозитория"},
                    {"name": "external imports", "result": f"{ext_imports} unverified", "note": "требуют проверки в окружении проекта"},
                    {"name": "file references", "result": f"{sum(1 for x in confirmed if x['type'] == 'stale_reference')} missing", "note": "пути из добавленных строк"},
                ],
            },
            "cwu": {
                "value": cwu_value,
                "unit": "%",
                "quality": "measured" if cwu_value is not None else "missing",
                "status": cwu_status,
                "summary": (
                    f"Прочитано {context.get('read_before_first_edit')} из {context.get('relevant_files')} релевантных файлов до первой правки; окно заполнено на {window_util} %."
                    if cwu_value is not None else "Лог чтения файлов не передан; coverage восстановить нельзя."
                ),
                "drivers": ([f"Пик окна: {context.get('peak_window_tokens')} из {context.get('window_tokens')} tokens."] if cwu_value is not None else []),
                "evidence": ([{"claim": "лог чтения сессии", "source": str(args.telemetry)}] if cwu_value is not None else []),
                "verdict": "Низкое покрытие означает действие вслепую, а не экономию." if (cwu_value is not None and cwu_value < 40) else "Сопоставьте с ADS в матрице.",
                "actions": [],
                "coverage": coverage,
                "window": window_util,
                "relevant": context.get("relevant_files"),
                "read": context.get("read_before_first_edit"),
                "read_list": context.get("read_list") or [],
                "missed_list": context.get("missed_list") or [],
            },
        },
        "matrix": {},
        "evidence": [
            {"claim": f"{len(commits)} коммитов, {changed_loc} LOC, {len(files)} файлов", "source": f"git diff --numstat {args.from_rev}..{rev_to}", "date": today},
            {"claim": "Cognitive Load и Hallucination Risk", "source": "collect_metrics.py (AST + git)", "date": today},
        ],
        "actions": [
            {"priority": "now", "text": "Подтвердить ADS по архитектурному контракту.", "owner": "ревьюер"},
        ],
        "method": {
            "commands": [f"python collect_metrics.py --repo {repo.name} --from {args.from_rev} --to {rev_to}"],
            "notes": [
                "CLI — сырой балл; для интерпретации нужна медиана последних 5–10 фич.",
                "HR проверяет только внутренние импорты и пути; внешние помечены unverified.",
                "Импорты и ссылки проверяются в рабочем дереве, а не в дереве ревизии --to.",
            ],
            "limitations": warnings[:20],
        },
    }
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Собрать метрики изменения в metrics.json")
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--from", dest="from_rev", required=True, help="начальная ревизия")
    parser.add_argument("--to", dest="to", default="HEAD", help="конечная ревизия (по умолчанию HEAD)")
    parser.add_argument("--out", type=Path, default=Path("metrics.json"))
    parser.add_argument("--telemetry", type=Path, help="JSON с usage/итерациями/контекстом")
    parser.add_argument("--title")
    parser.add_argument("--subtitle")
    parser.add_argument("--scope", choices=("feature", "milestone", "session"), default="feature")
    parser.add_argument("--budget-tokens", type=int, help="бюджет фичи в токенах")
    parser.add_argument("--max-files", type=int, default=8000, help="лимит файлов для индекса импортов")
    parser.add_argument("--no-blast-radius", action="store_true", help="не строить граф импортёров")
    args = parser.parse_args(argv)

    try:
        data = build(args)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ok: {args.out}")
    print(f"  cli={data['metrics']['cli']['value']} "
          f"hr={data['metrics']['hr']['value']} "
          f"ftb={'нет' if data['metrics']['ftb']['value'] is None else data['metrics']['ftb']['value']}")
    lim = data["method"]["limitations"]
    for line in lim[:10]:
        print(f"warn: {line}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())