#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пакетная хирургия .pptx на стандартной библиотеке: распаковка, дублирование
и удаление слайдов, очистка сирот, упаковка.

Использование:
    python from_template.py unpack  deck.pptx unpacked/
    python from_template.py list    deck.pptx            # слайды + макеты + превью текста
    python from_template.py layouts deck.pptx            # только макеты
    python from_template.py duplicate unpacked/ slide3.xml [--after slide5.xml]
    python from_template.py delete  unpacked/ slide7.xml [slide8.xml ...]
    python from_template.py clean   unpacked/            # убрать слайды вне <p:sldIdLst> и неиспользуемые медиа
    python from_template.py pack    unpacked/ out.pptx

Правила (как в anthropics/skills):
  * Все структурные операции (duplicate/delete/reorder) выполняйте ДО правки текста слайдов.
  * duplicate копирует ссылочные части (медиа, диаграммы) по ссылке: правка диаграммы
    на копии изменит и исходный слайд. Заметки докладчика (notesSlide) в копию не переносятся.
  * delete только убирает слайд из пакета и списков; затем обязательно clean.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET

NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"

REL_SLIDE = NS_R + "/slide"
REL_LAYOUT = NS_R + "/slideLayout"
REL_NOTES = NS_R + "/notesSlide"

CT_SLIDE = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"


def _register_ns(xml_bytes: bytes) -> None:
    """Регистрируем все префиксы файла, чтобы ET не переименовал их при записи."""
    for prefix, uri in re.findall(rb'xmlns:(\w+)="([^"]+)"', xml_bytes):
        try:
            ET.register_namespace(prefix.decode(), uri.decode())
        except ValueError:
            pass
    # префикс по умолчанию (редко, но встречается)
    m = re.search(rb'xmlns="([^"]+)"', xml_bytes)
    if m:
        ET.register_namespace("", m.group(1).decode())


def _parse(path: str) -> ET.Element:
    with open(path, "rb") as fh:
        data = fh.read()
    _register_ns(data)
    return ET.fromstring(data)


def _write(root: ET.Element, path: str, declaration: bool = True) -> None:
    data = ET.tostring(root, encoding="UTF-8", xml_declaration=declaration)
    with open(path, "wb") as fh:
        fh.write(data)


def _rels_path(part: str) -> str:
    d, f = os.path.dirname(part), os.path.basename(part)
    return os.path.join(d, "_rels", f + ".rels").replace("\\", "/")


def _all_parts(unpacked: str) -> list[str]:
    out = []
    for root, _d, files in os.walk(unpacked):
        for f in files:
            out.append(os.path.relpath(os.path.join(root, f), unpacked).replace("\\", "/"))
    return out


def _resolve(base_dir: str, target: str) -> str:
    """Нормализация относительного Target из .rels."""
    if target.startswith("/"):
        return target.lstrip("/")
    joined = os.path.normpath(os.path.join(base_dir, target)).replace("\\", "/")
    return joined


# ---------------------------------------------------------------- unpack/pack

def unpack(deck: str, outdir: str) -> None:
    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    with zipfile.ZipFile(deck) as zf:
        zf.extractall(outdir)
    print("Распаковано в %s" % outdir)


def pack(srcdir: str, out: str) -> None:
    srcdir = srcdir.rstrip("/\\")
    if os.path.abspath(out) == os.path.abspath(srcdir):
        raise SystemExit("Отказ: путь вывода совпадает с исходной папкой")
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        # [Content_Types].xml обязан быть первым
        ct = os.path.join(srcdir, "[Content_Types].xml")
        if os.path.exists(ct):
            zf.write(ct, "[Content_Types].xml")
        for root, _dirs, files in os.walk(srcdir):
            for name in sorted(files):
                full = os.path.join(root, name)
                arc = os.path.relpath(full, srcdir).replace("\\", "/")
                if arc == "[Content_Types].xml":
                    continue
                zf.write(full, arc)
    print("Упаковано: %s" % out)


# ---------------------------------------------------------------- list

