#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка строгой отчётной/научной презентации PPTX по JSON-спецификации.

Зависимость: python-pptx  (pip install python-pptx)

Использование:
    python build_deck.py spec.json -o report.pptx [--brand opi|harness] [--lint]
    python build_deck.py spec.json --projector --min-font 14   # проекторный режим
    python build_deck.py --example-spec > spec.json             # шаблон спецификации

Типы слайдов: title, section, summary, content, kpi, chart, table, cards,
matrix, timeline, closing, refs. Стиль — формальный, плотность высокая,
данные — нативными диаграммами и таблицами PowerPoint.

Спецификация (JSON):
{
  "brand": "opi",                      // или "harness"; CLI --brand переопределяет
  "min_font": 14,                      // минимальный кегль (для проектора — 14)
  "font_scale": 1.0,                   // множитель кеглей
  "projector": true,                   // пресет: min 14 pt + масштаб 1.12
  "show_footer": true, "show_page": true,
  "title_size": 25, "source_size": 9,
  "meta": {"author": "...", "role": "...", "org": "...", "date": "..."},
  "footer": "Наименование отчёта",     // нижний колонтитул на каждом слайде
  "slides": [
    {"type": "title", "kicker": "Аналитический отчёт", "title": "...", "subtitle": "..."},
    {"type": "section", "title": "...", "note": "..."},
    {"type": "summary", "title": "...", "columns": 2,
     "points": [{"head": "...", "text": "..."}]},
    {"type": "content", "title": "...", "lead": "...", "body_size": 12.5,
     "columns": [["пункт 1", "пункт 2"], ["пункт 3"]],  // 1 или 2 колонки
     "stat": {"value": "65 %", "label": "...", "height": 2.4},  // панель справа
     "source": "Источник: ..."},
    {"type": "kpi", "title": "...", "cards": [{"value": "-80 %", "label": "...", "delta": "..."}],
     "note": "...", "card_height": 2.6, "source": "..."},
    {"type": "chart", "title": "...", "takeaway": "...",
     "chart": {"kind": "col", "title": "...", "categories": [...],
               "series": [{"name": "...", "values": [...]}],
               "x_title": "...", "y_title": "...", "number_format": "0 %"},
     "bullets": ["вывод 1", "вывод 2"], "source": "..."},
    {"type": "table", "title": "...", "headers": [...], "rows": [[...]],
     "col_widths": [2, 1, 1], "font_size": 10.5, "align": "top",
     "bullets": [...], "source": "..."},
    {"type": "cards", "title": "...", "band": "Вывод под карточками",
     "columns": [{"num": "1", "head": "...", "kicker": "...",
                  "bullets": ["..."], "footer": "..."}]},
    {"type": "matrix", "title": "...", "headers": [...], "rows": [[...]],
     "col_widths": [1, 1, 1], "font_size": 10.5},
    {"type": "timeline", "title": "...", "align": "top",
     "milestones": [{"period": "2026", "text": "..."}], "source": "..."},
    {"type": "closing", "title": "Выводы и рекомендации",
     "conclusions": ["..."], "recommendations": ["..."]},
    {"type": "refs", "title": "Источники", "items": ["Автор. Название. — 2026."]}
  ]
}
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
from functools import lru_cache

try:  # опционально: точное измерение строк для динамических заголовков
    from PIL import ImageFont
except Exception:  # pragma: no cover - среда без Pillow
    ImageFont = None

_PPTX_SYMBOLS = (
    "Presentation", "CategoryChartData", "XyChartData", "RGBColor",
    "XL_CHART_TYPE", "XL_LEGEND_POSITION", "XL_LABEL_POSITION", "XL_TICK_MARK",
    "MSO_SHAPE", "PP_ALIGN", "MSO_ANCHOR", "MSO_AUTO_SIZE", "qn", "Inches", "Pt",
)


def _import_pptx() -> None:
    """Ленивая загрузка python-pptx в глобальное пространство модуля."""
    try:
        from pptx import Presentation
        from pptx.chart.data import CategoryChartData, XyChartData
        from pptx.dml.color import RGBColor
        from pptx.enum.chart import (XL_CHART_TYPE, XL_LEGEND_POSITION,
                                     XL_LABEL_POSITION, XL_TICK_MARK)
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
        from pptx.oxml.ns import qn
        from pptx.util import Inches, Pt
    except ImportError:
        print("Не установлен python-pptx. Выполните: pip install python-pptx",
              file=sys.stderr)
        raise SystemExit(3)
    g = globals()
    g.update({name: value for name, value in locals().items() if name in _PPTX_SYMBOLS})

# ------------------------------------------------------------------ метрики текста

_FONT_FILES = {
    ("cambria", False): ("cambria.ttc", "cambria.ttf", "Cambria.ttf"),
    ("cambria", True): ("cambriab.ttf", "Cambria Bold.ttf"),
    ("calibri", False): ("calibri.ttf", "Calibri.ttf"),
    ("calibri", True): ("calibrib.ttf", "Calibri Bold.ttf"),
    ("arial", False): ("arial.ttf", "Arial.ttf"),
    ("arial", True): ("arialbd.ttf", "Arial Bold.ttf"),
}
_FONT_DIRS = [
    os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
    "/usr/share/fonts/truetype/msttcorefonts",
    "/usr/share/fonts/truetype/microsoft",
    "/Library/Fonts",
    os.path.expanduser("~/Library/Fonts"),
]


@lru_cache(maxsize=32)
def _font_path(name: str, bold: bool) -> str | None:
    if ImageFont is None:
        return None
    base = (name or "").split()[0].lower()
    for candidate in _FONT_FILES.get((base, bold), ()) + _FONT_FILES.get((base, False), ()):
        for folder in _FONT_DIRS:
            path = os.path.join(folder, candidate)
            if os.path.exists(path):
                return path
    return None


