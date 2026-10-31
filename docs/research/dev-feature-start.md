# Research ledger: `dev-feature-start`

| Поле | Значение |
|---|---|
| Навык | `dev-feature-start` |
| Домен | `dev` |
| Приоритет | `P0` |
| Автор | OpenCode agent |
| Дата начала | `2026-10-31` |
| Дата снимка источников | `2026-10-31` |
| Статус | `ready-for-review` |

## 1. Задача

Начинать фичу одинаково: ветка от свежей основной ветки, привязка к цели
или пункту плана, краткий feature brief с границами и критериями приёмки,
передача в цепочку спецификации.

**Не входит в задачу:** писать `spec.md`, `plan.md` и задачи (это
spec-chain), реализовывать код, делать commit, push или merge.

## 2. Поисковые запросы

- GitHub: `spec-driven development`, `feature branch workflow`,
  `git branch automation`, `design before code`.
- Научные базы: `requirements engineering`, `risk-driven development`,
  `early defect detection`, `implementation intentions`.
- Официальные спецификации: GitHub flow, Git branching, spec-kit,
  Conventional Commits.

## 3. GitHub-аналоги

Данные API GitHub на `2026-10-31`.

| # | Репозиторий | Лицензия | Последний коммит | Звёзды | Что делает | Что берём | Что отвергаем |
|---|---|---|---|---|---|---|---|
| 1 | [`github/spec-kit`](https://github.com/github/spec-kit) | MIT | 2026-10-30 | 144 213 | Стартовый набор spec-driven development | create-feature, ветку и шаблон спецификации | полную методологию целиком |
| 2 | [`obra/superpowers`](https://github.com/obra/superpowers) | MIT | 2026-10-29 | 309 856 | Методология: сначала дизайн, потом код | явную фазу проектирования | тяжёлый процесс для мелкой фичи |
| 3 | [`git-town/git-town`](https://github.com/git-town/git-town) | MIT | 2026-10-23 | 3 391 | Автоматизация git-веток | проверку чистого дерева и синхронизацию с основной веткой | зависимость от внешнего CLI |
| 4 | [`nvie/gitflow`](https://github.com/nvie/gitflow) | NOASSERTION | 2025-10-14 (archived) | 26 764 | Расширения для модели Git Flow | идею именованных веток | тяжёлую модель с develop/release/hotfix |

## 4. Научные источники и стандарты

| # | Источник | Тип | Метод / вклад | Ограничение | Как относится к навыку |
|---|---|---|---|---|---|
| 1 | Boehm, *A spiral model of software development and enhancement*, Computer 21(5):61–72, 1988, DOI [10.1109/2.59](https://doi.org/10.1109/2.59) | рецензируемая | Риск-ориентированный старт: цели, ограничения, альтернативы | модель разработки, не git | старт фичи фиксирует цель и риски до кода |
| 2 | Boehm & Basili, *Top 10 list [software development]*, Computer 34(1):135–137, 2001, DOI [10.1109/2.962984](https://doi.org/10.1109/2.962984) | рецензируемая | Раннее обнаружение дефектов дешевле | обзор практик | критерии приёмки и границы задаются на старте |
| 3 | Gollwitzer, *Implementation intentions*, American Psychologist 54(7):493–503, 1999, DOI [10.1037/0003-066X.54.7.493](https://doi.org/10.1037/0003-066x.54.7.493) | рецензируемая | If-then планы повышают следование намерению | психология поведения | фича начинается с триггера и конкретного действия |
| 4 | GitHub flow, Git branching, spec-kit, Conventional Commits | официальные | Правила веток, коммитов и спецификаций | не научный источник | нормативная база старта |

## 5. Синтез

- **Повторяющиеся паттерны:** ветка от свежей основы, явная цель, brief,
  критерии приёмки и передача в спецификацию.
- **Противоречия:** тяжёлые branch-модели дают порядок, но дороги для
  маленьких команд; лёгкий feature-branch проще, но требует дисциплины.
- **Пробелы:** инструменты создают ветку, но не связывают её с планом,
  критериями и границами.
- **Что подтверждено эмпирически:** раннее обнаружение дефектов дешевле;
  риск-ориентированный старт фиксирует цели и ограничения; if-then
  формулировка повышает следование плану.
- **Что является решением автора:** формат feature brief, обязательные
  поля и минимальный набор проверок.

## 6. Выводы для дизайна

| Решение | Основание | Альтернатива | Почему не она |
|---|---|---|---|
| Ветка от свежей основной, чистое дерево | git-town; GitHub flow | ветка от локальной main | устаревшая база и конфликты |
| Feature brief до спецификации | Boehm; superpowers | сразу писать spec | нет цели и границ |
| Обязательная ссылка на пункт плана | Boehm; практика | «просто фича» | работа вне плана без обоснования |
| If-then критерий приёмки | Gollwitzer | общее описание | нельзя проверить |
| `start_feature.py --dry-run` | git-town | ручные команды | забытые шаги |
| Не делать commit/push | практика | полный автомат | скрытые side effects |

## 7. Открытые вопросы для ревью

1. Где хранить feature brief: `docs/features/<slug>/overview.md`?
2. Нужен ли отдельный `alignment.md` на старте или достаточно ссылки на план?
3. Разрешать ли `--force` для грязного дерева?
4. Делать ли fetch обязательным или опциональным?
5. Кто утверждает brief до перехода к спецификации?

## 8. Что дальше

- [x] Research Gate: 4 GitHub-аналога, 3 научных источника, 4 спецификации
- [ ] Собран `docs/reviews/dev-feature-start.html`
- [ ] Ревью проведено, статус `approved`
- [ ] Создан каталог `dev/dev-feature-start/`
- [ ] Ветка и brief воспроизводятся на тестовом репозитории
- [ ] Обновлены `docs/skills-map.html` и `README.md`

## 9. Источники

1. `github/spec-kit` — https://github.com/github/spec-kit — доступно 2026-10-31.
2. `obra/superpowers` — https://github.com/obra/superpowers — доступно 2026-10-31.
3. `git-town/git-town` — https://github.com/git-town/git-town — доступно 2026-10-31.
4. `nvie/gitflow` — https://github.com/nvie/gitflow — доступно 2026-10-31.
5. Boehm, 1988 — https://doi.org/10.1109/2.59 — доступно 2026-10-31.
6. Boehm & Basili, 2001 — https://doi.org/10.1109/2.962984 — доступно 2026-10-31.
7. Gollwitzer, 1999 — https://doi.org/10.1037/0003-066X.54.7.493 — доступно 2026-10-31.
8. GitHub flow — https://docs.github.com/get-started/using-github/github-flow — доступно 2026-10-31.
9. Git branching — https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell — доступно 2026-10-31.
10. spec-kit docs — https://github.com/github/spec-kit — доступно 2026-10-31.
11. Conventional Commits — https://www.conventionalcommits.org/ — доступно 2026-10-31.