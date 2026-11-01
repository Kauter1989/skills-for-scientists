---
name: dev-bug-process
description: >-
  Обработка дефектов в demo-project по подходу test-first: подробное описание,
  детерминированное воспроизведение (≥3 прогонов), минимальный
  вход, падающий тест и диагноз с evidence. Use when handling a bug in
  demo-project. Trigger on: bug, defect, regression, reproduce, отладка,
  воспроизвести баг, разобрать дефект.
license: Apache-2.0
metadata:
  domain: dev
  contract: harness-skill-template
  version: "0.1.0"
---

# dev-bug-process — обработка дефектов в demo-project

Операционный навык, сгенерированный `dev-bug-processing`. Подход:
**test-first**. Стек: `python`, тесты: `unittest`, команда:
`python -m unittest discover -s tests`, каталог тестов: `tests/`. Окружение:
`local`, трекер: `none`.

Основной путь — локальный тестовый фреймворк. Red test пишется в `tests/` и запускается командой `python -m unittest discover -s tests`. Минимальный вход уменьшается вручную или delta debugging; `git bisect` предлагается как следующий probe, но не запускается автоматически.

## Когда применять

- есть сообщение о дефекте, регрессии или неверном поведении;
- нужно воспроизвести дефект до исправления;
- нужно превратить описание в падающий автотест;
- нужно сузить причину и передать диагноз в фикс.

## Когда не применять

- нужна новая функциональность — это `dev-feature-start`;
- нужна цепочка спецификаций — это `dev-spec-chain`;
- дефект уже воспроизведён и есть red test — переходите к фиксу;
- нужна защита от целого класса регрессий — это `dev-regression-guard`;
- нужен только отчёт без теста — это не тот навык.

## Вход

- описание дефекта: symptom, expected, actual;
- версия, коммит, ОС, зависимости или образ;
- шаги воспроизведения, входные данные, логи и трейсы;
- команда запуска и путь к тесту;
- ссылка на issue не требуется.

## Процедура

1. **Зафиксировать описание.** Создайте `docs/bugs/<id>/repro.md` и
   `repro.json` из шаблонов. Заполните expected, actual, окружение, версию,
   шаги, входы и логи. Без этого шага дальше не идти.
2. **Воспроизвести.** Запустите точную команду:

   ```bash
   python .opencode/skill/dev-bug-process/scripts/probe_bug.py \
     --runs 3 --out docs/bugs/<id>/probe.json -- python -m unittest discover -s tests
   ```

   Все прогоны падают одинаково → `reproduced`. Смешанный результат →
   `flaky`, остановиться и зафиксировать частоту и условия. Все проходят →
   `not-reproduced`, записать следующий probe.
3. **Уменьшить вход.** Удаляйте шаги, данные и зависимости по одному.
   Оставляйте элемент только если без него падение исчезает. Запишите
   `minimal_case` и `removed`.
4. **Сделать red test.** Добавьте тест в `tests/`. Запустите только
   его. Убедитесь, что сообщение и стек соответствуют symptom, а не ошибке
   setup. Заполните `test.path`, `test.name`, `test.red_output` и
   `failure_matches_symptom`.
5. **Локализовать причину.** Используйте стек, логи, `git bisect` или
   SBFL. Каждая гипотеза получает `claim`, `evidence`, `confidence` и
   `next_probe`. Не выдавайте ранжирование за доказанную причину.
6. **Проверить отчёт.**

   ```bash
   python .opencode/skill/dev-bug-process/scripts/check_bug_report.py \
     --root . --report docs/bugs/<id>/repro.json --strict
   ```

7. **Передать в фикс.** Фикс начинается только после `reproduced` и
   зелёного `check_bug_report.py`. После фикса red test должен стать
   зелёным; это проверяет `dev-regression-guard`.

## Выход

- `docs/bugs/<id>/repro.md` — подробное описание;
- `docs/bugs/<id>/repro.json` — машиночитаемый отчёт;
- `docs/bugs/<id>/probe.json` — прогоны и классификация;
- падающий тест в `tests/`;
- ранжированные гипотезы с evidence;
- статус `reproduced`, `flaky`, `not-reproduced` или `blocked`;
- отчёт `check_bug_report.py`.

## Доказательства

- expected и actual сформулированы проверяемо;
- `probe.json` показывает ≥3 прогонов и одинаковый результат;
- `minimal_case` уменьшен, `removed` заполнен;
- red test существует и падает;
- `failure_matches_symptom: true`;
- у каждой гипотезы есть evidence и следующий probe;
- `check_bug_report.py --strict` проходит.

## Границы

- Не исправляет код: фикс — отдельный шаг.
- Не мержит изменения и не деплоит.
- Не считает один прогон доказательством.
- Не считает флейк воспроизведением.
- Не выдаёт гипотезу за установленную причину.
- Не запускает недоверенные команды без явного решения и sandbox.
- Не публикует секреты из логов и окружения.

## Типовые ошибки

- начинать с причины, а не с symptom;
- запускать тест один раз и называть это воспроизведением;
- игнорировать смешанный результат;
- уменьшать вход без baseline;
- писать тест после фикса;
- принимать ошибку setup за дефект;
- оставлять `estimated` гипотезу без следующего probe;
- чинить до red-гейта.

## QA

- [ ] `repro.md` и `repro.json` заполнены;
- [ ] `probe.json` содержит ≥3 прогонов;
- [ ] результат детерминирован или статус `flaky`;
- [ ] `minimal_case` и `removed` заполнены;
- [ ] red test существует и падает;
- [ ] падение соответствует symptom;
- [ ] гипотезы имеют evidence и `next_probe`;
- [ ] `check_bug_report.py --strict` проходит;
- [ ] фикс не начат до red-гейта.

## Файлы

| Путь | Назначение |
|---|---|
| `references/bug-contract.md` | инварианты, поля, статусы, confidence |
| `templates/bug-report.md` | человекочитаемый отчёт |
| `templates/repro.json` | машиночитаемый отчёт |
| `scripts/probe_bug.py` | прогоны и классификация |
| `scripts/check_bug_report.py` | проверка отчёта |
| `examples/README.md` | пример заполнения |
| `docs/bugs/README.md` | правила каталога дефектов |