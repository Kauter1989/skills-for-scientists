# Контракт HTML-страницы

Нормативный документ скилла `dev-pr-report-html`: что обязано быть на
странице, в каком виде и в каком формате передаются данные.

## 1. Файл

- Один `.html`, UTF-8, без сборки и зависимостей.
- CSS — в `<style>`, JS — в `<script>`, данные — в
  `<script type="application/json" id="report-data">`.
- Никаких `http(s)://` в `src`, `href`, `@import`, `url()`. Ссылки на
  внешние источники допустимы только как текст в реестре доказательств.
- Шрифты — системные; иконки — Unicode или inline SVG.
- Открывается через `file://`; при печати даёт читаемый PDF A4.

## 2. Порядок блоков

1. **Шапка** — название, тип (`feature` / `milestone` / `session`), диапазон,
   дата снимка, агент и модель, качество данных.
2. **Вердикт** — одно предложение о состоянии изменения + шесть KPI-карточек.
3. **Матрица** CWU × ADS с подсветкой квадранта и точкой.
4. **Шесть секций** строго в порядке:
   `ftb → ads → cli → air → hr → cwu`.
5. **Реестр доказательств** — утверждение, источник, дата.
6. **Решения** — `now` / `next` / `accept`.
7. **Метод** — команды сбора, допущения, известные ограничения.

Каждая секция содержит:

- номер и emoji-метку из задания;
- большое значение, единицу и бейдж качества;
- статус (`green` / `amber` / `red` / `unknown`);
- `summary` — 1–2 предложения;
- `drivers` — что дало именно это число;
- визуал (график/таблица/полосы);
- `evidence` — ссылки на файлы, строки, команды;
- `verdict` — что из этого следует;
- `actions` — что делать.

## 3. JSON-схема

Версия схемы — 1. Все поля, кроме `meta` и `metrics`, необязательны.
Отсутствующая метрика заменяется карточкой «нет данных».

