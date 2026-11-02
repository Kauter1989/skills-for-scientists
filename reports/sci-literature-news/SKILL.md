---
name: sci-literature-news
description: >-
  Собирает персональный научный дайджест по сохранённым направлениям
  пользователя за выбранный период: публикации в журналах Q1, конференциях A*
  и журналах Q2, синтез ключевых тем, таблицу новых датасетов и критерии
  попадания в A*/Q1. В методике — ключевые слова, количество публикаций по
  источникам, диаграммы и явное покрытие A* по направлениям с ближайшими
  площадками. Профиль, направления и период хранятся в MD и
  показываются перед запуском. Use when asked for a scientific literature
  news digest, research monitoring report, new papers by research direction,
  Q1/A*/Q2 venue report, new datasets in a field, or a repeatable literature
  watch with saved preferences. Триггеры: научный дайджест, новости
  литературы, литературный обзор за период, новые статьи по направлению,
  Q1 журналы, A* конференции, Q2 журналы, новые датасеты, научный профиль,
  literature news, research digest, paper monitoring.
---

# sci-literature-news — научный дайджест литературы

Навык ведёт личный профиль научных направлений и периода, ищет публикации в
OpenAlex/DataCite, раскладывает их по Q1/A*/Q2 с ranking-доказательствами,
синтезирует ключевые темы и собирает один автономный HTML-отчёт.

Домен — отчётность: каталог `reports/sci-literature-news/`. Навык не заменяет
систематический обзор и не читает полные тексты.

## Когда применять

- нужен регулярный обзор новых статей по своим направлениям;
- нужно отделить Q1-журналы, A*-конференции и Q2-журналы;
- нужно увидеть новые датасеты в своей области;
- нужно объяснить, почему работа попала в A*/Q1;
- нужен воспроизводимый отчёт с сохранёнными направлениями и периодом.

Не применять:

- для полного systematic review с full-text скринингом;
- для оценки конкретного исследователя или h-index;
- для официального JCR/Scopus-отчёта без соответствующих лицензий;
- для автоматического присвоения квартиля без ranking-источника.

## Состояние

```text
.sci-literature-news/
├── profile.md                 # профиль, направления, период
├── cache/
│   ├── sjr-2025.csv           # SJR-кэш
│   └── core-a-star.csv        # ICORE A*
├── candidates.json            # найденные работы и датасеты
├── analysis.json              # синтез, датасеты, критерии
└── reports/
    └── sci-literature-news-YYYY-MM-DD.html
```

### profile.md

Шаблон: `templates/profile.md`.

Главное:

- `## Directions` — таблица `id | Direction | Query terms (EN) | Notes`.
- `## Preferences` — период, категории, языки, лимиты, ranking source.
- `Last confirmed` обновляется только после подтверждения пользователем.

Если профиль не предоставлен, направления должны дать пользователь. Если
профиль есть (ORCID, Google Scholar, Scopus, сайт, текст), агент извлекает
направления и английские query terms, затем сохраняет их в MD.

## Процедура

### 1. Загрузить или создать профиль

```bash
python scripts/profile.py --file .sci-literature-news/profile.md show --json
```

Если файла нет:

- запросить научный профиль (ORCID / Google Scholar / Scopus / сайт / текст)
  **или** список направлений;
- для каждого направления записать английские `Query terms (EN)`;
- создать файл:

```bash
python scripts/profile.py --file .sci-literature-news/profile.md init \
  --name "Имя" \
  --direction "Графовые нейронные сети" --query "graph neural networks" \
  --direction "Сегментация медицинских изображений" --query "medical image segmentation"
```

Если профиль предоставлен, прочитать его, предложить направления и сохранить
их в `profile.md`; не выдумывать направления, которых нет в профиле.

### 2. Показать направления и период, получить правки

Показать пользователю:

- сохранённые направления;
- период (по умолчанию **6 месяцев**);
- категории Q1/A*/Q2;
- источники ranking.

Спросить: подтвердить / изменить направления / изменить период.

После правок:

