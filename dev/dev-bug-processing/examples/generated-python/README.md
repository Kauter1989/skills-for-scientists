# Demo project — намеренно падающий тест

Учебный проект для `dev-bug-processing`. В `median.py` есть дефект: для
чётной длины возвращается второй средний элемент без усреднения.

Тест `tests/test_median.py` **падает намеренно**:

```bash
python -m unittest discover -s tests
```

Ожидаемый результат: `AssertionError: 3 != 2.5`.

Артефакты дефекта лежат в `docs/bugs/median/`:

- `repro.md` — описание;
- `repro.json` — машиночитаемый отчёт;
- `probe.json` — три одинаковых падения.

Проверка отчёта:

```bash
python .opencode/skill/dev-bug-process/scripts/check_bug_report.py \
  --root . --report docs/bugs/median/repro.json --strict
```

Сгенерированный навык лежит в `.opencode/skill/dev-bug-process/`.