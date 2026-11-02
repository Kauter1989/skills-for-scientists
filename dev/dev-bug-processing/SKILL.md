---
name: dev-bug-processing
description: >-
  Мета-навык: опрос репозитория, выбор подхода к отладке (test-first,
  container-first, incident-first, benchmark-first, lightweight) и генерация
  навыка dev-bug-process с инвариантами воспроизводимости и подробного
  описания. Use when setting up bug processing for a repository. Trigger on:
  bug processing, bug workflow, defect workflow, debugging setup,
  bug reproduction, настроить обработку багов, отладка дефектов.
license: Apache-2.0
metadata:
  domain: dev
  contract: harness-skill-template
  version: "0.1.0"
---

# dev-bug-processing — обработка дефектов под конкретный репозиторий

Мета-навык не обрабатывает отдельный дефект. Он проводит опрос, определяет
профиль репозитория, выбирает подход к отладке и генерирует операционный
навык `dev-bug-process` в целевом репозитории. Ядро процесса не
настраивается: подробное описание и воспроизводимость обязательны. Меняются
команды, пути, трекер, окружение и глубина церемонии.

> **Точка входа.** Если не знаете, с чего начать, или нужен новый проект,
> научная работа либо набор навыков — сначала `harness-init`. Он проведёт
> опрос и направит сюда, если нужна настройка обработки дефектов. SDD для
> нового проекта настраивается отдельно командой `/dev-spec-chain`.

Нормативные документы:

| Файл | Содержание |
|---|---|
| `references/approach-selection.md` | профили, матрица подходов, правила выбора |
| `references/bug-contract.md` | контракт сгенерированного навыка, инварианты, поля |
| `templates/bug-processing-plan.html` | HTML-план на утверждение |
| `templates/bug-processing.yml` | манифест сгенерированного навыка |
| `templates/generated-SKILL.md` | шаблон `dev-bug-process` |
| `templates/bug-report.md` | человекочитаемый отчёт о дефекте |
| `templates/repro.json` | машиночитаемый отчёт |
| `templates/probe_bug.py` | измерение детерминированности |
| `templates/check_bug_report.py` | проверка отчёта о дефекте |
| `scripts/generate_bug_skill.py` | survey / plan / approve / apply |
| `scripts/check_bug_skill.py` | проверка сгенерированного навыка |

> Если `skill` tool не видит навык, положите каталог в
> `.opencode/skill/dev-bug-processing/` или
> `~/.config/opencode/skill/dev-bug-processing/`.

## Когда применять

- в репозитории настраивается единый процесс обработки дефектов;
- команда не знает, с чего начинать: issue, тест, логи или контейнер;
- нужно выбрать между test-first, container-first, incident-first,
  benchmark-first и lightweight;
- нужен сгенерированный навык с командами и путями конкретного репозитория;
- нужно обновить процесс при смене стека, трекера или окружения.

## Когда не применять

- нужно обработать конкретный дефект — это сгенерированный
  `dev-bug-process`;
- нужна новая фича — это `dev-feature-start`;
- нужна цепочка спецификаций — это `dev-spec-chain`;
- нужна защита от регрессий после фикса — это `dev-regression-guard`;
- нужен один общий навык без профиля репозитория — это `harness-skill-template`.

## Вход

- репозиторий или его профиль;
- стек, тестовый фреймворк, команда тестов, путь к тестам;
- трекер и шаблон issue;
- окружение: `local`, `container`, `production`, `benchmark`;
- размер команды и compliance;
- политика флейков и глубина воспроизведения;
- режим утверждения `user` / `autonomous`;
- подход, если пользователь уже выбрал.

## Процедура

1. **Провести опрос.**

   ```bash
   python scripts/generate_bug_skill.py survey --out answers.json
   ```

   Enter принимает значение по умолчанию. Для незнакомого стека укажите
   `other` и команду тестов вручную.