```bash
python scripts/profile.py --file .sci-literature-news/profile.md check
python scripts/profile.py --file .sci-literature-news/profile.md confirm
```

`confirm` ставит `Last confirmed`. **До подтверждения поиск не запускать.**

Изменить период:

```bash
python scripts/profile.py --file .sci-literature-news/profile.md set-period --months 6
# или явно:
python scripts/profile.py --file .sci-literature-news/profile.md set-period \
  --months 6 --from 2026-05-02 --to 2026-11-02
```

Период и направления сохраняются в `profile.md`; при следующем запуске
показываются снова.

### 3. Построить ranking-кэш

Первый запуск (один раз; нужен интернет):

```bash
python scripts/update_rankings.py \
  --out-dir .sci-literature-news/cache \
  --year 2025
```

Что происходит:

- `sjr-2025.csv` — SJR-панель; Q1/Q2 считаются по SJR внутри broad ASJC
  field. Это **derived**-квартиль, не официальная узкая subject category.
- `core-a-star.csv` — официальные A* строки ICORE2026.

Если есть официальный CSV SJR с колонками
`sourceid,title,issn,year,field,field_code,sjr,quartile,source`, передайте
его в `collect_literature.py --sjr-cache`. Тогда используется официальный
квартиль из файла.

Без кэшей отчёт всё равно собирается, но Q1/Q2/A* не присваиваются:
работы получают `unranked`. Не подставляйте категории «на глаз».

### 4. Собрать кандидатов

```bash
python scripts/collect_literature.py \
  --profile .sci-literature-news/profile.md \
  --out .sci-literature-news/candidates.json \
  --mailto you@example.org \
  --sjr-cache .sci-literature-news/cache/sjr-2025.csv \
  --core-cache .sci-literature-news/cache/core-a-star.csv
```

Скрипт:

- ищет каждое направление в OpenAlex;
- ищет датасеты в DataCite;
- дедуплицирует по DOI/названию;
- присваивает `q1`, `a_star`, `q2` или `unranked`;
- сохраняет запросы, период, ranking evidence и warnings.

Проверить summary:

```bash
python - <<'PY'
import json
c=json.load(open('.sci-literature-news/candidates.json',encoding='utf-8'))
from collections import Counter
print(Counter(p['category'] for p in c['papers']))
print('datasets',len(c['datasets']))
print('warnings',c['warnings'])
PY
```

Если категорий Q1/A*/Q2 нет, проверить кэши и запросы. Не расширять период
молча — сначала показать пользователю.

### 5. Синтез

Прочитать аннотации кандидатов и написать `analysis.json`:

- `summary` — 2–4 предложения о главных сдвигах;
- `themes` — 3–6 тем; каждая с DOI-доказательствами;
- `datasets` — новые датасеты из DataCite с описанием, годом, лицензией;
- `criteria` — venue gate + `criteria.tracks`: для каждого направления
  конкретные аналоги, новые датасеты, протокол валидации, аблации и
  воспроизводимость;
- `aStarCoverage` — покрытие A* по **каждому** направлению: `found`,
  `venues`, `target` и `nearest` с пояснениями; для `found: 0` список
  ближайших A*-площадок обязателен;
- `selection` — необязательный список DOI, если нужно убрать работы;
- `warnings` — что не проверено.

Правила:

- не пересказывать каждую статью;
- не утверждать то, чего нет в аннотации/метаданных;
- каждая тема — с DOI из `candidates.papers`;
- датасет — с DOI из `candidates.datasets` (или URL, если источник не DataCite);
- Q1/Q2 — свойство журнала, A* — конференции;
- если доказательств нет, `confidence: low` и предупреждение.

### 6. Собрать HTML

```bash
python scripts/build_report.py \
  --candidates .sci-literature-news/candidates.json \
  --analysis .sci-literature-news/analysis.json \
  -o .sci-literature-news/reports/sci-literature-news-2026-11-02.html \
  --strict
```

`--strict` требует:

- каждую тему с DOI-доказательством;
- каждый датасет с DOI/URL;
- непустые criteria.

Раздел «04 · Методика» собирается автоматически:

