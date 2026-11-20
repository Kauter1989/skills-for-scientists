#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снимок компаний ИИ-рынка: сбор из открытых источников.

Основной источник — открытый каталог моделей OpenRouter: организации и
провайдеры, публикующие ИИ-модели, вместе с годом первой и последней модели.
Каждая запись получает дату среза, `evidence` с URL и `quality: estimated`.

Второй источник — поиск по технологическим публикациям (RSS Хабра) для
когорты РФ: он подтверждает упоминания и активность, но не роль компании на
рынке. Такую запись нельзя включать в долю без ручной проверки, поэтому её
`quality` понижается, а `needsReview` ставится в true.

Скрипт требует сети. Ненайденное не превращается в ноль: запись получает
`missing`, а отчёт об этом предупреждает.

Использование:
    python collect.py --source openrouter --out companies-2026-11-06.json
    python collect.py --source habr --query "GigaChat" --query "YandexGPT" --out rf-habr.json
    python collect.py --source openrouter --merge examples/example-companies.json --out merged.json

Только стандартная библиотека Python 3.9+; нужен доступ в сеть.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OPENROUTER_URL = "https://openrouter.ai/api/v1/models"
HABR_RSS = "https://habr.com/ru/rss/search/?q={query}&target_type=posts&fl=ru"
USER_AGENT = "Mozilla/5.0 (compatible; ai-market-landscape/0.1)"

VENDORS = {
    "OpenAI": ("openai", "US", "https://openai.com"),
    "Anthropic": ("anthropic", "US", "https://www.anthropic.com"),
    "Google": ("google", "US", "https://deepmind.google"),
    "Meta": ("meta", "US", "https://ai.meta.com"),
    "Microsoft": ("microsoft", "US", "https://azure.microsoft.com"),
    "Amazon": ("amazon", "US", "https://aws.amazon.com/bedrock"),
    "NVIDIA": ("nvidia", "US", "https://www.nvidia.com"),
    "xAI": ("xai", "US", "https://x.ai"),
    "Perplexity": ("perplexity", "US", "https://www.perplexity.ai"),
    "Writer": ("writer", "US", "https://writer.com"),
    "Thinking Machines": ("thinking-machines", "US", "https://thinkingmachines.ai"),
    "Reflection": ("reflection", "US", "https://reflection.ai"),
    "Cohere": ("cohere", "CA", "https://cohere.com"),
    "Mistral": ("mistral-ai", "FR", "https://mistral.ai"),
    "Sakana": ("sakana-ai", "JP", "https://sakana.ai"),
    "Upstage": ("upstage", "KR", "https://www.upstage.ai"),
    "DeepSeek": ("deepseek", "CN", "https://www.deepseek.com"),
    "Qwen": ("alibaba-qwen", "CN", "https://qwen.ai"),
    "Z.ai": ("zhipu", "CN", "https://z.ai"),
    "MoonshotAI": ("moonshot-ai", "CN", "https://www.moonshot.cn"),
    "MiniMax": ("minimax", "CN", "https://www.minimaxi.com"),
    "ByteDance": ("bytedance", "CN", "https://www.bytedance.com"),
    "ByteDance Seed": ("bytedance", "CN", "https://www.bytedance.com"),
    "Tencent": ("tencent", "CN", "https://www.tencent.com"),
    "Meituan": ("meituan", "CN", "https://www.meituan.com"),
    "StepFun": ("stepfun", "CN", "https://www.stepfun.com"),
    "Xiaomi": ("xiaomi", "CN", "https://www.mi.com"),
    "inclusionAI": ("ant-group", "CN", "https://www.antgroup.com"),
    "IBM": ("ibm", "US", "https://www.ibm.com"),
    "Inception": ("inception-ai", "US", "https://www.inceptionai.ai"),
}

