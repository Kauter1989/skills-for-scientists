# Контракт профиля, снимка, анализа и отчёта

Нормативный документ `ai-market-landscape`. Описывает четыре артефакта и
правила их совместимости.

## 1. Профиль `landscape.md`

Путь по умолчанию: `.ai-market-landscape/landscape.md`. Шаблон:
`templates/landscape.md`.

Обязательны разделы:

- `## Profile` — имя, дата создания, `Last confirmed`;
- `## Cohorts` — таблица когорт `id | Label | Registry | Include`;
- `## Taxonomy` — таблица осей `axis | values`;
- `## Preferences` — `Period`, `Cohort focus`, `Sources`, `Gap threshold`,
  `Report language`.

Правила:

- таксономия объявляется до сбора;
- `Last confirmed` обновляется командой `confirm` и только после решения
  аналитика;
- период содержит годы; изменение периода фиксируется в профиле.

## 2. Снимок `companies-YYYY-MM-DD.json`

```json
{
  "schemaVersion": 1,
  "snapshotDate": "2026-11-06",
  "cohorts": {"RF": {"label": "...", "registry": "...", "source": "..."},
              "WORLD": {"label": "...", "registry": "...", "source": "..."}},
  "sources": [{"id": "openrouter", "url": "https://...", "retrievedAt": "2026-11-06",
               "kind": "catalog", "status": "ok"}],
  "companies": [
    {
      "id": "sber",
      "name": "Сбер",
      "country": "RU",
      "cohort": "RF",
      "founded": null,
      "site": "https://sber.ru",
      "roles": ["developer", "integrator"],
      "domains": ["fin"],
      "services": ["consulting", "integration"],
      "pak": "none",
      "delivery": "api",
      "evidence": [{"url": "https://sber.ru", "retrievedAt": "2026-11-06", "kind": "company_site"}],
      "source": "manual curator",
      "quality": "estimated",
      "needsReview": false,
      "caveats": ["домен выведен из описания линейки"]
    }
  ],
  "warnings": []
}
```

Обязательные поля компании: `id`, `name`, `cohort` (`RF` или `WORLD`),
`roles`, `pak`, `evidence`, `quality`.

Поле `needsReview: true` означает: источник подтверждает присутствие, но не
роль на рынке. Такие записи видны в отчёте и не входят в доли.

## 3. Анализ `analysis.json`

Собирается `analyze.py` из снимка. Ключи:

| Ключ | Содержание |
|---|---|
| `taxonomy` | набор осей, по которым проверялся снимок |
| `thresholds` | пороги доли и пробела |
| `cohorts.RF`, `cohorts.WORLD` | метрики когорты с метками качества |
| `growth` | динамика по годам основания с меткой `estimated` или `missing` |
| `gaps` | разница долей по каждой области, с меткой качества |
| `missingInRf` | области с нулём в РФ и не менее 3 в мире |
| `roleGap` | роли, которые есть в мире и отсутствуют в РФ |
| `changes` | сравнение с предыдущим снимком или явный `missing` |
| `pending` | записи, ожидающие проверки, и их источники |
| `caveats` | предупреждения снимка |

Правило: `analyze.py` не дополняет снимок данными, которых в нём нет.

## 4. Отчёт `report.html`

Один файл без сети. Обязательные блоки:

1. шапка с датой снимка, числом компаний и числом пробелов;
2. блок «Россия» с шестью метриками и таблицей компаний;
3. блок «Мир (без РФ)» в той же структуре;
4. блок «Разница рынков» с таблицей GAP и списком «есть в мире, нет в РФ»;
5. блок «Методика и качество данных» с ограничениями.

Требования к странице повторяют правила библиотеки: системные шрифты,
контраст не ниже 4,5:1, печать в A4, отсутствие внешних запросов.

## 5. Совместимость

- Снимки с разным `schemaVersion` не сливаются.
- Снимки с разными наборами осей сравниваются только по общим значениям.
- Отчёт собирается только из `analysis.json` и снимка; ручных правок в HTML
  не бывает.