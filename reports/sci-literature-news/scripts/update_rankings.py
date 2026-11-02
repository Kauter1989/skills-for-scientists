#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build local ranking caches for sci-literature-news.

- SJR: streams the public SCImago panel CSV from
  Michael-E-Rose/SCImagoJournalRankIndicators, keeps one year and computes
  Q1-Q4 by SJR rank within the broad ASJC field.
- ICORE: scrapes the public ICORE A* rows and stores title + acronym + rank.

Caches are local and not part of the skill. Cite SCImago and ICORE in reports.

Usage:
    python update_rankings.py --out-dir .sci-literature-news/cache --year 2025
    python update_rankings.py --sjr-file all.csv --out-dir ... --year 2025
"""

from __future__ import annotations

import argparse
import csv
import html as html_lib
import io
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SJR_URL = "https://raw.githubusercontent.com/Michael-E-Rose/SCImagoJournalRankIndicators/master/all.csv"
CORE_URL = "https://portal.core.edu.au/conf-ranks/"
USER_AGENT = "sci-literature-news/0.1 (ranking cache)"

FIELD_NAMES = {
    "1000": "Multidisciplinary",
    "1100": "Agricultural and Biological Sciences",
    "1200": "Arts and Humanities",
    "1300": "Biochemistry, Genetics and Molecular Biology",
    "1400": "Business, Management and Accounting",
    "1500": "Chemical Engineering",
    "1600": "Chemistry",
    "1700": "Computer Science",
    "1800": "Decision Sciences",
    "1900": "Earth and Planetary Sciences",
    "2000": "Economics, Econometrics and Finance",
    "2100": "Energy",
    "2200": "Engineering",
    "2300": "Environmental Science",
    "2400": "Immunology and Microbiology",
    "2500": "Materials Science",
    "2600": "Mathematics",
    "2700": "Medicine",
    "2800": "Neuroscience",
    "2900": "Nursing",
    "3000": "Pharmacology, Toxicology and Pharmaceutics",
    "3100": "Physics and Astronomy",
    "3200": "Psychology",
    "3300": "Social Sciences",
    "3400": "Veterinary",
    "3500": "Dentistry",
    "3600": "Health Professions",
}


def open_url(url: str, timeout: int = 120):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv,text/html;q=0.9,*/*;q=0.8"})
    return urllib.request.urlopen(request, timeout=timeout)


def quartile(rank: int, total: int) -> str:
    if total <= 0:
        return ""
    share = rank / total
    if share <= 0.25:
        return "Q1"
    if share <= 0.50:
        return "Q2"
    if share <= 0.75:
        return "Q3"
    return "Q4"


def build_sjr(out: Path, year: int, source: str | None) -> int:
    rows: dict[str, dict] = {}
    if source:
        handle = Path(source).open("r", encoding="utf-8-sig", newline="")
        close = True
    else:
        print(f"downloading SJR CSV ({SJR_URL})", file=sys.stderr)
        response = open_url(SJR_URL)
        handle = io.TextIOWrapper(response, encoding="utf-8-sig", newline="")
        close = True
    try:
        reader = csv.DictReader(handle)
        for row in reader:
            if str(row.get("year") or "").strip() != str(year):
                continue
            sourceid = (row.get("Sourceid") or "").strip()
            field = (row.get("field") or "").strip()
            if not sourceid or not field:
                continue
            key = f"{sourceid}|{field}"
            rows[key] = {
                "sourceid": sourceid,
                "title": (row.get("Title") or "").strip(),
                "year": year,
                "field_code": field,
                "field": FIELD_NAMES.get(field, field),
                "sjr": (row.get("SJR") or "").strip(),
                "issn": (row.get("Issn") or "").strip(),
            }
    finally:
        if close:
            handle.close()

    grouped: dict[str, list[dict]] = {}
    for row in rows.values():
        grouped.setdefault(row["field_code"], []).append(row)
    for group in grouped.values():
        numeric = []
        for row in group:
            try:
                row["_sjr"] = float(row["sjr"])
                numeric.append(row)
            except ValueError:
                row["quartile"] = ""
        numeric.sort(key=lambda item: item["_sjr"], reverse=True)
        for index, row in enumerate(numeric, start=1):
            row["quartile"] = quartile(index, len(numeric))

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sourceid", "title", "issn", "year", "field", "field_code", "sjr", "quartile", "source"],
        )
        writer.writeheader()
        for row in sorted(rows.values(), key=lambda item: (item["field_code"], item["title"])):
            writer.writerow(
                {
                    "sourceid": row["sourceid"],
                    "title": row["title"],
                    "issn": row["issn"],
                    "year": row["year"],
                    "field": row["field"],
                    "field_code": row["field_code"],
                    "sjr": row["sjr"],
                    "quartile": row.get("quartile", ""),
                    "source": f"SCImago SJR {year}",
                }
            )
    print(f"wrote {out} ({len(rows)} journal-field rows, year {year})")
    return 0


def strip_tags(value: str) -> str:
    return html_lib.unescape(re.sub(r"<[^>]+>", "", value)).strip()


def fetch_core_page(source: str, page: int) -> tuple[list[dict], int]:
    url = (
        f"{CORE_URL}?search=A%2A&by=rank&source={urllib.parse.quote(source)}"
        f"&sort=atitle&page={page}"
    )
    with open_url(url) as response:
        text = response.read().decode("utf-8", "replace")
    total = 0
    match = re.search(r"Showing results\s+\d+\s*-\s*\d+\s+of\s+(\d+)", text, re.I)
    if match:
        total = int(match.group(1))
    rows = []
    for row_html in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", text, re.I):
        cells = [strip_tags(cell) for cell in re.findall(r"<td[^>]*>([\s\S]*?)</td>", row_html, re.I)]
        if len(cells) < 4:
            continue
        title, acronym, row_source, rank = cells[0], cells[1], cells[2], cells[3]
        if rank.upper() != "A*":
            continue
        rows.append(
            {
                "title": title,
                "acronym": acronym,
                "rank": "A*",
                "source": row_source or source,
            }
        )
    return rows, total


def build_core(out: Path, source: str) -> int:
    print(f"downloading ICORE A* rows ({source})", file=sys.stderr)
    all_rows = []
    page = 1
    total = None
    while True:
        rows, count = fetch_core_page(source, page)
        if total is None:
            total = count
        all_rows.extend(rows)
        if not total or page * 50 >= total:
            break
        page += 1
        time.sleep(0.25)
    deduped = {}
    for row in all_rows:
        deduped[(row["title"], row["acronym"])] = row
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["title", "acronym", "rank", "source"])
        writer.writeheader()
        for row in sorted(deduped.values(), key=lambda item: item["title"].lower()):
            writer.writerow(row)
    print(f"wrote {out} ({len(deduped)} A* rows, source {source})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Построить кэш SJR и ICORE A*")
    parser.add_argument("--out-dir", type=Path, default=Path(".sci-literature-news/cache"))
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--sjr-file", type=Path)
    parser.add_argument("--core-source", default="ICORE2026")
    parser.add_argument("--skip-sjr", action="store_true")
    parser.add_argument("--skip-core", action="store_true")
    args = parser.parse_args(argv)
    if not args.skip_sjr:
        build_sjr(args.out_dir / f"sjr-{args.year}.csv", args.year, str(args.sjr_file) if args.sjr_file else None)
    if not args.skip_core:
        build_core(args.out_dir / "core-a-star.csv", args.core_source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())