DOMAIN_KEYWORDS = {
    "med": ("health", "medical", "med", "clinical"),
    "fin": ("fin", "bank", "trade"),
    "industrial": ("robot", "industrial", "manufactur"),
    "security": ("security", "guard", "safety"),
    "education": ("edu", "tutor"),
    "media": ("media", "video", "image", "audio", "speech", "voice"),
    "agro": ("agro", "farm"),
    "public": ("gov", "public"),
    "mobility": ("drive", "autonomous", "mobility", "vehicle"),
}


def now_date() -> str:
    return dt.date.today().isoformat()


def fetch_text(url: str, timeout: int = 40, retries: int = 3) -> str:
    last: Exception | None = None
    for attempt in range(retries):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"не удалось получить {url}: {last}")


def fetch_json(url: str) -> dict | list:
    return json.loads(fetch_text(url))


def vendor_of(model: dict) -> str | None:
    name = model.get("name") or ""
    if ":" in name:
        return name.split(":", 1)[0].strip() or None
    model_id = model.get("id") or ""
    if "/" in model_id:
        return model_id.split("/", 1)[0]
    return None


def vendor_site(vendor: str, model_id: str) -> str | None:
    known = VENDORS.get(vendor)
    if known:
        return known[2]
    if "/" in model_id:
        authority = model_id.split("/", 1)[0]
        if re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", authority):
            slug = re.sub(r"[^a-z0-9]+", "-", vendor.lower()).strip("-")
            return f"https://{authority}/{slug}"
    return None


def infer_domains(text: str) -> list[str]:
    lowered = text.lower()
    return [d for d, words in DOMAIN_KEYWORDS.items() if any(w in lowered for w in words)]


def cohort_meta(source: str) -> dict:
    return {
        "RF": {"label": "Российская Федерация", "registry": "ЕГРЮЛ / ФИПС", "source": source},
        "WORLD": {"label": "Мир (без РФ)", "registry": "открытые каталоги", "source": source},
    }


def collect_openrouter(retrieved_at: str) -> dict:
    payload = fetch_json(OPENROUTER_URL)
    models = payload.get("data") if isinstance(payload, dict) else None
    if not models:
        raise RuntimeError("OpenRouter вернул пустой список моделей")

    by_vendor: dict[str, list[dict]] = {}
    for model in models:
        vendor = vendor_of(model)
        if vendor:
            by_vendor.setdefault(vendor, []).append(model)

    companies = []
    seen_ids: set[str] = set()
    for vendor, items in sorted(by_vendor.items()):
        created = [int(m.get("created") or 0) for m in items if m.get("created")]
        first, last = (min(created), max(created)) if created else (None, None)
        text = " ".join((m.get("name") or "") + " " + (m.get("description") or "") for m in items[:5])
        known = VENDORS.get(vendor)
        company_id = known[0] if known else re.sub(r"[^a-z0-9]+", "-", vendor.lower()).strip("-")
        site = vendor_site(vendor, items[0].get("id") or "")
        evidence = [{"url": OPENROUTER_URL, "retrievedAt": retrieved_at, "kind": "catalog",
                     "note": f"{len(items)} моделей вендора {vendor}"}]
        # «ByteDance» и «ByteDance Seed» ведут к одному юридическому лицу:
        # такие записи сводятся в одну, а не дублируются.
        if company_id in seen_ids:
            target = next(c for c in companies if c["id"] == f"{company_id}--unverified")
            target["models"] += len(items)
            firsts = [y for y in (target.get("firstModelYear"),
                                  dt.datetime.fromtimestamp(first, dt.timezone.utc).year if first else None) if y]
            lasts = [y for y in (target.get("lastModelYear"),
                                 dt.datetime.fromtimestamp(last, dt.timezone.utc).year if last else None) if y]
            target["firstModelYear"] = min(firsts) if firsts else None
            target["lastModelYear"] = max(lasts) if lasts else None
            target["evidence"][0]["note"] = f"{target['models']} моделей вендора {target['name']}"
            target["aliases"] = sorted(set(target.get("aliases", [])) | {vendor})
            continue
        seen_ids.add(company_id)
        if site:
            evidence.append({"url": site, "retrievedAt": retrieved_at, "kind": "company_site",
                             "note": "сайт провайдера" if known else "домен из id модели"})
        companies.append({
            "id": f"{company_id}--unverified",
            "name": vendor,
            "country": known[1] if known else None,
            "countrySource": "expert" if known else "missing",
            "cohort": "WORLD",
            "founded": None,
            "site": site,
            "roles": ["developer"],
            "domains": infer_domains(text),
            "services": ["development", "licensing"],
            "pak": "none",
            "delivery": "api",
            "models": len(items),
            "firstModelYear": dt.datetime.fromtimestamp(first, dt.timezone.utc).year if first else None,
            "lastModelYear": dt.datetime.fromtimestamp(last, dt.timezone.utc).year if last else None,
            "evidence": evidence,
            "source": "collect.py:openrouter",
            "quality": "estimated",
            "needsReview": not known,
            "caveats": [
                "роль developer выведена из факта публикации модели",
                "домен применения каталогом не подтверждается; пустой домен означает missing",
            ],
        })

    return {
        "schemaVersion": 1,
        "snapshotDate": retrieved_at,
        "cohorts": cohort_meta("collect.py:openrouter"),
        "sources": [{"id": "openrouter", "url": OPENROUTER_URL, "retrievedAt": retrieved_at,
                     "kind": "catalog", "status": "ok"}],
        "companies": companies,
        "warnings": [
            "OpenRouter подтверждает публикацию модели, но не роль компании на рынке",
            "когорта РФ этим источником не покрывается и остаётся missing до курируемого реестра",
        ],
    }


