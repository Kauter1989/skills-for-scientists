# Дефект: `<id>`

| Поле | Значение |
|---|---|
| Статус | `reproduced` / `flaky` / `not-reproduced` / `blocked` |
| Symptom | ... |
| Expected | ... |
| Actual | ... |
| Окружение | ОС, версия, коммит или образ |
| Команда | точная команда запуска |
| Прогоны | N, из них failed / passed |
| Трекер | ссылка на issue или `none` |

## Шаги воспроизведения

1. ...
2. ...
3. ...

## Входные данные

- ...

## Логи и трейсы

```text
...
```

## Минимальный вход

```text
...
```

Удалено при минимизации:

- ...

## Падающий тест

- Путь: `...`
- Имя: `...`
- Red output:

```text
...
```

Соответствует ли падение symptom: `да` / `нет`.

## Гипотезы

| # | Гипотеза | Evidence | Confidence | Следующий probe |
|---|---|---|---|---|
| 1 | ... | ... | `measured` / `derived` / `estimated` / `expert` / `missing` | ... |

## Следующие шаги

- ...

## Проверка

```bash
python .opencode/skill/dev-bug-process/scripts/check_bug_report.py \
  --root . --report docs/bugs/<id>/repro.json --strict
```