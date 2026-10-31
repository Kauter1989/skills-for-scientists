# Research ledger: `harness-skill-eval`

| Поле | Значение |
|---|---|
| Навык | `harness-skill-eval` |
| Домен | `harness` |
| Приоритет | `P2 · possible` |
| Автор | OpenCode agent |
| Дата начала | `2026-10-31` |
| Дата снимка источников | `2026-10-31` |
| Статус | `deferred` |

> **Решение:** навык отнесён к категории «возможные» и не реализуется в
> текущем цикле. Для текущих практических сценариев большого значения не
> имеет. Research и review сохранены как основа будущей оценки.

## 1. Задача

Проверять навык на реальных задачах: срабатывает ли триггер, воспроизводим
ли результат, улучшает ли навык исходную модель и сколько это стоит.
Навык нужен, чтобы «работает» не означало «один раз получилось».

**Не входит в задачу:** аудит структуры библиотеки (это
`harness-skill-audit`), разработка навыка (это `harness-skill-template`) и
создание механизмов (это `harness-rule-to-mechanism`).

## 2. Поисковые запросы

- GitHub: `prompt evaluation`, `LLM evaluation harness`, `eval framework`,
  `reproducible evaluation`.
- Научные базы: `prompt sensitivity`, `reproducible evaluation`,
  `holistic evaluation`, `benchmark validity`.
- Официальные спецификации: promptfoo, Inspect AI, lm-evaluation-harness,
  HELM.

## 3. GitHub-аналоги

Данные API GitHub на `2026-10-31`.

