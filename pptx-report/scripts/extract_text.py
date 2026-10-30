#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Извлечение текста из .pptx по слайдам (только стандартная библиотека).

Использование:
    python extract_text.py deck.pptx                 # весь текст по слайдам
    python extract_text.py deck.pptx --slides 2,5-7  # только выбранные слайды
    python extract_text.py deck.pptx --layouts       # инвентаризация макетов (layouts)
    python extract_text.py deck.pptx --json          # машинный формат
    python extract_text.py deck.pptx --out text.txt  # запись в UTF-8-файл

Порядок слайдов берётся из <p:sldIdLst> presentation.xml, а не из имён файлов.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}

# Отношение слайд -> макет
REL_LAYOUT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout"


def _read(zf: zipfile.ZipFile, name: str) -> bytes:
    with zf.open(name) as fh:
        return fh.read()


def _slide_order(zf: zipfile.ZipFile) -> list[str]:
    """Список путей ppt/slides/slideN.xml в порядке показа."""
    pres = ET.fromstring(_read(zf, "ppt/presentation.xml"))
    rels = ET.fromstring(_read(zf, "ppt/_rels/presentation.xml.rels"))
    rid_to_target = {
        rel.get("Id"): rel.get("Target")
        for rel in rels.findall("pr:Relationship", NS)
    }
    order = []
    for sld in pres.findall("p:sldIdLst/p:sldId", NS):
        rid = sld.get("{%s}id" % NS["r"])
        target = rid_to_target.get(rid, "")
        target = target.lstrip("/")
        if not target.startswith("ppt/"):
            target = "ppt/" + target
        order.append(target)
    return order


def _text_of(part_xml: bytes) -> list[str]:
    """Абзацы текста из XML слайда: <a:p> -> строка, <a:br/> -> перевод строки."""
    root = ET.fromstring(part_xml)
    lines = []
    for p in root.iter("{%s}p" % NS["a"]):
        chunks = []
        for node in p.iter():
            tag = node.tag
            if tag == "{%s}t" % NS["a"] and node.text:
                chunks.append(node.text)
            elif tag == "{%s}br" % NS["a"]:
                chunks.append("\n")
        line = "".join(chunks).strip()
        if line:
            lines.append(line)
    return lines


def _has_chart(part_xml: bytes) -> bool:
    return b"graphicData" in part_xml and (
        b"chart" in part_xml or b"c:chartSpace" in part_xml
    )


def _has_table(part_xml: bytes) -> bool:
    return b"<a:tbl>" in part_xml or b"<a:tbl " in part_xml


def _min_font(part_xml: bytes) -> float | None:
    sizes = []
    for raw in re.findall(rb'<a:rPr[^>]*\bsz="(\d+)"', part_xml):
        try:
            sizes.append(int(raw) / 100.0)
        except ValueError:
            pass
    return min(sizes) if sizes else None


def _layout_of_slide(zf: zipfile.ZipFile, slide_path: str) -> str:
    rels_path = re.sub(r"(ppt/slides/)(slide\d+\.xml)$", r"\1_rels/\2.rels", slide_path)
    try:
        rels = ET.fromstring(_read(zf, rels_path))
    except KeyError:
        return ""
    for rel in rels.findall("pr:Relationship", NS):
        if rel.get("Type") == REL_LAYOUT:
            target = rel.get("Target", "")
            m = re.search(r"slideLayout(\d+)\.xml", target)
            if m:
                return "slideLayout%s" % m.group(1)
    return ""


def _layout_name(zf: zipfile.ZipFile, layout_file: str) -> str:
    path = "ppt/slideLayouts/%s.xml" % layout_file
    try:
        root = ET.fromstring(_read(zf, path))
    except KeyError:
        return ""
    name = root.get("name") or root.get("matchingName") or ""
    if not name:
        csld = root.find("{%s}cSld" % NS["p"])
        if csld is not None:
            name = csld.get("name", "") or ""
    return name


def parse_ranges(spec: str, total: int) -> set[int]:
    out: set[int] = set()
    for piece in spec.split(","):
        piece = piece.strip()
        if not piece:
            continue
        if "-" in piece:
            a, b = piece.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(piece))
    return {n for n in out if 1 <= n <= total}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck")
    ap.add_argument("--slides", help="номера слайдов: 2,5-7")
    ap.add_argument("--json", action="store_true", help="вывод в JSON")
    ap.add_argument("--layouts", action="store_true", help="показать макеты каждого слайда")
    ap.add_argument("--out", help="записать результат в UTF-8-файл")
    args = ap.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    with zipfile.ZipFile(args.deck) as zf:
        order = _slide_order(zf)
        if args.layouts:
            seen = {}
            for sp in order:
                lay = _layout_of_slide(zf, sp)
                if lay and lay not in seen:
                    seen[lay] = _layout_name(zf, lay)
            # все макеты пакета, не только использованные
            for name in sorted(zf.namelist()):
                m = re.match(r"ppt/slideLayouts/(slideLayout\d+)\.xml$", name)
                if m and m.group(1) not in seen:
                    seen[m.group(1)] = _layout_name(zf, m.group(1))
            rows = [{"layout": k, "name": v} for k, v in sorted(
                seen.items(), key=lambda kv: int(re.sub(r"\D", "", kv[0])))]
            if args.json:
                payload = json.dumps(rows, ensure_ascii=False, indent=1)
            else:
                payload = "\n".join("%-16s %s" % (r["layout"], r["name"]) for r in rows)
            if args.out:
                with open(args.out, "w", encoding="utf-8") as fh:
                    fh.write(payload + "\n")
                print("Записано: %s" % args.out)
            else:
                print(payload)
            return 0

        want = parse_ranges(args.slides, len(order)) if args.slides else set(range(1, len(order) + 1))
        slides = []
        for i, sp in enumerate(order, 1):
            if i not in want:
                continue
            xml = _read(zf, sp)
            slides.append({
                "number": i,
                "part": sp,
                "layout": _layout_of_slide(zf, sp),
                "text": _text_of(xml),
                "has_table": _has_table(xml),
                "has_chart": _has_chart(xml),
                "min_font": _min_font(xml),
            })

    if args.json:
        payload = json.dumps(slides, ensure_ascii=False, indent=1)
    else:
        lines_out = []
        for s in slides:
            marks = []
            if s["has_table"]:
                marks.append("таблица")
            if s["has_chart"]:
                marks.append("диаграмма")
            suffix = ("  [%s]" % ", ".join(marks)) if marks else ""
            lines_out.append("\n<!-- Слайд %d -->%s" % (s["number"], suffix))
            if s["min_font"] is not None:
                lines_out.append("Мин. кегль: %.1f pt" % s["min_font"])
            lines_out.extend(s["text"])
        payload = "\n".join(lines_out)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
        print("Записано: %s" % args.out)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
