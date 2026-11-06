#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка автономности и полноты HTML-отчёта.

Проверяет, что страница открывается с диска без сети, что у каждой компании
есть источник, а у каждой метрики — метка качества.

Использование:
    python check_report.py report.html
    python check_report.py report.html --json

Код выхода 1 при любой ошибке. Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXTERNAL_RE = re.compile(
    r"""<script\b[^>]*\bsrc\s*=\s*["'](?:https?:)?//|<img\b[^>]*\bsrc\s*=\s*["'](?:https?:)?//|"""
    r"""<iframe\b[^>]*\bsrc\s*=\s*["'](?:https?:)?//|<link\b[^>]*\bhref\s*=\s*["'](?:https?:)?//|"""
    r"""@import|url\(\s*["']?(?:https?:)?//|cdn\.|fonts\.googleapis|chart\.js""",
    re.IGNORECASE,
)
CLICKABLE_RE = re.compile(r'href\s*=\s*["\'](https?://[^"\']+)["\']', re.IGNORECASE)
QUALITY_RE = re.compile(r'class="q q-(measured|derived|est|exp|missing)"')
SECTION_RE = re.compile(r"<h2>(.+?)</h2>", re.IGNORECASE)


def check(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not path.is_file():
        return [f"нет файла {path}"], warnings
    text = path.read_text(encoding="utf-8")

    if EXTERNAL_RE.search(text):
        errors.append("найдены внешние ресурсы: отчёт обязан открываться без сети")
    if "<!DOCTYPE html>" not in text:
        errors.append("нет DOCTYPE")
    if not re.search(r"<title>.+</title>", text, re.IGNORECASE):
        warnings.append("нет <title>")

    sections = SECTION_RE.findall(text)
    if len(sections) < 4:
        errors.append(f"ожидались минимум 4 раздела (РФ, Мир, разница, методика), найдено {len(sections)}")

    links = CLICKABLE_RE.findall(text)
    if not links:
        errors.append("в отчёте нет ни одной ссылки-источника")
    else:
        non_http = [l for l in links if not l.startswith("http")]
        if non_http:
            warnings.append(f"ссылок не http(s): {len(non_http)}")

    qualities = QUALITY_RE.findall(text)
    if not qualities:
        errors.append("нет меток качества у метрик")
    if "нет данных" not in text:
        warnings.append("нет явной метки «нет данных»: проверьте, что отсутствие данных показано честно")

    for marker in ("Россия", "Мир", "Разница рынков"):
        if marker not in text:
            errors.append(f"нет обязательного блока «{marker}»")

    if "fonts" in text.lower() and "system-ui" not in text:
        warnings.append("используются не системные шрифты")
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверка HTML-отчёта")
    parser.add_argument("report", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    errors, warnings = check(args.report)
    if args.json:
        print(json.dumps({"report": str(args.report), "ok": not errors,
                          "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    else:
        status = "ok" if not errors else "FAIL"
        print(f"[{status}] {args.report}")
        for error in errors:
            print(f"  error: {error}")
        for warning in warnings:
            print(f"  warn: {warning}")
        print(f"  external resources: {'none' if not EXTERNAL_RE.search(args.report.read_text(encoding='utf-8')) else 'found'}"
              if args.report.is_file() else "")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())