```json
{
  "schema_version": 1,
  "meta": {
    "title": "public-share-link",
    "subtitle": "Публичная ссылка на задачу",
    "scope": "feature",
    "range": "v1.4.0..HEAD",
    "date": "2026-10-31",
    "repo": "example-service",
    "branch": "feature/public-share-link",
    "agent": "opencode / model-id",
    "commits": 9,
    "changed_loc": 1840,
    "files": 37,
    "quality": "derived",
    "budget": {"tokens": 1500000, "amount": 3.4, "currency": "USD"},
    "notes": "Свободный текст, одна строка."
  },

  "verdict": {
    "status": "amber",
    "headline": "Изменение принимается с оговорками: архитектура расширена без ADR.",
    "text": "1–3 предложения, согласованные с числами ниже."
  },

  "metrics": {
    "ftb": {
      "value": 1842310,
      "unit": "tokens",
      "quality": "measured",
      "status": "amber",
      "summary": "…",
      "drivers": ["…"],
      "evidence": [{"claim": "…", "source": "sessions/abc.json"}],
      "verdict": "…",
      "actions": ["…"],
      "parts": [{"label": "input", "value": 1240000}],
      "normalized": [{"label": "tokens / 100 LOC", "value": "100 121"}],
      "series": [{"label": "cycle 1", "value": 210000}]
    },

    "ads": {
      "value": 18.4,
      "unit": "%",
      "quality": "expert",
      "status": "red",
      "summary": "…",
      "drivers": ["…"],
      "evidence": [{"claim": "…", "source": "docs/adr/0003-layers.md"}],
      "verdict": "…",
      "actions": ["…"],
      "contract": {
        "name": "Слои приложения",
        "source": "docs/adr/0003-layers.md",
        "assumed": false
      },
      "violations": [
        {
          "severity": "critical",
          "rule": "domain не импортирует infrastructure",
          "location": "src/domain/pricing.py:14",
          "note": "Импорт SessionLocal ради проверки остатка.",
          "weight": 5
        }
      ],
      "compliant": [{"rule": "…", "note": "…"}]
    },

    "cli": {
      "value": 1.8,
      "unit": "×",
      "quality": "derived",
      "status": "amber",
      "summary": "…",
      "drivers": ["…"],
      "evidence": [{"claim": "…", "source": "git diff --numstat"}],
      "verdict": "…",
      "actions": ["…"],
      "entities": [
        {"kind": "modules", "count": 12, "weight": 1, "total": 12}
      ],
      "blast_radius": 9,
      "top_modules": [{"name": "services/budget.py", "importers": 7}]
    },

    "air": {
      "value": 26.5,
      "unit": "%",
      "quality": "derived",
      "status": "amber",
      "summary": "…",
      "drivers": ["…"],
      "evidence": [{"claim": "…", "source": "gh run list"}],
      "verdict": "…",
      "actions": ["…"],
      "attempts": 34,
      "failed": 9,
      "cycles": 7,
      "loops": 1.4,
      "thrash": 2,
      "interventions": 1,
      "series": [{"label": "cycle 1", "attempts": 4, "failed": 3}]
    },

    "hr": {
      "value": 1.1,
      "unit": "на 1000 LOC",
      "quality": "derived",
      "status": "amber",
      "summary": "…",
      "drivers": ["…"],
      "evidence": [{"claim": "…", "source": "find_spec…"}],
      "verdict": "…",
      "actions": ["…"],
      "confirmed": [
        {
          "type": "phantom_api",
          "symbol": "Session.commit_all()",
          "location": "services/budget.py:88",
          "evidence": "AttributeError в тесте"
        }
      ],
      "unconfirmed": [{"type": "missing_import", "symbol": "…", "note": "…"}],
      "checks": [
        {"name": "import resolution", "result": "34 / 35", "note": "1 внешний, не установлен"}
      ]
    },

    "cwu": {
      "value": 62,
      "unit": "%",
      "quality": "measured",
      "status": "amber",
      "summary": "…",
      "drivers": ["…"],
      "evidence": [{"claim": "…", "source": "session tool log"}],
      "verdict": "…",
      "actions": ["…"],
      "coverage": 62,
      "window": 41,
      "relevant": 34,
      "read": 21,
      "read_list": ["docs/adr/0003-layers.md"],
      "missed_list": ["src/app/services/budget.py"]
    }
  },

  "matrix": {
    "cw": "low",
    "ads": "high",
    "title": "Слепое нарушение",
    "text": "Агент не дочитал контракт и переопределил слой."
  },

  "evidence": [
    {"claim": "9 коммитов в диапазоне", "source": "git log v1.4.0..HEAD", "date": "2026-10-31"}
  ],

  "actions": [
    {"priority": "now", "text": "Добавить ADR на новый слой.", "owner": "автор изменения"},
    {"priority": "next", "text": "Разбить ревью по слоям.", "owner": "ревьюер"}
  ],

  "method": {
    "commands": ["python scripts/collect_metrics.py …"],
    "notes": ["ADS проверен вручную по docs/adr/0003-layers.md."],
    "limitations": ["Телеметрия токенов — оценка по словам, ±30 %."]
  }
}
```

Правила схемы:

- `value` — число, не строка; форматирование делает страница.
  Для отсутствующей метрики `value: null`, `quality: "missing"`.
- `status` — только `green`, `amber`, `red`, `unknown`.
- `weight` в нарушениях и сущностях — из `references/metrics.md`.
- `unit` — короткая строка (`%`, `tokens`, `×`, `на 1000 LOC`).
- `series` — не более 24 точек; подписи короткие.
- Даты — ISO `YYYY-MM-DD`.
- Никаких HTML-фрагментов в строковых полях: страница экранирует всё.

## 4. Дизайн-токены