def _slide_list(unpacked: str) -> list[str]:
    """Пути слайдов в порядке показа (относительно корня пакета)."""
    pres = _parse(os.path.join(unpacked, "ppt", "presentation.xml"))
    rels = _parse(os.path.join(unpacked, "ppt", "_rels", "presentation.xml.rels"))
    rid = {r.get("Id"): r.get("Target") for r in rels.findall("{%s}Relationship" % NS_REL)}
    out = []
    for s in pres.findall("{%s}sldIdLst/{%s}sldId" % (NS_P, NS_P)):
        t = rid.get(s.get("{%s}id" % NS_R), "")
        t = t.lstrip("/")
        if not t.startswith("ppt/"):
            t = "ppt/" + t
        out.append(t)
    return out


def _layout_of(unpacked: str, slide_part: str) -> str:
    rels_file = os.path.join(unpacked, _rels_path(slide_part))
    if not os.path.exists(rels_file):
        return ""
    rels = _parse(rels_file)
    for r in rels.findall("{%s}Relationship" % NS_REL):
        if r.get("Type") == REL_LAYOUT:
            m = re.search(r"(slideLayout\d+)\.xml", r.get("Target", ""))
            if m:
                return m.group(1)
    return ""


def _layout_names(unpacked: str) -> dict[str, str]:
    names = {}
    lay_dir = os.path.join(unpacked, "ppt", "slideLayouts")
    if not os.path.isdir(lay_dir):
        return names
    for f in os.listdir(lay_dir):
        if re.match(r"slideLayout\d+\.xml$", f):
            root = _parse(os.path.join(lay_dir, f))
            name = root.get("name") or root.get("matchingName") or ""
            if not name:
                csld = root.find("{%s}cSld" % NS_P)
                if csld is not None:
                    name = csld.get("name", "") or ""
            names[f[:-4]] = name
    return names


def _preview(unpacked: str, slide_part: str, limit: int = 110) -> str:
    root = _parse(os.path.join(unpacked, slide_part))
    chunks = [t.text for t in root.iter("{%s}t" % NS_A) if t.text]
    return (" ".join(chunks))[:limit].replace("\n", " ")


def cmd_list(unpacked_or_deck: str, layouts_only: bool) -> None:
    is_dir = os.path.isdir(unpacked_or_deck)
    if not is_dir:
        tmp = unpacked_or_deck + ".~tmp_unpack"
        unpack(unpacked_or_deck, tmp)
        unpacked = tmp
    else:
        unpacked = unpacked_or_deck
    try:
        names = _layout_names(unpacked)
        if layouts_only:
            for k in sorted(names, key=lambda x: int(re.sub(r"\D", "", x))):
                print("%-16s %s" % (k, names[k]))
            return
        for i, sp in enumerate(_slide_list(unpacked), 1):
            lay = _layout_of(unpacked, sp)
            print("%2d. %-24s [%s] %s" % (
                i, os.path.basename(sp),
                ("%s: %s" % (lay, names.get(lay, "?"))) if lay else "-",
                _preview(unpacked, sp)))
    finally:
        if not is_dir and os.path.isdir(unpacked):
            shutil.rmtree(unpacked, ignore_errors=True)


# ---------------------------------------------------------------- duplicate

def _next_free(parts: list[str], pattern: str, fmt: str) -> str:
    used = set()
    for p in parts:
        m = re.search(pattern, p.replace("\\", "/"))
        if m:
            used.add(int(m.group(1)))
    n = 1
    while n in used:
        n += 1
    return fmt % n


