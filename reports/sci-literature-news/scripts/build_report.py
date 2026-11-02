#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a standalone HTML literature-news report.

Usage:
    python build_report.py --candidates candidates.json --analysis analysis.json -o report.html --strict
    python build_report.py --example -o examples/example-report.html
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = SKILL_DIR / "templates" / "report.html"
EXAMPLE_DIR = SKILL_DIR / "examples"
CATEGORY_LABELS = {
    "q1": "Журналы Q1",
    "a_star": "Конференции A*",
    "q2": "Журналы Q2",
    "unranked": "Без подтверждённого ранга",
}
STOPWORDS = {
    "and",
    "for",
    "the",
    "with",
    "from",
    "into",
    "using",
    "based",
    "via",
    "over",
    "under",
    "among",
    "through",
    "toward",
    "towards",
}
QUALITY = {
    "measured": "measured",
    "derived": "derived",
    "expert": "expert",
    "missing": "missing",
}


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def safe_doi(value: object) -> str:
    doi = str(value or "").strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.I)
    if re.fullmatch(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", doi):
        return f"https://doi.org/{doi}"
    return ""


def safe_url(value: object) -> str:
    url = str(value or "").strip()
    return url if re.match(r"^https://", url) else ""


def truncate(value: object, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def bar_row(
    label: str,
    value: float,
    maximum: float,
    *,
    color: str = "",
    value_label: str | None = None,
    note: str = "",
) -> str:
    width = 0.0 if not maximum else max(0.0, min(100.0, value / maximum * 100))
    display = value_label if value_label is not None else f"{value:g}"
    color_class = f" {color}" if color else ""
    note_html = f"<small>{esc(note)}</small>" if note else ""
    return (
        '<div class="bar-row">'
        f'<div class="bar-label">{esc(label)}{note_html}</div>'
        f'<div class="bar-track"><span class="bar-fill{color_class}" style="width:{width:.1f}%"></span></div>'
        f'<div class="bar-val">{esc(display)}</div>'
        "</div>"
    )


def stacked_row(
    label: str,
    segments: list[tuple[float, str]],
    maximum: float,
    value_label: str,
    *,
    note: str = "",
) -> str:
    total = sum(value for value, _ in segments)
    width = 0.0 if not maximum else max(0.0, min(100.0, total / maximum * 100))
    parts = []
    for value, color in segments:
        if value <= 0 or not maximum:
            continue
        parts.append(f'<span class="bar-seg {color}" style="width:{value / maximum * 100:.1f}%"></span>')
    note_html = f"<small>{esc(note)}</small>" if note else ""
    return (
        '<div class="bar-row">'
        f'<div class="bar-label">{esc(label)}{note_html}</div>'
        f'<div class="bar-track"><span class="bar-stack" style="width:{width:.1f}%">{"".join(parts)}</span></div>'
        f'<div class="bar-val">{esc(value_label)}</div>'
        "</div>"
    )


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"error: файл не найден: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: некорректный JSON в {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"error: корень JSON должен быть объектом: {path}")
    return data


def default_criteria() -> dict:
    return {
        "a_star": [
            "Конференция имеет действующий ранг A* в ICORE/CORE для указанного года.",
            "Работа — полноценная рецензируемая публикация, а не тезис, постер или препринт.",
            "Дата публикации входит в выбранный период.",
            "Тема и площадка совпадают с направлением; название/акроним площадки подтверждены кэшем ICORE.",
        ],
        "q1": [
            "Журнал входит в Q1 по SJR в релевантной предметной категории и году.",
            "Работа — article/review, прошла рецензирование, имеет DOI и полные метаданные.",
            "Дата публикации входит в выбранный период.",
            "Квартиль относится к журналу, а не к конкретной статье; в отчёте указаны категория и год.",
        ],
        "q2": [
            "Журнал входит в Q2 по SJR в релевантной предметной категории и году.",
            "Работа — article/review, прошла рецензирование, имеет DOI и полные метаданные.",
            "Дата публикации входит в выбранный период.",
            "Q2 — не «слабее» автоматически; это другой квартиль и другой профиль риска.",
        ],
        "study": [
            "Peer-reviewed venue, не препринт и не редакционная заметка.",
            "DOI разрешается и совпадает с метаданными OpenAlex/Crossref.",
            "Тема релевантна одному из сохранённых направлений.",
            "Нет признаков retraction (если поле доступно).",
            "Аннотация и метаданные достаточны для синтеза; full text не читался.",
            "Наличие кода/датасета — плюс, но не обязательное условие.",
        ],
        "caveats": [
            "Ранг площадки — фильтр, а не доказательство качества статьи.",
            "Один журнал может быть Q1 в одной категории и Q2 в другой; категория и год указаны.",
            "OpenAlex и DataCite могут пропускать записи и обновляться с задержкой.",
            "Синтез основан на аннотациях и метаданных, если не указано иное.",
        ],
    }


def normalize_analysis(analysis: dict | None, candidates: dict) -> dict:
    analysis = analysis or {}
    directions = candidates.get("profile", {}).get("directions") or []
    direction_names = {item["id"]: item["direction"] for item in directions}
    papers = candidates.get("papers") or []
    paper_by_doi = {str(p.get("doi", "")).lower(): p for p in papers if p.get("doi")}
    dataset_by_doi = {
        str(d.get("doi", "")).lower(): d for d in candidates.get("datasets") or [] if d.get("doi")
    }

    selection = analysis.get("selection") or {}
    selected_by_category = {}
    for category in ("q1", "a_star", "q2"):
        chosen = selection.get(category)
        if isinstance(chosen, list) and chosen:
            wanted = {str(item).lower() for item in chosen}
            selected_by_category[category] = [
                p for p in papers if p.get("category") == category and str(p.get("doi", "")).lower() in wanted
            ]
        else:
            selected_by_category[category] = [p for p in papers if p.get("category") == category]

    datasets = []
    analysis_datasets = analysis.get("datasets")
    if isinstance(analysis_datasets, list) and analysis_datasets:
        for item in analysis_datasets:
            if not isinstance(item, dict):
                continue
            doi = str(item.get("doi") or "").lower()
            base = dataset_by_doi.get(doi, {})
            datasets.append({**base, **item, "doi": base.get("doi") or item.get("doi", "")})
    else:
        datasets = list(candidates.get("datasets") or [])

    themes = []
    for theme in analysis.get("themes") or []:
        if not isinstance(theme, dict):
            continue
        evidence = []
        for value in theme.get("evidence") or []:
            doi = str(value).lower()
            paper = paper_by_doi.get(doi)
            if paper:
                evidence.append(paper)
        themes.append(
            {
                "title": theme.get("title") or "Без названия",
                "summary": theme.get("summary") or "",
                "directionIds": theme.get("directionIds") or [],
                "confidence": theme.get("confidence") or "medium",
                "evidence": evidence,
                "quality": "expert" if evidence else "missing",
            }
        )

    criteria = default_criteria()
    for key, values in (analysis.get("criteria") or {}).items():
        if isinstance(values, list) and values:
            criteria[key] = values

    warnings = list(candidates.get("warnings") or [])
    warnings += [item for item in analysis.get("warnings") or [] if item not in warnings]
    if not analysis.get("summary"):
        warnings.append("analysis.summary не заполнен: отчёт показывает только метаданные")
    if not themes:
        warnings.append("analysis.themes пуст: синтез направлений отсутствует")
    if not datasets:
        warnings.append("Новые датасеты не найдены или не добавлены в analysis.datasets")

    a_star_by_direction = Counter()
    for paper in selected_by_category["a_star"]:
        for direction_id in set(paper.get("direction_ids") or []):
            a_star_by_direction[direction_id] += 1
    coverage_entries = {}
    for item in analysis.get("aStarCoverage") or analysis.get("aStarGaps") or []:
        if isinstance(item, dict) and item.get("directionId"):
            coverage_entries[str(item["directionId"])] = item
    a_star_coverage = []
    for direction in directions:
        direction_id = str(direction.get("id"))
        entry = coverage_entries.get(direction_id, {})
        found = a_star_by_direction.get(direction_id, 0)
        nearest = [item for item in entry.get("nearest") or [] if isinstance(item, dict)]
        a_star_coverage.append(
            {
                "directionId": direction_id,
                "direction": direction.get("direction") or direction_id,
                "found": found,
                "status": "found" if found else "missing",
                "venues": entry.get("venues") or [],
                "target": entry.get("target") or "",
                "note": entry.get("note") or "",
                "nearest": nearest,
            }
        )
        if not found and not nearest:
            warnings.append(
                f"{direction_id}: A*-публикаций нет и не указаны ближайшие площадки (analysis.aStarCoverage)"
            )

    return {
        "title": analysis.get("title") or "Научный дайджест литературы",
        "summary": analysis.get("summary") or "",
        "themes": themes,
        "selected": selected_by_category,
        "datasets": datasets,
        "criteria": criteria,
        "aStarCoverage": a_star_coverage,
        "warnings": warnings,
        "direction_names": direction_names,
        "generatedAt": analysis.get("generatedAt") or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "ranking_notes": analysis.get("ranking_notes") or [],
    }


def paper_table(papers: list[dict], category: str, direction_names: dict) -> str:
    if not papers:
        return '<p class="empty">Нет работ, подтверждённых для этой категории.</p>'
    rows = []
    for paper in sorted(papers, key=lambda item: item.get("date") or "", reverse=True):
        doi_url = safe_doi(paper.get("doi"))
        title = esc(paper.get("title"))
        if doi_url:
            title = f'<a href="{esc(doi_url)}" rel="noreferrer">{title}</a>'
        authors = ", ".join(paper.get("authors") or []) or "—"
        if len(paper.get("authors") or []) >= 8:
            authors += " и др."
        directions = "; ".join(direction_names.get(item, item) for item in paper.get("direction_ids") or [])
        ranking = paper.get("ranking_evidence") or []
        ranking_text = "; ".join(ranking) if ranking else "нет подтверждённого ранга"
        abstract = paper.get("abstract") or ""
        details = (
            f'<details><summary>Аннотация</summary><p>{esc(truncate(abstract, 1800)) or "Аннотация не получена."}</p></details>'
            if abstract
            else ""
        )
        rows.append(
            f'<tr data-paper="1" data-category="{esc(category)}" '
            f'data-directions="{esc(" ".join(paper.get("direction_ids") or []))}" '
            f'data-date="{esc(paper.get("date"))}" data-citations="{int(paper.get("citations") or 0)}" '
            f'data-search="{esc(norm_search(paper))}">'
            f'<td><div class="paper-title">{title}</div><div class="venue">{esc(paper.get("venue") or "—")}</div>{details}</td>'
            f'<td>{esc(paper.get("date") or "—")}</td>'
            f'<td>{esc(authors)}</td>'
            f'<td class="num">{int(paper.get("citations") or 0)}</td>'
            f'<td><span class="rank">{esc(ranking_text)}</span><span class="directions">{esc(directions)}</span></td>'
            f'<td>{f"<a href=\"{esc(doi_url)}\" rel=\"noreferrer\">{esc(paper.get('doi'))}</a>" if doi_url else "—"}</td>'
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table class="papers">'
        "<thead><tr><th>Работа</th><th>Дата</th><th>Авторы</th><th>Цит.</th><th>Ранг / направление</th><th>DOI</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def norm_search(paper: dict) -> str:
    parts = [
        paper.get("title") or "",
        paper.get("venue") or "",
        paper.get("abstract") or "",
        " ".join(paper.get("authors") or []),
        " ".join(paper.get("ranking_evidence") or []),
    ]
    return re.sub(r"\s+", " ", " ".join(parts)).lower()


def render_body(model: dict, candidates: dict) -> str:
    directions = candidates.get("profile", {}).get("directions") or []
    direction_names = model["direction_names"]
    papers = [p for cat in ("q1", "a_star", "q2") for p in model["selected"][cat]]
    counts = {
        "papers": len(papers),
        "q1": len(model["selected"]["q1"]),
        "a_star": len(model["selected"]["a_star"]),
        "q2": len(model["selected"]["q2"]),
        "datasets": len(model["datasets"]),
        "directions": len(directions),
    }
    profile = candidates.get("profile", {}).get("profile", {})
    period = candidates.get("period", {})
    kpis = [
        ("Работ", counts["papers"], "после фильтрации"),
        ("Q1", counts["q1"], "журналы"),
        ("A*", counts["a_star"], "конференции"),
        ("Q2", counts["q2"], "журналы"),
        ("Датасетов", counts["datasets"], "DataCite"),
        ("Направлений", counts["directions"], "из profile.md"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><span>{esc(label)}</span><b>{esc(value)}</b><small>{esc(note)}</small></div>'
        for label, value, note in kpis
    )
    direction_chips = "".join(
        f'<span class="chip"><b>{esc(item["id"])}</b> · {esc(item["direction"])}</span>' for item in directions
    )
    summary = f'<p class="summary">{esc(model["summary"])}</p>' if model["summary"] else ""
    theme_cards = []
    for theme in model["themes"]:
        evidence = []
        for paper in theme["evidence"]:
            url = safe_doi(paper.get("doi"))
            label = esc(paper.get("title"))
            evidence.append(
                f'<li>{f"<a href=\"{esc(url)}\" rel=\"noreferrer\">{label}</a>" if url else label}</li>'
            )
        dirs = ", ".join(direction_names.get(d, d) for d in theme["directionIds"])
        theme_cards.append(
            f'<article class="theme"><div class="theme-head"><h3>{esc(theme["title"])}</h3>'
            f'<span class="badge {esc(theme["confidence"])}">уверенность: {esc(theme["confidence"])}</span></div>'
            f'<p>{esc(theme["summary"])}</p>'
            f'<div class="meta">{esc(dirs) if dirs else "все направления"} · evidence: {len(theme["evidence"])}</div>'
            f'<ul class="evidence">{"" .join(evidence) or "<li>Нет DOI-доказательств</li>"}</ul></article>'
        )
    if not theme_cards:
        theme_cards = ['<p class="empty">Синтез не заполнен. Добавьте themes в analysis.json.</p>']
    warning_html = "".join(f"<li>{esc(item)}</li>" for item in model["warnings"])
    warning_block = f'<div class="callout"><b>Что требует внимания</b><ul>{warning_html}</ul></div>' if warning_html else ""

    def section(category: str, title: str, note: str) -> str:
        ident = {"q1": "q1", "a_star": "a-star", "q2": "q2"}[category]
        return (
            f'<section id="{ident}" class="section paper-section" data-category="{category}">'
            f'<div class="section-head"><div><p class="eyebrow">{esc(CATEGORY_LABELS[category])}</p>'
            f'<h2>{esc(title)}</h2></div><p class="section-note">{esc(note)}</p></div>'
            f'<div class="section-body">{paper_table(model["selected"][category], category, direction_names)}</div></section>'
        )

    sections = [
        section("q1", "Журналы Q1", "SJR Q1 в релевантной категории и году; ранг журнала, не оценка статьи."),
        section("a_star", "Конференции A*", "ICORE A*; проверено по названию/акрониму площадки."),
        section("q2", "Журналы Q2", "SJR Q2; другой квартиль, не автоматически «хуже»."),
    ]

    dataset_rows = []
    for item in model["datasets"]:
        doi_url = safe_doi(item.get("doi")) or safe_url(item.get("url"))
        title = esc(item.get("name") or item.get("title") or "Без названия")
        if doi_url:
            title = f'<a href="{esc(doi_url)}" rel="noreferrer">{title}</a>'
        dirs = ", ".join(direction_names.get(d, d) for d in item.get("direction_ids") or [])
        dataset_rows.append(
            f'<tr><td>{title}<div class="venue">{esc(truncate(item.get("description") or item.get("publisher") or "", 500))}</div></td>'
            f'<td>{esc(item.get("year") or "—")}</td><td>{esc(item.get("license") or "—")}</td>'
            f'<td>{esc(dirs or "—")}</td><td>{esc(item.get("doi") or item.get("url") or "—")}</td></tr>'
        )
    dataset_html = (
        '<div class="table-wrap"><table class="datasets"><thead><tr><th>Датасет</th><th>Год</th><th>Лицензия</th><th>Направление</th><th>DOI / ссылка</th></tr></thead>'
        f'<tbody>{"".join(dataset_rows)}</tbody></table></div>'
        if dataset_rows
        else '<p class="empty">DataCite не вернул датасетов за период; проверьте запросы или добавьте данные вручную.</p>'
    )

    def criteria_rows(key: str, label: str, source: str) -> str:
        items = model["criteria"].get(key) or []
        return (
            f'<tr><td><b>{esc(label)}</b></td><td>{esc(source)}</td><td><ul class="clean">'
            f'{"".join(f"<li>{esc(item)}</li>" for item in items)}</ul></td></tr>'
        )

    def bullets(items: list) -> str:
        return '<ul class="clean">' + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"

    track_cards = []
    for track in model["criteria"].get("tracks") or []:
        if not isinstance(track, dict):
            continue
        new_data = track.get("newDatasets") or track.get("new_datasets") or []
        track_cards.append(
            '<article class="track">'
            f'<div class="track-head"><h3>{esc(track.get("track") or track.get("directionId") or "Трек")}</h3>'
            f'<span class="badge quiet">{esc(track.get("directionId") or "")}</span></div>'
            f'<p class="venue">{esc(track.get("venue") or "")}</p>'
            '<div class="track-grid">'
            f'<div><h4>Обязательные аналоги</h4>{bullets(track.get("baselines") or [])}</div>'
            f'<div><h4>Новые данные</h4>{bullets(new_data)}</div>'
            f'<div><h4>Протокол валидации</h4>{bullets(track.get("validation") or [])}</div>'
            f'<div><h4>Аблации</h4>{bullets(track.get("ablations") or [])}</div>'
            f'<div><h4>Воспроизводимость</h4>{bullets(track.get("reproducible") or [])}</div>'
            '</div></article>'
        )
    track_block = (
        '<div class="tracks">' + "".join(track_cards) + "</div>"
        if track_cards
        else '<p class="empty">Track-specific требования не заполнены.</p>'
    )
    criteria_html = (
        '<div class="callout"><b>Ранг площадки — только входной фильтр</b>'
        "<p>A*/Q1/Q2 отвечают на вопрос «где опубликовано», но не «доказано ли». Ниже — что работа должна показать внутри трека: с какими аналогами сравниться, на каких новых данных провериться и какие аблации/артефакты приложить.</p></div>"
        '<table class="criteria"><thead><tr><th>Входной фильтр</th><th>Источник</th><th>Что проверяем</th></tr></thead><tbody>'
        + criteria_rows("a_star", "A* конференция", "ICORE / CORE")
        + criteria_rows("q1", "Q1 журнал", "SCImago SJR: квартиль в категории и году")
        + criteria_rows("q2", "Q2 журнал", "SCImago SJR: квартиль в категории и году")
        + "</tbody></table>"
        + '<h3 class="subhead">Ключевые требования по трекам</h3>'
        + track_block
        + '<h3 class="subhead">Общие критерии включения исследования</h3>'
        + bullets(model["criteria"].get("study") or [])
        + '<h3 class="subhead">Ограничения</h3>'
        + bullets(model["criteria"].get("caveats") or [])
    )

    query_meta = {}
    for item in candidates.get("queries") or []:
        direction_id = str(item.get("direction_id") or "")
        entry = query_meta.setdefault(
            direction_id, {"query": str(item.get("query") or ""), "sources": []}
        )
        source = str(item.get("source") or "")
        if source and source not in entry["sources"]:
            entry["sources"].append(source)

    direction_counts = {
        str(item.get("id")): {"q1": 0, "a_star": 0, "q2": 0} for item in directions
    }
    for category in ("q1", "a_star", "q2"):
        for paper in model["selected"][category]:
            for direction_id in set(paper.get("direction_ids") or []):
                if direction_id in direction_counts:
                    direction_counts[direction_id][category] += 1

    candidate_papers = Counter()
    candidate_datasets = Counter()
    for paper in candidates.get("papers") or []:
        for direction_id in set(paper.get("direction_ids") or []):
            candidate_papers[direction_id] += 1
    for dataset in candidates.get("datasets") or []:
        for direction_id in set(dataset.get("direction_ids") or []):
            candidate_datasets[direction_id] += 1

    max_direction_total = max(
        (sum(values.values()) for values in direction_counts.values()), default=0
    ) or 1

    keyword_rows = []
    for item in directions:
        direction_id = str(item.get("id"))
        meta = query_meta.get(
            direction_id,
            {"query": str(item.get("query") or item.get("direction") or ""), "sources": []},
        )
        query = meta["query"]
        words = [
            word
            for word in re.split(r"[^0-9A-Za-zА-Яа-я-]+", query)
            if len(word) > 2 and word.lower() not in STOPWORDS
        ]
        selected_total = sum(direction_counts.get(direction_id, {}).values())
        share = selected_total / max_direction_total * 100
        keyword_rows.append(
            '<div class="kw-row">'
            f'<div class="kw-head"><b>{esc(direction_id)}</b><span>{esc(item.get("direction"))}</span></div>'
            f'<div class="kw-terms">{"".join(f"<span class=\"kw\">{esc(word)}</span>" for word in words)}</div>'
            f'<div class="kw-query">запрос: <code>{esc(query)}</code></div>'
            f'<div class="kw-meter"><span style="width:{share:.1f}%"></span></div>'
            f'<div class="kw-counts">{esc(" + ".join(meta["sources"]) or "источник не сохранён")} · '
            f'кандидатов: OpenAlex {candidate_papers.get(direction_id, 0)}, '
            f'DataCite {candidate_datasets.get(direction_id, 0)} · '
            f'отобрано {selected_total}</div>'
            "</div>"
        )

    source_max = max(
        len(candidates.get("papers") or []), len(candidates.get("datasets") or []), 1
    )
    source_chart = (
        bar_row(
            "OpenAlex · найдено",
            len(candidates.get("papers") or []),
            source_max,
            color="ghost",
            value_label=str(len(candidates.get("papers") or [])),
        )
        + bar_row(
            "OpenAlex · отобрано",
            counts["papers"],
            source_max,
            value_label=f'{counts["papers"]} из {len(candidates.get("papers") or [])}',
        )
        + bar_row(
            "DataCite · найдено",
            len(candidates.get("datasets") or []),
            source_max,
            color="ghost",
            value_label=str(len(candidates.get("datasets") or [])),
        )
        + bar_row(
            "DataCite · отобрано",
            counts["datasets"],
            source_max,
            value_label=f'{counts["datasets"]} из {len(candidates.get("datasets") or [])}',
        )
    )

    category_max = max(counts["q1"], counts["a_star"], counts["q2"], 1)
    category_chart = (
        bar_row(
            "Q1 журналы",
            counts["q1"],
            category_max,
            color="q1",
            value_label=f'{counts["q1"]} · {counts["q1"] / max(counts["papers"], 1) * 100:.0f}%',
        )
        + bar_row(
            "A* конференции",
            counts["a_star"],
            category_max,
            color="a_star",
            value_label=f'{counts["a_star"]} · {counts["a_star"] / max(counts["papers"], 1) * 100:.0f}%',
        )
        + bar_row(
            "Q2 журналы",
            counts["q2"],
            category_max,
            color="q2",
            value_label=f'{counts["q2"]} · {counts["q2"] / max(counts["papers"], 1) * 100:.0f}%',
        )
    )

    direction_chart = "".join(
        stacked_row(
            f'{str(entry.get("id"))} · {truncate(entry.get("direction") or "", 30)}',
            [
                (direction_counts[str(entry.get("id"))]["q1"], "q1"),
                (direction_counts[str(entry.get("id"))]["a_star"], "a_star"),
                (direction_counts[str(entry.get("id"))]["q2"], "q2"),
            ],
            max_direction_total,
            str(sum(direction_counts[str(entry.get("id"))].values())),
            note=(
                f'Q1 {direction_counts[str(entry.get("id"))]["q1"]} · '
                f'A* {direction_counts[str(entry.get("id"))]["a_star"]} · '
                f'Q2 {direction_counts[str(entry.get("id"))]["q2"]}'
            ),
        )
        for entry in directions
    )

    venue_counts = Counter()
    for category in ("q1", "a_star", "q2"):
        for paper in model["selected"][category]:
            venue_counts[paper.get("venue") or "—"] += 1
    top_venues = venue_counts.most_common(8)
    venue_max = top_venues[0][1] if top_venues else 1
    venue_chart = "".join(
        bar_row(truncate(venue, 34), number, venue_max, value_label=str(number))
        for venue, number in top_venues
    ) or '<p class="empty">Площадки не определены.</p>'

    a_star_max = max((item["found"] for item in model["aStarCoverage"]), default=0) or 1
    a_star_chart = "".join(
        bar_row(
            f'{item["directionId"]} · {truncate(item["direction"], 32)}',
            item["found"],
            a_star_max,
            color="a_star" if item["found"] else "missing",
            value_label=str(item["found"]),
            note="" if item["found"] else "A* не найден",
        )
        for item in model["aStarCoverage"]
    )

    gap_cards = []
    for item in model["aStarCoverage"]:
        head = (
            f'<div class="gap-head"><h4>{esc(item["directionId"])} · {esc(item["direction"])}</h4>'
        )
        if item["found"]:
            venues = ", ".join(item["venues"]) or "площадка не указана"
            gap_cards.append(
                '<article class="gap found">'
                + head
                + f'<span class="badge high">A* найден: {item["found"]}</span></div>'
                + f'<p><b>Площадки:</b> {esc(venues)}</p>'
                + (f'<p><b>Целевые A*:</b> {esc(item["target"])}</p>' if item["target"] else "")
                + (f'<p>{esc(item["note"])}</p>' if item["note"] else "")
                + "</article>"
            )
        else:
            nearest = "".join(
                f'<li><b>{esc(venue.get("venue"))}</b> '
                f'<span class="badge quiet">A*</span> — {esc(venue.get("note"))}</li>'
                for venue in item["nearest"]
            ) or "<li>Ближайшие площадки не указаны.</li>"
            gap_cards.append(
                '<article class="gap missing">'
                + head
                + '<span class="badge low">A* не найден</span></div>'
                + f'<p>{esc(item["note"])}</p>'
                + '<div class="gap-nearest"><b>Ближайшие A*-площадки</b>'
                + f'<ul class="clean">{nearest}</ul></div></article>'
            )

    missing_directions = [
        item["directionId"] for item in model["aStarCoverage"] if not item["found"]
    ]
    if missing_directions:
        missing_callout = (
            '<div class="callout warn"><b>A* не найден по части направлений</b>'
            f'<p>За период {esc(period.get("from"))} — {esc(period.get("to"))} в выборке нет '
            f'A*-публикаций по направлениям <b>{esc(", ".join(missing_directions))}</b>. '
            "Это ограничение выборки, а не доказательство отсутствия работ: ниже перечислены "
            "ближайшие A*-площадки, на которые стоит ориентировать следующую итерацию поиска.</p></div>"
        )
    else:
        missing_callout = ""

    method_html = f"""
    <p class="method-lede">Поиск шёл по сохранённым запросам профиля: OpenAlex — статьи, DataCite — датасеты.
    Ниже — ключевые слова, объём выдачи по источникам, фильтрация и покрытие A* по направлениям.
    Все диаграммы построены по <code>candidates.json</code> и <code>analysis.json</code>; внешних библиотек нет.</p>
    <h3 class="subhead">Ключевые слова и объём поиска</h3>
    <p class="hint">Длина полосы — число отобранных работ относительно самого крупного направления; чипы — слова запроса.</p>
    <div class="kw-map">{''.join(keyword_rows) or '<p class="empty">Запросы не сохранены.</p>'}</div>
    <div class="charts">
      <div class="chart">
        <h3>Записи по источникам</h3>
        <p class="hint">Сколько вернул каждый источник и сколько осталось после отбора.</p>
        {source_chart}
      </div>
      <div class="chart">
        <h3>Публикации по категориям</h3>
        <p class="hint">Доля от {counts["papers"]} отобранных работ.</p>
        {category_chart}
        <div class="legend"><span><i class="q1"></i>Q1</span><span><i class="a_star"></i>A*</span><span><i class="q2"></i>Q2</span></div>
      </div>
    </div>
    <div class="charts">
      <div class="chart">
        <h3>Отобрано по направлениям</h3>
        <p class="hint">Работа может входить в несколько направлений.</p>
        {direction_chart}
        <div class="legend"><span><i class="q1"></i>Q1</span><span><i class="a_star"></i>A*</span><span><i class="q2"></i>Q2</span></div>
      </div>
      <div class="chart">
        <h3>Топ площадок</h3>
        <p class="hint">Топ-8 по числу отобранных работ; полный список — в таблицах Q1/A*/Q2.</p>
        {venue_chart}
      </div>
    </div>
    <h3 class="subhead">Покрытие A* по направлениям</h3>
    {missing_callout}
    <div class="chart chart-wide">
      <h3>A* по направлениям</h3>
      <p class="hint">Ноль означает, что в выборке за период нет A*-публикации по направлению.</p>
      {a_star_chart}
    </div>
    <div class="gaps">{''.join(gap_cards)}</div>
    <div class="method-notes">
      <p><b>Период:</b> {esc(period.get('from'))} — {esc(period.get('to'))}. <b>Сформировано:</b> {esc(model['generatedAt'])}.</p>
      <p><b>Ranking:</b> {esc(candidates.get('ranking', {}).get('note') or '—')}</p>
      <p><b>Качество данных:</b> <code>measured</code> — метаданные OpenAlex/DataCite; <code>derived</code> — SJR-квартиль и ICORE A*; <code>expert</code> — синтез и критерии; <code>missing</code> — нет ранга или цитаты, значение не подставляется.</p>
      <p><b>Ограничения:</b> аннотации и метаданные, не full text; OpenAlex/DataCite могут быть неполными; квартиль зависит от категории и года.</p>
    </div>
    """

    return f"""
    <section class="hero">
      <div class="topline"><span class="brand">SCIENCE · LITERATURE NEWS</span><span class="stamp">{esc(profile.get('name') or 'Научный профиль')} · {esc(period.get('from'))} — {esc(period.get('to'))}</span></div>
      <h1>{esc(model['title'])}</h1>
      <p class="lede">Новые публикации по сохранённым направлениям: Q1-журналы, A*-конференции и Q2-журналы. Синтез, датасеты и критерии — с явными источниками и ограничениями.</p>
      <div class="chips">{direction_chips}</div>
      <div class="kpis">{kpi_html}</div>
    </section>
    <nav class="nav"><div class="wrap"><a href="#themes">Синтез</a><a href="#q1">Q1</a><a href="#a-star">A*</a><a href="#q2">Q2</a><a href="#datasets">Датасеты</a><a href="#criteria">Критерии</a><a href="#method">Методика</a></div></nav>
    <main class="wrap">
      {warning_block}
      {summary}
      <section id="themes" class="section"><div class="section-head"><div><p class="eyebrow">01 · Синтез</p><h2>Ключевые направления исследований</h2></div><p class="section-note">Каждый тезис подкреплён DOI из candidates.json.</p></div><div class="section-body themes">{''.join(theme_cards)}</div></section>
      <div class="toolbar" role="search">
        <label class="field"><span>Поиск</span><input id="paper-search" type="search" placeholder="Название, автор, площадка" autocomplete="off"></label>
        <label class="field"><span>Направление</span><select id="paper-direction"><option value="all">Все</option>{''.join(f'<option value="{esc(item["id"])}">{esc(item["direction"])}</option>' for item in directions)}</select></label>
        <label class="field"><span>Категория</span><select id="paper-category"><option value="all">Все</option><option value="q1">Q1</option><option value="a_star">A*</option><option value="q2">Q2</option></select></label>
        <label class="field"><span>Сортировка</span><select id="paper-sort"><option value="date">По дате</option><option value="citations">По цитатам</option></select></label>
      </div>
      {''.join(sections)}
      <section id="datasets" class="section"><div class="section-head"><div><p class="eyebrow">02 · Данные</p><h2>Новые опубликованные датасеты</h2></div><p class="section-note">DataCite: DOI, год, лицензия и направление.</p></div><div class="section-body">{dataset_html}</div></section>
      <section id="criteria" class="section"><div class="section-head"><div><p class="eyebrow">03 · Критерии</p><h2>Как работа попадает в A*, Q1 и Q2</h2></div><p class="section-note">Ранг площадки — фильтр, не оценка статьи.</p></div><div class="section-body">{criteria_html}</div></section>
      <section id="method" class="section"><div class="section-head"><div><p class="eyebrow">04 · Методика</p><h2>Поиск, качество и ограничения</h2></div></div><div class="section-body">{method_html}</div></section>
    </main>
    """


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Собрать HTML-отчёт sci-literature-news.")
    parser.add_argument("--candidates", type=Path)
    parser.add_argument("--analysis", type=Path)
    parser.add_argument("-o", "--out", type=Path, default=Path("sci-literature-news.html"))
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--example", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    if args.example:
        candidates_path = EXAMPLE_DIR / "example-candidates.json"
        analysis_path = EXAMPLE_DIR / "example-analysis.json"
    else:
        if not args.candidates or not args.analysis:
            parser.error("--candidates и --analysis обязательны без --example")
        candidates_path = args.candidates
        analysis_path = args.analysis

    candidates = load_json(candidates_path)
    analysis = load_json(analysis_path) if analysis_path.exists() else None
    if args.strict and analysis is None:
        raise SystemExit("error: --strict требует analysis.json")
    model = normalize_analysis(analysis, candidates)
    if args.strict:
        errors = []
        for theme in model["themes"]:
            if not theme["evidence"]:
                errors.append(f"theme без DOI-доказательства: {theme['title']}")
        for dataset in model["datasets"]:
            if not dataset.get("doi") and not dataset.get("url"):
                errors.append(f"dataset без DOI/ссылки: {dataset.get('title') or dataset.get('name')}")
        if errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            return 1

    template = args.template.read_text(encoding="utf-8")
    body = render_body(model, candidates)
    payload = {
        "schemaVersion": 1,
        "generatedAt": model["generatedAt"],
        "title": model["title"],
        "period": candidates.get("period"),
        "directions": [
            {"id": item.get("id"), "direction": item.get("direction")}
            for item in candidates.get("profile", {}).get("directions") or []
        ],
        "stats": {
            "papers": sum(len(model["selected"][key]) for key in ("q1", "a_star", "q2")),
            "q1": len(model["selected"]["q1"]),
            "a_star": len(model["selected"]["a_star"]),
            "q2": len(model["selected"]["q2"]),
            "datasets": len(model["datasets"]),
            "themes": len(model["themes"]),
        },
        "warnings": model["warnings"],
    }
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html_output = (
        template.replace("__TITLE__", esc(model["title"]))
        .replace("__PERIOD__", esc(f"{candidates.get('period', {}).get('from')} — {candidates.get('period', {}).get('to')}"))
        .replace("__BODY__", body)
        .replace("__REPORT_DATA__", payload_json)
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html_output, encoding="utf-8")
    print(f"report: {args.out} ({len(html_output) / 1024:.1f} KiB)")
    print(
        f"papers: {payload['stats']['papers']} "
        f"(Q1 {payload['stats']['q1']}, A* {payload['stats']['a_star']}, Q2 {payload['stats']['q2']}); "
        f"datasets: {payload['stats']['datasets']}; themes: {payload['stats']['themes']}"
    )
    if model["warnings"]:
        for warning in model["warnings"]:
            print(f"warning: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())