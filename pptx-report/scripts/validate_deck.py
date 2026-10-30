#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Структурная валидация .pptx (только стандартная библиотека).

Использование:
    python validate_deck.py out.pptx
    python validate_deck.py out.pptx --strict
    python validate_deck.py out.pptx --min-font 14 --check-overlap --check-bounds --check-overflow

Проверяет дефекты, из-за которых PowerPoint отказывается открывать файл:
  1. Целостность ZIP и непустые части.
  2. [Content_Types].xml покрывает все части (Defaults по расширению + Overrides).
  3. Все .rels: цели существуют, Id уникальны, нет ссылок в никуда.
  4. <p:sldIdLst>: каждый r:id ведёт на существующий слайд; каждый слайд в списке показан.
  5. XML всех частей хорошо сформирован.
  6. Слайды: нет пустых <a:t>, нет явного placeholder-мусора.
  7. Диаграммы: нет авто-заголовка из имени серии, допустимые позиции подписей.
  8. По флагам: минимальный кегль, пересечения, границы, переполнение.
Каждая ошибка печатается вместе с рекомендуемым исправлением.
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"

REL_SLIDE = NS_R + "/slide"
PLACEHOLDER_RE = re.compile(
    r"\blorem\b|\bipsum\b|\bTODO\b|\[встав|\[insert|\bx{3,}\b|заголовок\s*слайда|click to (add|edit)",
    re.IGNORECASE)

errors: list[str] = []
warnings: list[str] = []


def err(msg: str, fix: str) -> None:
    errors.append("%s\n    Исправление: %s" % (msg, fix))


def warn(msg: str, fix: str) -> None:
    warnings.append("%s\n    Рекомендация: %s" % (msg, fix))


def norm(base: str, target: str) -> str:
    import posixpath
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(base, target))


def emu_in(v: str | None) -> float:
    try:
        return int(v or 0) / 914400.0
    except ValueError:
        return 0.0


def shape_boxes(root: ET.Element) -> list[tuple[float, float, float, float, str, float, int]]:
    """Текстовые фигуры слайда: (x, y, x2, y2, текст, кегль, число абзацев)."""
    out = []
    for sp in root.iter("{%s}sp" % NS_P):
        tx = sp.find("{%s}txBody" % NS_P)
        if tx is None:
            continue
        text = " ".join((t.text or "") for t in tx.iter("{%s}t" % NS_A)).strip()
        if not text:
            continue
        xfrm = sp.find("{%s}spPr/{%s}xfrm" % (NS_P, NS_A))
        if xfrm is None:
            continue
        off = xfrm.find("{%s}off" % NS_A)
        ext = xfrm.find("{%s}ext" % NS_A)
        if off is None or ext is None:
            continue
        x, y = emu_in(off.get("x")), emu_in(off.get("y"))
        w, h = emu_in(ext.get("cx")), emu_in(ext.get("cy"))
        sizes = []
        for rpr in sp.iter("{%s}rPr" % NS_A):
            if rpr.get("sz"):
                try:
                    sizes.append(int(rpr.get("sz")) / 100.0)
                except ValueError:
                    pass
        size = max(sizes) if sizes else 14.0
        paras = len(list(tx.iter("{%s}p" % NS_A))) or 1
        out.append((x, y, x + w, y + h, text, size, paras))
    return out