def cmd_duplicate(unpacked: str, source: str, after: str | None) -> str:
    src = source if source.startswith("ppt/") else "ppt/slides/" + source
    src_file = os.path.join(unpacked, src)
    if not os.path.exists(src_file):
        raise SystemExit("Не найден слайд: %s" % src)

    def all_files() -> list[str]:
        return _all_parts(unpacked)

    files = all_files()
    new_part = _next_free(files, r"ppt/slides/slide(\d+)\.xml$", "ppt/slides/slide%d.xml")
    new_abs = os.path.join(unpacked, new_part)
    shutil.copyfile(src_file, new_abs)

    # копия .rels без заметок докладчика
    src_rels = os.path.join(unpacked, _rels_path(src))
    new_rels = os.path.join(unpacked, _rels_path(new_part))
    dropped_notes = False
    if os.path.exists(src_rels):
        rels = _parse(src_rels)
        for r in list(rels.findall("{%s}Relationship" % NS_REL)):
            if r.get("Type") == REL_NOTES:
                rels.remove(r)
                dropped_notes = True
        os.makedirs(os.path.dirname(new_rels), exist_ok=True)
        _write(rels, new_rels)

    # [Content_Types].xml: Override для новой части
    ct_file = os.path.join(unpacked, "[Content_Types].xml")
    ct = _parse(ct_file)
    ov = ET.SubElement(ct, "{%s}Override" % NS_CT)
    ov.set("PartName", "/" + new_part)
    ov.set("ContentType", CT_SLIDE)
    _write(ct, ct_file)

    # presentation.xml.rels: новое отношение
    pres_rels_file = os.path.join(unpacked, "ppt", "_rels", "presentation.xml.rels")
    pres_rels = _parse(pres_rels_file)
    rids = [int(m.group(1)) for r in pres_rels.findall("{%s}Relationship" % NS_REL)
            for m in [re.match(r"rId(\d+)$", r.get("Id", ""))] if m]
    new_rid = "rId%d" % (max(rids) + 1 if rids else 1)
    rel = ET.SubElement(pres_rels, "{%s}Relationship" % NS_REL)
    rel.set("Id", new_rid)
    rel.set("Type", REL_SLIDE)
    rel.set("Target", "slides/" + os.path.basename(new_part))
    _write(pres_rels, pres_rels_file)

    # presentation.xml: sldId в нужную позицию
    pres_file = os.path.join(unpacked, "ppt", "presentation.xml")
    pres = _parse(pres_file)
    lst = pres.find("{%s}sldIdLst" % NS_P)
    ids = [int(s.get("id")) for s in lst.findall("{%s}sldId" % NS_P)]
    new_id = str(max(ids) + 1 if ids else 256)
    pos = len(list(lst))
    if after:
        after_part = after if after.startswith("ppt/") else "ppt/slides/" + after
        rels = _parse(pres_rels_file)
        after_rid = None
        for r in rels.findall("{%s}Relationship" % NS_REL):
            if r.get("Type") == REL_SLIDE and _resolve("ppt", r.get("Target", "")) == after_part:
                after_rid = r.get("Id")
        if after_rid is not None:
            for i, s in enumerate(lst.findall("{%s}sldId" % NS_P)):
                if s.get("{%s}id" % NS_R) == after_rid:
                    pos = i + 1
                    break
        else:
            print("Предупреждение: --after %s не найден, добавляю в конец" % after)
    el = ET.Element("{%s}sldId" % NS_P)
    el.set("id", new_id)
    el.set("{%s}id" % NS_R, new_rid)
    lst.insert(pos, el)
    _write(pres, pres_file)

    msg = "Создан %s из %s (позиция %d, r:id %s, sldId %s)" % (new_part, src, pos + 1, new_rid, new_id)
    if dropped_notes:
        msg += "; заметки докладчика не копировались"
    print(msg)
    print("Внимание: медиа/диаграммы разделены между слайдами по ссылке.")
    return new_part


# ---------------------------------------------------------------- delete/clean

def cmd_delete(unpacked: str, slides: list[str]) -> None:
    pres_file = os.path.join(unpacked, "ppt", "presentation.xml")
    pres_rels_file = os.path.join(unpacked, "ppt", "_rels", "presentation.xml.rels")
    targets = {("ppt/slides/" + s) if not s.startswith("ppt/") else s for s in slides}

    pres_rels = _parse(pres_rels_file)
    rid_to_target = {}
    for r in pres_rels.findall("{%s}Relationship" % NS_REL):
        if r.get("Type") == REL_SLIDE:
            rid_to_target[r.get("Id")] = _resolve("ppt", r.get("Target", ""))
    drop_rids = {rid for rid, t in rid_to_target.items() if t in targets}

    pres = _parse(pres_file)
    lst = pres.find("{%s}sldIdLst" % NS_P)
    removed = 0
    for s in list(lst.findall("{%s}sldId" % NS_P)):
        if s.get("{%s}id" % NS_R) in drop_rids:
            lst.remove(s)
            removed += 1
    _write(pres, pres_file)

    for r in list(pres_rels.findall("{%s}Relationship" % NS_REL)):
        if r.get("Id") in drop_rids:
            pres_rels.remove(r)
    _write(pres_rels, pres_rels_file)
    print("Удалено из <p:sldIdLst>: %d. Запустите clean для удаления файлов." % removed)