| # | Репозиторий | Лицензия | Последний коммит | Звёзды | Что делает | Что берём | Что отвергаем |
|---|---|---|---|---|---|---|---|
| 1 | [`promptfoo/promptfoo`](https://github.com/promptfoo/promptfoo) | MIT | 2026-10-31 | 26 669 | Декларативные проверки промптов, агентов и RAG | assertions, сравнение вариантов, CI | оценку модели вместо оценки навыка |
| 2 | [`UKGovernmentBEIS/inspect_ai`](https://github.com/UKGovernmentBEIS/inspect_ai) | MIT | 2026-10-31 | 3 147 | Фреймворк LLM-оценки: задачи, датасеты, метрики | task → solver → scorer → log | тяжёлую инфраструктуру для одного навыка |
| 3 | [`EleutherAI/lm-evaluation-harness`](https://github.com/EleutherAI/lm-evaluation-harness) | MIT | 2026-09-14 | 14 350 | Few-shot оценка языковых моделей | воспроизводимый запуск и логирование | публичные бенчмарки вместо задач навыка |
| 4 | [`stanford-crfm/helm`](https://github.com/stanford-crfm/helm) | Apache-2.0 | 2026-09-01 | 2 961 | Holistic evaluation: сценарии, метрики, прозрачность | матрицу сценариев и метрик | масштаб и стоимость полной HELM |
| 5 | [`openai/evals`](https://github.com/openai/evals) | NOASSERTION | 2026-04-14 | 19 683 | Фреймворк и реестр бенчмарков | формат реестра и отчёта | зависимость от чужого реестра |

## 4. Научные источники и стандарты

| # | Источник | Тип | Метод / вклад | Ограничение | Как относится к навыку |
|---|---|---|---|---|---|
| 1 | Liang et al., *Holistic Evaluation of Language Models*, arXiv:2211.09110, 2022 | препринт | Таксономия сценариев и метрик, прозрачная оценка | очень широкая и дорогая | оценка должна задавать сценарии и метрики заранее |
| 2 | Sclar et al., *Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design*, arXiv:2310.11324, 2023 | препринт | Форматирование промпта сильно меняет результат | исследование промптов, не навыков | один запуск не доказывает качество; нужны повторы и варианты |
| 3 | Biderman et al., *Lessons from the Trenches on Reproducible Evaluation of Language Models*, arXiv:2405.14782, 2024 | препринт | Воспроизводимость: окружение, версии, логи, сравнение | общая методология оценки | фиксировать модель, версии, температуру и артефакты |
| 4 | promptfoo, Inspect AI, lm-evaluation-harness, HELM docs | официальные | Нормативные форматы задач, метрик и отчётов | не научный источник | практическая база для протокола |

## 5. Синтез

- **Повторяющиеся паттерны:** сначала набор задач и метрики, потом запуск;
  baseline обязателен; результаты логируются; сравнение идёт по одному
  протоколу.
- **Противоречия:** публичные бенчмарки дешёвы, но не проверяют навык;
  собственные задачи релевантны, но их мало и они смещены к автору.
- **Пробелы:** аналоги оценивают модели и промпты, но не связывают
  срабатывание навыка, качество результата и стоимость в одном отчёте.
- **Что подтверждено эмпирически:** формат промпта влияет на результат;
  воспроизводимость требует фиксации окружения и логов; holistic-подход
  требует явных сценариев и метрик.
- **Что является решением автора:** минимальный размер выборки, число
  повторов, порог принятия и формат отчёта.

## 6. Выводы для дизайна

| Решение | Основание | Альтернатива | Почему не она |
|---|---|---|---|
| Сравнивать baseline и skill на одном наборе задач | HELM; inspect_ai | только запуск со skill | нет доказательства прироста |
| Минимум 5 positive / 5 negative / 3 edge, 2 повтора | Sclar; практика | один запуск | высокая дисперсия |
| Фиксировать модель, версию, температуру и хэш промпта | Biderman | «примерно та же модель» | результат не воспроизводится |
| Метрики: trigger precision/recall, pass rate, variance, cost | HELM; promptfoo | только pass rate | не видно цены и ложных срабатываний |
| Отчёт `docs/evals/<skill>/<date>.html` + JSON | inspect_ai; HELM | свободный текст | нет тренда и сравнения |
| Решение keep/revise/retire принимает пользователь | практика | автоматический вывод | малая выборка не даёт права на вердикт |

## 7. Открытые вопросы для ревью

1. Где хранить отчёты: `docs/evals/<skill>/<date>.html`?
2. Сколько повторов считать достаточным: 2 или 3?
3. Нужен ли baseline без навыка всегда или только для нового навыка?
4. Кто утверждает keep/revise/retire?
5. Допустимо ли оценивать на одной модели или нужна матрица моделей?

## 8. Что дальше

- [x] Research Gate: 5 GitHub-аналогов, 3 научных источника, 4 спецификации
- [x] Собран `docs/reviews/harness-skill-eval.html`
- [x] Ревью: `deferred`, реализация не начинается
- [ ] Создан каталог `harness/harness-skill-eval/` — не планируется в текущем цикле
- [ ] Протокол и пример отчёта воспроизводятся — не планируется в текущем цикле
- [ ] Обновлены `docs/skills-map.html` и `README.md` — навык остаётся proposed

## 9. Источники

1. `promptfoo/promptfoo` — https://github.com/promptfoo/promptfoo — доступно 2026-10-31.
2. `UKGovernmentBEIS/inspect_ai` — https://github.com/UKGovernmentBEIS/inspect_ai — доступно 2026-10-31.
3. `EleutherAI/lm-evaluation-harness` — https://github.com/EleutherAI/lm-evaluation-harness — доступно 2026-10-31.
4. `stanford-crfm/helm` — https://github.com/stanford-crfm/helm — доступно 2026-10-31.
5. `openai/evals` — https://github.com/openai/evals — доступно 2026-10-31.
6. Liang et al., HELM — https://arxiv.org/abs/2211.09110 — доступно 2026-10-31.
7. Sclar et al., prompt sensitivity — https://arxiv.org/abs/2310.11324 — доступно 2026-10-31.
8. Biderman et al., reproducible evaluation — https://arxiv.org/abs/2405.14782 — доступно 2026-10-31.
9. promptfoo docs — https://www.promptfoo.dev/docs/ — доступно 2026-10-31.
10. Inspect AI docs — https://inspect.aisi.org.uk/ — доступно 2026-10-31.
11. lm-evaluation-harness docs — https://github.com/EleutherAI/lm-evaluation-harness — доступно 2026-10-31.
12. HELM docs — https://crfm.stanford.edu/helm/ — доступно 2026-10-31.