| Токен | Значение | Назначение |
|---|---|---|
| `--paper` | `#f6f5f2` | фон документа |
| `--card` | `#ffffff` | карточки и секции |
| `--ink` | `#14181f` | основной текст |
| `--muted` | `#5f6875` | подписи, единицы |
| `--line` | `#dfe2e7` | границы, сетка |
| `--accent` | `#1f5f5b` | основной акцент |
| `--green` | `#1f7a4d` | норма |
| `--amber` | `#a96500` | внимание |
| `--red` | `#b42318` | нарушение |
| `--violet` | `#6d5aa8` | expert-суждение |

Типографика: заголовок страницы 40–44 px, заголовок секции 24–26 px,
значение метрики 48–56 px, тело 15–16 px, подписи 12–13 px. Межстрочный
интервал 1,5 для тела. Максимальная ширина 1180 px.

Цвет не единственный носитель смысла: рядом со статусом всегда стоит слово
или иконка. Числа — табличные цифры (`font-variant-numeric: tabular-nums`).

## 5. Визуалы

| Секция | Обязательный визуал | Допустимая замена |
|---|---|---|
| FTB | состав бюджета (stacked bar) + динамика по циклам | таблица состава |
| ADS | шкала 0–100 % + таблица нарушений | список с severity |
| CLI | полосы по типам сущностей + blast radius | таблица |
| AIR | линия попыток/провалов по циклам + три стата | таблица |
| HR | таблица подтверждённых + список проверок | список |
| CWU | две полосы (coverage/window) + квадрант | таблица |

Графики рисуются inline SVG без библиотек. Ось значений подписывается,
нулевая линия видна, подписи не наезжают. Если данных меньше двух точек,
график заменяется таблицей.

## 6. Матрица CWU × ADS

Оси: CWU coverage (низкий `<40 %`, высокий `>70 %`), ADS (низкий `<5 %`,
высокий `>15 %`). Пограничные значения — отдельная зона «серая».

| Квадрант | Заголовок | Смысл |
|---|---|---|
| низкий CWU / низкий ADS | Слепая удача | малое изменение, связность не проверена |
| низкий CWU / высокий ADS | Слепое нарушение | агент не знал правил; лечить контекст |
| высокий CWU / низкий ADS | Informed compliance | норма |
| высокий CWU / высокий ADS | Архитектурное противоречие | знал и нарушил; нужен ADR и разговор |

Точка на матрице ставится по фактическим числам, а не по тексту вывода.

## 7. Доступность

- Семантические `header`, `main`, `section`, `footer`; у каждой секции
  `aria-labelledby`.
- Контраст текста не ниже 4,5:1; крупных значений — не ниже 3:1.
- Фокус видимый, Tab проходит по ссылкам и фильтрам.
- Таблицы с `<caption>` и `scope="col"`.
- `prefers-reduced-motion` отключает анимации.
- Никакой информации только цветом.
- Печать: фон не обязателен, но текст и границы различимы в ч/б.

## 8. Безопасность и приватность

- Все строки из JSON вставляются через `textContent`/экранирование.
- Запрещены `innerHTML` с данными, `eval`, `new Function`.
- Не попадают: токены, пароли, содержимое `.env`, персональные данные,
  приватные URL с ключами. Пути и имена файлов — можно.
- Внешние ссылки, если появились, получают `rel="noopener noreferrer"` и
  явную пометку «внешняя».
- Файл не содержит аналитики, пикселей и автоотправки данных.

## 9. Проверка страницы

```bash
# 1. Данные проходят схему и нет внешних ресурсов
python scripts/build_report.py metrics.json -o report.html --strict

# 2. Нет сетевых ссылок в атрибутах загрузки
grep -nE '(src|href)="https?://' report.html   # должно быть пусто

# 3. Открыть и пройти чек-лист из SKILL.md
```

`--strict` завершается кодом 1, если:

- отсутствует обязательная секция;
- `value` не число и не `null`;
- `status` вне допустимых значений;
- `estimated` без `range`/`~` в `summary` или `method.limitations`;
- в шаблоне остался плейсхолдер `__REPORT_DATA__`.