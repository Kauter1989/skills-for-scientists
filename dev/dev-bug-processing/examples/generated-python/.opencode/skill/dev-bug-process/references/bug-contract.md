# Контракт `dev-bug-process`

Нормативный документ сгенерированного навыка. Определяет артефакты, поля,
статусы и гейты. Профиль репозитория меняет команды и пути, но не этот
контракт.

## 1. Расположение

```text
<repo>/
├── .opencode/
│   ├── bug-processing.yml
│   └── skill/dev-bug-process/
│       ├── SKILL.md
│       ├── references/bug-contract.md
│       ├── templates/bug-report.md
│       ├── templates/repro.json
│       ├── scripts/probe_bug.py
│       ├── scripts/check_bug_report.py
│       └── examples/README.md
└── docs/
    └── bugs/
        ├── README.md
        └── <id>/
            ├── repro.md
            ├── repro.json
            └── probe.json
```

`<id>` — короткий идентификатор дефекта: номер issue или slug. Один дефект —
один каталог.

## 2. Манифест

```yaml
version: 1
repo: example-service
generated_skill: dev-bug-process
profile:
  stack: python
  test_framework: pytest
  test_command: python -m pytest
  test_root: tests/
  tracker: github
  environment: local
  team: small
  compliance: none
  flake_policy: strict
  repro_depth: standard
  approval: user
approach: test-first
invariants:
  detailed_description: true
  reproducibility: true
  minimal_case: true
  red_test: true
  failure_matches_symptom: true
  evidence_based_diagnosis: true
  no_fix_before_red: true
  repo_artifacts: true
  no_auto_run: true
gates:
  min_runs: 3
  require_minimal: true
  require_failure_match: true
  require_hypotheses: true
artifacts:
  bug_dir: docs/bugs/<id>
  report: docs/bugs/<id>/repro.md
  manifest: docs/bugs/<id>/repro.json
  probe: docs/bugs/<id>/probe.json
  test_root: tests/
```

Правила:

- `version` — 1;
- `generated_skill` — `dev-bug-process`;
- `approach` — один из пяти;
- все 9 инвариантов — `true`;
- `gates.min_runs` — не меньше 3;
- `profile.test_command` и `profile.test_root` не пустые.

## 3. `repro.json`

Обязательные поля:

| Поле | Тип | Смысл |
|---|---|---|
| `version` | int | 1 |
| `id` | string | совпадает с каталогом |
| `status` | string | `reproduced`, `not-reproduced`, `flaky`, `blocked` |
| `symptom` | string | наблюдаемое поведение |
| `expected` | string | ожидаемое поведение |
| `actual` | string | фактическое поведение |
| `environment` | string | ОС, версия, образ, коммит |
| `command` | string | точная команда запуска |
| `runs` | int | число прогонов, ≥ `min_runs` |
| `results` | object | `failed` и `passed` |
| `minimal_case` | string | минимальный вход или сценарий |
| `removed` | array | что удалено при минимизации и почему |
| `test` | object | `path`, `name`, `red_output`, `failure_matches_symptom` |
| `diagnosis` | object | `hypotheses[]` |
| `probe_path` | string | путь к `probe.json`; опционально |
| `next_steps` | array | обязателен для `not-reproduced` |
| `blocked_reason` | string | обязателен для `blocked` |

## 4. Статусы

| Статус | Условие | Что разрешено |
|---|---|---|
| `reproduced` | все прогоны падают одинаково, есть red test | диагноз и передача в фикс |
| `flaky` | есть и падения, и прохождения | нельзя фиксить; нужен план стабилизации |
| `not-reproduced` | все прогоны проходят | нельзя фиксить; нужен следующий probe |
| `blocked` | нет доступа, окружения или данных | нельзя фиксить; зафиксировать причину |

`flaky` в `--strict` считается ошибкой: недетерминированный дефект не
проходит гейт.

## 5. Гипотезы и confidence

Каждая гипотеза:

```json
{
  "claim": "функция возвращает середину без усреднения",
  "evidence": "строка 4 в median.py; падают только чётные длины",
  "confidence": "derived",
  "next_probe": "проверить median([1, 2]) и median([])"
}
```

Допустимые значения `confidence`:

- `measured` — проверено измерением или тестом;
- `derived` — выведено из кода, логов или стека;
- `estimated` — правдоподобно, но не проверено;
- `expert` — мнение без воспроизводимого основания;
- `missing` — данных нет.

Фикс разрешён при `measured` или `derived`. При `estimated` и ниже нужно
явное решение пользователя. `expert` и `missing` не считаются диагнозом.

## 6. Минимальность

Вход считается минимальным, если:

- удаление любого оставшегося элемента прекращает падение;
- каждый оставшийся элемент связан с symptom;
- `removed` перечисляет удалённые части и причину;
- для больших входов применяется delta debugging или shrinking.

Нельзя уменьшать вход, пока не зафиксирован baseline: команда, ревизия и
окружение.

## 7. Флейки

- минимум 3 прогона; при `flake_policy=retry` или `repro_depth=deep` — 5;
- одинаковый результат обязателен для `reproduced`;
- смешанный результат — `flaky`, даже если падений больше;
- для `flaky` фиксируются частота, условия и следующий probe;
- фикс флейка начинается только после стабильного red test.

## 8. Запуск команд

- `probe_bug.py` запускает команду только по явному `--`;
- по умолчанию команда не выполняется;
- недоверенные команды запускаются в sandbox;
- сеть, секреты и разрушительные операции — только с разрешения
  пользователя;
- вывод сохраняется в `probe.json`, но не публикуется с секретами.

## 9. Проверка

```bash
python .opencode/skill/dev-bug-process/scripts/check_bug_report.py \
  --root . --report docs/bugs/<id>/repro.json --strict
```

Проверяется:

- обязательные поля и типы;
- `runs ≥ min_runs`;
- согласованность `results` и `status`;
- существование red test;
- непустой `red_output`;
- `failure_matches_symptom`;
- наличие гипотез и полей evidence / next_probe;
- соответствие `probe.json`, если он указан.

Смысл гипотез и качество теста проверяются на ревью, а не скриптом.