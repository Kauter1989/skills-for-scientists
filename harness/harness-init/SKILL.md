---
name: harness-init
description: >-
  Разворачивает процесс в новом репозитории: опрос пользователя, подбор
  стартовых навыков и плагинов, профиль, AGENTS.md, docs, хуки, CI и утверждение workflow
  в HTML. Use when starting a repository, onboarding a project, or creating a
  skill harness. Trigger on: инициализация репозитория, новый проект, bootstrap,
  onboarding, harness init, опрос для старта.
license: Apache-2.0
metadata:
  domain: harness
  contract: harness-skill-template
  version: "0.1.0"
---

# harness-init — bootstrap с опросом и утверждением

Навык поднимает процесс в новом репозитории: задаёт вопросы пользователю,
подбирает стартовые навыки, собирает HTML-план workflow и создаёт файлы
только после `approved`.

Нормативные документы:

| Файл | Содержание |
|---|---|
| `references/survey.md` | вопросы опроса и правила формулировок |
| `references/bootstrap-checklist.md` | минимальный состав bootstrap |
| `templates/bootstrap-plan.html` | форма плана на утверждение |
| `scripts/init_repo.py` | survey, plan, approve, apply |
| `scripts/check_bootstrap.py` | проверка результата |

> При добавлении нового плагина обновите `references/plugins.json` и строку
> в `opencode-plugins/INSTALL.md`.

> Если `skill` tool не видит навык, положите каталог в
> `.opencode/skill/harness-init/` или
> `~/.config/opencode/skill/harness-init/`.

## Когда применять

- новый репозиторий или проект без процесса;
- нужно перенести процесс в существующий репозиторий без перезаписи;
- нужно выбрать стартовый набор навыков под задачи;
- нужен утверждаемый workflow для команды.

## Когда не применять

- репозиторий уже настроен и проходит `check_bootstrap.py`;
- нужен только новый навык — это `harness-skill-template`;
- нужен аудит библиотеки — это `harness-skill-audit`;
- нужна оценка навыка — это `harness-skill-eval` (deferred).

## Вход

- путь к новому или существующему репозиторию;
- ответы пользователя: домен, стек, команды, роли, задачи, ограничения;
- выбранные плагины OpenCode из `references/plugins.json` по категориям или `none`;
- выбранный workflow: минимальный или расширенный;
- решение по CI и перезаписи.

## Процедура

1. **Провести опрос.** Задать вопросы из `references/survey.md`; сохранить
   ответы в `answers.json`. Перед вопросом о плагинах показать каталог
   `references/plugins.json` по категориям с краткими описаниями задач;
   временные интеграции пометить `temporary`; по умолчанию — `none`.

   ```bash
   python scripts/init_repo.py survey --out answers.json
   ```

2. **Собрать план.** Сгенерировать `bootstrap-plan.html` и JSON:

   ```bash
   python scripts/init_repo.py plan --root . \
     --answers answers.json \
     --out bootstrap-plan.html \
     --json bootstrap-plan.json
   ```

3. **Показать план пользователю.** В плане: стартовые навыки, выбранные
   плагины и их задачи, этапы workflow, команды и список создаваемых файлов.
4. **Получить `approved`.** Только после явного решения:

   ```bash
   python scripts/init_repo.py approve \
     --plan bootstrap-plan.html --json bootstrap-plan.json
   ```

5. **Создать файлы.** `apply` откажется работать без `approved`; по
   умолчанию существующие файлы не перезаписываются.

   ```bash
   python scripts/init_repo.py apply --root . --plan-json bootstrap-plan.json
   ```

6. **Проверить bootstrap.**

   ```bash
   python scripts/check_bootstrap.py --root .
   ```

## Выход

- `answers.json` — ответы опроса;
- `bootstrap-plan.html` — workflow, набор навыков и плагинов на утверждение;
- `bootstrap-plan.json` — статус и данные плана;
- `profile.yml`, `AGENTS.md`, `docs/`, `docs/plugins.md`, `.pre-commit-config.yaml`, CI;
- `bootstrap-report.md` — что создано и что пропущено.

## Доказательства

- `bootstrap-plan.html` содержит статус `approved` до scaffold;
- `apply` отказывается работать со статусом `draft`;
- `check_bootstrap.py` проходит на созданном репозитории;
- повторный `apply` не перезаписывает файлы без `--force`;
- в плане перечислены только реализованные навыки;
- выбранные плагины перечислены в плане, `profile.yml` и `docs/plugins.md`.

## Границы

- Не устанавливает зависимости и не выбирает стек.
- Не устанавливает плагины автоматически: только фиксирует выбор и ссылку на инструкцию.
- Не делает commit, push и PR.
- Не перезаписывает существующие файлы без `--force`.
- Не рекомендует proposed-навыки как установленные.
- Не заменяет ревью плана пользователем.

## Типовые ошибки

- запуск `apply` без `approved`;
- рекомендация proposed-навыка как готового;
- плагин без описания задачи или без инструкции установки;
- перезапись `AGENTS.md` без подтверждения;
- пустая команда тестов, замаскированная под проверку;
- план без списка создаваемых файлов;
- `check_bootstrap.py` не запускался.

## QA

- [ ] опрос проведён, ответы сохранены;
- [ ] в плане есть навыки, этапы, команды и файлы;
- [ ] план утверждён пользователем;
- [ ] `apply` не перезаписал существующее;
- [ ] `check_bootstrap.py` проходит;
- [ ] `profile.yml` содержит команды и навыки;
- [ ] выбранные плагины есть в `profile.yml` и `docs/plugins.md`;
- [ ] категории плагинов указаны;
- [ ] временные интеграции помечены `temporary`;
- [ ] CI создан только если выбран;
- [ ] нет секретов и проектных данных в шаблонах.

## Файлы

| Путь | Назначение |
|---|---|
| `references/survey.md` | вопросы опроса |
| `references/plugins.json` | каталог плагинов и ссылок на установку |
| `references/bootstrap-checklist.md` | минимальный состав |
| `templates/bootstrap-plan.html` | план на утверждение |
| `templates/profile.yml` | профиль |
| `templates/AGENTS.md` | правила репозитория |
| `scripts/init_repo.py` | survey/plan/approve/apply |
| `scripts/check_bootstrap.py` | проверка |
| `examples/answers-example.json` | пример ответов |
| `examples/bootstrap-plan-example.html` | пример плана |