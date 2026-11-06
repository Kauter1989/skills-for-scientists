#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analysis.json -> автономный HTML-отчёт.

Отчёт содержит три независимых блока: «Россия», «Мир» и «Разница рынков».
Диаграммы — inline HTML/CSS, без CDN, шрифтов и сетевых запросов. Каждая
метрика подписана уровнем качества; у каждой компании видна ссылка-источник.

Использование:
    python build_report.py --analysis analysis.json -o report.html --strict
    python build_report.py --example -o examples/example-report.html --strict

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOMAIN_LABELS = {
    "med": "Медицина", "fin": "Финансы", "industrial": "Промышленность",
    "security": "Безопасность", "education": "Образование", "media": "Медиа и контент",
    "agro": "Агро", "public": "Госсектор", "mobility": "Транспорт",
}
SERVICE_LABELS = {
    "consulting": "Консалтинг", "integration": "Интеграция", "development": "Разработка",
    "licensing": "Лицензирование", "mlops": "MLOps", "data_services": "Работа с данными",
    "support": "Поддержка", "training": "Обучение", "hardware": "Аппаратные поставки",
}
PAK_LABELS = {
    "none": "Без ПАК", "ai_component": "ИИ-компонент в ПАК",
    "ai_system": "ИИ-система (ПАК)", "ai_software_package": "ИИ-программно-аппаратный комплекс",
}
QUALITY_LABELS = {
    "measured": "измерено", "derived": "расчёт", "estimated": "оценка",
    "expert": "экспертно", "missing": "нет данных",
}
QUALITY_CLASS = {"measured": "q-measured", "derived": "q-derived", "estimated": "q-est",
                 "expert": "q-exp", "missing": "q-missing"}

CSS = """
:root{--paper:#f6f5f2;--card:#fff;--ink:#14181f;--muted:#5f6875;--line:#dfe2e7;
--strong:#c4cad2;--accent:#1f5f5b;--rf:#a2622a;--world:#2f5f9a;--green:#1f7a4d;
--amber:#8a5300;--red:#b42318;--mono:ui-monospace,"Cascadia Code",Consolas,monospace;
--sans:ui-sans-serif,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 var(--sans)}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px}
header{padding:38px 0 8px}
.kicker{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--accent)}
h1{font-size:clamp(28px,3.6vw,40px);line-height:1.12;letter-spacing:-.02em;margin:8px 0 10px}
.sub{color:var(--muted);font-size:16px;margin:0 0 16px;max-width:880px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}
.chip{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:5px 10px;font-size:11.5px;color:var(--muted)}
.chip b{color:var(--ink)}
section{background:var(--card);border:1px solid var(--line);border-radius:14px;margin-bottom:16px;overflow:hidden}
.sec-head{padding:15px 22px 12px;border-bottom:1px solid var(--line);display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.sec-head h2{margin:0;font-size:20px;letter-spacing:-.01em}
.sec-head .n{font-family:var(--mono);font-size:11px;color:var(--muted);border:1px solid var(--line);border-radius:6px;padding:2px 6px}
.sec-head p{margin:0;color:var(--muted);font-size:12px}
.body{padding:16px 22px 20px}
p{margin:0 0 12px}
table{width:100%;border-collapse:collapse;font-size:12.5px;margin:8px 0 12px}
th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);
border-bottom:1px solid var(--strong);padding:7px 8px}
td{border-bottom:1px solid var(--line);padding:7px 8px;vertical-align:top}
tr:last-child td{border-bottom:0}
code,.mono{font-family:var(--mono);font-size:11.5px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:6px 0 16px}
.tile{border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:#fdfdfc}
.tile b{display:block;font-size:22px;letter-spacing:-.02em;line-height:1.15}
.tile span{font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.bars{margin:10px 0 16px}
.bar-row{display:grid;grid-template-columns:190px 1fr 104px;gap:10px;align-items:center;
padding:4px 0;border-bottom:1px dashed var(--line);font-size:12.5px}
.bar-row:last-child{border-bottom:0}
.bar-track{background:#eef0f2;border-radius:5px;height:14px;position:relative;overflow:hidden}
.bar-fill{height:100%;background:var(--accent);border-radius:5px}
.bar-row.rf .bar-fill{background:var(--rf)}
.bar-row.world .bar-fill{background:var(--world)}
.bar-val{text-align:right;font-family:var(--mono);font-size:11.5px;color:var(--muted);white-space:nowrap}
.q{font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;
padding:1px 6px;border-radius:5px;white-space:nowrap}
.q-measured{background:#e7f4ec;color:var(--green)}
.q-derived{background:#e8eff8;color:#204a7c}
.q-est{background:#fbf0dc;color:var(--amber)}
.q-exp{background:#efebf9;color:#4a3a8a}
.q-missing{background:#fbe9e7;color:var(--red)}
.gap-pos{color:#204a7c;font-weight:600}
.gap-neg{color:var(--rf);font-weight:600}
.callout{border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:10px;
padding:12px 14px;background:#fcfdfd;margin:10px 0 14px}
.callout b{display:block;font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-bottom:4px}
.callout p{margin:0}
.badge{display:inline-block;border:1px solid var(--line);border-radius:6px;padding:1px 7px;font-size:10.5px;color:var(--muted);margin-right:4px}
.empty{color:var(--muted);font-style:italic}
footer{padding:6px 0 40px;color:var(--muted);font-size:11.5px}
@media (max-width:760px){.wrap{padding:0 14px}.bar-row{grid-template-columns:120px 1fr 54px}}
@media print{@page{size:A4;margin:14mm}body{background:#fff;font-size:10pt}
section{break-inside:avoid;box-shadow:none}.wrap{max-width:none;padding:0}}
"""


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def qbadge(level: str) -> str:
    return f'<span class="q {QUALITY_CLASS.get(level, "q-missing")}">{esc(QUALITY_LABELS.get(level, level))}</span>'


