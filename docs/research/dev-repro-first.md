# Research ledger: `dev-repro-first`

| Поле | Значение |
|---|---|
| Навык | `dev-repro-first` |
| Домен | `dev` |
| Приоритет | `P0` |
| Автор | OpenCode agent |
| Дата начала | `2026-11-01` |
| Дата снимка источников | `2026-11-01` |
| Статус | `draft` |

## 1. Задача

Превращать сообщение о дефекте в воспроизводимый падающий тест и
обоснованный диагноз до начала исправления.

**Не входит в задачу:** исправлять код, закрывать регрессии после фикса,
проверять живой стенд, оценивать людей и угадывать причину без evidence.
Эти шаги выполняют `dev-regression-guard`, `dev-verification-live` и
`dev-ship`.

## 2. Поисковые запросы

- GitHub: `bug reproduction benchmark`, `reproducible bugs`,
  `property-based testing shrinking`, `fault localization`,
  `delta debugging`, `reproducing crashes`, `defects4j`, `bugsinpy`.
- Научные базы (Crossref): `bug reproduction empirical study`,
  `fault localization survey`, `simplifying failure-inducing input`,
  `what makes a good bug report`, `defects4j`, `TDD meta-analysis`.
- Официальные спецификации и документация: `git bisect`,
  `OSS-Fuzz reproducing`, `Hypothesis replaying failures`,
  `pytest cache / last failed`.

## 3. GitHub-аналоги

Данные API GitHub на `2026-11-01`.

