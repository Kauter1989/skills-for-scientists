#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Собрать автономную HTML-страницу отчёта об изменениях.

Использование:
    python build_report.py metrics.json -o report.html [--strict] [--open]
    python build_report.py --example -o example-report.html

Шаблон — templates/report.html; данные вставляются в
<script type="application/json" id="report-data">.
Стандартная библиотека, без зависимостей.
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = SKILL_DIR / "templates" / "report.html"
EXAMPLE_DATA = SKILL_DIR / "examples" / "metrics-example.json"
PLACEHOLDER = "__REPORT_DATA__"
SECTIONS = ("ftb", "ads", "cli", "air", "hr", "cwu")
STATUSES = {"green", "amber", "red", "unknown"}
QUALITIES = {"measured", "derived", "estimated", "expert", "missing"}


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        fail(f"файл не найден: {path}")
    except json.JSONDecodeError as exc:
        fail(f"некорректный JSON в {path}: {exc}")
    if not isinstance(data, dict):
        fail("корень JSON должен быть объектом")
    return data


def validate(data: dict, strict: bool) -> list[str]:
    """Вернуть список предупреждений; при strict — падать на ошибках."""
    warnings: list[str] = []
    errors: list[str] = []

    meta = data.get("meta")
    if not isinstance(meta, dict):
        errors.append("нет объекта meta")
    else:
        for key in ("title", "date", "range"):
            if not meta.get(key):
                warnings.append(f"meta.{key} не заполнен")

    metrics = data.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("нет объекта metrics")
        metrics = {}

    for key in SECTIONS:
        m = metrics.get(key)
        if not isinstance(m, dict):
            errors.append(f"нет секции metrics.{key}")
            continue
        value = m.get("value")
        if value is not None and not isinstance(value, (int, float)):
            errors.append(f"metrics.{key}.value должен быть числом или null")
        quality = m.get("quality")
        if quality not in QUALITIES:
            errors.append(f"metrics.{key}.quality = {quality!r}, допустимо: {sorted(QUALITIES)}")
        status = m.get("status")
        if status not in STATUSES:
            errors.append(f"metrics.{key}.status = {status!r}, допустимо: {sorted(STATUSES)}")
        if quality == "estimated":
            blob = json.dumps(m, ensure_ascii=False)
            if "~" not in blob and not (data.get("method") or {}).get("limitations"):
                errors.append(
                    f"metrics.{key}: estimated без '~' и без method.limitations"
                )
        if value is None and quality != "missing":
            warnings.append(f"metrics.{key}: value=null, но quality={quality}")

    for key in ("evidence", "actions", "method"):
        if not data.get(key):
            warnings.append(f"раздел {key} пуст")

    if strict and errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)

    for error in errors:
        warnings.append(error)
    return warnings


def render(template: str, data: dict) -> str:
    if PLACEHOLDER not in template:
        fail(f"в шаблоне нет плейсхолдера {PLACEHOLDER}")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # Данные внутри <script>: не даём закрыть тег и не ломаем HTML-парсер.
    payload = payload.replace("</", "<\\/").replace("<!--", "\\u003c!--")
    return template.replace(PLACEHOLDER, payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Собрать HTML-отчёт об изменениях фичи или майлстоуна."
    )
    parser.add_argument("metrics", nargs="?", type=Path, help="JSON с данными отчёта")
    parser.add_argument("-o", "--out", type=Path, default=Path("change-report.html"))
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--example", action="store_true", help="взять examples/metrics-example.json")
    parser.add_argument("--strict", action="store_true", help="падать на ошибках схемы")
    parser.add_argument("--open", action="store_true", help="открыть результат в браузере")
    args = parser.parse_args(argv)

    source = EXAMPLE_DATA if args.example else args.metrics
    if source is None:
        parser.error("укажите metrics.json или --example")
    if not source.exists():
        fail(f"файл данных не найден: {source}")
    if not args.template.exists():
        fail(f"шаблон не найден: {args.template}")

    data = load_json(source)
    warnings = validate(data, args.strict)

    template = args.template.read_text(encoding="utf-8")
    html = render(template, data)

    if PLACEHOLDER in html:
        fail("плейсхолдер остался в результате")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")

    size_kb = args.out.stat().st_size / 1024
    print(f"ok: {args.out} ({size_kb:.1f} KB, schema v{data.get('schema_version', 1)})")
    for warning in warnings:
        print(f"warn: {warning}", file=sys.stderr)

    if args.open:
        webbrowser.open(args.out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())