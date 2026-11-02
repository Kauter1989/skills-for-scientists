#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверить автономность и обязательные блоки HTML-отчёта Pachca.

Использование:
    python scripts/check_report.py examples/example-report.html
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_IDS = ("projects", "activity", "tasks", "method", "report-data")

FORBIDDEN = (
    (re.compile(r"<script\b[^>]*\bsrc\s*=", re.I), "внешний script src"),
    (re.compile(r"<link\b[^>]*\brel\s*=\s*['\"]?stylesheet", re.I), "внешний stylesheet"),
    (re.compile(r"@import\b", re.I), "@import"),
    (re.compile(r"url\(\s*['\"]?https?:", re.I), "CSS url(http...)"),
    (re.compile(r"\bfetch\s*\(", re.I), "fetch()"),
    (re.compile(r"\bXMLHttpRequest\b", re.I), "XMLHttpRequest"),
    (re.compile(r"\bnew\s+WebSocket\b", re.I), "WebSocket"),
    (re.compile(r"<img\b[^>]*\bsrc\s*=\s*['\"]https?:", re.I), "внешняя картинка"),
    (re.compile(r"\bsrcset\s*=\s*['\"]https?:", re.I), "внешний srcset"),
    (re.compile(r"href\s*=\s*['\"]javascript:", re.I), "javascript: ссылка"),
)


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверить автономный HTML-отчёт Pachca.")
    parser.add_argument("html", type=Path)
    args = parser.parse_args(argv)

    if not args.html.is_file():
        fail(f"файл не найден: {args.html}")
        return 2

    text = args.html.read_text(encoding="utf-8")
    errors: list[str] = []

    if "<!DOCTYPE HTML>" not in text[:200].upper():
        errors.append("нет <!DOCTYPE html>")
    if 'charset="utf-8"' not in text.lower():
        errors.append("нет meta charset=utf-8")

    for element_id in REQUIRED_IDS:
        if f'id="{element_id}"' not in text:
            errors.append(f"нет обязательного блока #{element_id}")

    for pattern, label in FORBIDDEN:
        if pattern.search(text):
            errors.append(f"запрещённый ресурс: {label}")

    hrefs = re.findall(r"href\s*=\s*['\"]([^'\"]+)['\"]", text, re.I)
    for href in hrefs:
        if href.startswith("#"):
            continue
        if href.startswith("https://app.pachca.com/"):
            continue
        if href.lower().startswith(("mailto:", "tel:")):
            continue
        errors.append(f"внешняя ссылка вне app.pachca.com: {href[:120]}")

    match = re.search(
        r'<script\b[^>]*id="report-data"[^>]*>(.*?)</script>',
        text,
        re.I | re.S,
    )
    if not match:
        errors.append("не найден JSON #report-data")
    else:
        try:
            payload = json.loads(match.group(1))
            if not isinstance(payload, dict):
                errors.append("#report-data должен быть объектом")
            elif payload.get("schemaVersion") != 1:
                errors.append("#report-data.schemaVersion должен быть 1")
        except json.JSONDecodeError as exc:
            errors.append(f"#report-data не JSON: {exc}")

    if 'data-by-chat=' not in text:
        errors.append("нет data-by-chat у участников: фильтр по чату не работает")
    if 'class="person' not in text:
        errors.append("нет строк участников")

    if errors:
        for error in errors:
            fail(error)
        return 1

    size_kb = args.html.stat().st_size / 1024
    print(f"ok: {args.html} ({size_kb:.1f} KiB)")
    print(f"blocks: {', '.join('#' + item for item in REQUIRED_IDS)}")
    print("external requests: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())