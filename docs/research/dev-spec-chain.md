# Research ledger: `dev-spec-chain`

| Поле | Значение |
|---|---|
| Навык | `dev-spec-chain` |
| Домен | `dev` |
| Приоритет | `P0` |
| Автор | OpenCode agent |
| Дата начала | `2026-11-01` |
| Дата снимка источников | `2026-11-01` |
| Статус | `approved` |

## 1. Задача

Мета-навык для конкретного репозитория: провести опрос, определить профиль
(greenfield / brownfield, размер изменений, роли, compliance, стек), выбрать
подход из аналогов и **сгенерировать цепочку stage-навыков** с гейтами под
этот репозиторий.

Ключевые принципы, которые наследует сгенерированная цепочка:

- одна стадия — один навык;
- artifact-driven gates: `spec.md → plan.md → tasks.md → report`;
- traceability `US → REQ → T`;
- тестовые задачи раньше implementation;
- approval mode `user` / `autonomous`;
- артефакты в `docs/features/<slug>/`.

Выбор подхода (предварительно):

| Профиль | Ближе к | Почему |
|---|---|---|
| Greenfield, стабильные требования | spec-kit | полный spec-first с нуля |
| Brownfield, изменения в существующем коде | OpenSpec | spec deltas и изменения |
| Много ролей и enterprise-процесс | BMAD | story-файлы и роли |
| Малая команда, лёгкий процесс | superpowers / minimal | дизайн без тяжёлой церемонии |

**Не входит в задачу:** выполнять стадии за сгенерированные навыки, писать
код, делать commit, push или merge.

Сгенерированные навыки живут в **целевом репозитории**, а не в этой
библиотеке: `.opencode/skill/<stage>/SKILL.md` и манифест
`.opencode/spec-chain.yml`.

## 2. Поисковые запросы

- GitHub: `spec-driven development`, `spec kit`, `OpenSpec`, `BMAD`,
  `requirements traceability`.
- Научные базы: `requirements smells`, `requirements engineering`,
  `early defect detection`, `implementation intentions`.
- Официальные спецификации: spec-kit, OpenSpec, BMAD, GitHub.

## 3. GitHub-аналоги

Данные API GitHub на `2026-11-01`.

