# Источники, ranking и критерии

Дата снимка: `2026-11-02`.

## 1. OpenAlex

- База: <https://api.openalex.org/works>.
- Ключ не обязателен; для polite pool укажите `--mailto`.
- Основные поля: `id`, `doi`, `display_name`, `publication_date`,
  `publication_year`, `type`, `primary_location.source` (название, ISSN, тип),
  `authorships`, `cited_by_count`, `open_access`, `primary_topic`,
  `abstract_inverted_index`.
- Поиск: `search=<query>`, фильтр
  `from_publication_date`, `to_publication_date`.
- Абстракт приходит инвертированным индексом; скрипт восстанавливает его.
- Ограничения: не все записи имеют DOI/абстракт; source type не всегда
  отражает «журнал/конференция»; метаданные обновляются с задержкой.
- Не использовать `cited_by_count` как оценку качества статьи.

## 2. DataCite

- API: <https://api.datacite.org/dois>.
- Фильтр `resource-type-id=dataset`; поиск по `query`.
- Поля: DOI, titles, descriptions, publicationYear, publisher, rightsList,
  creators, url.
- Датасеты могут не иметь лицензии или описания; отчёт показывает `—`.
- DataCite не гарантирует, что датасет связан с найденной статьёй; связь
  указывается только при наличии DOI/метаданных.

## 3. SJR и Q1/Q2

Официальный источник: SCImago Journal & Country Rank,
<https://www.scimagojr.com/>.

В навыке используется локальный кэш, построенный из открытой панели
`Michael-E-Rose/SCImagoJournalRankIndicators` (MIT):
<https://github.com/Michael-E-Rose/SCImagoJournalRankIndicators>.

Методика кэша:

1. взять один год (по умолчанию 2025);
2. для каждой пары «журнал × ASJC field» взять SJR;
3. отсортировать по SJR внутри field;
4. `Q1` — верхние 25%, `Q2` — 25–50%, `Q3` — 50–75%, `Q4` — 75–100%.

Это **derived**-квартиль по широкому ASJC field, а не официальный квартиль
SCImago по узкой subject category. Поэтому в отчёте всегда печатаются:

- год;
- field/категория;
- источник (`SCImago SJR 2025`);
- пометка `match: field` или `match: best`.

Если нужна официальная категория, положите свой CSV и передайте его через
`--sjr-cache`; формат:

```csv
sourceid,title,issn,year,field,field_code,sjr,quartile,source
```

Правила:

- без ISSN и подтверждённого title квартиль не присваивается;
- если журнал есть в нескольких категориях, выбирается категория,
  ближайшая к `primary_topic.field`, иначе лучший квартиль с пометкой `best`;
- `unranked` — не «плохо», а «нет доказательства»;
- Q1/Q2 — свойство журнала, не статьи.

## 4. ICORE / CORE A*

Официальный портал: <https://portal.core.edu.au/conf-ranks/>.

- A* — флагманские конференции, около 7,5% рейтингуемых CS-площадок.
- Кэш `update_rankings.py` скачивает строки `A*` для выбранного source
  (по умолчанию `ICORE2026`).
- Сопоставление: акроним в названии площадки → точное название → fuzzy
  token overlap ≥ 0.72.
- A* относится к конференции, не к статье. Совпадение названия/акронима
  всё равно требует человеческой проверки для спорных случаев.
- ICORE покрывает computer science; для других дисциплин A* может не быть.

## 5. Критерии включения

### Venue-level

| Категория | Источник | Критерий | Что доказывает | Что не доказывает |
|---|---|---|---|---|
| A* | ICORE/CORE | действующий A* в указанном source | ранг конференции | качество конкретной статьи |
| Q1 | SJR | верхние 25% в категории/году | ранг журнала | качество статьи, цитируемость здесь и сейчас |
| Q2 | SJR | 25–50% в категории/году | ранг журнала | «хуже Q1» автоматически |

### Study-level

Работа попадает в отчёт, если:

1. это peer-reviewed article/review, не препринт/редакционная заметка;
2. дата входит в период;
3. тема совпадает с сохранённым направлением;
4. есть DOI и достаточные метаданные;
5. нет явного признака retraction;
6. площадка подтверждена ranking-кэшем или явно помечена `unranked`;
7. аннотация доступна для синтеза (если нет — `missing`).

Наличие кода/датасета — плюс, но не обязательное условие.

## 6. Ограничения и честность

- Ранжирование — фильтр, а не оценка исследователя.
- Один журнал может быть Q1 и Q2 в разных категориях.
- ICORE A* не покрывает не-CS области.
- OpenAlex/DataCite неполны; отчёт показывает warnings.
- Синтез основан на аннотациях, если не указано иное.
- Ссылки DOI ведут наружу; HTML не загружает внешние ресурсы.
- Кэши ranking не коммитятся в репозиторий; они строятся локально.

## 7. Ссылки

- OpenAlex: <https://docs.openalex.org/>
- OpenAlex paper: <https://arxiv.org/abs/2205.01833>
- DataCite: <https://schema.datacite.org/>
- SCImago: <https://www.scimagojr.com/>
- SJR paper: <https://doi.org/10.1016/j.joi.2009.11.005>
- ICORE: <https://portal.core.edu.au/conf-ranks/>
- PRISMA 2020: <https://doi.org/10.1136/bmj.n71>
- PRISMA-S: <https://doi.org/10.1186/s13643-020-01542-z>