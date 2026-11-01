# Дефект: `median`

| Поле | Значение |
|---|---|
| Статус | `reproduced` |
| Symptom | `median([1, 2, 3, 4])` возвращает `3` вместо `2.5` |
| Expected | `2.5` |
| Actual | `3` |
| Окружение | Python 3.12, Windows, demo-project, commit HEAD |
| Команда | `python -m unittest discover -s tests` |
| Прогоны | 3, из них failed 3 / passed 0 |
| Трекер | `none` |

## Шаги воспроизведения

1. Открыть каталог `examples/generated-python`.
2. Выполнить `python -m unittest discover -s tests`.
3. Увидеть `AssertionError: 3 != 2.5`.

## Входные данные

- `[1, 2, 3, 4]`

## Логи и трейсы

```text
FAIL: test_even_length_returns_mean_of_middle_two
AssertionError: 3 != 2.5
```

## Минимальный вход

```text
median([1, 2, 3, 4])
```

Удалено при минимизации:

- CLI-обёртка;
- файловый ввод;
- значения 5..10.

## Падающий тест

- Путь: `tests/test_median.py`
- Имя: `tests.test_median.MedianTest.test_even_length_returns_mean_of_middle_two`
- Red output:

```text
AssertionError: 3 != 2.5
```

Соответствует ли падение symptom: да.

## Гипотезы

| # | Гипотеза | Evidence | Confidence | Следующий probe |
|---|---|---|---|---|
| 1 | `median` возвращает `ordered[len // 2]` и игнорирует второй средний элемент для чётной длины | `median.py` возвращает `ordered[middle]`; тест падает только на чётной длине | `derived` | Проверить `median([1, 2])` и `median([])` |

## Следующие шаги

- Исправить `median` для чётной длины.
- После фикса прогнать red test и полный набор тестов.

## Проверка

```bash
python .opencode/skill/dev-bug-process/scripts/check_bug_report.py \
  --root . --report docs/bugs/median/repro.json --strict
```