| # | Репозиторий | Лицензия | Последний коммит | Звёзды | Что делает | Что берём | Что отвергаем |
|---|---|---|---|---|---|---|---|
| 1 | [`soarsmu/BugsInPy`](https://github.com/soarsmu/BugsInPy) | не указана | 2025-10-09 | 154 | Бенчмарк реальных дефектов Python с тестами, воспроизводящими каждый дефект | структуру «дефект → триггерный тест → окружение» | код и данные: лицензия не заявлена |
| 2 | [`rjust/defects4j`](https://github.com/rjust/defects4j) | MIT | 2026-04-07 | 1 011 | База реальных дефектов Java и инфраструктура контролируемых экспериментов | минимальный триггерный тест как единицу воспроизведения; checkout конкретной ревизии | тяжёлую Java-инфраструктуру и привязку к бенчмарку |
| 3 | [`HypothesisWorks/hypothesis`](https://github.com/HypothesisWorks/hypothesis) | MPL-2.0 | 2026-10-30 | 9 131 | Property-based testing с автоматическим уменьшением контрпримера | shrinking до минимального входа и replay по seed | генерацию входов для каждого дефекта |
| 4 | [`dubzzz/fast-check`](https://github.com/dubzzz/fast-check) | MIT | 2026-11-01 | 5 226 | Property-based testing для JavaScript с shrinking | воспроизводимый минимальный контрпример и явный replay | JavaScript-специфику |
| 5 | [`GZoltar/gzoltar`](https://github.com/GZoltar/gzoltar) | LGPL-3.0 | 2023-06-19 | 89 | Автоматическая локализация дефектов для Java | ранжирование подозрительных мест как гипотез, а не приговор | инструментальную зависимость и SBFL как единственный источник истины |
| 6 | [`google/oss-fuzz`](https://github.com/google/oss-fuzz) | Apache-2.0 | 2026-10-29 | 12 834 | Непрерывный фаззинг и воспроизведение падений | отдельный reproducer, фиксированное окружение, детерминированный запуск | фаззинг-инфраструктуру и длительные прогоны |

## 4. Научные источники и стандарты

| # | Источник | Тип | Метод / вклад | Ограничение | Как относится к навыку |
|---|---|---|---|---|---|
| 1 | Zeller & Hildebrandt, *Simplifying and isolating failure-inducing input*, IEEE TSE 28(2):183–200, 2002, DOI [10.1109/32.988498](https://doi.org/10.1109/32.988498) | рецензируемая | Delta debugging: систематическое уменьшение входа с сохранением падения | цена растёт с размером входа; нужен автоматический оракул | минимальный reproducer вместо «большого» сценария |
| 2 | Wong, Gao, Li, Abreu, *A Survey on Software Fault Localization*, IEEE TSE 42(8):707–740, 2016, DOI [10.1109/TSE.2016.2521368](https://doi.org/10.1109/TSE.2016.2521368) | рецензируемая | Обзор spectrum-based, slice-based и других методов локализации | ранжирование не равно причине; шумные и несбалансированные тесты искажают результат | локализация выдаёт гипотезы с оценкой, а не «найденный баг» |
| 3 | Parnin & Orso, *Are automated debugging techniques actually helping programmers?*, ISSTA 2011, DOI [10.1145/2001420.2001445](https://doi.org/10.1145/2001420.2001445) | рецензируемая | Эксперимент: автоматические подсказки без контекста часто не помогают | небольшая выборка, лабораторная задача | диагноз обязан объяснять symptom и опираться на проверяемый факт |
| 4 | Bettenburg, Just, Schröter, Weiss, *What makes a good bug report?*, FSE 2008, DOI [10.1145/1453101.1453146](https://doi.org/10.1145/1453101.1453146) | рецензируемая | Опрос: шаги воспроизведения — одно из самых полезных полей отчёта | самоотчёт разработчиков | вход навыка требует expected/actual, шаги и окружение |
| 5 | Just, Jalali, Ernst, *Defects4J: a database of existing faults to enable controlled testing studies for Java programs*, ISSTA 2014, DOI [10.1145/2610384.2628055](https://doi.org/10.1145/2610384.2628055) | рецензируемая | Реальные дефекты с тестами, которые падают до фикса и проходят после | Java-only, отобранные проекты | падающий тест — основной артефакт воспроизведения |
| 6 | Rafique & Misic, *The Effects of Test-Driven Development on External Quality and Productivity: A Meta-Analysis*, IEEE TSE 39(6):835–856, 2013, DOI [10.1109/TSE.2012.28](https://doi.org/10.1109/TSE.2012.28) | рецензируемая | Метаанализ TDD: эффект на качество зависит от контекста | неоднородные исследования | тест до фикса и красный гейт обязательны |
| 7 | Wang, Zhang, Feng, Halfond, *An Empirical Study on Leveraging Images in Automated Bug Report Reproduction*, MSR 2025, DOI [10.1109/MSR66628.2025.00019](https://doi.org/10.1109/MSR66628.2025.00019) | рецензируемая | Автоматическое воспроизведение дефектов по отчётам, включая изображения | узкий класс веб-приложений | reproducer должен сохранять все входы, включая не-текстовые |
| 8 | Git `bisect`, OSS-Fuzz reproducing, Hypothesis replaying failures, pytest cache | официальные | Детерминированный replay, автоматическое сужение диапазона коммитов, кэш падений | не научный источник | нормативные команды и форма evidence |

## 5. Синтез

- **Повторяющиеся паттерны:** сначала стабильное воспроизведение, затем
  уменьшение входа, затем автоматический тест, и только потом поиск
  причины. Все аналоги хранят окружение и точную команду запуска.
- **Противоречия:** delta debugging и shrinking дают минимальный вход, но
  требуют автоматического оракула и могут удалить семантически важный
  элемент; SBFL ранжирует подозрительные места, но не объясняет причину.
  Автоматические подсказки без контекста в исследовании Parnin & Orso не
  улучшали результат.
- **Пробелы:** бенчмарки (BugsInPy, Defects4J) поставляют готовые падающие
  тесты, а алгоритмы (delta debugging, SBFL) решают отдельные подзадачи.
  Нет лёгкого рабочего процесса, который в обычном репозитории выдаёт
  red-тест, минимальный вход и журнал гипотез с evidence.
- **Что подтверждено эмпирически:** шаги воспроизведения критичны для
  отчёта; падающий тест — воспроизводимая единица дефекта; уменьшение
  входа сохраняет падение при меньшем объёме; TDD-эффект зависит от
  контекста; автоматическая локализация без контекста помогает не всегда.
- **Что является решением автора:** формат `repro.json`, порог
  детерминированности, уровни confidence и правило «нет фикса до red».

## 6. Выводы для дизайна

| Решение | Основание | Альтернатива | Почему не она |
|---|---|---|---|
| Сначала сформулировать expected/actual и окружение | Bettenburg 2008 | сразу искать причину | неясно, что считать дефектом |
| Минимум 3 прогона, все падают одинаково | OSS-Fuzz; практика | один запуск | флейк принимается за дефект |
| Флейк не проходит гейт, фиксируется частота и условия | OSS-Fuzz; практика | «иногда падает» | нельзя проверить фикс |
| Уменьшать вход до 1-minimal | Zeller & Hildebrandt 2002 | оставить большой сценарий | причина тонет в шуме |
| Падающий автотест — обязательный артефакт | Just 2014; Rafique 2013 | ручные шаги в отчёте | не проверяется автоматически |
| Проверять, что падение соответствует symptom | Parnin & Orso 2011 | любой красный тест | setup-ошибка выдаётся за дефект |
| Гипотезы ранжируются, у каждой evidence и confidence | Wong 2016 | одна «догадка» | нет способа оспорить диагноз |
| Фикс не начинается до red-гейта | Rafique 2013 | чинить по описанию | тест подгоняется под фикс |
| `probe_repro.py` измеряет детерминированность | OSS-Fuzz; pytest cache | верить автору отчёта | нет измерения |
| `check_repro.py` проверяет полноту отчёта | Defects4J; практика | ревью глазами | поля теряются |

## 7. Открытые вопросы для ревью

1. Где хранить падающий тест: в обычном тестовом дереве или в
   `docs/bugs/<slug>/` до фикса?
2. Достаточно ли 3 прогонов для детерминированности или нужно 5?
3. Разрешать фикс при confidence `estimated` или требовать `derived`?
4. Нужен ли отдельный `repro.sh`/`repro.ps1` или достаточно команды в
   `repro.json`?
5. Что делать, если дефект не воспроизводится: закрывать как
   `not-reproduced` или оставлять `investigating` с планом?
6. Нужно ли автоматически запускать `git bisect` или только предлагать
   команду?

## 8. Что дальше

- [x] Research Gate: 6 GitHub-аналогов, 7 научных источников, 4 официальных
- [ ] Собран `docs/reviews/dev-repro-first.html`
- [ ] Ревью проведено, статус `approved`
- [ ] Создан каталог `dev/dev-repro-first/`
- [ ] Пример с падающим тестом воспроизводится
- [ ] Обновлены `docs/skills-map.html` и `README.md`

## 9. Источники

1. `soarsmu/BugsInPy` — https://github.com/soarsmu/BugsInPy — доступно 2026-11-01.
2. `rjust/defects4j` — https://github.com/rjust/defects4j — доступно 2026-11-01.
3. `HypothesisWorks/hypothesis` — https://github.com/HypothesisWorks/hypothesis — доступно 2026-11-01.
4. `dubzzz/fast-check` — https://github.com/dubzzz/fast-check — доступно 2026-11-01.
5. `GZoltar/gzoltar` — https://github.com/GZoltar/gzoltar — доступно 2026-11-01.
6. `google/oss-fuzz` — https://github.com/google/oss-fuzz — доступно 2026-11-01.
7. Zeller & Hildebrandt, 2002 — https://doi.org/10.1109/32.988498 — доступно 2026-11-01.
8. Wong et al., 2016 — https://doi.org/10.1109/TSE.2016.2521368 — доступно 2026-11-01.
9. Parnin & Orso, 2011 — https://doi.org/10.1145/2001420.2001445 — доступно 2026-11-01.
10. Bettenburg et al., 2008 — https://doi.org/10.1145/1453101.1453146 — доступно 2026-11-01.
11. Just et al., 2014 — https://doi.org/10.1145/2610384.2628055 — доступно 2026-11-01.
12. Rafique & Misic, 2013 — https://doi.org/10.1109/TSE.2012.28 — доступно 2026-11-01.
13. Wang et al., 2025 — https://doi.org/10.1109/MSR66628.2025.00019 — доступно 2026-11-01.
14. Git `bisect` — https://git-scm.com/docs/git-bisect — доступно 2026-11-01.
15. OSS-Fuzz, Reproducing — https://google.github.io/oss-fuzz/advanced-topics/reproducing/ — доступно 2026-11-01.
16. Hypothesis, Replaying failures — https://hypothesis.readthedocs.io/en/latest/tutorial/replaying-failures.html — доступно 2026-11-01.
17. pytest, How to handle test failures — https://docs.pytest.org/en/stable/how-to/failures.html — доступно 2026-11-01.