def fmt(value, unit: str = "") -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        text = f"{value:.1f}".rstrip("0").rstrip(".")
    else:
        text = str(value)
    return f"{text} {unit}".strip()


def tiles(cohort: dict) -> str:
    items = []
    for m in cohort["metrics"]:
        items.append(
            f'<div class="tile"><b>{esc(fmt(m["value"], m["unit"]))}</b>'
            f'<span>{esc(m["id"])} · {qbadge(m["quality"])}</span>'
            f'<div class="mono" style="font-size:10.5px;color:var(--muted);margin-top:4px">{esc(m["note"])}</div></div>'
        )
    return '<div class="tiles">' + "".join(items) + "</div>"


def bars(values: dict, labels: dict, cohort_class: str) -> str:
    top = max([v["share"] or 0 for v in values.values()] + [1])
    rows = []
    for key, value in values.items():
        width = 0 if not value["share"] else max(1.5, 100 * value["share"] / top)
        rows.append(
            f'<div class="bar-row {cohort_class}"><div>{esc(labels.get(key, key))}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{width:.1f}%"></div></div>'
            f'<div class="bar-val">{value["count"]} · {fmt(value["share"], "%")}</div></div>'
        )
    return '<div class="bars">' + "".join(rows) + "</div>"


def cohort_section(index: str, title: str, note: str, cohort: dict, companies: list[dict],
                   labels: dict[str, dict]) -> str:
    domains = bars(cohort["domains"], labels["domains"], "rf" if cohort["cohort"] == "RF" else "world")
    services = bars(cohort["services"], labels["services"], "rf" if cohort["cohort"] == "RF" else "world")
    pak_rows = "".join(
        f'<tr><td>{esc(PAK_LABELS.get(k, k))}</td><td class="mono">{v["count"]}</td>'
        f'<td class="mono">{fmt(v["share"], "%")}</td></tr>'
        for k, v in cohort["pak"].items()
    )
    countries = "".join(f'<li>{esc(k)}: <b>{v}</b></li>' for k, v in cohort["countries"].items())
    rows = []
    for company in sorted(companies, key=lambda c: c.get("name", "")):
        roles = ", ".join(company.get("roles") or [])
        doms = ", ".join(DOMAIN_LABELS.get(d, d) for d in company.get("domains") or []) or "—"
        serv = ", ".join(SERVICE_LABELS.get(s, s) for s in company.get("services") or []) or "—"
        link = company.get("site") or next((e["url"] for e in company.get("evidence") or []), "")
        status = company.get("siteStatus")
        status_badge = f' <span class="badge">{esc(status)}</span>' if status else ""
        link_html = f'<a href="{esc(link)}" rel="noopener noreferrer">{esc(link)}</a>{status_badge}' if link else "—"
        year = company.get("founded") if company.get("founded") else "—"
        rows.append(
            f'<tr><td>{esc(company.get("name"))}</td><td class="mono">{esc(company.get("country") or "—")}</td>'
            f'<td>{esc(roles)}</td><td>{esc(doms)}</td><td>{esc(serv)}</td>'
            f'<td>{esc(PAK_LABELS.get(company.get("pak", "none"), company.get("pak", "")))}</td>'
            f'<td class="mono">{esc(year)}</td><td>{qbadge(company.get("quality", "missing"))}</td>'
            f'<td class="mono">{link_html}</td></tr>'
        )
    pending = cohort.get("pending") or []
    pending_html = ""
    if pending:
        by_source = cohort.get("pendingBySource") or {}
        items = "".join(f"<li>{esc(k)}: <b>{v}</b></li>" for k, v in sorted(by_source.items()))
        examples = ", ".join(esc(p.get("name") or p.get("id") or "") for p in pending[:8])
        pending_html = (
            '<div class="callout"><b>Ждут проверки</b>'
            f'<p>{len(pending)} записей не участвуют в долях: источник подтверждает публикацию, '
            f'но не роль на рынке. По источникам: <ul style="margin:6px 0 0 18px">{items}</ul>'
            f'</p><p style="margin-top:6px;font-size:12px;color:var(--muted)">Примеры: {examples}</p></div>'
        )
    table = (
        '<table><thead><tr><th>Компания</th><th>Страна</th><th>Роль</th><th>Домен</th>'
        '<th>Услуги</th><th>ПАК</th><th>Осн.</th><th>Кач.</th><th>Источник</th></tr></thead><tbody>'
        + "".join(rows) + "</tbody></table>"
    )
    return (
        f'<section><div class="sec-head"><span class="n">{index}</span><h2>{esc(title)}</h2>'
        f'<p>{esc(note)}</p></div><div class="body">'
        f'{tiles(cohort)}{pending_html}'
        f'<h3 style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)">'
        f'Доменные области</h3>{domains}'
        f'<h3 style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)">'
        f'Спектр услуг</h3>{services}'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
        f'<div><h3 style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)">'
        f'ПАК</h3><table><thead><tr><th>Класс</th><th>Компаний</th><th>Доля</th></tr></thead><tbody>'
        f'{pak_rows}</tbody></table></div>'
        f'<div><h3 style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)">'
        f'География</h3><ul style="font-size:12.5px;padding-left:18px">{countries or "<li>—</li>"}</ul></div>'
        f'</div>{table}</div></section>'
    )


