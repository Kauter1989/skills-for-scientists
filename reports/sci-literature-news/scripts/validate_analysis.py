#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate analysis.json against candidates.json.

Usage:
    python validate_analysis.py candidates.json analysis.json
    python validate_analysis.py candidates.json analysis.json --strict
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STATUS = {"q1", "a_star", "q2", "unranked"}


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"error: файл не найден: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: некорректный JSON в {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"error: корень {path} должен быть объектом")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверить analysis.json для literature-news.")
    parser.add_argument("candidates", type=Path)
    parser.add_argument("analysis", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    candidates = load(args.candidates)
    analysis = load(args.analysis)
    papers = candidates.get("papers") or []
    paper_by_doi = {str(item.get("doi", "")).lower(): item for item in papers if item.get("doi")}
    datasets = candidates.get("datasets") or []
    dataset_by_doi = {str(item.get("doi", "")).lower(): item for item in datasets if item.get("doi")}
    directions = {str(item.get("id")) for item in candidates.get("profile", {}).get("directions") or []}
    errors = []
    warnings = []
    if not analysis.get("summary"):
        warnings.append("analysis.summary пуст")
    if not analysis.get("themes"):
        errors.append("analysis.themes пуст")
    for index, theme in enumerate(analysis.get("themes") or [], start=1):
        label = f"themes[{index}]"
        if not isinstance(theme, dict):
            errors.append(f"{label}: должен быть объектом")
            continue
        if not str(theme.get("title") or "").strip():
            errors.append(f"{label}: title пуст")
        if not str(theme.get("summary") or "").strip():
            errors.append(f"{label}: summary пуст")
        evidence = theme.get("evidence") or []
        if not evidence:
            (errors if args.strict else warnings).append(f"{label}: нет DOI-доказательств")
        for doi in evidence:
            key = str(doi).lower()
            if key not in paper_by_doi:
                errors.append(f"{label}: DOI {doi} отсутствует в candidates.papers")
        for direction in theme.get("directionIds") or []:
            if str(direction) not in directions:
                warnings.append(f"{label}: направление {direction} отсутствует в profile")
    for index, dataset in enumerate(analysis.get("datasets") or [], start=1):
        label = f"datasets[{index}]"
        if not isinstance(dataset, dict):
            errors.append(f"{label}: должен быть объектом")
            continue
        doi = str(dataset.get("doi") or "").lower()
        if doi and doi not in dataset_by_doi:
            (errors if args.strict else warnings).append(f"{label}: DOI {dataset['doi']} отсутствует в candidates.datasets")
        if not doi and not dataset.get("url"):
            errors.append(f"{label}: нет DOI или URL")
    selection = analysis.get("selection") or {}
    for category in ("q1", "a_star", "q2"):
        for doi in selection.get(category) or []:
            item = paper_by_doi.get(str(doi).lower())
            if not item:
                errors.append(f"selection.{category}: DOI {doi} отсутствует в candidates.papers")
            elif item.get("category") != category:
                warnings.append(f"selection.{category}: {doi} в candidates имеет категорию {item.get('category')}")
    criteria = analysis.get("criteria") or {}
    for key in ("a_star", "q1", "q2", "study"):
        if not criteria.get(key):
            warnings.append(f"criteria.{key} пуст")
    if candidates.get("warnings"):
        warnings.extend(candidates["warnings"])
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(
        f"ok: {len(papers)} papers, {len(analysis.get('themes') or [])} themes, "
        f"{len(analysis.get('datasets') or [])} datasets, {len(warnings)} warnings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())