| # | Репозиторий | Лицензия | Последний коммит | Звёзды | Что делает | Что берём | Что отвергаем |
|---|---|---|---|---|---|---|---|
| 1 | [`github/spec-kit`](https://github.com/github/spec-kit) | MIT | 2026-10-30 | 144 854 | Toolkit для spec-driven development | specify → plan → tasks, конституция | жёсткую привязку к шаблонам |
| 2 | [`Fission-AI/OpenSpec`](https://github.com/Fission-AI/OpenSpec) | MIT | 2026-10-30 | 73 598 | SDD для AI-ассистентов, spec deltas | изменения спецификации и проверки | избыточную церемонию для мелких фич |
| 3 | [`bmad-code-org/BMAD-METHOD`](https://github.com/bmad-code-org/BMAD-METHOD) | NOASSERTION | 2026-11-01 | 54 858 | Ролевой agile-метод для AI-разработки | story-файлы и разделение ролей | тяжёлую ролевую модель |
| 4 | [`obra/superpowers`](https://github.com/obra/superpowers) | MIT | 2026-10-29 | 310 501 | Дизайн до кода и декомпозиция | явную фазу проектирования | процесс целиком |

## 4. Научные источники и стандарты

| # | Источник | Тип | Метод / вклад | Ограничение | Как относится к навыку |
|---|---|---|---|---|---|
| 1 | Boehm, *A spiral model of software development and enhancement*, Computer 21(5):61–72, 1988, DOI [10.1109/2.59](https://doi.org/10.1109/2.59) | рецензируемая | Риск-ориентированный старт: цели и ограничения | модель разработки | план фиксирует риски и альтернативы |
| 2 | Boehm & Basili, *Top 10 list [software development]*, Computer 34(1):135–137, 2001, DOI [10.1109/2.962984](https://doi.org/10.1109/2.962984) | рецензируемая | Раннее обнаружение дефектов дешевле | обзор практик | ambiguity и пропуски ловятся до кода |
| 3 | Gollwitzer, *Implementation intentions*, American Psychologist 54(7):493–503, 1999, DOI [10.1037/0003-066X.54.7.493](https://doi.org/10.1037/0003-066x.54.7.493) | рецензируемая | If-then планы повышают следование намерению | психология поведения | задачи формулируются как проверяемые шаги |
| 4 | Femmer et al., *Rapid quality assurance with Requirements Smells*, JSS 123:190–213, 2017, DOI [10.1016/j.jss.2016.02.047](https://doi.org/10.1016/j.jss.2016.02.047) | рецензируемая | Requirements smells: неоднозначность, пассив, отсутствие критериев | не автоматический анализ смысла | clarify и analyze проверяют формулировки |

## 5. Синтез

- **Повторяющиеся паттерны:** артефакты цепочки, явные идентификаторы,
  трассировка к stories, задачи по story, проверка перед реализацией.
- **Противоречия:** тяжёлая церемония повышает полноту, но замедляет
  мелкие фичи; лёгкий процесс быстрее, но теряет traceability.
- **Пробелы:** инструменты создают spec/plan/tasks, но не проверяют, что
  тестовые задачи идут раньше implementation и что каждая задача привязана
  к story.
- **Что подтверждено эмпирически:** раннее обнаружение дефектов дешевле;
  требования с smells чаще приводят к переделкам; if-then формулировка
  повышает следование плану.
- **Что является решением автора:** обязательные артефакты, формат ID и
  правила анализа.

## 6. Выводы для дизайна

| Решение | Основание | Альтернатива | Почему не она |
|---|---|---|---|
| Классифицировать репозиторий до выбора подхода | OpenSpec; spec-kit | одна цепочка для всех | greenfield и brownfield различаются |
| Greenfield → spec-kit, brownfield → OpenSpec | spec-kit; OpenSpec | всегда spec-kit | spec deltas лучше для существующего кода |
| Генерировать stage-навыки под репозиторий | spec-kit; harness-skill-template | держать один универсальный | разные гейты и профили |
| Артефакты в `docs/features/<slug>/` | dev-feature-start | общий `specs/` | привязка к фиче |
| Approval mode наследуется из overview | dev-feature-start | всегда user | автономный режим уже согласован |
| Тестовые задачи раньше implementation | Rafique; dev-feature-start | код, потом тесты | тесты подгоняются под код |
| Мета-навык не выполняет стадии | практика | всё в одном | смешиваются генерация и работа |

## 7. Решения ревью

1. **Профиль репозитория:** greenfield / brownfield, размер изменений,
   роли, compliance, стек — определяются опросом.
2. **Подход:** greenfield → spec-kit; brownfield → OpenSpec; роли и
   enterprise → BMAD; малая команда → lightweight.
3. **Генерация:** stage-навыки создаются в целевом репозитории:
   `.opencode/skill/<stage>/SKILL.md`.
4. **Манифест:** `.opencode/spec-chain.yml` с профилем, подходом,
   стадиями и гейтами.
5. **Утверждение:** HTML-план `spec-chain-plan.html` до генерации; статус
   `approved`.
6. **Артефакты:** `docs/features/<slug>/`; `analysis.md` не нужен —
   достаточно отчёта `check_spec_chain.py`.
7. **Тестовые задачи:** `T-TEST-*` раньше `T-IMPL-*`.
8. **Мета-навык не выполняет стадии** — это делают сгенерированные
   навыки.

## 8. Что дальше

- [x] Research Gate: 4 GitHub-аналога, 4 научных источника, 4 спецификации
- [x] Собран `docs/reviews/dev-spec-chain.html`
- [x] Ревью проведено, статус `approved`
- [x] Создан каталог `dev/dev-spec-chain/`
- [x] Опрос и выбор подхода воспроизводятся
- [x] Генерация chain и `check_spec_chain.py` проверены
- [x] Обновлены `docs/skills-map.html` и `README.md`

## 9. Источники

1. `github/spec-kit` — https://github.com/github/spec-kit — доступно 2026-11-01.
2. `Fission-AI/OpenSpec` — https://github.com/Fission-AI/OpenSpec — доступно 2026-11-01.
3. `bmad-code-org/BMAD-METHOD` — https://github.com/bmad-code-org/BMAD-METHOD — доступно 2026-11-01.
4. `obra/superpowers` — https://github.com/obra/superpowers — доступно 2026-11-01.
5. Boehm, 1988 — https://doi.org/10.1109/2.59 — доступно 2026-11-01.
6. Boehm & Basili, 2001 — https://doi.org/10.1109/2.962984 — доступно 2026-11-01.
7. Gollwitzer, 1999 — https://doi.org/10.1037/0003-066X.54.7.493 — доступно 2026-11-01.
8. Femmer et al., 2017 — https://doi.org/10.1016/j.jss.2016.02.047 — доступно 2026-11-01.
9. spec-kit docs — https://github.com/github/spec-kit — доступно 2026-11-01.
10. OpenSpec docs — https://github.com/Fission-AI/OpenSpec — доступно 2026-11-01.
11. BMAD docs — https://github.com/bmad-code-org/BMAD-METHOD — доступно 2026-11-01.
12. GitHub docs — https://docs.github.com/ — доступно 2026-11-01.