2. **Собрать план.**

   ```bash
   python scripts/generate_bug_skill.py plan --root . \
     --answers answers.json \
     --out bug-processing-plan.html \
     --json bug-processing-plan.json
   ```

3. **Показать HTML-план.** Профиль, подход, инварианты, гейты и файлы.
4. **Получить `approved`.**

   ```bash
   python scripts/generate_bug_skill.py approve \
     --plan bug-processing-plan.html --json bug-processing-plan.json
   ```

5. **Сгенерировать навык.** `apply` откажется работать без `approved` и не
   перезапишет существующий навык без `--force`.

   ```bash
   python scripts/generate_bug_skill.py apply \
     --root . --plan-json bug-processing-plan.json
   ```

6. **Проверить навык.**

   ```bash
   python scripts/check_bug_skill.py --root .
   ```

7. **Передать работу.** Дальше дефекты обрабатывает сгенерированный
   `dev-bug-process`; мета-навык в них не участвует.

## Выход

- `bug-processing-plan.html` и `bug-processing-plan.json`;
- `.opencode/bug-processing.yml`;
- `.opencode/skill/dev-bug-process/SKILL.md`;
- `references/`, `templates/`, `scripts/` и `examples/` сгенерированного
  навыка;
- `docs/bugs/README.md` — шаблон артефактов дефекта;
- `bug-processing-report.md`;
- отчёт `check_bug_skill.py`.

## Доказательства

- HTML-план имеет статус `approved` до генерации;
- `apply` отказывается работать с `draft`;
- манифест содержит профиль, подход, 9 инвариантов и гейты;
- сгенерированный `SKILL.md` содержит обязательные разделы;
- `dev-bug-process` ссылается на существующие templates и scripts;
- `check_bug_skill.py` проходит;
- повторный `apply` без `--force` не перезаписывает файлы.

## Границы

- Не обрабатывает конкретный дефект за сгенерированный навык.
- Не исправляет код и не мержит изменения.
- Не выбирает подход без ответов или явного решения пользователя.
- Не генерирует навык до `approved`.
- Не перезаписывает существующий навык без `--force`.
- Не запускает недоверенные команды автоматически.
- Не хранит сгенерированный навык в этой библиотеке.

## Типовые ошибки

- генерировать навык без профиля репозитория;
- выбирать `test-first` для production-инцидента без локального
  воспроизведения;
- отключать инвариант воспроизводимости ради «лёгкого» процесса;
- запускать `apply` до `approved`;
- перезаписывать существующий `dev-bug-process`;
- считать один прогон доказательством;
- выдавать гипотезу за установленную причину;
- запускать недоверенную команду без sandbox.

## QA

- [ ] профиль репозитория зафиксирован;
- [ ] подход выбран и обоснован;
- [ ] HTML-план утверждён;
- [ ] манифест создан;
- [ ] 9 инвариантов включены;
- [ ] сгенерированный навык содержит обязательные разделы;
- [ ] `check_bug_skill.py` проходит;
- [ ] существующие файлы не перезаписаны без решения.

## Файлы

| Путь | Назначение |
|---|---|
| `references/approach-selection.md` | матрица подходов |
| `references/bug-contract.md` | контракт `dev-bug-process` |
| `templates/bug-processing-plan.html` | план на утверждение |
| `templates/bug-processing.yml` | манифест |
| `templates/generated-SKILL.md` | шаблон операционного навыка |
| `templates/bug-report.md` | отчёт о дефекте |
| `templates/repro.json` | машиночитаемый отчёт |
| `templates/probe_bug.py` | прогоны и классификация |
| `templates/check_bug_report.py` | проверка отчёта |
| `scripts/generate_bug_skill.py` | генерация |
| `scripts/check_bug_skill.py` | проверка |
| `examples/answers-python.json` | пример test-first |
| `examples/answers-container.json` | пример container-first |
| `examples/bug-processing-plan-python.html` | пример плана |
| `examples/generated-python/` | пример сгенерированного навыка |