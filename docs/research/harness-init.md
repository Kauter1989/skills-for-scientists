# Research ledger: `harness-init`

| Поле | Значение |
|---|---|
| Навык | `harness-init` |
| Домен | `harness` |
| Приоритет | `P1` |
| Автор | OpenCode agent |
| Дата начала | `2026-10-31` |
| Дата снимка источников | `2026-10-31` |
| Статус | `ready-for-review` |

## 1. Задача

Разворачивать процесс в новом репозитории одной командой: профиль проекта,
`AGENTS.md`, структура `docs/`, хуки, CI и шаблоны research/review. Навык
нужен, чтобы старт не зависел от памяти и не терял половину проверок.

**Не входит в задачу:** устанавливать зависимости, выбирать стек, делать
первый коммит или push, перезаписывать существующие файлы без решения.

## 2. Поисковые запросы

- GitHub: `project template`, `copier`, `cookiecutter`, `spec-driven
  development`, `pre-commit`, `developer environment`.
- Научные базы: `newcomer onboarding`, `open source onboarding`,
  `cognitive load documentation`.
- Официальные спецификации: Agent Skills, pre-commit, Copier,
  GitHub Actions.

## 3. GitHub-аналоги

Данные API GitHub на `2026-10-31`.

| # | Репозиторий | Лицензия | Последний коммит | Звёзды | Что делает | Что берём | Что отвергаем |
|---|---|---|---|---|---|---|---|
| 1 | [`copier-org/copier`](https://github.com/copier-org/copier) | MIT | 2026-10-30 | 3 669 | Шаблоны проектов с обновлением и вопросами | параметризованный шаблон и `--dry-run` | жёсткую привязку к Jinja-шаблонам |
| 2 | [`cookiecutter/cookiecutter`](https://github.com/cookiecutter/cookiecutter) | BSD-3-Clause | 2026-04-01 | 25 175 | Создание проектов из шаблонов | структуру каталогов и вопросы | отсутствие обновления уже созданного проекта |
| 3 | [`github/spec-kit`](https://github.com/github/spec-kit) | MIT | 2026-10-30 | 144 209 | Стартовый набор для spec-driven development | конституцию, шаблоны и цепочку спецификаций | полную методологию целиком |
| 4 | [`pre-commit/pre-commit`](https://github.com/pre-commit/pre-commit) | MIT | 2026-10-20 | 15 673 | Хуки перед коммитом | ранние локальные проверки | единственный механизм контроля |
| 5 | [`cachix/devenv`](https://github.com/cachix/devenv) | Apache-2.0 | 2026-10-30 | 7 786 | Декларативные воспроизводимые окружения | фиксацию окружения и команд | зависимость от Nix как обязательную |

## 4. Научные источники и стандарты

| # | Источник | Тип | Метод / вклад | Ограничение | Как относится к навыку |
|---|---|---|---|---|---|
| 1 | Steinmacher et al., *Social Barriers Faced by Newcomers Placing Their First Contribution in Open Source Software Projects*, CSCW 2015, DOI [10.1145/2675133.2675215](https://doi.org/10.1145/2675133.2675215) | рецензируемая | Барьеры новичков: документация, поиск задачи, коммуникация | open source, не корпоративный репозиторий | старт должен давать явные точки входа и первые шаги |
| 2 | Fagerholm et al., *Onboarding in Open Source Projects*, IEEE Software 31(6), 2014, DOI [10.1109/MS.2014.107](https://doi.org/10.1109/ms.2014.107) | рецензируемая | Практики онбординга и наставничества | open source | шаблоны и чек-листы снижают стоимость входа |
| 3 | Sweller, *Cognitive Load During Problem Solving*, Cognitive Science 12(2):257–285, 1988, DOI [10.1207/s15516709cog1202_4](https://doi.org/10.1207/s15516709cog1202_4) | рецензируемая | Ограниченность рабочей памяти | теория обучения | стартовый набор должен быть минимальным, детали — в ссылках |
| 4 | Agent Skills, pre-commit, Copier, GitHub Actions docs | официальные | Форматы профиля, хуков, шаблонов и CI | не научный источник | нормативная база scaffold |

## 5. Синтез

- **Повторяющиеся паттерны:** шаблон с вопросами, декларативный профиль,
  ранние хуки, CI и документация «первый шаг».
- **Противоречия:** чем больше шаблон, тем полнее старт и тем выше
  когнитивная нагрузка. Решение: минимальный обязательный набор, остальное
  — опциональные блоки.
- **Пробелы:** аналоги создают проект, но не связывают профиль, правила,
  research/review и проверки в один воспроизводимый bootstrap.
- **Что подтверждено эмпирически:** барьеры новичков связаны с
  документацией и точками входа; онбординг требует явных практик;
  когнитивная нагрузка ограничивает объём стартовой инструкции.
- **Что является решением автора:** состав минимального профиля, формат
  `AGENTS.md`, набор хуков и CI, политика перезаписи.

## 6. Выводы для дизайна

| Решение | Основание | Альтернатива | Почему не она |
|---|---|---|---|
| Один профиль `profile.yml` как источник команд | Copier; spec-kit | разбросанные команды в docs | нельзя проверить и обновить |
| `AGENTS.md` из шаблона с проектными командами | Steinmacher; практика | общий текст без команд | новичок не знает, что запускать |
| Минимальный набор: profile, AGENTS, docs, hooks, CI | Sweller | всё сразу | высокая нагрузка и мёртвые файлы |
| `--dry-run` и запрет перезаписи по умолчанию | Copier | сразу писать | риск потерять существующее |
| `check_bootstrap.py` проверяет результат | Fagerholm | «выглядит правильно» | нет доказательства |
| Не устанавливать зависимости и не делать commit | практика | полный автомат | скрытые side effects |

## 7. Открытые вопросы для ревью

1. Формат профиля: `profile.yml` в корне или `.opencode/profile.yml`?
2. Делать ли CI под GitHub Actions по умолчанию?
3. Разрешать ли `--force` и какие файлы он может перезаписать?
4. Нужен ли отдельный шаблон для Python/JS или один язык-агностик?
5. Что считать минимальным bootstrap: 5 файлов или 8?

## 8. Что дальше

- [x] Research Gate: 5 GitHub-аналогов, 3 научных источника, 4 спецификации
- [ ] Собран `docs/reviews/harness-init.html`
- [ ] Ревью проведено, статус `approved`
- [ ] Создан каталог `harness/harness-init/`
- [ ] Bootstrap воспроизводится на пустом репозитории
- [ ] Обновлены `docs/skills-map.html` и `README.md`

## 9. Источники

1. `copier-org/copier` — https://github.com/copier-org/copier — доступно 2026-10-31.
2. `cookiecutter/cookiecutter` — https://github.com/cookiecutter/cookiecutter — доступно 2026-10-31.
3. `github/spec-kit` — https://github.com/github/spec-kit — доступно 2026-10-31.
4. `pre-commit/pre-commit` — https://github.com/pre-commit/pre-commit — доступно 2026-10-31.
5. `cachix/devenv` — https://github.com/cachix/devenv — доступно 2026-10-31.
6. Steinmacher et al., 2015 — https://doi.org/10.1145/2675133.2675215 — доступно 2026-10-31.
7. Fagerholm et al., 2014 — https://doi.org/10.1109/MS.2014.107 — доступно 2026-10-31.
8. Sweller, 1988 — https://doi.org/10.1207/s15516709cog1202_4 — доступно 2026-10-31.
9. Agent Skills specification — https://agentskills.io/specification — доступно 2026-10-31.
10. pre-commit docs — https://pre-commit.com/ — доступно 2026-10-31.
11. Copier docs — https://copier.readthedocs.io/ — доступно 2026-10-31.
12. GitHub Actions docs — https://docs.github.com/actions — доступно 2026-10-31.