ITEM_RE = re.compile(r"<item>(.*?)</item>", re.DOTALL)
TITLE_RE = re.compile(r"<title><!\[CDATA\[(.*?)\]\]></title>", re.DOTALL)
LINK_RE = re.compile(r"<link>(.*?)</link>", re.DOTALL)
DATE_RE = re.compile(r"<pubDate>(.*?)</pubDate>", re.DOTALL)


def collect_habr(queries: list[str], retrieved_at: str) -> dict:
    companies = []
    for query in queries:
        url = HABR_RSS.format(query=urllib.parse.quote(query, safe=""))
        try:
            feed = fetch_text(url)
        except RuntimeError as exc:
            print(f"warn: {exc}", file=sys.stderr)
            continue
        items = ITEM_RE.findall(feed)
        titles = [TITLE_RE.search(i).group(1).strip() for i in items if TITLE_RE.search(i)]
        links = [LINK_RE.search(i).group(1).strip() for i in items if LINK_RE.search(i)]
        latin = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
        slug = latin or "q-" + hashlib.sha1(query.encode("utf-8")).hexdigest()[:8]
        if not titles:
            companies.append({
                "id": f"{slug}--missing",
                "name": query,
                "country": "RU",
                "cohort": "RF",
                "site": None,
                "roles": [],
                "domains": [],
                "services": [],
                "pak": "none",
                "evidence": [{"url": url, "retrievedAt": retrieved_at, "kind": "news", "note": "0 публикаций"}],
                "source": "collect.py:habr",
                "quality": "missing",
                "needsReview": True,
                "caveats": ["поиск не вернул публикаций: это не доказательство отсутствия компании"],
            })
            continue
        companies.append({
            "id": f"{slug}--habr",
            "name": query,
            "country": "RU",
            "cohort": "RF",
            "site": None,
            "roles": [],
            "domains": [],
            "services": [],
            "pak": "none",
            "mentions": len(titles),
            "titles": titles[:3],
            "evidence": [{"url": url, "retrievedAt": retrieved_at, "kind": "news",
                          "note": f"{len(titles)} публикаций"}]
                       + [{"url": link, "retrievedAt": retrieved_at, "kind": "news"} for link in links[:3]],
            "source": "collect.py:habr",
            "quality": "estimated",
            "needsReview": True,
            "caveats": ["публикации подтверждают активность, а не роль developer/integrator"],
        })
        time.sleep(2)
    return {
        "schemaVersion": 1,
        "snapshotDate": retrieved_at,
        "cohorts": cohort_meta("collect.py:habr"),
        "sources": [{"id": "habr", "url": "https://habr.com/ru/rss/search/", "retrievedAt": retrieved_at,
                     "kind": "news", "status": "ok"}],
        "companies": companies,
        "warnings": [
            "поиск по публикациям не является реестром; записи с needsReview не участвуют в долях до проверки",
        ],
    }


