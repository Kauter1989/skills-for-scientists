# Формат registry правил

Источник правды: **`docs/rules/registry.yml`**. Один файл, один формат,
версия вместе с кодом.

## 1. Зачем

Registry отвечает на вопросы:

- какие правила у репозитория есть;
- чем каждое проверяется;
- кто владелец и что делать при ложном срабатывании;
- сколько стоит проверка;
- разрешён ли обход;
- где доказательство, что проверка работает.

Registry — не замена конфигам. Он ссылается на них, а не копирует.

## 2. Схема

```yaml
version: 1
rules:
  - id: ARCH-001
    rule: "domain не импортирует infrastructure"
    trigger: "import из infrastructure в domain/"
    mechanism:
      type: test
      command: "pytest tests/architecture/test_layers.py"
      config: ""
      contract: "domain-independent"
    level: CI
    owner: architecture
    cost: "8 секунд в CI"
    bypass: "только через ADR"
    evidence: tests/architecture/test_layers.py
    status: active
    since: "2026-10-31"
```

## 3. Поля

| Поле | Обязательно | Тип | Ограничение |
|---|---|---|---|
| `version` | да | int | сейчас `1` |
| `rules` | да | list | может быть пустым |
| `id` | да | string | `PREFIX-001`, уникальный |
| `rule` | да | string | одно предложение |
| `trigger` | да | string | как выглядит нарушение |
| `mechanism.type` | да | string | `hook`, `lint`, `test`, `policy`, `scanner`, `ci`, `script` |
| `mechanism.command` | нет | string | команда запуска |
| `mechanism.config` | нет | string | путь к конфигу |
| `mechanism.contract` | нет | string | имя контракта для architecture/policy |
| `level` | да | string | `editor`, `pre-commit`, `CI`, `runtime` |
| `owner` | да | string | команда или роль |
| `cost` | да | string | latency/шум/обслуживание |
| `bypass` | да | string | правило обхода или `нет` |
| `evidence` | да | string | путь к тесту |
| `status` | да | string | `proposed`, `active`, `deprecated` |
| `since` | нет | date | ISO `YYYY-MM-DD` |
| `notes` | нет | string | ограничение или ссылка |

В `mechanism` нужен хотя бы один из `command`, `config`, `contract`.

## 4. Статусы

| Статус | Значит |
|---|---|
| `proposed` | правило сформулировано, механизм ещё не проверен |
| `active` | тест падает на нарушении, baseline чист, evidence существует |
| `deprecated` | правило больше не действует; запись сохраняется для истории |

`active` без существующего `evidence` запрещён.

## 5. Жизненный цикл

1. **Proposed.** Добавить запись, указать предполагаемый механизм.
2. **Implement.** Написать тест и механизм.
3. **Verify.** Показать падение на нарушении и чистый baseline.
4. **Active.** Обновить статус и evidence.
5. **Deprecated.** Пометить и указать замену в `notes`.

## 6. Проверка

```bash
python scripts/validate_rule.py --registry docs/rules/registry.yml --repo .
python scripts/validate_rule.py --registry docs/rules/registry.yml --repo . --json
```

Проверяется:

- версия и структура;
- обязательные поля;
- уникальность `id` и формат;
- допустимые `status`, `level`, `mechanism.type`;
- существование `evidence` относительно `--repo`;
- `active` без evidence;
- пустые `owner`, `cost`, `bypass`.

Смысл правила и качество механизма валидатор не проверяет.

## 7. Правила ведения

- Один id — одно правило. Не переиспользовать id после удаления.
- Не менять смысл правила под тем же id; создать новый.
- Обход фиксируется в `bypass`, а не в переписке.
- При смене механизма обновить `mechanism`, `cost` и `evidence`.
- Устаревшие правила не удалять сразу: `deprecated` сохраняет историю.
- Registry и механизм меняются одним PR.

## 8. Пример пустого registry

```yaml
version: 1
rules: []
```

Пустой registry допустим, но навык не должен считать это покрытием правил.