def cmd_clean(unpacked: str) -> None:
    live = set(_slide_list(unpacked))
    removed = 0
    slides_dir = os.path.join(unpacked, "ppt", "slides")
    for f in sorted(os.listdir(slides_dir)):
        if not re.match(r"slide\d+\.xml$", f):
            continue
        part = "ppt/slides/" + f
        if part in live:
            continue
        os.remove(os.path.join(slides_dir, f))
        rels = os.path.join(slides_dir, "_rels", f + ".rels")
        if os.path.exists(rels):
            os.remove(rels)
        # Override в [Content_Types].xml
        ct_file = os.path.join(unpacked, "[Content_Types].xml")
        ct = _parse(ct_file)
        for ov in list(ct.findall("{%s}Override" % NS_CT)):
            if ov.get("PartName") == "/" + part:
                ct.remove(ov)
        _write(ct, ct_file)
        removed += 1

    # неиспользуемые медиа: собираем все Target из всех .rels
    referenced: set[str] = set()
    for root, _d, files in os.walk(unpacked):
        for f in files:
            if not f.endswith(".rels"):
                continue
            full = os.path.join(root, f)
            base_dir = os.path.relpath(os.path.dirname(os.path.dirname(full)), unpacked).replace("\\", "/")
            rels = _parse(full)
            for r in rels.findall("{%s}Relationship" % NS_REL):
                if r.get("TargetMode") == "External":
                    continue
                referenced.add(_resolve(base_dir, r.get("Target", "")))

    # осиротевшие заметки докладчика: notesSlide, указывающий на удалённый слайд
    notes_dir = os.path.join(unpacked, "ppt", "notesSlides")
    notes_removed = 0
    if os.path.isdir(notes_dir):
        existing = {p.replace("\\", "/") for p in _all_parts(unpacked)}
        for f in sorted(os.listdir(notes_dir)):
            if not re.match(r"notesSlide\d+\.xml$", f):
                continue
            rels_file = os.path.join(notes_dir, "_rels", f + ".rels")
            orphan = True
            if os.path.exists(rels_file):
                rels = _parse(rels_file)
                for r in rels.findall("{%s}Relationship" % NS_REL):
                    if r.get("Type") == "%s/slide" % NS_R and \
                            _resolve("ppt/notesSlides", r.get("Target", "")) in existing:
                        orphan = False
                        break
            if orphan:
                part = "ppt/notesSlides/" + f
                os.remove(os.path.join(notes_dir, f))
                if os.path.exists(rels_file):
                    os.remove(rels_file)
                ct_file = os.path.join(unpacked, "[Content_Types].xml")
                ct = _parse(ct_file)
                for ov in list(ct.findall("{%s}Override" % NS_CT)):
                    if ov.get("PartName") == "/" + part:
                        ct.remove(ov)
                _write(ct, ct_file)
                notes_removed += 1

    media_dir = os.path.join(unpacked, "ppt", "media")
    orphaned = 0
    if os.path.isdir(media_dir):
        for f in sorted(os.listdir(media_dir)):
            part = "ppt/media/" + f
            if part not in referenced:
                os.remove(os.path.join(media_dir, f))
                orphaned += 1
    print("clean: удалено слайдов %d, заметок %d, осиротевших медиа %d" % (removed, notes_removed, orphaned))


# ---------------------------------------------------------------- main

def main() -> int:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("unpack"); p.add_argument("deck"); p.add_argument("outdir")
    p = sub.add_parser("pack"); p.add_argument("srcdir"); p.add_argument("out")
    p = sub.add_parser("list"); p.add_argument("path")
    p = sub.add_parser("layouts"); p.add_argument("path")
    p = sub.add_parser("duplicate"); p.add_argument("unpacked"); p.add_argument("source")
    p.add_argument("--after", default=None)
    p = sub.add_parser("delete"); p.add_argument("unpacked"); p.add_argument("slides", nargs="+")
    p = sub.add_parser("clean"); p.add_argument("unpacked")

    a = ap.parse_args()
    if a.cmd == "unpack":
        unpack(a.deck, a.outdir)
    elif a.cmd == "pack":
        pack(a.srcdir, a.out)
    elif a.cmd == "list":
        cmd_list(a.path, layouts_only=False)
    elif a.cmd == "layouts":
        cmd_list(a.path, layouts_only=True)
    elif a.cmd == "duplicate":
        cmd_duplicate(a.unpacked, a.source, a.after)
    elif a.cmd == "delete":
        cmd_delete(a.unpacked, a.slides)
    elif a.cmd == "clean":
        cmd_clean(a.unpacked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