def merge_curated(base: dict, manual_path: Path) -> dict:
    extra = json.loads(manual_path.read_text(encoding="utf-8"))
    known = {c.get("id") for c in base.get("companies", [])}
    added = 0
    for company in extra.get("companies", []):
        if company.get("id") in known:
            continue
        base.setdefault("companies", []).append(company)
        known.add(company.get("id"))
        added += 1
    base.setdefault("warnings", []).append(
        f"добавлено {added} записей из {manual_path.name}; курируемые записи не перезаписываются")
    return base


def check_sites(snapshot: dict, retrieved_at: str, timeout: int = 20) -> int:
    """Проверить доступность сайтов компаний. Недоступный сайт не удаляет
    запись: он помечается `siteStatus`, чтобы отчёт показал это явно."""
    failures = 0
    for company in snapshot.get("companies", []):
        site = company.get("site")
        if not site:
            company["siteStatus"] = "missing"
            continue
        request = urllib.request.Request(site, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                company["siteStatus"] = f"ok:{response.status}"
        except urllib.error.HTTPError as exc:
            company["siteStatus"] = f"http:{exc.code}"
            failures += 1
        except (urllib.error.URLError, TimeoutError) as exc:
            company["siteStatus"] = f"unreachable:{type(exc).__name__}"
            failures += 1
        evidence = company.setdefault("evidence", [])
        evidence.append({"url": site, "retrievedAt": retrieved_at, "kind": "site_check",
                         "note": company["siteStatus"]})
    snapshot.setdefault("warnings", []).append(
        f"проверка сайтов: недоступно {failures} из {len(snapshot.get('companies', []))}; "
        "недоступность сайта не означает отсутствие компании")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Снимок компаний ИИ-рынка")
    parser.add_argument("--source", choices=["openrouter", "habr"], default="openrouter")
    parser.add_argument("--query", action="append", default=[], help="запрос для --source habr")
    parser.add_argument("--in", dest="inp", type=Path, help="существующий снимок для слияния")
    parser.add_argument("--merge", type=Path, action="append", default=[], help="курируемый снимок")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--as-of", default=None, help="дата снимка ISO; по умолчанию сегодня")
    parser.add_argument("--check-sites", action="store_true",
                        help="проверить доступность site у каждой компании и записать siteStatus")
    args = parser.parse_args(argv)

    retrieved_at = args.as_of or now_date()
    try:
        if args.inp:
            snapshot = json.loads(args.inp.read_text(encoding="utf-8"))
        elif args.source == "openrouter":
            snapshot = collect_openrouter(retrieved_at)
        else:
            if not args.query:
                print("error: --source habr требует хотя бы один --query", file=sys.stderr)
                return 2
            snapshot = collect_habr(args.query, retrieved_at)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    for path in args.merge:
        snapshot = merge_curated(snapshot, path)

    seen: set[str] = set()
    deduped = []
    for company in snapshot.get("companies", []):
        if company.get("id") in seen:
            continue
        seen.add(company.get("id"))
        deduped.append(company)
    snapshot["companies"] = deduped

    if args.check_sites:
        check_sites(snapshot, retrieved_at)

    snapshot["snapshotDate"] = retrieved_at
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    companies = snapshot.get("companies", [])
    need = sum(1 for c in companies if c.get("needsReview"))
    print(f"ok: {args.out} — {len(companies)} записей, требуют проверки {need}, снимок {retrieved_at}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())