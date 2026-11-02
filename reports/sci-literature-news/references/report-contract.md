# Контракт профиля, candidates, analysis и HTML

## 1. profile.md

Путь по умолчанию: `.sci-literature-news/profile.md`.

```markdown
# Scientific profile — literature news

## Profile
- Name: ...
- Affiliation: ...
- ORCID: ...
- Google Scholar: ...
- Scopus: ...
- ResearchGate: ...
- Personal site: ...
- Profile source: ...
- Profile fetched at: ...

## Directions
| id | Direction | Query terms (EN) | Notes |
|---|---|---|---|
| D1 | Графовые нейронные сети | graph neural networks | ... |

## Preferences
- Period months: 6
- From: 2026-05-02
- To: 2026-11-02
- Categories: Q1 journals; A* conferences; Q2 journals
- Languages: en
- Include preprints: false
- Max results per direction: 100
- Ranking source: SJR 2025; ICORE2026
- Report language: ru
- Last confirmed: 2026-11-02
```

Правила:

- направления и период показываются перед запуском;
- правки сохраняются в этот файл;
- `Last confirmed` обновляется только после подтверждения;
- без `Query terms (EN)` поиск не запускается: направление на русском
  переводится в английские термины и записывается сюда;
- личные данные не коммитятся.

## 2. candidates.json

```json
{
  "schemaVersion": 1,
  "generatedAt": "2026-11-02T11:55:00Z",
  "period": { "from": "2026-05-02", "to": "2026-11-02" },
  "profile": { "profile": {}, "directions": [], "preferences": {} },
  "queries": [
    { "direction_id": "D1", "query": "graph neural networks", "source": "OpenAlex" }
  ],
  "ranking": {
    "sjr": ".sci-literature-news/cache/sjr-2025.csv",
    "core": ".sci-literature-news/cache/core-a-star.csv",
    "note": "Q1/Q2 — SJR; A* — ICORE"
  },
  "papers": [
    {
      "id": "W123",
      "doi": "10.1234/example",
      "title": "...",
      "abstract": "...",
      "date": "2026-09-12",
      "year": 2026,
      "type": "article",
      "venue": "...",
      "venue_type": "journal",
      "authors": ["..."],
      "citations": 42,
      "direction_ids": ["D1"],
      "category": "q1",
      "ranking_evidence": ["SCImago SJR 2025 Q1"],
      "sjr": { "quartile": "Q1", "source": "SCImago SJR 2025", "year": "2025", "match": "field" },
      "core": null
    }
  ],
  "datasets": [
    {
      "doi": "10.5281/zenodo.10000001",
      "title": "...",
      "description": "...",
      "year": 2026,
      "publisher": "Zenodo",
      "license": "CC BY 4.0",
      "direction_ids": ["D1"]
    }
  ],
  "warnings": []
}
```

Категории: `q1`, `a_star`, `q2`, `unranked`. `unranked` не попадает в
основные таблицы, но остаётся в candidates для аудита.

## 3. analysis.json

```json
{
  "schemaVersion": 1,
  "generatedAt": "2026-11-02T12:00:00Z",
  "title": "...",
  "summary": "2–4 предложения о главных сдвигах за период.",
  "themes": [
    {
      "title": "...",
      "summary": "...",
      "directionIds": ["D1"],
      "confidence": "high",
      "evidence": ["10.1234/example"]
    }
  ],
  "selection": {
    "q1": ["10.1234/example"],
    "a_star": [],
    "q2": []
  },
  "datasets": [
    {
      "doi": "10.5281/zenodo.10000001",
      "name": "...",
      "description": "...",
      "year": 2026,
      "license": "CC BY 4.0",
      "directionIds": ["D1"]
    }
  ],
  "criteria": {
    "a_star": ["..."],
    "q1": ["..."],
    "q2": ["..."],
    "study": ["..."],
    "caveats": ["..."]
  },
  "ranking_notes": ["..."],
  "warnings": []
}
```

Правила:

- `themes[].evidence` — только DOI из `candidates.papers`;
- `datasets[].doi` — только DOI из `candidates.datasets` (или URL, если
  источник не DataCite);
- `selection` необязателен: без него берутся все подтверждённые категории;
- synthesis не должен пересказывать все статьи: только сдвиги, противоречия,
  пробелы и практические следствия;
- `confidence` — `high`, `medium`, `low`; без evidence максимум `low`.

## 4. HTML-контракт

Обязательные блоки:

- `id="themes"` — синтез;
- `id="q1"` — таблица Q1;
- `id="a-star"` — таблица A*;
- `id="q2"` — таблица Q2;
- `id="datasets"` — датасеты;
- `id="criteria"` — критерии A*/Q1;
- `id="method"` — методика;
- `id="report-data"` — JSON сводки;
- `data-paper="1"` у строк, `paper-search`, `paper-direction`,
  `paper-category`, `paper-sort` — фильтры.

Запрещено:

- `<script src>`, `<link rel=stylesheet>`, `@import`, CDN;
- `fetch`, `XMLHttpRequest`, WebSocket;
- внешние шрифты и картинки;
- неэкранированный пользовательский текст;
- `javascript:` ссылки;
- внешние домены, кроме DOI, OpenAlex, DataCite, SCImago, ICORE, Crossref,
  ORCID (ссылки, не ресурсы).

Ссылки DOI открываются в новой вкладке; HTML не делает запросов.

## 5. Качество

| Уровень | Что означает |
|---|---|
| `measured` | OpenAlex/DataCite: дата, DOI, площадка, авторы |
| `derived` | SJR-квартиль и ICORE A* после сопоставления |
| `expert` | синтез и критерии, с DOI |
| `estimated` | приближение, если ranking неполный |
| `missing` | нет данных; не подставляется правдоподобное значение |

## 6. UX-поток

1. Показать `profile.md`: профиль, направления, период.
2. Спросить: подтвердить, изменить направления, изменить период.
3. Сохранить правки; обновить `Last confirmed` только после «подтверждаю».
4. Запустить поиск.
5. Показать `candidates` summary и спросить, продолжать ли синтез.
6. Записать `analysis.json`.
7. Собрать `report.html`.
8. Проверить `check_report.py` и `validate_analysis.py --strict`.
9. Открыть HTML; при необходимости поправить analysis и пересобрать.