def measure_lines(text: str, size_pt: float, width_in: float,
                  font_name: str, bold: bool = False, safety: float = 0.96) -> int:
    """Число строк с переносом по словам. Pillow — точно, иначе эвристика."""
    text = (text or "").strip()
    if not text or width_in <= 0:
        return 1
    # запас: PowerPoint переносит раньше, чем «идеальная» метрика
    width_in *= safety
    path = _font_path(font_name, bold)
    if path:
        try:
            fnt = ImageFont.truetype(path, max(8, int(round(size_pt * 4))))
            def width(part: str) -> float:
                return fnt.getlength(part) / 4.0 / 72.0
            lines, current = 1, ""
            for word in text.split():
                trial = word if not current else current + " " + word
                if width(trial) <= width_in:
                    current = trial
                elif current:
                    lines += 1
                    current = word
                else:
                    lines += max(0, int(width(word) // width_in))
                    current = word
            return lines
        except Exception:
            pass
    cpl = max(10, int(width_in / (size_pt * 0.0075)))
    return max(1, math.ceil(len(text) / cpl))


# ------------------------------------------------------------------ бренды

BRANDS = {
    # Отчёт о результатах НИР (по шаблону ОПИ19.05): компактный холст, сине-зелёная гамма
    "opi": {
        "size": (10.0, 5.625),
        "bg_dark": "002060", "bg_light": "FFFFFF", "panel": "E5E9F0", "panel2": "F4F7FC",
        "ink": "002060", "ink2": "1F3864", "text": "262B3A", "muted": "64748B",
        "accent": "1B6B3A", "accent2": "297FD5", "on_dark": "FFFFFF", "on_dark_muted": "C9D6F5",
        "series": ["002060", "297FD5", "5AA2AE", "1B6B3A", "7F8FA9", "9D90A0"],
        "head_font": "Calibri", "body_font": "Calibri",
    },
    # Аналитика для руководства (по шаблону Harness/AI OS): широкий холст, тёмно-синий + терракота
    "harness": {
        "size": (13.333, 7.5),
        "bg_dark": "1B1E2B", "bg_light": "FFFFFF", "panel": "E7E9F2", "panel2": "EAF1FB",
        "ink": "1E2761", "ink2": "2C3A85", "text": "1B1E2B", "muted": "5B5F6E",
        "accent": "B85042", "accent2": "7C9885", "on_dark": "FFFFFF", "on_dark_muted": "CADCFC",
        "series": ["1E2761", "B85042", "7C9885", "5A6B87", "B8935A", "2C3A85"],
        "head_font": "Cambria", "body_font": "Calibri",
    },
}

EXAMPLE = {
    "brand": "opi",
    "meta": {"author": "Иванов И. И.", "role": "Руководитель направления",
             "org": "Отдел перспективных исследований", "date": "Октябрь 2026"},
    "footer": "Аналитический отчёт — для внутреннего использования",
    "slides": [
        {"type": "title", "kicker": "Аналитический отчёт",
         "title": "Результаты исследования и рекомендации руководству",
         "subtitle": "Ключевые показатели, оценка рисков, план внедрения"},
        {"type": "summary", "title": "Отчёт построен вокруг четырёх тезисов",
         "points": [
             {"head": "Результат подтверждён", "text": "Метрики второго этапа соответствуют плановым значениям."},
             {"head": "Эффект измерим", "text": "Сокращение трудоёмкости составило 80 % на контрольной выборке."},
             {"head": "Риски управляемы", "text": "Основные ограничения этапа сняты в плане третьего квартала."},
             {"head": "Готовность к масштабированию", "text": "Архитектура решения допускает тиражирование на смежные задачи."}]},
        {"type": "kpi", "title": "Ключевые показатели этапа соответствуют плану",
         "cards": [{"value": "96 %", "label": "Успешность обработки", "delta": "+4 п.п. к плану"},
                   {"value": "-80 %", "label": "Трудоёмкость подготовки"},
                   {"value": "12", "label": "Внедрённых модулей"}],
         "source": "Источник: внутренний протокол испытаний № 14 от 09.2026"},
        {"type": "chart", "title": "Трудоёмкость снижена на всех переделах",
         "takeaway": "Наибольший эффект достигнут на этапе подготовки геометрии.",
         "chart": {"kind": "col", "categories": ["Геометрия", "Сетка", "Расчёт", "Постобработка"],
                   "series": [{"name": "Было, ч", "values": [40, 12, 20, 8]},
                              {"name": "Стало, ч", "values": [8, 6, 18, 3]}],
                   "y_title": "Часы"},
         "bullets": ["Подготовка геометрии: сокращение в 5 раз",
                    "Постобработка: сокращение в 2,7 раза"],
         "source": "Источник: результаты замеров, сентябрь 2026"},
        {"type": "closing", "title": "Выводы и рекомендации",
         "conclusions": ["Цели этапа достигнуты, метрики подтверждены испытаниями."],
         "recommendations": ["Одоб переход к третьему этапу с финансированием по смете."]},
        {"type": "refs", "title": "Источники",
         "items": ["Внутренний протокол испытаний № 14. — 2026."]},
    ],
}


# ------------------------------------------------------------------ утилиты

class Deck:
    def __init__(self, brand: str, spec: dict):
        b = dict(BRANDS[brand])
        b.update(spec.get("brand_overrides", {}))
        if spec.get("fonts"):
            b["head_font"] = spec["fonts"].get("heading", b["head_font"])
            b["body_font"] = spec["fonts"].get("body", b["body_font"])
        self.b = b
        self.meta = spec.get("meta", {})
        self.footer = spec.get("footer", "")
        self.show_footer = bool(spec.get("show_footer", True))
        self.show_page = bool(spec.get("show_page", True))
        self.min_font = float(spec.get("min_font", 9.0))
        self.font_scale = float(spec.get("font_scale", 1.0))
        self.projector = bool(spec.get("projector", False))
        if self.projector:
            self.min_font = max(self.min_font, 14.0)
            if "font_scale" not in spec:
                self.font_scale *= 1.12
        self.title_size = float(spec.get("title_size", 25.0))
        self.source_size = float(spec.get("source_size", 9.0))
        self.prs = Presentation()
        sw, sh = b["size"]
        self.prs.slide_width = Inches(sw)
        self.prs.slide_height = Inches(sh)
        self.SW, self.SH = sw, sh
        self.u = sw / 13.333                      # масштабный коэффициент
        self.M = 0.55 * self.u + 0.12             # поле страницы, дюймы
        self.blank = self.prs.slide_layouts[6]
        self.page = 0
        self.warnings: list[str] = []

    # -- базовые примитивы -----------------------------------------------
    def pt(self, base: float) -> float:
        """Кегль с учётом холста, масштаба и минимального размера."""
        raw = base * (0.55 + 0.45 * self.u) * self.font_scale
        return max(self.min_font, round(raw, 1))

    def lines(self, text: str, size_pt: float, width_in: float,
              font: str | None = None, bold: bool = False, safety: float = 0.96) -> int:
        return measure_lines(text, size_pt, width_in,
                             font or self.b["body_font"], bold, safety)

    def new(self, dark: bool = False):
        s = self.prs.slides.add_slide(self.blank)
        bg = s.background.fill
        bg.solid()
        bg.fore_color.rgb = RGBColor.from_string(self.b["bg_dark"] if dark else self.b["bg_light"])
        self.page += 1
        return s

    def rect(self, s, x, y, w, h, fill, line=None, shadow=False, round_=False, oval=False):
        if oval:
            shape_type = MSO_SHAPE.OVAL
        elif round_:
            shape_type = MSO_SHAPE.ROUNDED_RECTANGLE
        else:
            shape_type = MSO_SHAPE.RECTANGLE
        sp = s.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
        if round_:
            try:
                sp.adjustments[0] = 0.045
            except Exception:
                pass
        if fill is None:
            sp.fill.background()
        else:
            sp.fill.solid()
            sp.fill.fore_color.rgb = RGBColor.from_string(fill)
        if line is None:
            sp.line.fill.background()
        else:
            sp.line.color.rgb = RGBColor.from_string(line)
            sp.line.width = Pt(0.75)
        sp.shadow.inherit = False
        return sp

    def text(self, s, x, y, w, h, runs, size=14, color=None, bold=False, font=None,
             align=None, anchor=None, leading=1.0, space_after=0,
             wrap=True, italic=False, raw_size=False):
        """runs: str | [{"t": ..., "b": ..., "i": ..., "c": ..., "size": ...}, ...] | список таких (абзацы)."""
        if align is None:
            align = PP_ALIGN.LEFT
        if anchor is None:
            anchor = MSO_ANCHOR.TOP
        base_size = size if raw_size else self.pt(size)
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = wrap
        tf.auto_size = MSO_AUTO_SIZE.NONE
        tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        color = color or self.b["text"]
        font = font or self.b["body_font"]
        if isinstance(runs, str):
            runs = [runs]
        if runs and isinstance(runs[0], dict):
            runs = [runs]
        first = True
        for para in runs:
            p = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            p.alignment = align
            p.line_spacing = leading
            if space_after:
                p.space_after = Pt(space_after)
            if isinstance(para, str):
                para = [{"t": para}]
            for rs in para:
                r = p.add_run()
                r.text = rs.get("t", "")
                r.font.size = Pt(rs.get("size", base_size))
                r.font.bold = rs.get("b", bold)
                r.font.italic = rs.get("i", italic)
                r.font.name = rs.get("font", font)
                r.font.color.rgb = RGBColor.from_string(rs.get("c", color))
        return tb

    def bullets(self, s, x, y, w, h, items, size=14, color=None, bold_lead=True,
                space_after=6, numbered=False, raw_size=False):
        """Список с настоящими маркерами (buChar/buAutoNum) и висячим отступом."""
        base_size = size if raw_size else self.pt(size)
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.auto_size = MSO_AUTO_SIZE.NONE
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        color = color or self.b["text"]
        for i, item in enumerate(items):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.line_spacing = 1.06
            p.space_after = Pt(self.pt(space_after))
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", str(int(0.22 * 914400 * self.u)))
            pPr.set("indent", str(int(-0.22 * 914400 * self.u)))
            if numbered:
                num = pPr.makeelement(qn("a:buAutoNum"), {"type": "arabicPeriod"})
            else:
                fnt = pPr.makeelement(qn("a:buFont"), {"typeface": "Arial"})
                ch = pPr.makeelement(qn("a:buChar"), {"char": "—"})
                pPr.append(fnt)
                num = ch
            pPr.append(num)
            pieces = [{"t": item}] if isinstance(item, str) else item
            for rs in pieces:
                r = p.add_run()
                r.text = rs.get("t", "")
                r.font.size = Pt(rs.get("size", base_size))
                r.font.name = self.b["body_font"]
                r.font.bold = rs.get("b", False) and bold_lead
                if rs.get("b") and not bold_lead:
                    r.font.bold = True
                r.font.color.rgb = RGBColor.from_string(rs.get("c", color))
        return tb

    # -- хроматика слайда --------------------------------------------------
    def chrome(self, s, dark: bool, source: str | None = None, page_number: bool = True):
        muted = self.b["on_dark_muted"] if dark else self.b["muted"]
        size = self.pt(self.source_size)
        y = self.SH - max(self.M * 0.62, size * 1.4 / 72.0 + 0.08)
        if self.footer and self.show_footer:
            self.text(s, self.M, y, self.SW * 0.7, 0.3, self.footer,
                      size=size, color=muted, raw_size=True)
        if source:
            sy = y - max(0.3, size * 1.2 / 72.0 + 0.1)
            self.text(s, self.M, sy, self.SW - 2 * self.M, 0.3, source,
                      size=size, color=muted, italic=True, raw_size=True)
        if page_number and self.show_page:
            self.text(s, self.SW - self.M - 0.8, y, 0.8, 0.3, str(self.page),
                      size=self.pt(10), color=muted, align=PP_ALIGN.RIGHT)

    def slide_title(self, s, title: str, kicker: str | None = None, dark: bool = False,
                    size: float | None = None):
        ink = self.b["on_dark"] if dark else self.b["ink"]
        mut = self.b["on_dark_muted"] if dark else self.b["muted"]
        y = self.M * 0.85
        if kicker:
            self.text(s, self.M, y, self.SW - 2 * self.M, 0.3, kicker.upper(),
                      size=11, color=self.b["accent"] if not dark else mut,
                      bold=True, font=self.b["body_font"])
            y += self.pt(11) * 1.25 / 72.0 + 0.12
        size_eff = self.pt(size or self.title_size)
        lh = size_eff * 1.25 / 72.0               # высота строки заголовка, дюймы
        lines = self.lines(title, size_eff, self.SW - 2 * self.M - 0.02,
                           self.b["head_font"], bold=True, safety=0.88)
        cpl_floor = max(20, int((self.SW - 2 * self.M) / (size_eff * 0.0072)))
        lines = max(lines, math.ceil(len(title) / cpl_floor))
        self.text(s, self.M, y, self.SW - 2 * self.M, lines * lh + 0.1, title,
                  size=size_eff, color=ink, bold=True, font=self.b["head_font"],
                  leading=1.02, raw_size=True)
        return y + lines * lh + (0.38 if lines > 1 else 0.18)

    # -- типы слайдов -------------------------------------------------------
    def s_title(self, d):
        s = self.new(dark=True)
        b = self.b
        y = self.SH * 0.16
        if d.get("kicker"):
            self.text(s, self.M + 0.1, y, self.SW - 2 * self.M, 0.35, d["kicker"].upper(),
                      size=12, color=b["on_dark_muted"], bold=True)
            y += 0.42 * self.u + 0.12
        self.text(s, self.M + 0.1, y, self.SW - 2 * self.M - 0.2, self.SH * 0.34, d["title"],
                  size=34, color=b["on_dark"], bold=True, font=b["head_font"], leading=1.04)
        title_eff = self.pt(34)
        title_lines = self.lines(d["title"], title_eff, self.SW - 2 * self.M - 0.3,
                                 b["head_font"], bold=True, safety=1.0)
        y2 = y + min(self.SH * 0.42, title_lines * title_eff * 1.04 / 72.0 + 0.35)
        if d.get("subtitle"):
            self.text(s, self.M + 0.1, y2 + 0.1, self.SW * 0.75, 0.8, d["subtitle"],
                      size=15, color=b["on_dark_muted"], leading=1.15)
        meta = " · ".join(x for x in [
            self.meta.get("author"), self.meta.get("role"),
            self.meta.get("org"), self.meta.get("date")] if x)
        if meta:
            self.text(s, self.M + 0.1, self.SH - self.M - 0.55, self.SW - 2 * self.M, 0.5,
                      meta, size=11, color=b["on_dark_muted"], leading=1.2)
        self.chrome(s, dark=True, page_number=False)

    def s_section(self, d):
        s = self.new(dark=True)
        b = self.b
        num = d.get("number") or ("%02d" % self.page)
        self.text(s, self.M + 0.1, self.SH * 0.24, 2.2, 1.2, str(num),
                  size=54, color=b["accent2"] if b["accent2"] else b["on_dark_muted"],
                  bold=True, font=b["head_font"])
        self.text(s, self.M + 0.1, self.SH * 0.42, self.SW * 0.8, 2.2, d["title"],
                  size=30, color=b["on_dark"], bold=True, font=b["head_font"], leading=1.05)
        if d.get("note"):
            title_eff = self.pt(30)
            title_lines = self.lines(d["title"], title_eff, self.SW * 0.8 - 0.02,
                                     b["head_font"], bold=True, safety=0.9)
            cpl_floor = max(16, int((self.SW * 0.8) / (title_eff * 0.0072)))
            title_lines = max(title_lines, math.ceil(len(d["title"]) / cpl_floor))
            note_y = self.SH * 0.42 + title_lines * title_eff * 1.1 / 72.0 + 0.38
            self.text(s, self.M + 0.1, note_y, self.SW * 0.7, 1.0, d["note"], size=13,
                      color=b["on_dark_muted"], leading=1.2)
        self.chrome(s, dark=True)

    def s_summary(self, d):
        s = self.new()
        b = self.b
        y = self.slide_title(s, d["title"], d.get("kicker", "Ключевые положения"))
        pts = d.get("points", [])
        if len(pts) > 6:
            self.warnings.append("summary: более 6 тезисов (%d) — разделите на два слайда" % len(pts))
        cols = int(d.get("columns") or (2 if len(pts) > 2 else 1))
        if cols not in (1, 2, 3):
            self.warnings.append("summary: columns=%r, допустимо 1–3; взято 2" % cols)
            cols = 2
        gap = 0.22 * self.u + 0.06
        cw = (self.SW - 2 * self.M - gap * (cols - 1)) / cols
        avail_h = self.SH - y - self.M * (1.9 if d.get("source") else 1.55)
        rows = (len(pts) + cols - 1) // cols
        ch = (avail_h - gap * (rows - 1)) / rows
        for i, p in enumerate(pts):
            full = cols > 1 and i == len(pts) - 1 and len(pts) % cols == 1
            card_w = cw * cols + gap * (cols - 1) if full else cw
            cx = self.M if full else self.M + (i % cols) * (cw + gap)
            cy = y + (i // cols) * (ch + gap)
            self.rect(s, cx, cy, card_w, ch, b["panel2"] if i % 2 else b["panel"], round_=True)
            pad = 0.16 * self.u + 0.08
            if isinstance(p, str):
                p = {"head": "", "text": p}
            tx = cx + pad + 0.42 * self.u + 0.12
            tw = card_w - (tx - cx) - pad
            paras = []
            if p.get("head"):
                paras.append([{"t": p["head"], "b": True, "size": self.pt(13.5),
                               "c": b["ink"], "font": b["body_font"]}])
            paras.append([{"t": p["text"], "size": self.pt(11.5), "c": b["text"]}])
            need = (self.lines(p.get("head", ""), self.pt(13.5), tw, bold=True) * self.pt(13.5) * 1.14 / 72.0
                    + self.lines(p.get("text", ""), self.pt(11.5), tw) * self.pt(11.5) * 1.14 / 72.0 + 0.28)
            if need > ch - 0.05:
                self.warnings.append("summary: тезис %d не помещается в карточку — сократите текст" % (i + 1))
            self.text(s, tx, cy + pad, tw, ch - pad * 2, paras,
                      anchor=MSO_ANCHOR.MIDDLE, leading=1.14, space_after=6)
            self.text(s, cx + pad, cy + pad, 0.5, ch - pad * 2, "%d." % (i + 1),
                      size=17, color=b["accent"], bold=True, font=b["head_font"],
                      anchor=MSO_ANCHOR.MIDDLE)
        self.chrome(s, False, d.get("source"))

    def s_content(self, d):
        s = self.new()
        b = self.b
        y = self.slide_title(s, d["title"], d.get("kicker"))
        stat = d.get("stat")
        bottom = self.SH - self.M * (1.9 if d.get("source") else 1.4)
        right_w = (stat.get("width") if stat and stat.get("width") else
                   (2.6 * self.u + 0.6) if stat else 0)
        body_w = self.SW - 2 * self.M - right_w - (0.3 if right_w else 0)
        if d.get("lead"):
            lead_size = d.get("lead_size", 13)
            lead_eff = self.pt(lead_size)
            lead_lines = self.lines(d["lead"], lead_eff, body_w - 0.02, bold=False)
            lead_h = lead_lines * lead_eff * 1.18 / 72.0
            self.text(s, self.M, y, body_w, lead_h + 0.05, d["lead"], size=lead_size,
                      color=b["ink2"], leading=1.18)
            y += lead_h + 0.22
        cols = d.get("columns") or ([d["bullets"]] if d.get("bullets") else [])
        n = len(cols)
        if n > 2:
            self.warnings.append("content: более 2 колонок не поддерживается, взяты первые две")
            cols = cols[:2]; n = 2
        gap = 0.3 * self.u + 0.1
        cw = (body_w - gap * (n - 1)) / n if n else body_w
        for i, col in enumerate(cols):
            items = col
            if len(items) > 8:
                self.warnings.append("content: в колонке %d более 8 пунктов — сократите" % (i + 1))
            body_size = d.get("body_size", 12.5)
            eff = self.pt(body_size)
            need = sum(self.lines(it if isinstance(it, str) else "".join(
                x.get("t", "") for x in it), eff, cw - 0.24) for it in items)
            need_h = need * eff * 1.06 / 72.0 + max(0, len(items) - 1) * self.pt(7) / 72.0
            if need_h > bottom - y:
                self.warnings.append("content: колонка %d не помещается (%.1f″ > %.1f″) — сократите"
                                     % (i + 1, need_h, bottom - y))
            self.bullets(s, self.M + i * (cw + gap), y, cw, bottom - y, items,
                         size=body_size, space_after=7)
        if stat:
            x = self.SW - self.M - right_w
            stat_h = stat.get("height") or min(bottom - y, max(1.6, 2.2 * self.u + 0.45))
            sy = y + max(0.0, (bottom - y - stat_h) / 2.0)
            self.rect(s, x, sy, right_w, stat_h, b["panel"], round_=True)
            paras = [[{"t": stat["value"], "size": self.pt(stat.get("value_size", 40)), "b": True,
                       "c": b["accent"], "font": b["head_font"]}]]
            if stat.get("label"):
                paras.append([{"t": stat["label"], "size": self.pt(11.5), "c": b["text"]}])
            self.text(s, x + 0.2, sy + 0.15, right_w - 0.4, stat_h - 0.3, paras,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                      leading=1.15, space_after=8)
        self.chrome(s, False, d.get("source"))

    def s_kpi(self, d):
        s = self.new()
        b = self.b
        y = self.slide_title(s, d["title"], d.get("kicker", "Результаты и метрики"))
        cards = d.get("cards", [])
        if not 2 <= len(cards) <= 4:
            self.warnings.append("kpi: рекомендуется 2–4 карточки, получено %d" % len(cards))
        gap = 0.24 * self.u + 0.08
        cw = (self.SW - 2 * self.M - gap * (len(cards) - 1)) / max(1, len(cards))
        bottom = self.SH - self.M * (1.9 if d.get("source") else 1.35)
        note_h = 0.0
        note_w = self.SW - 2 * self.M - 0.4
        if d.get("note"):
            lines = self.lines(d["note"], self.pt(11.5), note_w - 0.02)
            note_h = min(bottom - y - 2.0, lines * self.pt(11.5) * 1.2 / 72.0 + 0.3)
        ch = d.get("card_height") or min(2.3 * self.u + 0.5,
                                         (self.SH - y - self.M * 2.1) * (0.62 if d.get("note") else 1.0))
        group_h = ch + (0.18 + note_h if note_h else 0.0)
        y += max(0.0, (bottom - y - group_h) / 2.0)   # вертикальное центрирование блока
        colors = [b["ink"], b["accent"], b["accent2"], b["ink2"]]
        for i, c in enumerate(cards):
            x = self.M + i * (cw + gap)
            self.rect(s, x, y, cw, ch, b["panel2"], round_=True)
            # цвет значения: явный HEX > роль > позиция
            col = c.get("color") or b.get(c.get("color_role", ""), None) or colors[i % len(colors)]
            paras = [[{"t": c["value"], "size": self.pt(34), "b": True,
                       "c": col, "font": b["head_font"]}]]
            if c.get("label"):
                paras.append([{"t": c["label"], "size": self.pt(11.5), "c": b["text"]}])
            if c.get("delta"):
                paras.append([{"t": c["delta"], "size": self.pt(10), "c": b["muted"]}])
            self.text(s, x + 0.16, y + 0.12, cw - 0.32, ch - 0.24, paras,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                      leading=1.12, space_after=8)
        ny = y + ch + 0.18
        if d.get("note"):
            self.rect(s, self.M, ny, self.SW - 2 * self.M, note_h, b["panel"], round_=True)
            self.text(s, self.M + 0.2, ny + 0.12, note_w, note_h - 0.24, d["note"],
                      size=11.5, color=b["text"], leading=1.18)
        self.chrome(s, False, d.get("source"))

    # -- диаграммы -----------------------------------------------------------
    _CHART_KINDS = {
        "col": "COLUMN_CLUSTERED",
        "col_stacked": "COLUMN_STACKED",
        "bar": "BAR_CLUSTERED",
        "bar_stacked": "BAR_STACKED",
        "line": "LINE_MARKERS",
        "area": "AREA",
        "pie": "PIE",
        "doughnut": "DOUGHNUT",
    }

    def _style_chart(self, gf, kind, n_series, number_format=None):
        b = self.b
        chart = gf.chart
        chart.font.size = Pt(self.pt(10))
        chart.font.name = b["body_font"]
        chart.font.color.rgb = RGBColor.from_string(b["text"])
        if kind in ("pie", "doughnut"):
            chart.has_legend = True
            chart.legend.position = XL_LEGEND_POSITION.RIGHT
            chart.legend.include_in_layout = False
            pts = chart.plots[0]
            pts.has_data_labels = True
            pts.data_labels.number_format = number_format or "0 %"
            pts.data_labels.number_format_is_linked = False
            pts.data_labels.font.size = Pt(self.pt(10))
            pts.data_labels.font.bold = True
            pts.data_labels.font.color.rgb = RGBColor.from_string(b["on_dark"])
        else:
            chart.has_legend = n_series > 1
            if chart.has_legend:
                chart.legend.position = XL_LEGEND_POSITION.TOP
                chart.legend.include_in_layout = False
                chart.legend.font.size = Pt(self.pt(10))
            plot = chart.plots[0]
            try:
                plot.gap_width = 90 if kind.startswith(("col", "bar")) else 60
            except Exception:
                pass  # XY-диаграммы не имеют gap_width
            if kind in ("col_stacked", "bar_stacked"):
                plot.overlap = 100
            plot.has_data_labels = True
            dl = plot.data_labels
            dl.font.size = Pt(self.pt(9.5))
            dl.font.color.rgb = RGBColor.from_string(b["muted"])
            if number_format:
                dl.number_format = number_format
                dl.number_format_is_linked = False
            # Позиция подписей зависит от типа: outEnd/inEnd допустимы только
            # для столбчатых; у line/scatter PowerPoint их отклоняет вместе
            # с файлом. Area не поддерживает подписи значений вовсе.
            if kind == "area":
                plot.has_data_labels = False
            else:
                pos = {
                    "col": XL_LABEL_POSITION.OUTSIDE_END,
                    "bar": XL_LABEL_POSITION.OUTSIDE_END,
                    "col_stacked": XL_LABEL_POSITION.INSIDE_END,
                    "bar_stacked": XL_LABEL_POSITION.INSIDE_END,
                    "line": XL_LABEL_POSITION.ABOVE,
                }.get(kind)
                if pos is not None:
                    try:
                        dl.position = pos
                    except Exception:
                        pass
            # оси: у XY-scatter нет категориальной оси — обе оси значений
            try:
                cats = chart.category_axis
                cats.tick_labels.font.size = Pt(self.pt(9.5))
                cats.tick_labels.font.color.rgb = RGBColor.from_string(b["muted"])
                cats.format.line.color.rgb = RGBColor.from_string(b["panel"])
                cats.major_tick_mark = XL_TICK_MARK.NONE
                cats.has_major_gridlines = False
            except Exception:
                pass
            vals = chart.value_axis
            vals.tick_labels.font.size = Pt(self.pt(9.5))
            vals.tick_labels.font.color.rgb = RGBColor.from_string(b["muted"])
            vals.format.line.color.rgb = RGBColor.from_string(b["panel"])
            vals.major_tick_mark = XL_TICK_MARK.NONE
            vals.has_major_gridlines = True
            vals.major_gridlines.format.line.color.rgb = RGBColor.from_string(b["panel"])
            vals.major_gridlines.format.line.width = Pt(0.5)
        for i, ser in enumerate(chart.series):
            if kind == "line":
                ser.format.line.color.rgb = RGBColor.from_string(b["series"][i % len(b["series"])])
                ser.format.line.width = Pt(2.0)
                ser.smooth = False
            elif kind in ("pie", "doughnut"):
                for j, pt_ in enumerate(ser.points):
                    pt_.format.fill.solid()
                    pt_.format.fill.fore_color.rgb = RGBColor.from_string(
                        b["series"][j % len(b["series"])])
            else:
                ser.format.fill.solid()
                ser.format.fill.fore_color.rgb = RGBColor.from_string(
                    b["series"][i % len(b["series"])])
                ser.format.line.fill.background()

    def s_chart(self, d):
        s = self.new()
        b = self.b
        y = self.slide_title(s, d["title"], d.get("kicker", "Данные и динамика"))
        c = d["chart"]
        kind = c.get("kind", "col")
        bullets = d.get("bullets") or []
        takeaway = d.get("takeaway")
        side_w = (3.6 * self.u + 0.9) if (bullets or takeaway) else 0
        chart_w = self.SW - 2 * self.M - side_w - (0.3 * self.u if side_w else 0)
        bottom = self.SH - self.M * (1.9 if d.get("source") else 1.35)
        chart_h = bottom - y
        if kind == "scatter":
            data = XyChartData()
            for ser in c["series"]:
                xs = data.add_series(ser.get("name", ""))
                for x, yv in ser["values"]:
                    xs.add_data_point(x, yv)
            xl_kind = XL_CHART_TYPE.XY_SCATTER_LINES_NO_MARKERS
        else:
            data = CategoryChartData()
            data.categories = c["categories"]
            for ser in c["series"]:
                data.add_series(ser.get("name", ""), ser["values"])
            attr = self._CHART_KINDS.get(kind)
            xl_kind = getattr(XL_CHART_TYPE, attr, None) if attr else None
            if xl_kind is None:
                raise SystemExit("Неизвестный тип диаграммы: %s (col, col_stacked, bar, "
                                 "bar_stacked, line, area, pie, doughnut, scatter)" % kind)
        gf = s.shapes.add_chart(xl_kind, Inches(self.M), Inches(y),
                                Inches(chart_w), Inches(chart_h), data)
        self._style_chart(gf, kind, len(c["series"]), c.get("number_format"))
        ch = gf.chart
        if c.get("title"):
            ch.has_title = True
            ch.chart_title.text_frame.text = c["title"]
            for p in ch.chart_title.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(self.pt(c.get("title_size", 12)))
                    r.font.bold = True
                    r.font.name = b["body_font"]
                    r.font.color.rgb = RGBColor.from_string(b["ink"])
        else:
            # без явного title не даём PowerPoint подставить имя серии
            ch.has_title = False
        if c.get("x_title") and kind not in ("pie", "scatter"):
            ch.category_axis.has_title = True
            ch.category_axis.axis_title.text_frame.text = c["x_title"]
            self._axis_title_font(ch.category_axis)
        if c.get("y_title") and kind not in ("pie", "doughnut"):
            ch.value_axis.has_title = True
            ch.value_axis.axis_title.text_frame.text = c["y_title"]
            self._axis_title_font(ch.value_axis)
        if side_w:
            x = self.SW - self.M - side_w
            yy = y
            if takeaway:
                take_size = 11.5
                take_lines = self.lines(takeaway, self.pt(take_size), side_w - 0.32, bold=True)
                take_h = take_lines * self.pt(take_size) * 1.14 / 72.0 + 0.3
                self.rect(s, x, yy, side_w, take_h, b["panel"], round_=True)
                self.text(s, x + 0.16, yy + 0.13, side_w - 0.32, take_h - 0.24,
                          takeaway, size=take_size, color=b["ink"], bold=True, leading=1.14)
                yy += take_h + 0.2
            if bullets:
                self.bullets(s, x, yy, side_w, bottom - yy, bullets, size=11.5, space_after=7)
        self.chrome(s, False, d.get("source"))

    def _axis_title_font(self, axis):
        for p in axis.axis_title.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(self.pt(10))
                r.font.color.rgb = RGBColor.from_string(self.b["muted"])
                r.font.name = self.b["body_font"]

    # -- таблицы -------------------------------------------------------------
    def s_table(self, d):
        s = self.new()
        b = self.b
        y = self.slide_title(s, d["title"], d.get("kicker", "Сравнение и детали"))
        headers, rows = d["headers"], d["rows"]
        bullets = d.get("bullets") or []
        side_w = (3.4 * self.u + 0.9) if bullets else 0
        tw = self.SW - 2 * self.M - side_w - (0.3 * self.u if side_w else 0)
        bottom = self.SH - self.M * (1.9 if d.get("source") else 1.35)
        nrows = len(rows) + 1
        if nrows > 9:
            self.warnings.append("table: более 8 строк данных — рассмотрите разбивку или диаграмму")
        font_size = float(d.get("font_size", 10.5))
        head_size = float(d.get("header_size", 11))
        eff_font, eff_head = self.pt(font_size), self.pt(head_size)
        row_h = float(d.get("row_height") or max(0.34 * self.u + 0.16,
                                                 eff_font * 1.35 / 72.0 + 0.14))
        th = min(bottom - y, row_h * nrows + 0.02)
        if row_h * nrows > bottom - y:
            self.warnings.append("table: таблица не помещается по высоте (%.1f″ > %.1f″) — "
                                 "сократите строки или кегль" % (row_h * nrows, bottom - y))
        align = d.get("align", "top")
        ty = y + 0.12 if align == "top" else y + max(0.0, (bottom - y - th) / 2.0)
        gf = s.shapes.add_table(nrows, len(headers), Inches(self.M), Inches(ty),
                                Inches(tw), Inches(th))
        table = gf.table
        table.first_row = True
        table.horz_banding = False
        for i in range(nrows):
            table.rows[i].height = Inches(min(row_h, th / nrows))
        col_widths = d.get("col_widths")
        if col_widths and len(col_widths) == len(headers):
            total = sum(float(x) for x in col_widths) or 1.0
            for j, w in enumerate(col_widths):
                table.columns[j].width = Inches(tw * float(w) / total)
        for j, htxt in enumerate(headers):
            cell = table.cell(0, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor.from_string(b["ink"])
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            r = p.add_run(); r.text = str(htxt)
            r.font.bold = True; r.font.size = Pt(eff_head)
            r.font.color.rgb = RGBColor.from_string(b["on_dark"])
            r.font.name = b["body_font"]
            cell.margin_left = cell.margin_right = Inches(0.06)
        for i, row in enumerate(rows):
            for j in range(len(headers)):
                cell = table.cell(i + 1, j)
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor.from_string(
                    b["bg_light"] if i % 2 else b["panel2"])
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                p = cell.text_frame.paragraphs[0]
                r = p.add_run(); r.text = str(row[j]) if j < len(row) else ""
                r.font.size = Pt(eff_font)
                r.font.color.rgb = RGBColor.from_string(b["text"])
                r.font.bold = (j == 0)
                r.font.name = b["body_font"]
                cell.margin_left = cell.margin_right = Inches(0.06)
        if side_w:
            self.bullets(s, self.SW - self.M - side_w, ty, side_w, bottom - ty,
                         bullets, size=11.5, space_after=7)
        self.chrome(s, False, d.get("source"))

    # -- карточки и матрица ---------------------------------------------------
    def s_cards(self, d):
        s = self.new()
        b = self.b
        y = self.slide_title(s, d["title"], d.get("kicker"))
        cols = d.get("columns") or []
        n = len(cols)
        if n < 2 or n > 4:
            self.warnings.append("cards: поддерживается 2–4 колонки, получено %d" % n)
            cols = cols[:4]
            n = len(cols)
        if not cols:
            self.warnings.append("cards: нет колонок")
            return
        band = d.get("band")
        band_size = float(d.get("band_size", 14.5))
        band_h = 0.0
        if band:
            band_lines = self.lines(band, self.pt(band_size), self.SW - 2 * self.M - 0.6)
            band_h = max(0.6 * self.u + 0.2, band_lines * self.pt(band_size) * 1.15 / 72.0 + 0.22)
        bottom = self.SH - self.M * (1.9 if d.get("source") else 1.35)
        if band:
            bottom -= band_h + 0.18
        ch = bottom - y
        gap = float(d.get("gap", 0.17))
        cw = (self.SW - 2 * self.M - gap * (n - 1)) / n
        head_size = float(d.get("head_size", 16))
        kicker_size = float(d.get("kicker_size", 14))
        body_size = float(d.get("body_size", 14.5))
        footer_size = float(d.get("footer_size", 14))
        footer_label = d.get("footer_label", "КОМПОНЕНТЫ AI OS")
        palette = [b["accent"], b["accent2"], b["ink2"], b["accent"]]
        for i, card in enumerate(cols):
            x = self.M + i * (cw + gap)
            self.rect(s, x, y, cw, ch, b["panel2"], round_=True)
            self.rect(s, x, y, cw, 0.08, card.get("color") or palette[i % len(palette)])
            num = card.get("num", str(i + 1))
            has_num = num is not None and str(num) != ""
            head_x = x + 0.22 + (0.5 if has_num else 0.0)
            head_w = cw - (head_x - x) - 0.22
            if has_num:
                self.rect(s, x + 0.22, y + 0.22, 0.36, 0.36, b["ink"], oval=True)
                self.text(s, x + 0.22, y + 0.22, 0.36, 0.36, str(num),
                          size=self.pt(15), color=b["on_dark"], bold=True,
                          align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, raw_size=True)
            head = card.get("head", "")
            head_h = self.lines(head, self.pt(head_size), head_w, bold=True) * self.pt(head_size) * 1.08 / 72.0 + 0.02
            self.text(s, head_x, y + 0.2, head_w, head_h, head,
                      size=head_size, color=b["ink"], bold=True, leading=1.02)
            kicker = card.get("kicker", "")
            kicker_y = y + 0.2 + head_h + 0.08
            kicker_h = self.lines(kicker, self.pt(kicker_size), cw - 0.44,
                                  bold=True) * self.pt(kicker_size) * 1.1 / 72.0 + 0.02
            if kicker:
                self.text(s, x + 0.22, kicker_y, cw - 0.44, kicker_h, kicker,
                          size=kicker_size, color=b["accent"], bold=True)
            body_y = kicker_y + (kicker_h if kicker else 0.0) + 0.12
            footer_text = card.get("footer", "")
            footer_lines = (self.lines(footer_text, self.pt(footer_size), cw - 0.44)
                            if footer_text else 0)
            footer_h = (0.26 + footer_lines * self.pt(footer_size) * 1.15 / 72.0
                        if footer_text else 0.0)
            footer_y = y + ch - footer_h - 0.16
            if footer_text:
                self.rect(s, x + 0.22, footer_y - 0.08, cw - 0.44, 0.01, b["panel"])
                if footer_label:
                    self.text(s, x + 0.22, footer_y, cw - 0.44, 0.25,
                              footer_label, size=footer_size, color=b["muted"], bold=True)
                self.text(s, x + 0.22, footer_y + 0.26, cw - 0.44,
                          max(0.32, footer_h - 0.18),
                          footer_text, size=footer_size, color=b["text"], leading=1.03)
            body_h = footer_y - 0.14 - body_y
            if body_h <= 0.3:
                self.warnings.append("cards: колонка %d — не хватает места под пункты" % (i + 1))
            items = card.get("bullets") or []
            eff = self.pt(body_size)
            need = sum(self.lines(str(it), eff, cw - 0.44 - 0.24) for it in items)
            need_h = need * eff * 1.06 / 72.0 + max(0, len(items) - 1) * self.pt(6) / 72.0
            if need_h > body_h:
                self.warnings.append("cards: колонка %d переполнена (%.1f″ > %.1f″)"
                                     % (i + 1, need_h, body_h))
            self.bullets(s, x + 0.22, body_y, cw - 0.44, max(0.2, body_h), items,
                         size=body_size, space_after=6)
        if band:
            by = bottom + 0.18
            self.rect(s, self.M, by, self.SW - 2 * self.M, band_h, b["ink"], round_=True)
            self.text(s, self.M + 0.3, by, self.SW - 2 * self.M - 0.6, band_h, band,
                      size=band_size, color=b["on_dark"], bold=True,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, leading=1.05)
        self.chrome(s, False, d.get("source"))

    def s_matrix(self, d):
        s = self.new()
        b = self.b
        y = self.slide_title(s, d["title"], d.get("kicker", "Матрица"))
        headers, rows = d["headers"], d.get("rows", [])
        ncols = len(headers)
        bottom = self.SH - self.M * (1.9 if d.get("source") else 1.35)
        nrows = len(rows) + 1
        font_size = float(d.get("font_size", 10.5))
        head_size = float(d.get("header_size", 11))
        eff_font, eff_head = self.pt(font_size), self.pt(head_size)
        row_h = float(d.get("row_height") or max(0.34 * self.u + 0.16,
                                                 eff_font * 1.35 / 72.0 + 0.14))
        th = min(bottom - y, row_h * nrows + 0.02)
        if row_h * nrows > bottom - y:
            self.warnings.append("matrix: матрица не помещается по высоте")
        gf = s.shapes.add_table(nrows, ncols, Inches(self.M), Inches(y),
                                Inches(self.SW - 2 * self.M), Inches(th))
        table = gf.table
        table.first_row = True
        table.horz_banding = False
        for i in range(nrows):
            table.rows[i].height = Inches(min(row_h, th / nrows))
        col_widths = d.get("col_widths")
        if col_widths and len(col_widths) == ncols:
            total = sum(float(x) for x in col_widths) or 1.0
            for j, w in enumerate(col_widths):
                table.columns[j].width = Inches((self.SW - 2 * self.M) * float(w) / total)
        for j, htxt in enumerate(headers):
            cell = table.cell(0, j)
            cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor.from_string(b["ink"])
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run(); r.text = str(htxt)
            r.font.bold = True; r.font.size = Pt(eff_head)
            r.font.color.rgb = RGBColor.from_string(b["on_dark"])
            r.font.name = b["body_font"]
            cell.margin_left = cell.margin_right = Inches(0.06)
        for i, row in enumerate(rows):
            for j in range(ncols):
                cell = table.cell(i + 1, j)
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor.from_string(
                    b["panel2"] if j == 0 else (b["bg_light"] if i % 2 else b["panel"]))
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                p = cell.text_frame.paragraphs[0]
                p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
                r = p.add_run(); r.text = str(row[j]) if j < len(row) else ""
                r.font.size = Pt(eff_font)
                r.font.color.rgb = RGBColor.from_string(b["text"])
                r.font.bold = (j == 0)
                r.font.name = b["body_font"]
                cell.margin_left = cell.margin_right = Inches(0.06)
        self.chrome(s, False, d.get("source"))

    # -- таймлайн ------------------------------------------------------------
    def s_timeline(self, d):
        s = self.new()
        b = self.b
        y = self.slide_title(s, d["title"], d.get("kicker", "Дорожная карта"))
        ms = d.get("milestones", [])
        if len(ms) > 6:
            self.warnings.append("timeline: более 6 вех — укрупните этапы")
        n = max(2, len(ms))
        bottom = self.SH - self.M * (1.9 if d.get("source") else 1.35)
        step = (self.SW - 2 * self.M) / n
        card_w = step - 0.16
        body_size = 10.5
        card_h_max = 0.0
        for m in ms:
            lines = self.lines(m.get("text", ""), self.pt(body_size), card_w - 0.24)
            card_h_max = max(card_h_max, lines * self.pt(body_size) * 1.15 / 72.0 + 0.32)
        block_h = (0.35 * self.u) + (0.85 * self.u + 0.35) + 0.24 + card_h_max
        align = d.get("align", "top")
        dy = 0.0 if align == "top" else max(0.0, (bottom - y - block_h) / 2.0)
        top = y + dy + 0.35 * self.u
        line_y = top + 0.85 * self.u + 0.35
        card_h = min(bottom - line_y - 0.35, card_h_max)
        if card_h_max > bottom - line_y - 0.35:
            self.warnings.append("timeline: карточки не помещаются по высоте — сократите тексты")
        self.rect(s, self.M, line_y, self.SW - 2 * self.M, 0.028, b["panel"])
        for i, m in enumerate(ms):
            cx = self.M + step * i + step / 2
            dot = 0.16 * self.u + 0.06
            self.rect(s, cx - dot / 2, line_y - dot / 2 + 0.014, dot, dot,
                      b["accent"] if i == len(ms) - 1 else b["ink"], oval=True)
            self.text(s, cx - step / 2 + 0.06, line_y - 0.62 * self.u - 0.22,
                      step - 0.12, 0.35, m.get("period", ""), size=13,
                      color=b["ink"], bold=True, align=PP_ALIGN.CENTER, font=b["head_font"])
            txt = m.get("text", "")
            lines = self.lines(txt, self.pt(body_size), card_w - 0.24)
            need = lines * self.pt(body_size) * 1.12 / 72.0 + 0.12
            if need > card_h - 0.12:
                self.warnings.append("timeline: карточка %d не помещается — сократите текст" % (i + 1))
            self.rect(s, cx - card_w / 2, line_y + 0.24, card_w, card_h,
                      b["panel2"], round_=True)
            self.text(s, cx - card_w / 2 + 0.11, line_y + 0.36, card_w - 0.22,
                      card_h - 0.24, txt, size=body_size,
                      color=b["text"], leading=1.12)
        self.chrome(s, False, d.get("source"))

    # -- выводы и источники ---------------------------------------------------
    def s_closing(self, d):
        s = self.new(dark=True)
        b = self.b
        y = self.slide_title(s, d.get("title", "Выводы и рекомендации"), dark=True)
        half = (self.SW - 2 * self.M - 0.4) / 2
        bottom = self.SH - self.M * 1.5
        if d.get("conclusions"):
            self.text(s, self.M, y, half, 0.35, "ВЫВОДЫ", size=12,
                      color=b["on_dark_muted"], bold=True)
            self.bullets(s, self.M, y + 0.45, half, bottom - y - 0.45,
                         d["conclusions"], size=12.5, color=b["on_dark"],
                         numbered=True, space_after=8)
        if d.get("recommendations"):
            x = self.M + half + 0.4
            self.text(s, x, y, half, 0.35, "РЕКОМЕНДАЦИИ", size=12,
                      color=b["accent2"] if b["accent2"] else b["on_dark_muted"], bold=True)
            self.bullets(s, x, y + 0.45, half, bottom - y - 0.45,
                         d["recommendations"], size=12.5, color=b["on_dark"],
                         numbered=True, space_after=8)
        self.chrome(s, dark=True)

    def s_refs(self, d):
        s = self.new()
        b = self.b
        y = self.slide_title(s, d.get("title", "Источники"))
        items = d.get("items", [])
        paras = [[{"t": "%d. " % (i + 1), "b": True}, {"t": it}]
                 for i, it in enumerate(items)]
        tb = s.shapes.add_textbox(Inches(self.M), Inches(y),
                                  Inches(self.SW - 2 * self.M), Inches(self.SH - y - self.M * 1.4))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.auto_size = MSO_AUTO_SIZE.NONE
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        for i, runs in enumerate(paras):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.space_after = Pt(self.pt(7))
            p.line_spacing = 1.1
            for rs in runs:
                r = p.add_run(); r.text = rs["t"]
                r.font.size = Pt(self.pt(11.5))
                r.font.name = b["body_font"]
                r.font.bold = rs.get("b", False)
                r.font.color.rgb = RGBColor.from_string(b["text"])
        self.chrome(s, False)

    # ------------------------------------------------------------------ сборка
    BUILDERS = {
        "title": s_title, "section": s_section, "summary": s_summary,
        "content": s_content, "kpi": s_kpi, "chart": s_chart, "table": s_table,
        "cards": s_cards, "matrix": s_matrix,
        "timeline": s_timeline, "closing": s_closing, "refs": s_refs,
    }

    def build(self, slides: list[dict], lint: bool) -> list[str]:
        for i, d in enumerate(slides, 1):
            t = d.get("type")
            fn = self.BUILDERS.get(t)
            if fn is None:
                raise SystemExit("Слайд %d: неизвестный тип %r" % (i, t))
            if t != "title" and not d.get("title") and t not in ("closing",):
                self.warnings.append("слайд %d (%s): нет заголовка" % (i, t))
            title = d.get("title", "")
            if title:
                if len(title) > 90:
                    self.warnings.append("слайд %d: заголовок длиннее 90 знаков — сократите" % i)
                tsize = self.pt(d.get("title_size", self.title_size))
                if self.lines(title, tsize, self.SW - 2 * self.M - 0.02,
                              self.b["head_font"], bold=True) > 2:
                    self.warnings.append("слайд %d: заголовок занимает более двух строк" % i)
            fn(self, d)
        if lint:
            self.lint(slides)
        return self.warnings

    def lint(self, slides: list[dict]) -> None:
        types = [s.get("type") for s in slides]
        if types and types[0] != "title":
            self.warnings.append("первый слайд не title — отчёт должен начинаться титулом")
        if len(slides) >= 8 and "summary" not in types:
            self.warnings.append("нет слайда summary — для отчёта руководству добавьте ключевые положения")
        if not any(t in ("chart", "table", "kpi") for t in types):
            self.warnings.append("ни одного слайда с данными (chart/table/kpi) — представьте цифры визуально")
        if len(slides) >= 10 and not any(t == "closing" for t in types):
            self.warnings.append("нет слайда closing — завершите отчёт выводами и рекомендациями")
        from collections import Counter
        dup = [k for k, v in Counter(types).items() if k == "content" and v > 4]
        if dup:
            self.warnings.append("более 4 слайдов content подряд/всего — разнообразьте компоновку")


def main() -> int:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", nargs="?")
    ap.add_argument("-o", "--out", default="report.pptx")
    ap.add_argument("--brand", choices=list(BRANDS), default=None)
    ap.add_argument("--lint", action="store_true", help="дополнительные проверки структуры отчёта")
    ap.add_argument("--example-spec", action="store_true", help="напечатать пример спецификации")
    ap.add_argument("--min-font", type=float, help="минимальный кегль, pt (например, 14)")
    ap.add_argument("--font-scale", type=float, help="множитель кеглей (1.0 — базовый)")
    ap.add_argument("--projector", action="store_true", help="проекторный режим: min 14 pt и крупнее")
    ap.add_argument("--title-size", type=float, help="базовый кегль заголовков, pt")
    ap.add_argument("--no-footer", action="store_true", help="не выводить нижний колонтитул")
    args = ap.parse_args()

    if args.example_spec:
        print(json.dumps(EXAMPLE, ensure_ascii=False, indent=2))
        return 0
    if not args.spec:
        ap.error("укажите файл спецификации или --example-spec")

    _import_pptx()

    with open(args.spec, encoding="utf-8-sig") as fh:
        spec = json.load(fh)
    if args.min_font is not None:
        spec["min_font"] = args.min_font
    if args.font_scale is not None:
        spec["font_scale"] = args.font_scale
    if args.projector:
        spec["projector"] = True
    if args.title_size is not None:
        spec["title_size"] = args.title_size
    if args.no_footer:
        spec["show_footer"] = False
    brand = args.brand or spec.get("brand", "opi")
    deck = Deck(brand, spec)
    warns = deck.build(spec.get("slides", []), args.lint)
    deck.prs.save(args.out)
    print("Сохранено: %s  (бренд: %s, слайдов: %d, мин. кегль: %.1f pt)"
          % (args.out, brand, len(deck.prs.slides._sldIdLst), deck.min_font))
    for w in warns:
        print("ПРЕДУПРЕЖДЕНИЕ: %s" % w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