def gap_section(analysis: dict) -> str:
    gaps = analysis.get("gaps") or []
    rows = []
    for g in gaps:
        if g.get("gapShare") is None and not g.get("missingInRf"):
            continue
        cls = "gap-pos" if (g.get("gapShare") or 0) > 0 else "gap-neg"
        label = DOMAIN_LABELS.get(g["key"], SERVICE_LABELS.get(g["key"], g["key"]))
        flag = ' <span class="badge">нет в РФ</span>' if g.get("missingInRf") else ""
        rows.append(
            f'<tr><td>{esc(label)}{flag}</td><td class="mono">{esc(g["axis"])}</td>'
            f'<td class="mono">{g["rfCount"]}</td><td class="mono">{fmt(g["rfShare"], "%")}</td>'
            f'<td class="mono">{g["worldCount"]}</td><td class="mono">{fmt(g["worldShare"], "%")}</td>'
            f'<td class="mono {cls}">{fmt(g["gapShare"], "п.п.")}</td>'
            f'<td>{qbadge(g.get("gapQuality", "missing"))}</td></tr>'
        )
    role_gap = analysis.get("roleGap") or []
    role_html = (", ".join(role_gap) if role_gap else "расхождений по ролям не найдено")
    missing = analysis.get("missingInRf") or []
    missing_list = "".join(
        f'<li><b>{esc(DOMAIN_LABELS.get(m["key"], SERVICE_LABELS.get(m["key"], m["key"])))}</b> — '
        f'в мире {m["worldCount"]} компаний, в РФ 0</li>'
        for m in missing
    ) or '<li class="empty">ни одной области с нулём компаний в РФ при пороге не найдено</li>'
    th = analysis.get("thresholds", {})
    return (
        '<section><div class="sec-head"><span class="n">03</span><h2>Разница рынков РФ и мира</h2>'
        f'<p>порог доли: не менее {esc(th.get("gapMinCohort", "?"))} компаний в когорте; '
        f'порог пробела: 0 в РФ и не менее {esc(th.get("gapMinGlobal", "?"))} в мире</p></div>'
        '<div class="body">'
        '<div class="callout"><b>Как читать</b><p>Доли считаются внутри своей когорты, '
        'поэтому их разность — разница структуры рынка, а не разница числа компаний. '
        'Знак «+» означает, что в мире эта область занимает большую долю рынка, чем в РФ.</p></div>'
        '<table><thead><tr><th>Область</th><th>Ось</th><th>РФ, шт.</th><th>РФ, %</th>'
        '<th>Мир, шт.</th><th>Мир, %</th><th>Разница</th><th>Кач.</th></tr></thead><tbody>'
        + ("".join(rows) or '<tr><td colspan="8" class="empty">доля не посчитана: когорта меньше порога или данных нет</td></tr>')
        + '</tbody></table>'
        f'<h3 style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)">'
        f'Есть в мире, нет в РФ</h3><ul style="font-size:13px">{missing_list}</ul>'
        f'<h3 style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)">'
        f'Роли</h3><p style="font-size:13px">{esc(role_html)}</p>'
        '</div></section>'
    )