def estimate_height(text: str, width: float, size: float) -> float:
    cpl = max(4, int((width or 0.1) / (size * 0.0072)))
    lines = max(1, -(-len(text) // cpl))
    return lines * size * 1.2 / 72.0


def min_font_pt(root: ET.Element) -> float | None:
    sizes = []
    for rpr in root.iter("{%s}rPr" % NS_A):
        sz = rpr.get("sz")
        if sz:
            try:
                sizes.append(int(sz) / 100.0)
            except ValueError:
                pass
    return min(sizes) if sizes else None


def chart_info(root: ET.Element) -> tuple[bool, str, list[str]]:
    """(авто-заголовок включён, текст заголовка, имена серий)."""
    auto = root.find("{%s}chart/{%s}autoTitleDeleted" % (NS_C, NS_C))
    auto_on = auto is None or auto.get("val", "0") != "1"
    title = ""
    title_el = root.find("{%s}chart/{%s}title" % (NS_C, NS_C))
    if title_el is not None:
        title = " ".join((t.text or "") for t in title_el.iter("{%s}t" % NS_A)).strip()
    names = []
    for ser in root.iter("{%s}ser" % NS_C):
        tx = ser.find("{%s}tx" % NS_C)
        if tx is not None:
            val = " ".join((t.text or "") for t in tx.iter("{%s}v" % NS_C)).strip()
            if val:
                names.append(val)
    return auto_on, title, names


def main() -> int:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--min-font", type=float, help="минимально допустимый кегль, pt")
    ap.add_argument("--check-overlap", action="store_true", help="проверять пересечения текстовых блоков")
    ap.add_argument("--check-bounds", action="store_true", help="проверять выход фигур за границы слайда")
    ap.add_argument("--check-overflow", action="store_true", help="оценивать переполнение текстовых блоков")
    args = ap.parse_args()

    # 1. ZIP
    try:
        zf = zipfile.ZipFile(args.deck)
        bad = zf.testzip()
        if bad:
            err("Повреждённая запись в ZIP: %s" % bad, "пересоберите файл (pack/запись заново)")
    except zipfile.BadZipFile as e:
        print("ФАТАЛЬНО: файл не является ZIP-архивом: %s" % e)
        return 2
    names = set(zf.namelist())

    if "[Content_Types].xml" not in names:
        err("Нет [Content_Types].xml", "добавьте часть с Overrides для всех XML-частей")
        print("\n".join(errors)); return 2

    # 5. XML well-formed (заодно кэш распарсенного)
    parsed: dict[str, ET.Element] = {}
    for n in sorted(names):
        if not n.endswith((".xml", ".rels")):
            continue
        try:
            parsed[n] = ET.fromstring(zf.read(n))
        except ET.ParseError as e:
            err("XML не сформирован: %s (%s)" % (n, e), "проверьте правки этого файла; перепакуйте из исправного источника")

    # 2. Content types
    ct = parsed.get("[Content_Types].xml")
    if ct is not None:
        defaults = {d.get("Extension", "").lower() for d in ct.findall("{%s}Default" % NS_CT)}
        overrides = {o.get("PartName", "").lstrip("/") for o in ct.findall("{%s}Override" % NS_CT)}
        for n in sorted(names):
            if n == "[Content_Types].xml":
                continue
            ext = n.rsplit(".", 1)[-1].lower() if "." in n else ""
            if n not in overrides and ext not in defaults:
                err("Часть без Content Type: %s" % n,
                    "добавьте Override (XML-часть) или Default по расширению в [Content_Types].xml")
        for o in sorted(overrides):
            if o not in names:
                warn("Override для несуществующей части: %s" % o, "удалите лишний Override (clean)")

    # 3. Rels
    slide_parts_in_rels: set[str] = set()
    for n in sorted(names):
        if not n.endswith(".rels"):
            continue
        base = re.sub(r"/_rels/[^/]+\.rels$", "", n.replace("_rels/", "", 1) if n.startswith("_rels/") else n)
        # base dir: для ppt/_rels/presentation.xml.rels это "ppt"; для _rels/.rels это ""
        if n == "_rels/.rels":
            base = ""
        else:
            m = re.match(r"(.*)/_rels/[^/]+\.rels$", n)
            base = m.group(1) if m else ""
        root = parsed.get(n)
        if root is None:
            continue
        seen_ids: set[str] = set()
        for r in root.findall("{%s}Relationship" % NS_REL):
            rid = r.get("Id", "")
            if rid in seen_ids:
                err("Дублирующийся Id %s в %s" % (rid, n), "назначьте уникальные rId")
            seen_ids.add(rid)
            if r.get("TargetMode") == "External":
                continue
            t = norm(base, r.get("Target", ""))
            if t not in names:
                err("Битая ссылка в %s: %s -> %s" % (n, rid, t),
                    "восстановите цель или удалите отношение (clean после delete)")
            if r.get("Type") == REL_SLIDE and n == "ppt/_rels/presentation.xml.rels":
                slide_parts_in_rels.add(t)

    # 4. sldIdLst
    pres = parsed.get("ppt/presentation.xml")
    pres_rels = parsed.get("ppt/_rels/presentation.xml.rels")
    shown: set[str] = set()
    if pres is not None and pres_rels is not None:
        rid_to_slide = {r.get("Id"): norm("ppt", r.get("Target", ""))
                        for r in pres_rels.findall("{%s}Relationship" % NS_REL)
                        if r.get("Type") == REL_SLIDE}
        ids_seen: set[str] = set()
        for s in pres.findall("{%s}sldIdLst/{%s}sldId" % (NS_P, NS_P)):
            rid = s.get("{%s}id" % NS_R)
            sid = s.get("id")
            if sid in ids_seen:
                err("Дублирующийся sldId id=%s" % sid, "id слайдов должны быть уникальны (>=256)")
            ids_seen.add(sid)
            if rid not in rid_to_slide:
                err("sldId ссылается на несуществующий r:id %s" % rid,
                    "добавьте Relationship в presentation.xml.rels или удалите sldId")
            else:
                shown.add(rid_to_slide[rid])
        for t in sorted(slide_parts_in_rels - shown):
            warn("Слайд %s объявлен в rels, но не показан в <p:sldIdLst>" % t,
                 "добавьте sldId или удалите слайд (delete+clean)")
        for t in sorted(shown):
            if t not in names:
                err("Показанный слайд отсутствует в пакете: %s" % t, "восстановите файл слайда")

    # 6. Диаграммы: позиция подписей, недопустимая для типа (PowerPoint
    #    отклоняет файл целиком; python-pptx/LibreOffice — принимают)
    POS_OK = {
        "barChart": {"ctr", "inEnd", "inBase", "outEnd"},
        "bar3DChart": {"ctr", "inEnd", "inBase", "outEnd"},
        "lineChart": {"ctr", "t", "b", "l", "r", "bestFit"},
        "line3DChart": {"ctr", "t", "b", "l", "r", "bestFit"},
        "scatterChart": {"ctr", "t", "b", "l", "r", "bestFit"},
        "areaChart": set(),          # подписи значений не поддерживаются
        "area3DChart": set(),
        "pieChart": {"ctr", "inEnd", "outEnd", "bestFit"},
        "doughnutChart": {"ctr", "inEnd", "outEnd", "bestFit"},
    }
    NS_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
    chart_files = sorted(n for n in names
                         if n.startswith("ppt/") and re.search(r"chart\d*\.xml$", n))
    for n in chart_files:
        root = parsed.get(n)
        if root is None:
            continue
        for plot_kind, allowed in POS_OK.items():
            for plot in root.iter("{%s}%s" % (NS_C, plot_kind)):
                for dlbls in plot.iter("{%s}dLbls" % NS_C):
                    for pos in dlbls.iter("{%s}dLblPos" % NS_C):
                        val = pos.get("val", "")
                        if val not in allowed:
                            err("Диаграмма %s (%s): dLblPos val=%r недопустима — "
                                "PowerPoint отклонит файл" % (n, plot_kind, val),
                                "допустимые значения: %s; у area удалите dLbls/dLblPos, "
                                "у line/scatter используйте t/b/l/r/ctr/bestFit"
                                % (sorted(allowed) if allowed else "подписи не поддерживаются"))

    # 7. Контент слайдов
    slide_files = sorted(n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n))
    for n in slide_files:
        root = parsed.get(n)
        if root is None:
            continue
        full_text = []
        for t in root.iter("{%s}t" % NS_A):
            full_text.append(t.text or "")
        joined = " ".join(full_text)
        m = PLACEHOLDER_RE.search(joined)
        if m:
            warn("Похоже на незаполненный placeholder в %s: «%s»" % (n, m.group(0)),
                 "замените текст заглушки реальным содержанием")

    # 7. Типографика и геометрия
    deck_min = 999.0
    for n in slide_files:
        root = parsed.get(n)
        if root is None:
            continue
        mf = min_font_pt(root)
        if mf is not None:
            deck_min = min(deck_min, mf)
        if not (args.check_bounds or args.check_overlap or args.check_overflow):
            continue
        boxes = shape_boxes(root)
        if args.check_bounds and pres is not None:
            sz = pres.find("{%s}sldSz" % NS_P)
            if sz is not None:
                sw, sh = emu_in(sz.get("cx")), emu_in(sz.get("cy"))
                for x1, y1, x2, y2, txt, size, paras in boxes:
                    if x1 < -0.02 or y1 < -0.02 or x2 > sw + 0.02 or y2 > sh + 0.02:
                        warn("Фигура выходит за границы слайда (%s): «%s»" % (n, txt[:60]),
                             "уменьшите размер или сместите фигуру")
        if args.check_overlap:
            for a in range(len(boxes)):
                for b in range(a + 1, len(boxes)):
                    x1, y1, x2, y2, t1, s1, _ = boxes[a]
                    u1, v1, u2, v2, t2, s2, _ = boxes[b]
                    h1 = min(y2 - y1, estimate_height(t1, x2 - x1, s1))
                    h2 = min(v2 - v1, estimate_height(t2, u2 - u1, s2))
                    ox = min(x2, u2) - max(x1, u1)
                    oy = min(y1 + h1, v1 + h2) - max(y1, v1)
                    if ox > 0.02 and oy > 0.02 and ox * oy > 0.01:
                        warn("Пересечение текстовых блоков в %s: «%s» и «%s»" % (n, t1[:50], t2[:50]),
                             "разнесите блоки или сократите текст")
        if args.check_overflow:
            for x1, y1, x2, y2, txt, size, paras in boxes:
                if paras > 1 or not size:
                    continue
                need = estimate_height(txt, x2 - x1, size)
                if need > (y2 - y1) + 0.05:
                    warn("Возможное переполнение в %s: «%s» (нужно %.1f″, блок %.1f″)"
                         % (n, txt[:60], need, y2 - y1),
                         "увеличьте блок, уменьшите текст или кегль")

    for n in chart_files:
        root = parsed.get(n)
        if root is None:
            continue
        mf = min_font_pt(root)
        if mf is not None:
            deck_min = min(deck_min, mf)
        auto_on, title, series_names = chart_info(root)
        if auto_on and not title:
            warn("Диаграмма %s без явного title: PowerPoint подставит имя серии" % n,
                 "задайте chart.title или отключите авто-заголовок (has_title=False)")
        if title and series_names and title.strip() == series_names[0].strip():
            warn("Диаграмма %s: заголовок дублирует имя серии «%s»" % (n, title),
                 "задайте содержательный заголовок или отключите его")

    if deck_min < 999:
        if args.min_font is not None and deck_min < args.min_font:
            warn("Минимальный кегль %.1f pt ниже порога %.1f pt" % (deck_min, args.min_font),
                 "увеличьте кегль или соберите с --projector / --min-font")
        else:
            print("Минимальный кегль: %.1f pt" % deck_min)

    # Итог
    print("Проверено: %s (%d частей, %d слайдов)" % (args.deck, len(names), len(slide_files)))
    for w in warnings:
        print("ПРЕДУПРЕЖДЕНИЕ: %s" % w)
    for e in errors:
        print("ОШИБКА: %s" % e)
    failed = bool(errors) or (args.strict and bool(warnings))
    if not failed:
        print("OK: структурных дефектов не найдено%s" % (" (предупреждения есть)" if warnings else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
