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
from collections import Counter
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
    tracks = criteria.get("tracks") or []
    if not tracks:
        warnings.append("criteria.tracks пуст: нет track-specific требований к аналогам и валидации")
    for index, track in enumerate(tracks, start=1):
        label = f"criteria.tracks[{index}]"
        if not isinstance(track, dict):
            errors.append(f"{label}: должен быть объектом")
            continue
        direction_id = str(track.get("directionId") or "")
        if direction_id and direction_id not in directions:
            warnings.append(f"{label}: направление {direction_id} отсутствует в profile")
        if not str(track.get("track") or "").strip():
            errors.append(f"{label}: track пуст")
        baselines = track.get("baselines") or []
        validation = track.get("validation") or []
        new_datasets = track.get("newDatasets") or track.get("new_datasets") or []
        if not baselines:
            (errors if args.strict else warnings).append(f"{label}: нет обязательных аналогов")
        if not validation:
            (errors if args.strict else warnings).append(f"{label}: нет протокола валидации")
        if not new_datasets:
            warnings.append(f"{label}: нет новых датасетов; укажите, на чём расширять валидацию")
    a_star_counts = Counter()
    selected_a_star = selection.get("a_star")
    if not selected_a_star:
        selected_a_star = [
            item.get("doi") for item in papers if item.get("category") == "a_star" and item.get("doi")
        ]
    for doi in selected_a_star:
        item = paper_by_doi.get(str(doi).lower())
        if item:
            for direction_id in set(item.get("direction_ids") or []):
                a_star_counts[direction_id] += 1
    coverage = analysis.get("aStarCoverage") or analysis.get("aStarGaps") or []
    if not coverage:
        (errors if args.strict else warnings).append(
            "analysis.aStarCoverage пуст: не показано покрытие A* и ближайшие площадки"
        )
    covered_directions = set()
    for index, entry in enumerate(coverage, start=1):
        label = f"aStarCoverage[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: должен быть объектом")
            continue
        direction_id = str(entry.get("directionId") or "")
        if not direction_id:
            errors.append(f"{label}: directionId пуст")
            continue
        if direction_id not in directions:
            warnings.append(f"{label}: направление {direction_id} отсутствует в profile")
        covered_directions.add(direction_id)
        expected = a_star_counts.get(direction_id, 0)
        declared = entry.get("found")
        if declared is not None and int(declared) != expected:
            (errors if args.strict else warnings).append(
                f"{label}: found={declared}, а в selection.a_star {expected} работ по {direction_id}"
            )
        nearest = entry.get("nearest") or []
        if expected == 0:
            if not nearest:
                (errors if args.strict else warnings).append(
                    f"{label}: A* не найден, но nearest пуст — укажите ближайшие A*-площадки"
                )
            for venue_index, venue in enumerate(nearest, start=1):
                if not isinstance(venue, dict):
                    errors.append(f"{label}.nearest[{venue_index}]: должен быть объектом")
                    continue
                if not str(venue.get("venue") or "").strip():
                    errors.append(f"{label}.nearest[{venue_index}]: venue пуст")
                if not str(venue.get("note") or "").strip():
                    warnings.append(
                        f"{label}.nearest[{venue_index}]: нет пояснения, почему площадка ближайшая"
                    )
        else:
            if not entry.get("venues"):
                warnings.append(f"{label}: A* найден, но venues пуст")
    missing_coverage = sorted(directions - covered_directions)
    if missing_coverage:
        (errors if args.strict else warnings).append(
            "aStarCoverage не покрывает направления: " + ", ".join(missing_coverage)
        )
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