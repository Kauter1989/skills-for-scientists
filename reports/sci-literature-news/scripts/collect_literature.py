#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect papers and datasets for a scientific literature-news report.

Primary sources:
- OpenAlex works (no key, polite pool with --mailto);
- DataCite datasets (no key);
- optional local SJR cache and ICORE A* cache (see update_rankings.py).

The script writes candidates.json; the agent writes analysis.json; build_report.py
merges them into standalone HTML.

Usage:
    python collect_literature.py --profile .sci-literature-news/profile.md \
        --out .sci-literature-news/candidates.json --mailto you@example.org \
        --sjr-cache .sci-literature-news/cache/sjr.csv \
        --core-cache .sci-literature-news/cache/core-a-star.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

from profile import load_profile

USER_AGENT = "sci-literature-news/0.1 (research literature digest)"
OPENALEX = "https://api.openalex.org/works"
DATACITE = "https://api.datacite.org/dois"

FIELD_CODES = {
    "multidisciplinary": "1000",
    "agricultural and biological sciences": "1100",
    "arts and humanities": "1200",
    "biochemistry, genetics and molecular biology": "1300",
    "business, management and accounting": "1400",
    "chemical engineering": "1500",
    "chemistry": "1600",
    "computer science": "1700",
    "decision sciences": "1800",
    "earth and planetary sciences": "1900",
    "economics, econometrics and finance": "2000",
    "energy": "2100",
    "engineering": "2200",
    "environmental science": "2300",
    "immunology and microbiology": "2400",
    "materials science": "2500",
    "mathematics": "2600",
    "medicine": "2700",
    "neuroscience": "2800",
    "nursing": "2900",
    "pharmacology, toxicology and pharmaceutics": "3000",
    "physics and astronomy": "3100",
    "psychology": "3200",
    "social sciences": "3300",
    "veterinary": "3400",
    "health professions": "3600",
    "dentistry": "3500",
}


def norm(value: object) -> str:
    text = str(value or "").lower()
    text = text.replace("&amp;", "&").replace("&", " and ")
    return re.sub(r"[^a-z0-9а-яё]+", " ", text).strip()


def norm_doi(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text, flags=re.I)
    return text.lower()


def norm_issn(value: object) -> str:
    return re.sub(r"[^0-9Xx]", "", str(value or "")).upper()


def tokens(value: object) -> set[str]:
    return {item for item in norm(value).split() if len(item) > 2}


def parse_date(value: object) -> date | None:
    text = str(value or "").strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def http_json(url: str, params: dict, mailto: str = "", timeout: int = 60) -> dict:
    if mailto:
        params = {**params, "mailto": mailto}
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code == 429:
                time.sleep(3 * (attempt + 1))
                continue
            if 500 <= exc.code < 600:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"request failed: {url}: {last}")


def abstract_from_openalex(inverted: object) -> str:
    if not isinstance(inverted, dict):
        return ""
    positions = []
    for word, indexes in inverted.items():
        if not isinstance(indexes, list):
            continue
        for index in indexes:
            if isinstance(index, int):
                positions.append((index, word))
    return " ".join(word for _, word in sorted(positions))