- ключевые слова из `candidates.queries`;
- количество записей по источникам OpenAlex/DataCite: найдено и отобрано;
- публикации по категориям Q1/A*/Q2;
- отобрано по направлениям и топ площадок;
- покрытие A* по направлениям и блок «A* не найден» с ближайшими
  A*-площадками из `analysis.aStarCoverage`.

Все диаграммы — inline HTML/CSS, без Chart.js, CDN и сетевых запросов.

### 7. Проверить

```bash
python scripts/check_report.py .sci-literature-news/reports/sci-literature-news-2026-11-02.html
python scripts/validate_analysis.py .sci-literature-news/candidates.json .sci-literature-news/analysis.json --strict
```

Проверить глазами:

- Q1/A*/Q2 не перепутаны;
- у каждой категории есть ranking evidence;
- датасеты не дублируются;
- ссылки DOI открываются;
- фильтры по направлению/категории работают;
- в методике видны ключевые слова, объём по источникам и диаграммы;
- для каждого направления с `0` A* явно написан «A* не найден» и ближайшие
  альтернативы;
- HTML не делает внешних запросов.

## Критерии A*/Q1/Q2

### Venue-level

- **A*** — ICORE/CORE A* для указанного source; A* — ранг конференции.
- **Q1** — SJR верхние 25% в категории/году.
- **Q2** — SJR 25–50% в категории/году.

Ранг площадки — только входной фильтр. Он не доказывает качество статьи.

### Track-level: что работа должна доказать

Для каждого направления в `analysis.criteria.tracks` укажите:

- **обязательные аналоги** — с какими конкретными моделями/методами сравниваться
  (например, для сегментации: nnU-Net, U-Net, SwinUNETR, SAM/MedSAM, M2SNet;
  для foundation models: BiomedCLIP/FetalCLIP, MedSAM, linear probe и full
  fine-tuning; для spine: SpineTool, 3D shape descriptors, ручная морфометрия);
- **новые данные** — на каких опубликованных датасетах валидировать и как
  расширять задачи профиля (например, ISLES 2017, PneumoCT-202, PAXRay++,
  PelviSet, PUWF-AV, MedGround-35K, COBRA, TotalSegmentator v3);
- **протокол** — внешний test set, zero/few-shot, cross-centre, low-label,
  blinded manual validation, метрики Dice/HD95/ASD/калибровка;
- **аблации** — что именно проверяли: encoder, prompt, semi-supervision,
  noise model, PSF, representation;
- **воспроизводимость** — код, чекпойнты, split'ы, версии датасетов, лицензии.

Если для трека нет нового датасета, это нужно сказать явно и указать, на каких
внешних данных проверять. Пример: для graphics за период не найдено нового
DataCite-датасета — использовать Mip-NeRF 360 / DL3DV / Sponza и добавить
новый датасет при публикации.

### Покрытие A* по направлениям

В `analysis.aStarCoverage` — запись на каждое направление:

- `found` — число A*-работ в выборке; `venues` — где они;
- `target` — целевые A*-площадки для следующей итерации;
- при `found: 0` — обязательный `nearest` со списком конкретных A*-площадок
  и пояснением, почему они ближайшие.

В отчёте это показывается диаграммой и явными карточками. Если A* нет,
нельзя молча подставлять Q1 или площадку без A*: MICCAI — A, не A*;
SIGGRAPH / SIGGRAPH Asia — A* для graphics; CVPR / ICCV / ECCV / NeurIPS /
ICML / AAAI — ближайшие A* для медицинских изображений, нейронаук и
scientific ML.

### Study-level

- peer-reviewed article/review, не препринт и не редакционная заметка;
- дата входит в период;
- тема соответствует направлению;
- DOI и достаточные метаданные;
- нет явного retraction;
- площадка подтверждена ranking-кэшем или помечена `unranked`;
- аннотация доступна; full text не читался.

Подробно: `references/sources-and-rankings.md`.

## Границы и честность

- Ранг площадки — фильтр, не оценка статьи и не оценка исследователя.
- SJR-квартиль зависит от категории и года; кэш по broad ASJC field —
  приближение, это явно написано в отчёте.