def method_section(analysis: dict, companies_count: int) -> str:
    growth = analysis.get("growth") or {}
    growth_rows = "".join(
        f'<tr><td>{esc(name)}</td><td class="mono">{fmt(m.get("value"), m.get("unit", ""))}</td>'
        f'<td>{qbadge(m.get("quality", "missing"))}</td><td>{esc(m.get("note"))}</td></tr>'
        for name, m in growth.items()
    )
    caveats = "".join(f"<li>{esc(c)}</li>" for c in analysis.get("caveats") or []) or "<li>—</li>"
    changes = analysis.get("changes") or {}
    return (
        '<section><div class="sec-head"><span class="n">04</span><h2>Методика и качество данных</h2>'
        f'<p>снимок {esc(analysis.get("snapshotDate"))}, компаний {companies_count}</p></div>'
        '<div class="body">'
        '<p>Каждая метрика несёт уровень качества: <b>измерено</b> — прямо в источнике; '
        '<b>расчёт</b> — производное от измеренного; <b>оценка</b> — вывод по публичным данным; '
        '<b>экспертно</b> — решение аналитика; <b>нет данных</b> — источник не подтверждает.</p>'
        '<table><thead><tr><th>Когорта</th><th>Прирост по годам</th><th>Кач.</th><th>Пояснение</th></tr></thead>'
        f'<tbody>{growth_rows}</tbody></table>'
        f'<p style="font-size:13px">Сравнение снимков: с {esc(changes.get("from") or "—")} по '
        f'{esc(changes.get("to") or "—")}. Новых компаний: {len(changes.get("newCompanies") or [])}, '
        f'выбывших: {len(changes.get("droppedCompanies") or [])}. {esc(changes.get("note") or "")}</p>'
        f'<h3 style="font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)">'
        f'Ограничения</h3><ul style="font-size:13px">{caveats}</ul>'
        '</div></section>'
    )