def load_sjr_cache(path: Path | None) -> dict | None:
    if not path:
        return None
    if not path.exists():
        raise FileNotFoundError(f"SJR cache not found: {path}")
    by_issn: dict[str, list[dict]] = {}
    by_title: dict[str, list[dict]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            item = {
                "sourceid": (row.get("sourceid") or "").strip(),
                "title": (row.get("title") or "").strip(),
                "issn": norm_issn(row.get("issn")),
                "year": (row.get("year") or "").strip(),
                "field": (row.get("field") or "").strip(),
                "field_code": (row.get("field_code") or "").strip(),
                "sjr": (row.get("sjr") or "").strip(),
                "quartile": (row.get("quartile") or "").strip().upper(),
                "source": (row.get("source") or "SJR").strip(),
            }
            if item["issn"]:
                by_issn.setdefault(item["issn"], []).append(item)
            if item["title"]:
                by_title.setdefault(norm(item["title"]), []).append(item)
    return {"by_issn": by_issn, "by_title": by_title, "path": str(path)}


def load_core_cache(path: Path | None) -> dict | None:
    if not path:
        return None
    if not path.exists():
        raise FileNotFoundError(f"ICORE cache not found: {path}")
    by_title: dict[str, dict] = {}
    by_acronym: dict[str, dict] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            item = {
                "title": (row.get("title") or "").strip(),
                "acronym": (row.get("acronym") or "").strip(),
                "rank": (row.get("rank") or "").strip().upper(),
                "source": (row.get("source") or "ICORE").strip(),
            }
            if item["title"]:
                by_title.setdefault(norm(item["title"]), item)
            if item["acronym"]:
                by_acronym.setdefault(norm(item["acronym"]), item)
    return {"by_title": by_title, "by_acronym": by_acronym, "path": str(path)}


def best_quartile(rows: list[dict]) -> dict | None:
    order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    valid = [row for row in rows if row.get("quartile") in order]
    if not valid:
        return None
    valid.sort(key=lambda row: (order[row["quartile"]], -float(row.get("sjr") or 0)))
    return valid[0]


def lookup_sjr(work: dict, cache: dict | None) -> dict | None:
    if not cache:
        return None
    source = (work.get("primary_location") or {}).get("source") or {}
    issns = {norm_issn(source.get("issn_l"))}
    issns.update(norm_issn(item) for item in source.get("issn") or [])
    issns.discard("")
    rows = []
    for issn in issns:
        rows.extend(cache["by_issn"].get(issn, []))
    if not rows:
        rows = cache["by_title"].get(norm(work.get("venue")), [])
    if not rows:
        return None
    field_name = ((work.get("primary_topic") or {}).get("field") or {}).get("display_name") or ""
    field_code = FIELD_CODES.get(norm(field_name), "")
    matching = [row for row in rows if field_code and row.get("field_code") == field_code]
    if matching:
        chosen = best_quartile(matching)
        match = "field"
    else:
        chosen = best_quartile(rows)
        match = "best"
    if not chosen:
        return None
    return {
        "quartile": chosen["quartile"],
        "field": chosen["field"],
        "year": chosen["year"],
        "source": chosen["source"],
        "sjr": chosen["sjr"],
        "match": match,
        "quality": "derived",
    }


def lookup_core(work: dict, cache: dict | None) -> dict | None:
    if not cache:
        return None
    venue = work.get("venue") or ""
    venue_norm = norm(venue)
    if not venue_norm:
        return None
    for token in tokens(venue):
        item = cache["by_acronym"].get(token)
        if item and item["rank"] == "A*":
            return {**item, "quality": "derived", "match": "acronym"}
    direct = cache["by_title"].get(venue_norm)
    if direct and direct["rank"] == "A*":
        return {**direct, "quality": "derived", "match": "title"}
    venue_tokens = tokens(venue)
    best = None
    best_score = 0.0
    for title, item in cache["by_title"].items():
        if item["rank"] != "A*":
            continue
        title_tokens = tokens(title)
        if not title_tokens:
            continue
        score = len(venue_tokens & title_tokens) / len(venue_tokens | title_tokens)
        if score > best_score:
            best_score = score
            best = item
    if best and best_score >= 0.72:
        return {**best, "quality": "derived", "match": f"fuzzy:{best_score:.2f}"}
    return None


def normalize_work(work: dict, direction_id: str) -> dict | None:
    title = (work.get("display_name") or work.get("title") or "").strip()
    if not title:
        return None
    source = (work.get("primary_location") or {}).get("source") or {}
    source_name = source.get("display_name") or (work.get("primary_location") or {}).get("raw_source_name") or ""
    source_type = source.get("type") or ""
    if "conference" in source_type.lower() or "proceedings" in str(source_name).lower():
        venue_type = "conference"
    elif "journal" in source_type.lower():
        venue_type = "journal"
    else:
        venue_type = source_type or "unknown"
    authors = []
    for authorship in (work.get("authorships") or [])[:8]:
        name = (authorship.get("author") or {}).get("display_name")
        if name:
            authors.append(name)
    topic = work.get("primary_topic") or {}
    return {
        "id": str(work.get("id") or "").rstrip("/").split("/")[-1],
        "doi": norm_doi(work.get("doi")),
        "title": title,
        "abstract": abstract_from_openalex(work.get("abstract_inverted_index")),
        "date": work.get("publication_date") or "",
        "year": work.get("publication_year") or 0,
        "type": work.get("type") or "unknown",
        "venue": source_name,
        "venue_type": venue_type,
        "issn": [norm_issn(source.get("issn_l"))] + [norm_issn(v) for v in source.get("issn") or []],
        "authors": authors,
        "citations": work.get("cited_by_count") or 0,
        "oa_url": ((work.get("open_access") or {}).get("oa_url") or ""),
        "url": work.get("doi") or work.get("id") or "",
        "field": ((topic.get("field") or {}).get("display_name") or ""),
        "subfield": ((topic.get("subfield") or {}).get("display_name") or ""),
        "direction_ids": [direction_id],
        "primary_location_type": source_type,
    }


def openalex_search(query: str, start: date, end: date, limit: int, mailto: str) -> list[dict]:
    output = []
    cursor = "*"
    while cursor and len(output) < limit:
        batch = min(100, limit - len(output))
        data = http_json(
            OPENALEX,
            {
                "search": query,
                "filter": f"from_publication_date:{start.isoformat()},to_publication_date:{end.isoformat()}",
                "per_page": batch,
                "cursor": cursor,
            },
            mailto=mailto,
        )
        output.extend((data.get("results") or []))
        cursor = (data.get("meta") or {}).get("next_cursor")
        if not data.get("results"):
            break
        time.sleep(0.2)
    return output


def datacite_search(query: str, start: date, end: date, limit: int, mailto: str) -> list[dict]:
    output = []
    page = 1
    while len(output) < limit:
        data = http_json(
            DATACITE,
            {
                "query": query,
                "resource-type-id": "dataset",
                "page[size]": min(100, limit - len(output)),
                "page[number]": page,
            },
            mailto=mailto,
        )
        items = data.get("data") or []
        if not items:
            break
        output.extend(items)
        meta = data.get("meta") or {}
        if page >= int(meta.get("totalPages") or page):
            break
        page += 1
        time.sleep(0.2)
    result = []
    for item in output:
        attrs = item.get("attributes") or {}
        year = int(attrs.get("publicationYear") or 0)
        if year and not (start.year <= year <= end.year):
            continue
        titles = attrs.get("titles") or []
        descriptions = attrs.get("descriptions") or []
        rights = attrs.get("rightsList") or []
        creators = []
        for creator in (attrs.get("creators") or [])[:8]:
            name = creator.get("name")
            if name:
                creators.append(name)
        result.append(
            {
                "doi": norm_doi(attrs.get("doi") or item.get("id")),
                "title": (titles[0].get("title") if titles else "") or "",
                "description": (descriptions[0].get("description") if descriptions else "") or "",
                "year": year,
                "publisher": attrs.get("publisher") or "",
                "license": (rights[0].get("rights") if rights else "") or "",
                "url": attrs.get("url") or "",
                "creators": creators,
                "direction_id": "",
            }
        )
    return result


def classify(work: dict, sjr_cache: dict | None, core_cache: dict | None) -> dict:
    core = lookup_core(work, core_cache)
    sjr = lookup_sjr(work, sjr_cache)
    if core and core.get("rank") == "A*":
        category = "a_star"
    elif sjr and sjr.get("quartile") == "Q1":
        category = "q1"
    elif sjr and sjr.get("quartile") == "Q2":
        category = "q2"
    else:
        category = "unranked"
    return {
        "category": category,
        "sjr": sjr,
        "core": core,
        "ranking_evidence": [
            item
            for item in (
                f"{sjr['source']} {sjr['year']} {sjr['quartile']}" if sjr else "",
                f"{core['source']} A*" if core and core.get("rank") == "A*" else "",
            )
            if item
        ],
    }


def merge_by_doi(items: list[dict], key: str = "doi") -> list[dict]:
    output = {}
    for item in items:
        value = item.get(key) or norm(item.get("title"))
        if not value:
            continue
        if value in output:
            existing = output[value]
            for direction in item.get("direction_ids") or []:
                if direction not in existing["direction_ids"]:
                    existing["direction_ids"].append(direction)
            if item.get("abstract") and not existing.get("abstract"):
                existing["abstract"] = item["abstract"]
        else:
            output[value] = item
    return list(output.values())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Собрать публикации и датасеты для literature-news")
    parser.add_argument("--profile", type=Path, default=Path(".sci-literature-news/profile.md"))
    parser.add_argument("--out", type=Path, default=Path(".sci-literature-news/candidates.json"))
    parser.add_argument("--from", dest="from_", default="")
    parser.add_argument("--to", default="")
    parser.add_argument("--mailto", default="")
    parser.add_argument("--max-results", type=int, default=0)
    parser.add_argument("--sjr-cache", type=Path)
    parser.add_argument("--core-cache", type=Path)
    args = parser.parse_args(argv)

    profile = load_profile(args.profile)
    prefs = profile["preferences"]
    start = date.fromisoformat(args.from_ or prefs.get("from") or "2000-01-01")
    end = date.fromisoformat(args.to or prefs.get("to") or date.today().isoformat())
    limit = args.max_results or int(prefs.get("max_results_per_direction") or 100)
    directions = [item for item in profile["directions"] if item.get("direction", "").strip()]
    if not directions:
        print("error: в профиле нет направлений", file=sys.stderr)
        return 2
    sjr_cache = load_sjr_cache(args.sjr_cache)
    core_cache = load_core_cache(args.core_cache)
    warnings = []
    if not sjr_cache:
        warnings.append("SJR cache не передан: Q1/Q2 не будут присвоены; запустите update_rankings.py")
    if not core_cache:
        warnings.append("ICORE cache не передан: A* не будет присвоен; запустите update_rankings.py")

    papers = []
    datasets = []
    queries = []
    for direction in directions:
        query = direction.get("query") or direction.get("direction") or ""
        queries.append({"direction_id": direction["id"], "query": query, "source": "OpenAlex"})
        try:
            raw = openalex_search(query, start, end, limit, args.mailto)
        except Exception as exc:
            warnings.append(f"OpenAlex {direction['id']}: {exc}")
            raw = []
        for item in raw:
            normalized = normalize_work(item, direction["id"])
            if not normalized:
                continue
            classification = classify(normalized, sjr_cache, core_cache)
            normalized.update(classification)
            papers.append(normalized)
        queries.append({"direction_id": direction["id"], "query": query, "source": "DataCite"})
        try:
            data_items = datacite_search(query, start, end, limit, args.mailto)
        except Exception as exc:
            warnings.append(f"DataCite {direction['id']}: {exc}")
            data_items = []
        for item in data_items:
            item["direction_id"] = direction["id"]
            datasets.append(item)

    papers = merge_by_doi(papers)
    dataset_map = {}
    for item in datasets:
        key = item.get("doi") or norm(item.get("title"))
        if not key:
            continue
        if key in dataset_map:
            if item["direction_id"] not in dataset_map[key]["direction_ids"]:
                dataset_map[key]["direction_ids"].append(item["direction_id"])
        else:
            dataset_map[key] = {**item, "direction_ids": [item["direction_id"]]}
    datasets = list(dataset_map.values())

    payload = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "period": {"from": start.isoformat(), "to": end.isoformat()},
        "profile": profile,
        "queries": queries,
        "ranking": {
            "sjr": str(args.sjr_cache) if args.sjr_cache else "",
            "core": str(args.core_cache) if args.core_cache else "",
            "note": "Q1/Q2 — квартиль SJR в категории/году; A* — ICORE. См. ranking_evidence.",
        },
        "papers": papers,
        "datasets": datasets,
        "warnings": warnings,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"papers: {len(papers)}; datasets: {len(datasets)}; queries: {len(queries)}")
    print(f"categories: Q1={sum(1 for p in papers if p['category'] == 'q1')} "
          f"A*={sum(1 for p in papers if p['category'] == 'a_star')} "
          f"Q2={sum(1 for p in papers if p['category'] == 'q2')} "
          f"unranked={sum(1 for p in papers if p['category'] == 'unranked')}")
    if warnings:
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())