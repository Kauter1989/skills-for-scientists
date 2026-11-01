# Research ledger: `dev-bug-processing`

| Поле | Значение |
|---|---|
| Навык | `dev-bug-processing` |
| Домен | `dev` |
| Приоритет | `P0` |
| Автор | OpenCode agent |
| Дата начала | `2026-11-01` |
| Дата снимка источников | `2026-11-01` |
| Статус | `draft` |

## 1. Задача

Мета-навык для конкретного репозитория: провести опрос, определить профиль
(стек, тестовый фреймворк, трекер, окружение, команда, compliance), выбрать
подход к обработке дефектов и **сгенерировать навык `dev-bug-process`**,
который превращает сообщение о дефекте в воспроизводимый падающий тест и
обоснованный диагноз.

Инварианты, которые наследует любой сгенерированный вариант:

- подробное описание дефекта: expected / actual, окружение, версия, шаги,
  входные данные, логи;
- воспроизводимость: минимум 3 прогона с одинаковым результатом; флейк
  отмечается отдельно и не считается воспроизведением;
- минимальный вход, сохраняющий падение;
- падающий автотест до исправления;
- падение соответствует заявленному symptom, а не ошибке setup;
- диагноз — ранжированные гипотезы с evidence и confidence;
- исправление не начинается до красного гейта.

**Не входит в задачу:** выполнять обработку дефекта за сгенерированный
навык, исправлять код, закрывать регрессии, проверять живой стенд,
оценивать людей. Это `dev-bug-process`, `dev-regression-guard`,
`dev-verification-live` и `dev-ship`.

Сгенерированный навык живёт в **целевом репозитории**, а не в этой
библиотеке: `.opencode/skill/dev-bug-process/SKILL.md` и манифест
`.opencode/bug-processing.yml`.

## 2. Поисковые запросы

- GitHub: `bug reproduction benchmark`, `reproducible bugs`,
  `fault localization`, `delta debugging`, `property-based testing shrinking`,
  `spec-driven development`, `OpenSpec`, `BMAD`, `bug report template`.
- Научные базы (Crossref): `bug reproduction empirical study`,
  `fault localization survey`, `simplifying failure-inducing input`,
  `what makes a good bug report`, `defects4j`, `TDD meta-analysis`.
- Официальные спецификации и документация: `git bisect`,
  `OSS-Fuzz reproducing`, `Hypothesis replaying failures`,
  `pytest failures`.

## 3. GitHub-аналоги

Данные API GitHub на `2026-11-01`.