def build_html(analysis: dict) -> str:
    companies = analysis.get("_companies") or []
    rf_companies = [c for c in companies if c.get("cohort") == "RF"]
    world_companies = [c for c in companies if c.get("cohort") == "WORLD"]
    labels = {"domains": DOMAIN_LABELS, "services": SERVICE_LABELS}
    rf, world = analysis["cohorts"]["RF"], analysis["cohorts"]["WORLD"]
    title = "ИИ-рынок: РФ и мир"
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{esc(title)} — снимок {esc(analysis.get("snapshotDate"))}</title>
<style>{CSS}</style></head><body><main class="wrap">
<header>
<div class="kicker">Анализ рынка ИИ-компаний</div>
<h1>{esc(title)}: динамика по домену, услугам и ПАК</h1>
<p class="sub">Две когорты считаются независимо: Россия и мир без России. Затем сравниваются доли, а не абсолютные числа. Каждая строка имеет источник, каждая метрика — уровень качества.</p>
<div class="chips">
<span class="chip">Снимок: <b>{esc(analysis.get("snapshotDate"))}</b></span>
<span class="chip">РФ: <b>{rf["companies"]}</b></span>
<span class="chip">Мир: <b>{world["companies"]}</b></span>
<span class="chip">Пробелов в РФ: <b>{len(analysis.get("missingInRf") or [])}</b></span>
</div>
</header>
{cohort_section("01", "Россия", f"{rf['companies']} компаний", rf, rf_companies, labels)}
{cohort_section("02", "Мир (без РФ)", f"{world['companies']} компаний", world, world_companies, labels)}
{gap_section(analysis)}
{method_section(analysis, len(companies))}
<footer>ai-market-landscape · снимок {esc(analysis.get("snapshotDate"))} · автономный HTML без сетевых запросов</footer>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="analysis.json -> HTML")
    parser.add_argument("--analysis", type=Path)
    parser.add_argument("--companies", type=Path, help="снимок для таблиц компаний")
    parser.add_argument("-o", "--out", type=Path, required=True)
    parser.add_argument("--example", action="store_true")
    parser.add_argument("--strict", action="store_true", help="требует URL у каждой компании")
    args = parser.parse_args(argv)

    analysis_path = args.analysis or HERE.parent / "examples" / "example-analysis.json"
    companies_path = args.companies or HERE.parent / "examples" / "example-companies.json"
    if not analysis_path.is_file():
        print(f"error: нет {analysis_path}")
        return 2
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    companies = []
    if companies_path.is_file():
        companies = json.loads(companies_path.read_text(encoding="utf-8")).get("companies", [])
    analysis["_companies"] = companies

    if args.strict:
        missing = [c.get("id") for c in companies if not (c.get("site") or (c.get("evidence") or []))]
        if missing:
            print(f"error: у компаний нет источника: {', '.join(map(str, missing))}")
            return 1
        unnamed = [m["id"] for m in analysis["cohorts"]["RF"]["metrics"] + analysis["cohorts"]["WORLD"]["metrics"]
                   if m["quality"] not in QUALITY_LABELS]
        if unnamed:
            print(f"error: метрики без метки качества: {', '.join(unnamed)}")
            return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_html(analysis), encoding="utf-8")
    print(f"ok: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())