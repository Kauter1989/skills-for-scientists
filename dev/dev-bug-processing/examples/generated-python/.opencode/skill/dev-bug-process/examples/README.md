# Пример обработки дефекта — demo-project

Подход: `test-first`. Команда тестов: `python -m unittest discover -s tests`.

1. Создайте `docs/bugs/<id>/repro.md` и `repro.json` из шаблонов.
2. Запустите прогоны:

   ```bash
   python .opencode/skill/dev-bug-process/scripts/probe_bug.py \
     --runs 3 --out docs/bugs/<id>/probe.json -- \
     python -m unittest discover -s tests
   ```

3. Заполните red test и гипотезы.
4. Проверьте отчёт:

   ```bash
   python .opencode/skill/dev-bug-process/scripts/check_bug_report.py \
     --root . --report docs/bugs/<id>/repro.json --strict
   ```
