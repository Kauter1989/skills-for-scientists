# Каталог дефектов

Один дефект — один каталог `docs/bugs/<id>/`.

| Файл | Назначение |
|---|---|
| `repro.md` | подробное описание, шаги, логи |
| `repro.json` | машиночитаемый отчёт |
| `probe.json` | прогоны и классификация |

Подход: `test-first`. Минимум прогонов: 3.
Проверка: `python .opencode/skill/dev-bug-process/scripts/check_bug_report.py --root . --report docs/bugs/<id>/repro.json --strict`.
