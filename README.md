# opencode-skills

Личная библиотека навыков для OpenCode: разработка ПО, научная работа и
подготовка отчётности. Каждый навык — отдельный каталог с `SKILL.md` и, если
нужно, нормативами, скриптами и шаблонами. Результат работы навыка — артефакт,
который можно проверить, а не только текст в чате.

Карта библиотеки по блокам процесса: [`docs/skills-map.html`](docs/skills-map.html).
План разработки и очередь: [`docs/skills-development-plan.html`](docs/skills-development-plan.html).
Обязательный регламент для агентов: [`AGENTS.md`](AGENTS.md).

Новый навык не пишется без исследования аналогов и научных источников.
Порядок приоритетов: **harness → dev → science → reports**.

## Что внутри

| Навык | Папка | Назначение | Артефакт |
|---|---|---|---|
| [`harness-skill-template`](harness/harness-skill-template/SKILL.md) | `harness/` | Контракт и каркас навыка: frontmatter, обязательные разделы, шаблон, генератор и валидатор | `SKILL.md`, отчёт валидатора |
| [`harness-rule-to-mechanism`](harness/harness-rule-to-mechanism/SKILL.md) | `harness/` | Переводит правило в исполняемую проверку: хук, lint, тест, policy или CI, с registry и negative fixture | проверка, `docs/rules/registry.yml` |
| [`dev-pr-report-html`](dev/dev-pr-report-html/SKILL.md) | `dev/` | HTML-отчёт об изменениях фичи или майлстоуна: шесть метрик агентской разработки, доказательства и решения | автономный `report.html` |
| [`pptx-report`](reports/pptx-report/SKILL.md) | `reports/` | Строгие презентации и аналитические отчёты PPTX: научные доклады, отчёты о НИР, аналитика для руководства | `deck.pptx`, PNG для проверки |

`dev-pr-report-html` считает: Feature Token Budget, Architecture Drift Score,
Cognitive Load Index, Agent Iteration Rate, Hallucination Risk и Context
Window Utilization. Страница не требует сети и открывается с диска.
Пример: [`dev/dev-pr-report-html/examples/example-report.html`](dev/dev-pr-report-html/examples/example-report.html).

## Домены и префиксы

Имя навыка начинается с префикса домена, а каталог задаёт область:

| Папка | Префикс имени | Домен |
|---|---|---|
| `dev/` | `dev-` | разработка: фичи, дефекты, проверки, аудит, релиз |
| `sci/` | `sci-` | научная работа: гипотезы, эксперименты, статистика, данные |
| `harness/` | `harness-` | общее для харнесса: инициализация, правила, сами навыки |
| `reports/` | без префикса | отчётность и презентации; сейчас только `pptx-report` |

Префикс нужен, чтобы после установки в плоский каталог навыков
(`~/.config/opencode/skill/`) было видно, к какому домену он относится.
Папка-домен — только организация репозитория; при установке копируется
конкретный навык, а имя его каталога совпадает с именем навыка.

## Установка

OpenCode видит навыки в двух местах:

- личные: `~/.config/opencode/skill/<name>/SKILL.md`;
- проектные: `<repo>/.opencode/skill/<name>/SKILL.md`.

Скопируйте нужный каталог целиком — `SKILL.md`, `references/`, `scripts/`,
`templates/`, `examples/`:

```powershell
# Windows: навык харнесса
Copy-Item -Recurse .\harness\harness-skill-template "$env:USERPROFILE\.config\opencode\skill\harness-skill-template"

# Windows: навык разработки
Copy-Item -Recurse .\dev\dev-pr-report-html "$env:USERPROFILE\.config\opencode\skill\dev-pr-report-html"

# Windows: отчётный навык
Copy-Item -Recurse .\reports\pptx-report "$env:USERPROFILE\.config\opencode\skill\pptx-report"
```

```bash
# Linux/macOS
cp -r harness/harness-skill-template ~/.config/opencode/skill/
cp -r dev/dev-pr-report-html ~/.config/opencode/skill/
cp -r reports/pptx-report ~/.config/opencode/skill/
```

После установки проверьте, что `skill` tool находит навык. До установки
можно читать `SKILL.md` и `references/` прямо из этого репозитория.

## Структура

```
skills/
├── AGENTS.md                  обязательный регламент разработки
├── docs/
│   ├── skills-map.html        карта навыков и блоков процесса
│   ├── skills-development-plan.html  план и очередь
│   ├── research/              research ledger по навыкам
│   ├── reviews/               HTML-ревью по навыкам
│   ├── rules/                 registry.yml — реестр правил
│   └── templates/
│       ├── skill-research.md  research ledger
│       └── skill-review.html  HTML-ревью навыка
├── dev/                       разработка, префикс dev-
│   └── dev-pr-report-html/
│       ├── SKILL.md
│       ├── references/
│       ├── scripts/
│       ├── templates/
│       └── examples/
├── sci/                       наука, префикс sci- (пока пусто)
├── harness/                   харнесс, префикс harness-
│   ├── harness-skill-template/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   ├── scripts/
│   │   ├── templates/
│   │   └── examples/
│   └── harness-rule-to-mechanism/
│       ├── SKILL.md
│       ├── references/
│       ├── scripts/
│       ├── templates/
│       └── examples/
├── reports/                   отчётность, без префикса
│   └── pptx-report/
│       ├── SKILL.md
│       ├── examples/
│       ├── references/
│       ├── scripts/
│       └── templates/
└── LICENSE
```

## Как разрабатывается навык

Каждый навык проходит пять гейтов, описанные в `AGENTS.md`:

```
Research → Review → Implementation → Verification → PR
```

1. **Research.** Не менее трёх GitHub-аналогов и двух научных или
   официальных источников. Результат — `docs/research/<skill>.md`.
2. **Review.** План в виде автономного HTML по шаблону
   `docs/templates/skill-review.html`. Без статуса `approved` код не
   пишется.
3. **Implementation.** `SKILL.md`, `references/`, `scripts/`,
   `templates/`, `examples/`.
4. **Verification.** Пример воспроизводится, скрипты работают, HTML
   открывается без сети, карта и README обновлены.
5. **PR.** Ветка запушена, PR открыт, в описании — research ledger,
   review HTML и вывод валидатора. Мерж без PR запрещён.

Правила библиотеки:

1. Домен задаётся папкой и префиксом имени: `dev/` + `dev-`, `sci/` + `sci-`,
   `harness/` + `harness-`. Отчётные навыки лежат в `reports/`.
2. Каталоги навыков плоские внутри домена: один каталог — один навык.
3. `description` в frontmatter содержит русские и английские триггеры:
   навык должен находиться по формулировке задачи, а не по имени файла.
4. Если навык обещает число, у числа есть формула, источник и уровень
   качества данных.
5. Если навык меняет репозиторий, у него есть проверка и уборка.
6. Новый навык не дублирует существующий: сначала проверяются карта и
   триггеры соседей.

## Проверка

```bash
# собрать демонстрационный HTML-отчёт
cd dev/dev-pr-report-html
python scripts/build_report.py --example -o examples/example-report.html --strict

# собрать метрики из Git
python scripts/collect_metrics.py --repo . --from HEAD~1 --to HEAD --out metrics.json
```

Скрипты используют только стандартную библиотеку Python 3.9+.

## Лицензия

Apache License 2.0 — см. [`LICENSE`](LICENSE).