| # | Репозиторий | Лицензия | Последний коммит | Звёзды | Что делает | Что берём | Что отвергаем |
|---|---|---|---|---|---|---|---|
| 1 | [`github/spec-kit`](https://github.com/github/spec-kit) | MIT | 2026-10-30 | 144 854 | Toolkit для spec-driven development | опрос → профиль → генерация артефактов под репозиторий | фиксированную цепочку стадий |
| 2 | [`Fission-AI/OpenSpec`](https://github.com/Fission-AI/OpenSpec) | MIT | 2026-10-30 | 73 598 | SDD для AI-ассистентов, spec deltas | изменение как отдельный артефакт и проверки | избыточную церемонию |
| 3 | [`bmad-code-org/BMAD-METHOD`](https://github.com/bmad-code-org/BMAD-METHOD) | NOASSERTION | 2026-11-01 | 54 858 | Ролевой agile-метод для AI-разработки | story-файлы и разделение ролей | тяжёлую ролевую модель |
| 4 | [`soarsmu/BugsInPy`](https://github.com/soarsmu/BugsInPy) | не указана | 2025-10-09 | 154 | Бенчмарк реальных дефектов Python с тестами | структуру «дефект → тест → окружение» | код и данные: лицензия не заявлена |
| 5 | [`rjust/defects4j`](https://github.com/rjust/defects4j) | MIT | 2026-04-07 | 1 011 | База дефектов Java и инфраструктура экспериментов | минимальный триггерный тест и checkout ревизии | тяжёлую Java-инфраструктуру |
| 6 | [`HypothesisWorks/hypothesis`](https://github.com/HypothesisWorks/hypothesis) | MPL-2.0 | 2026-10-30 | 9 131 | Property-based testing с shrinking | уменьшение контрпримера и replay по seed | генерацию входов для каждого дефекта |
| 7 | [`dubzzz/fast-check`](https://github.com/dubzzz/fast-check) | MIT | 2026-11-01 | 5 226 | Property-based testing для JavaScript | минимальный воспроизводимый контрпример | JavaScript-специфику |
| 8 | [`GZoltar/gzoltar`](https://github.com/GZoltar/gzoltar) | LGPL-3.0 | 2023-06-19 | 89 | Автоматическая локализация дефектов Java | ранжирование подозрительных мест как гипотез | SBFL как единственный источник истины |
| 9 | [`google/oss-fuzz`](https://github.com/google/oss-fuzz) | Apache-2.0 | 2026-10-29 | 12 834 | Фаззинг и воспроизведение падений | отдельный reproducer и фиксированное окружение | фаззинг-инфраструктуру |

## 4. Научные источники и стандарты

| # | Источник | Тип | Метод / вклад | Ограничение | Как относится к навыку |
|---|---|---|---|---|---|
| 1 | Zeller & Hildebrandt, *Simplifying and isolating failure-inducing input*, IEEE TSE 28(2):183–200, 2002, DOI [10.1109/32.988498](https://doi.org/10.1109/32.988498) | рецензируемая | Delta debugging: уменьшение входа с сохранением падения | цена растёт с размером входа; нужен автоматический оракул | минимальный reproducer вместо большого сценария |
| 2 | Wong, Gao, Li, Abreu, *A Survey on Software Fault Localization*, IEEE TSE 42(8):707–740, 2016, DOI [10.1109/TSE.2016.2521368](https://doi.org/10.1109/TSE.2016.2521368) | рецензируемая | Обзор spectrum-based, slice-based и других методов локализации | ранжирование не равно причине; шумные тесты искажают | локализация выдаёт гипотезы, а не приговор |
| 3 | Parnin & Orso, *Are automated debugging techniques actually helping programmers?*, ISSTA 2011, DOI [10.1145/2001420.2001445](https://doi.org/10.1145/2001420.2001445) | рецензируемая | Эксперимент: автоматические подсказки без контекста часто не помогают | небольшая выборка, лабораторная задача | диагноз обязан объяснять symptom |
| 4 | Bettenburg, Just, Schröter, Weiss, *What makes a good bug report?*, FSE 2008, DOI [10.1145/1453101.1453146](https://doi.org/10.1145/1453101.1453146) | рецензируемая | Шаги воспроизведения — одно из самых полезных полей отчёта | самоотчёт разработчиков | вход требует expected/actual, шаги и окружение |
| 5 | Just, Jalali, Ernst, *Defects4J: a database of existing faults to enable controlled testing studies for Java programs*, ISSTA 2014, DOI [10.1145/2610384.2628055](https://doi.org/10.1145/2610384.2628055) | рецензируемая | Реальные дефекты с тестами, падающими до фикса | Java-only, отобранные проекты | падающий тест — основной артефакт |
| 6 | Rafique & Misic, *The Effects of Test-Driven Development on External Quality and Productivity: A Meta-Analysis*, IEEE TSE 39(6):835–856, 2013, DOI [10.1109/TSE.2012.28](https://doi.org/10.1109/TSE.2012.28) | рецензируемая | Метаанализ TDD: эффект зависит от контекста | неоднородные исследования | тест до фикса и красный гейт обязательны |
| 7 | Wang, Zhang, Feng, Halfond, *An Empirical Study on Leveraging Images in Automated Bug Report Reproduction*, MSR 2025, DOI [10.1109/MSR66628.2025.00019](https://doi.org/10.1109/MSR66628.2025.00019) | рецензируемая | Автоматическое воспроизведение по отчётам, включая изображения | узкий класс веб-приложений | reproducer сохраняет все входы |
| 8 | Git `bisect`, OSS-Fuzz reproducing, Hypothesis replaying failures, pytest cache | официальные | Replay, сужение диапазона коммитов, кэш падений | не научный источник | нормативные команды и evidence |

## 5. Синтез

- **Два слоя.** Мета-слой (`spec-kit`, OpenSpec, BMAD) показывает, как
  опрос превращается в профиль и набор артефактов. Прикладной слой
  (BugsInPy, Defects4J, Hypothesis, GZoltar, OSS-Fuzz) показывает, из чего
  состоит проверяемое воспроизведение: тест, минимальный вход,
  фиксированное окружение и ранжированные гипотезы.
- **Повторяющиеся паттерны:** артефакты важнее обещаний; профиль
  репозитория определяет команды и пути; падающий тест — единица
  воспроизведения; минимальный вход уменьшает шум; локализация — это
  ранжирование, а не доказательство.
- **Противоречия:** тяжёлые фреймворки дают полноту, но замедляют мелкие
  команды; лёгкий процесс быстрее, но теряет evidence. Поэтому инварианты
  фиксированы, а церемония и инструменты выбираются по профилю.
- **Пробелы:** существующие инструменты решают отдельные задачи —
  генерацию спецификаций, shrinking, SBFL или бенчмарки. Нет навыка,
  который по профилю репозитория генерирует процесс обработки дефектов с
  неизменными гейтами воспроизводимости.
- **Что подтверждено эмпирически:** шаги воспроизведения критичны для
  отчёта; падающий тест — воспроизводимая единица дефекта; уменьшение
  входа сохраняет падение; TDD-эффект зависит от контекста;
  автоматическая локализация без контекста помогает не всегда.
- **Что является решением автора:** набор подходов, формат манифеста,
  порог 3 прогонов, уровни confidence и правило «нет фикса до red».

## 6. Выводы для дизайна

| Решение | Основание | Альтернатива | Почему не она |
|---|---|---|---|
| Мета-навык, а не один фиксированный процесс | spec-kit, OpenSpec, BMAD; пробел | один процесс для всех | стек, трекер и окружение различаются |
| Опрос до генерации | spec-kit; spec-chain | значения по умолчанию | неверные команды и пути |
| Инварианты фиксированы, церемония — нет | Bettenburg 2008; Just 2014 | настраиваемые гейты | качество дрейфует |
| Пять подходов: test-first, container-first, incident-first, benchmark-first, lightweight | профили репозиториев | один подход | не подходит части команд |
| Сгенерированный навык `dev-bug-process` в целевом репозитории | spec-chain | глобальный навык | проектные команды и пути |
| Манифест `.opencode/bug-processing.yml` | OpenSpec; spec-chain | только текст | нельзя проверить |
| `check_bug_skill.py` проверяет структуру и инварианты | практика | ревью глазами | поля теряются |
| `probe_bug.py` измеряет детерминированность | OSS-Fuzz; pytest cache | верить автору | нет измерения |
| `check_bug_report.py` проверяет отчёт | Defects4J; практика | свободная форма | нельзя сравнить |
| Incident-first: mitigation можно, фикс — только после red | практика | сначала hotfix | нет evidence и регрессии |
| Не запускать недоверенные команды без явного решения | безопасность | полный автомат | побочные эффекты |

## 7. Подходы и инварианты

| Профиль | Подход | Что добавляет к инвариантам |
|---|---|---|
| Локальный тестовый фреймворк, обычные дефекты | `test-first` | red test, минимальный вход, bisect |
| Дефект зависит от окружения или сервисов | `container-first` | закреплённый образ, compose, детерминированные данные |
| Production-инцидент, живая система | `incident-first` | timeline, логи и трейсы, rollback, затем локальное воспроизведение |
| Много дефектов или исследовательский стенд | `benchmark-first` | пакетная обработка, метаданные, сравнение ревизий |
| Малая команда, простой процесс | `lightweight` | минимальный отчёт, без тяжёлого трекера |

Инварианты не отключаются ни одним подходом:

1. Подробное описание: expected / actual, окружение, версия, шаги, входы,
   логи.
2. Воспроизводимость: ≥3 прогонов, одинаковый результат; флейк — отдельный
   статус.
3. Минимальный вход: каждый оставшийся элемент обоснован.
4. Падающий автотест до фикса.
5. Падение соответствует symptom.
6. Диагноз: гипотезы с evidence, confidence и следующим probe.
7. Нет фикса до красного гейта.
8. Артефакты в `docs/bugs/<id>/`.
9. Недоверенные команды не запускаются автоматически.

## 8. Открытые вопросы для ревью

1. Имя сгенерированного навыка: `dev-bug-process` или
   `dev-bug-processing`? Предлагается `dev-bug-process`, чтобы не
   конфликтовать с мета-навыком при установке.
2. Минимум 3 прогона достаточно? Предлагается 3 обязательных, 5 для
   флейков.
3. Разрешать фикс при confidence `estimated` или только при
   `derived`/`measured`? Предлагается `derived`, иначе явное решение
   пользователя.
4. Incident-first: разрешать mitigation до red? Предлагается да, но фикс
   только после red.
5. Генерировать шаблон issue для GitHub/Jira или ограничиться
   `docs/bugs/<id>/`? Предлагается шаблон опционально.
6. Нужен ли `git bisect` в сгенерированном навыке? Предлагается только
   команда и правило, без автоматического запуска.

## 9. Что дальше

- [x] Research Gate: 9 GitHub-аналогов, 7 научных источников, 4 официальных
- [ ] Собран `docs/reviews/dev-bug-processing.html`
- [ ] Ревью проведено, статус `approved`
- [ ] Создан каталог `dev/dev-bug-processing/`
- [ ] Генерация навыка и пример воспроизводятся
- [ ] Обновлены `docs/skills-map.html` и `README.md`

## 10. Источники

1. `github/spec-kit` — https://github.com/github/spec-kit — доступно 2026-11-01.
2. `Fission-AI/OpenSpec` — https://github.com/Fission-AI/OpenSpec — доступно 2026-11-01.
3. `bmad-code-org/BMAD-METHOD` — https://github.com/bmad-code-org/BMAD-METHOD — доступно 2026-11-01.
4. `soarsmu/BugsInPy` — https://github.com/soarsmu/BugsInPy — доступно 2026-11-01.
5. `rjust/defects4j` — https://github.com/rjust/defects4j — доступно 2026-11-01.
6. `HypothesisWorks/hypothesis` — https://github.com/HypothesisWorks/hypothesis — доступно 2026-11-01.
7. `dubzzz/fast-check` — https://github.com/dubzzz/fast-check — доступно 2026-11-01.
8. `GZoltar/gzoltar` — https://github.com/GZoltar/gzoltar — доступно 2026-11-01.
9. `google/oss-fuzz` — https://github.com/google/oss-fuzz — доступно 2026-11-01.
10. Zeller & Hildebrandt, 2002 — https://doi.org/10.1109/32.988498 — доступно 2026-11-01.
11. Wong et al., 2016 — https://doi.org/10.1109/TSE.2016.2521368 — доступно 2026-11-01.
12. Parnin & Orso, 2011 — https://doi.org/10.1145/2001420.2001445 — доступно 2026-11-01.
13. Bettenburg et al., 2008 — https://doi.org/10.1145/1453101.1453146 — доступно 2026-11-01.
14. Just et al., 2014 — https://doi.org/10.1145/2610384.2628055 — доступно 2026-11-01.
15. Rafique & Misic, 2013 — https://doi.org/10.1109/TSE.2012.28 — доступно 2026-11-01.
16. Wang et al., 2025 — https://doi.org/10.1109/MSR66628.2025.00019 — доступно 2026-11-01.
17. Git `bisect` — https://git-scm.com/docs/git-bisect — доступно 2026-11-01.
18. OSS-Fuzz, Reproducing — https://google.github.io/oss-fuzz/advanced-topics/reproducing/ — доступно 2026-11-01.
19. Hypothesis, Replaying failures — https://hypothesis.readthedocs.io/en/latest/tutorial/replaying-failures.html — доступно 2026-11-01.
20. pytest, How to handle test failures — https://docs.pytest.org/en/stable/how-to/failures.html — доступно 2026-11-01.