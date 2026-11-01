---
name: dev-spec-chain
description: >-
  Мета-навык: по опросу определяет профиль репозитория, выбирает spec-kit,
  OpenSpec, BMAD или lightweight и генерирует цепочку stage-навыков с гейтами.
  Use when setting up spec-driven development for a repository. Trigger on:
  spec chain, spec-driven setup, greenfield, brownfield, OpenSpec, spec-kit,
  BMAD, сгенерировать цепочку навыков.
license: Apache-2.0
metadata:
  domain: dev
  contract: harness-skill-template
  version: "0.1.0"
---

# dev-spec-chain — цепочка под конкретный репозиторий

Мета-навык не выполняет стадии. Он проводит опрос, выбирает подход и
генерирует stage-навыки в целевом репозитории. Один и тот же chain не
подходит greenfield и brownfield, поэтому профиль определяется до выбора
подхода.

Нормативные документы:

| Файл | Содержание |
|---|---|
| `references/approach-selection.md` | профили, матрица подходов и гейты |
| `references/chain-contract.md` | манифест и структура сгенерированных навыков |
| `templates/spec-chain-plan.html` | HTML-план на утверждение |
| `templates/spec-chain.yml` | манифест |
| `templates/stage-SKILL.md` | шаблон stage-навыка |
| `scripts/generate_chain.py` | survey / plan / approve / apply |
| `scripts/check_spec_chain.py` | проверка chain |

> Если `skill` tool не видит навык, положите каталог в
> `.opencode/skill/dev-spec-chain/` или
> `~/.config/opencode/skill/dev-spec-chain/`.

## Когда применять

- в репозитории настраивается spec-driven процесс;
- нужно выбрать между spec-kit, OpenSpec, BMAD и lightweight;
- нужен набор stage-навыков под гейты конкретной команды;
- нужно обновить chain при смене профиля репозитория.

## Когда не применять

- chain уже сгенерирован и проходит `check_spec_chain.py`;
- нужен только один навык — это `harness-skill-template`;
- нужен старт фичи — это `dev-feature-start`;
- нужно выполнить стадию — это сгенерированный stage-навык.

## Вход

- репозиторий или его профиль;
- режим: greenfield / brownfield;
- размер изменений, роли, compliance, стек;
- режим утверждения `user` / `autonomous`;
- строгость гейтов `light` / `standard` / `strict`;
- подход, если пользователь уже выбрал.

## Процедура

1. **Провести опрос.**

   ```bash
   python scripts/generate_chain.py survey --out answers.json
   ```

2. **Собрать план.**

   ```bash
   python scripts/generate_chain.py plan --root . \
     --answers answers.json \
     --out spec-chain-plan.html \
     --json spec-chain-plan.json
   ```

3. **Показать HTML-план.** Профиль, подход, стадии, гейты и файлы.
4. **Получить `approved`.**

   ```bash
   python scripts/generate_chain.py approve \
     --plan spec-chain-plan.html --json spec-chain-plan.json
   ```

5. **Сгенерировать chain.** `apply` откажется работать без `approved` и
   не перезапишет существующие навыки без `--force`.

   ```bash
   python scripts/generate_chain.py apply --root . --plan-json spec-chain-plan.json
   ```

6. **Проверить chain.**

   ```bash
   python scripts/check_spec_chain.py --root .
   ```

## Выход

- `spec-chain-plan.html` и `spec-chain-plan.json`;
- `.opencode/spec-chain.yml`;
- `.opencode/skill/<stage>/SKILL.md` для выбранных стадий;
- `spec-chain-report.md`;
- отчёт `check_spec_chain.py`.

## Доказательства

- HTML-план имеет статус `approved` до генерации;
- `apply` отказывается работать с `draft`;
- манифест содержит подход, профиль и стадии;
- каждый stage-навык существует и проходит структурную проверку;
- порядок стадий соблюдён;
- `tests_first: true` в манифесте.

## Границы

- Не выполняет стадии за сгенерированные навыки.
- Не пишет `spec.md`, `plan.md`, `tasks.md` и код.
- Не перезаписывает существующие навыки без `--force`.
- Не выбирает подход без ответов или явного решения пользователя.
- Не хранит сгенерированные навыки в этой библиотеке.

## Типовые ошибки

- генерировать chain без профиля репозитория;
- выбирать spec-kit для brownfield без spec deltas;
- выбирать lightweight без traceability;
- запускать apply до approved;
- перезаписывать существующие stage-навыки;
- генерировать implement раньше analyze.

## QA

- [ ] профиль и подход зафиксированы;
- [ ] HTML-план утверждён;
- [ ] манифест создан;
- [ ] stage-навыки созданы;
- [ ] порядок стадий соблюдён;
- [ ] `check_spec_chain.py` проходит;
- [ ] существующие файлы не перезаписаны без решения.

## Файлы

| Путь | Назначение |
|---|---|
| `references/approach-selection.md` | матрица подходов |
| `references/chain-contract.md` | контракт chain |
| `templates/spec-chain-plan.html` | план |
| `templates/spec-chain.yml` | манифест |
| `templates/stage-SKILL.md` | stage-навык |
| `scripts/generate_chain.py` | генерация |
| `scripts/check_spec_chain.py` | проверка |
| `examples/answers-greenfield.json` | пример greenfield |
| `examples/answers-brownfield.json` | пример brownfield |
| `examples/spec-chain-plan-greenfield.html` | пример плана |