- ICORE A* покрывает computer science; для других областей A* может не быть.
- OpenAlex/DataCite неполны; warnings и coverage обязательны.
- Синтез — суждение по аннотациям; он не заменяет чтение полного текста.
- Не добавлять статьи/датасеты, которых нет в candidates.
- Не публиковать профиль и отчёт с личными данными без решения пользователя.

## Типовые ошибки

| Симптом | Причина | Что делать |
|---|---|---|
| `profile not found` | нет MD | создать профиль/направления |
| `нет направлений` | пустая таблица | заполнить Directions |
| `Q1=0, A*=0` | нет кэшей | `update_rankings.py` |
| `unranked` у всех | ranking не совпал | проверить ISSN/venue; передать официальный CSV |
| `DOI отсутствует` | анализ выдумал DOI | исправить analysis по candidates |
| `theme без evidence` | нет цитаты | добавить DOI или снизить confidence |
| пустой HTML | нет analysis | заполнить analysis.json |
| внешние ресурсы | добавлен CDN | убрать; HTML только автономный |

## QA-чек-лист

- [ ] `profile.md` содержит направления и период.
- [ ] `profile.py check` проходит.
- [ ] `Last confirmed` обновлён после подтверждения.
- [ ] `update_rankings.py` выполнен или передан официальный CSV.
- [ ] `collect_literature.py` сохранил queries и period.
- [ ] В `candidates` есть Q1/A*/Q2 или явные `unranked`.
- [ ] Каждая тема имеет DOI-доказательство.
- [ ] Каждый датасет имеет DOI/URL.
- [ ] `aStarCoverage` покрывает все направления.
- [ ] Для направлений с `0` A* указаны ближайшие A*-площадки.
- [ ] В методике есть ключевые слова и диаграммы по источникам.
- [ ] `build_report.py --strict` зелёный.
- [ ] `check_report.py` — external resources: none.
- [ ] `validate_analysis.py --strict` зелёный.
- [ ] HTML открывается без сети; фильтры работают.
- [ ] Итог не выдаёт ranking за оценку статьи.

## Проверка примера

```bash
cd reports/sci-literature-news
python scripts/make_example.py
python scripts/build_report.py --example -o examples/example-report.html --strict
python scripts/check_report.py examples/example-report.html
python scripts/validate_analysis.py examples/example-candidates.json examples/example-analysis.json --strict
python scripts/profile.py --file examples/example-profile.md check
```

Ожидаемо: 9 работ (Q1 3, A* 3, Q2 3), 3 датасета, 4 темы, 4 направления
(D4 без публикаций — демонстрирует блок «A* не найден»); HTML без внешних
ресурсов. Пример синтетический: DOI и названия не являются реальными
публикациями.

## Файлы

| Файл | Содержание |
|---|---|
| `references/sources-and-rankings.md` | OpenAlex/DataCite/SJR/ICORE, критерии, ограничения |
| `references/report-contract.md` | profile/candidates/analysis/HTML |
| `scripts/profile.py` | чтение, проверка, подтверждение, период |
| `scripts/update_rankings.py` | SJR-кэш и ICORE A* |
| `scripts/collect_literature.py` | поиск и категоризация |
| `scripts/build_report.py` | HTML |
| `scripts/check_report.py` | автономность HTML |
| `scripts/validate_analysis.py` | evidence и категории |
| `scripts/make_example.py` | демо-данные |
| `templates/profile.md` | шаблон профиля |
| `templates/report.html` | шаблон HTML |
| `examples/` | профиль, candidates, analysis, готовый отчёт |

## Источники

- PRISMA 2020: <https://doi.org/10.1136/bmj.n71>
- PRISMA-S: <https://doi.org/10.1186/s13643-020-01542-z>
- OpenAlex: <https://docs.openalex.org/>
- DataCite: <https://schema.datacite.org/>
- SCImago: <https://www.scimagojr.com/>
- ICORE: <https://portal.core.edu.au/conf-ranks/>