---
name: pachca-report
description: >-
  Собирает статистику всех чатов Пачки (Pachca) через MCP или REST в один
  интерактивный автономный HTML-отчёт: структурированная сводка, прогресс и
  блокеры по проектам, активность участников с выделением молчащих более двух
  дней, исключения участников в отдельном Markdown, сохранённые задачи по
  каналам с проверкой прав API до сохранения, редактируемые черновики
  сообщений с кнопкой отправки через outbox-очередь. Use when asked for a
  Pachca chat digest, project progress and blockers from Pachca messages,
  participant activity report, removal of people from the activity chart,
  a saved channel-specific task in Pachca, draft messages with a send button,
  or an outbox queue for Pachca sends. Триггеры: отчёт по Пачке, Pachca report,
  статистика чатов Пачки, прогресс по проектам, блокеры из чатов, активность
  участников, кто не пишет, исключить участника из диаграммы, задача по каналу
  Пачки, черновик сообщения, кнопка отправить, outbox, личные сообщения,
  Pachca MCP.
---

# pachca-report — статистика чатов Пачки в HTML

Домен — интеграции с внешними средами и API: навык лежит в `integrations/` и
имя каталога `pachca-report` сохраняется как историческое.

Навык превращает новый слой сообщений из всех чатов Пачки, где состоит
пользователь, в один файл `report.html` (форма v2). Файл открывается с диска,
не делает внешних запросов, печатается в A4 и прикладывается к ревью, ретро
или отчёту. Форма v2: структурированная сводка, панель личных сообщений
первой после сводки, редактируемые черновики с каналом и кнопкой «Отправить»
у каждого блокера и личного действия; отправка — только через outbox-очередь
с отдельным подтверждением пользователя.

Два компонента:

| Компонент | Путь | Роль |
|---|---|---|
| Навык | `integrations/pachca-report/` | процедура, нормативы, проверки, пример |
| Плагин | `opencode-plugins/pachca/` | MCP-подключение, сбор, расчёт, HTML, MD-состояние, preflight задач |

Плагин регистрирует MCP-сервер Пачки `https://mcp.pachca.com/mcp` и локальные
инструменты `pachca.status`, `pachca.collect`, `pachca.report`,
`pachca.exclusions`, `pachca.projects`, `pachca.tasks`. В Code Mode они
доступны в namespace `pachca`.

## Когда применять

- нужен срез всех рабочих чатов за последние дни: что сдвинулось, где
  блокеры, кто перестал писать;
- нужно убрать конкретных людей из диаграммы активности и сохранить это
  решение между запусками;
- нужно добавить повторяемую задачу по каналу: мониторинг ключевых слов,
  дайджест, активность, разбор треда;
- нужно проверить, что текущий токен и роль в Пачке вообще позволяют
  выполнять задачу, до её сохранения.

Не применять:

- для оценки сотрудников, рейтингов и KPI отдельного человека;
- для чтения чатов, недоступных токену, или обхода скоупов;
- для отправки сообщений без явной задачи и подтверждения;
- для экспорта всей переписки: это отдельный метод с тарифом «Корпорация» и
  ролью Владельца;
- для замены штатной аналитики Пачки.

## Инварианты

1. **Измерение отдельно от интерпретации.** Плагин считает сообщения и
   молчание. Модель пишет прогресс и блокеры. Числа не придумываются в
   тексте.
2. **Каждый вывод — с цитатой.** Блокер или прогресс без ID сообщения
   получает `confidence: low` и пометку «без подтверждённой цитаты». Если
   данных нет, статус `unknown`, а не выдуманный «в графике».
3. **Прочерк — это ответ.** Пустой список блокеров печатается как «—» и
   означает «новых блокеров в окне не найдено».
4. **Активность — не продуктивность.** Отчёт не ранжирует людей и не
   называет молчание «плохим». Формулировки — про сообщения и дни.
5. **Исключения — только диаграмма.** Участник из `exclusions.md` исчезает
   из диаграммы, но остаётся в данных проектов и в панели исключений.
6. **Задача сохраняется только после preflight.** Проверяются скоупы, роль
   в пространстве, роль в чате, тариф и доступ к каналу. Неподтверждённая
   задача не пишется в `tasks.md`.
7. **HTML автономен.** Ни CDN, ни внешних шрифтов, ни `fetch`, ни картинок
   по сети. Текст сообщений экранируется. Кнопки отправки не делают запросов:
   только запись в outbox (см. инвариант 9).
8. **Секреты не попадают в артефакты.** Токен живёт в `PACHCA_TOKEN` (алиас
   `PACHKA_TOKEN`) или в OAuth-хранилище OpenCode. В HTML, Markdown, snapshot
   и файлах outbox его нет.
9. **Отчёт не отправляет сообщения.** Кнопка «Отправить» активна только при
   скоупе `messages:create` и лишь ставит черновик в `.pachca/outbox/` со
   статусом `pending_confirmation`. Отправку выполняет плагин/агент через
   `pachca_send_message` после отдельного подтверждения пользователя по
   каждому сообщению и preflight прав. Канал назначения указан у каждого
   черновика.

## Входы

| Вход | Обязательность | Значение |
|---|---|---|
| `PACHCA_TOKEN` (алиас `PACHKA_TOKEN`) | для REST-сбора | персональный токен или токен бота; не коммитится |
| MCP-подключение `pachca` | альтернатива токену | OAuth через `/mcps` |
| окно | нет | по умолчанию 14 дней от последнего сбора; настраивается (`days`), в сессиях пользователя применялось 7 дней |
| `analysis.json` | для прогресса | проекты, статусы, блокеры, evidence ID; форма v2: `progressPoints`, `blockers[].draft`, структурированный `crossProject` |
| `actions-*.json` | нет | панель личных сообщений владельца (дата соответствует analysis) |
| `.pachca/projects.md` | нет | сопоставление чата и проекта |
| `.pachca/exclusions.md` | нет | исключения из диаграммы |
| `.pachca/tasks.md` | нет | сохранённые задачи |

## Артефакты

```
.pachca/
├── state.json
├── exclusions.md
├── projects.md
├── tasks.md
├── snapshots/snapshot-*.json
├── analyses/analysis-*.json
├── analyses/actions-*.json
├── reports/pachca-report-YYYY-MM-DD.html
├── outbox/pachca-outbox-*.json      ← очередь черновиков (pending_confirmation)
├── outbox/sent/                     ← отправленные после подтверждения
└── task-results/*.md
```

## Быстрый старт

### 1. Установить навык и плагин

```powershell
# навык
Copy-Item -Recurse .\integrations\pachca-report "$env:USERPROFILE\.config\opencode\skill\pachca-report"

# плагин: путь к каталогу, а не к файлу
# ~/.config/opencode/opencode.json
# "plugins": ["C:/path/to/opencode-skills/skills/opencode-plugins/pachca"]
```

Плагин сам добавит MCP-сервер `pachca`, если его ещё нет. Для OAuth откройте
`/mcps` и войдите в Пачку. Для токена задайте `PACHCA_TOKEN` в окружении
OpenCode (допустим алиас `PACHKA_TOKEN`); токен не пишется в конфиг.

### 2. Проверить связь

```text
pachca.status { "deep": true }
```

Ожидаемо: `mcp.configured: true`, `tokenConfigured: true` или подключённый
OAuth, список скоупов и `stateDir`.

Если MCP не подключён: откройте `/mcps`, выберите `pachca`, войдите. Если
токена нет и OAuth недоступен, используйте MCP-сбор по шагам ниже.

### 3. Собрать новый слой

```text
pachca.collect { "days": 14 }
```

Инструмент читает все чаты пользователя, сообщения с курсорной пагинацией,
треды, участников и пользователей, пишет snapshot и обновляет
`state.lastCollectedAt`.

Без `PACHCA_TOKEN`:

1. `pachca_get_token_info` — скоупы и `user_id`;
2. `pachca_get_my_card` — имя и роль;
3. `pachca_list_chats` с `availability=is_member`, `archived=true` — все чаты;
4. `pachca_list_chat_messages` по каждому чату, `limit=50`, курсор — до
   начала окна;
5. `pachca_list_users` — имена участников;
6. соберите объект по схеме `references/report-schema.md` и передайте его в
   `pachca.report` как `snapshot`.

### 4. Сопоставить проекты

```text
pachca.projects { "action": "set", "chatId": "1", "project": "Платформа", "aliases": ["core"] }
```

Если проект не задан, отчёт берёт название чата и помечает проект `unknown`.

### 5. Заполнить анализ

Прочитайте новые сообщения по каждому проекту и запишите `analysis.json`
(форма v2 — с буллитами прогресса, черновиками и структурированной сводкой):

```json
{
  "schemaVersion": 1,
  "generatedAt": "2026-11-02T12:10:00.000Z",
  "projects": [
    {
      "chatId": "1",
      "project": "Платформа",
      "status": "on_track",
      "progress": "API v2 готов на 80%, осталась интеграция с биллингом.",
      "progressPoints": ["API v2 готов на 80%.", "Осталась интеграция с биллингом."],
      "blockers": [
        {
          "text": "Нет доступа к staging.",
          "severity": "high",
          "evidenceMessageIds": ["m2"],
          "draft": "Коллеги, для интеграции с биллингом нужен доступ к staging. Кто выдаст до [дата]?"
        }
      ],
      "nextSteps": ["Закрыть интеграцию с биллингом"],
      "confidence": "high",
      "evidenceMessageIds": ["m1", "m2"]
    }
  ],
  "crossProject": {
    "summary": "Один проект заблокирован доступом к staging.",
    "highlights": [{ "project": "Платформа", "text": "API v2 готов на 80%." }],
    "risks": [{ "project": "Платформа", "severity": "high", "text": "Нет доступа к staging." }],
    "deadlines": [{ "date": "2026-11-04", "when": "завтра", "time": "12:00", "what": "Интеграция с биллингом", "project": "Платформа" }],
    "external": [{ "project": "Платформа", "text": "Доступ к staging — администратор" }]
  }
}
```

Правила:

- `status`: `on_track`, `at_risk`, `blocked`, `unknown`;
- `blockers: []` — новый блокер не найден, в HTML будет «—»;
- каждый блокер и прогресс подкрепляйте `evidenceMessageIds`;
- если цитат нет, ставьте `confidence: low` и не выдавайте вывод за факт;
- блокер предыдущего среза без цитаты в текущем окне переносится с пометкой
  «предыдущий срез» и «без подтверждённой цитаты», `confidence: low`;
- `progressPoints` — 2–4 буллита; `draft` — черновик сообщения по блокеру
  (канал — чат проекта), редактируемый, без секретов и оценок людей;
- сводка структурирована: сроки → риски → главное → зависимости, тезисами;
- не анализируйте личные чаты как проекты;
- не пересказывайте всю переписку: только изменения, решения, риски, следующий шаг.

Панель личных сообщений: соберите обращения к владельцу аккаунта (упоминания,
`@all`, личные чаты, собственные открытые запросы) в `actions-YYYY-MM-DD.json`
по схеме `references/report-schema.md` §2a; открытые запросы прошлого среза
переносите с пометкой «предыдущий срез». У каждого item — `draft` и `chatId`
канала назначения.

### 6. Собрать HTML

```text
pachca.report {
  "analysisPath": ".pachca/analyses/analysis-2026-11-02.json",
  "actionsPath": ".pachca/analyses/actions-2026-11-02.json",
  "inactivityDays": 2,
  "title": "Pachca · рабочие чаты, 2 недели"
}
```

Инструмент проверит, что каждый evidence ID существует в snapshot, посчитает
активность и запишет `.pachca/reports/pachca-report-YYYY-MM-DD.html` формы v2:
структурированная сводка, личные сообщения первой секцией после сводки,
карточки проектов с буллитами и спойлерами-черновиками под блокерами, у каждого
черновика канал и кнопка «Отправить» (активна только при `messages:create`).
Заголовок и подзаголовок отражают фактическую длительность окна.

### 7. Убрать участника из диаграммы

```text
pachca.exclusions { "action": "add", "name": "Глеб Орлов", "reason": "отпуск до 10 ноября" }
```

Участник исчезнет из диаграммы, но останется в панели исключений и в данных
проектов. Вернуть:

```text
pachca.exclusions { "action": "remove", "name": "Глеб Орлов" }
```

Файл `.pachca/exclusions.md` можно править вручную. После изменения
исключений пересоберите HTML тем же `pachca.report`, чтобы диаграмма
обновилась.

### 8. Добавить задачу по каналу

```text
pachca.tasks {
  "action": "add",
  "channel": "Мобильное приложение",
  "title": "Мониторинг блокеров",
  "kind": "monitor",
  "actions": ["read_messages"],
  "keywords": ["блокер", "ключ", "staging"]
}
```

Перед сохранением плагин проверяет:

- существует ли канал и видит ли его токен;
- есть ли скоупы `chats:read`, `messages:read` (и другие по действиям);
- не архивный ли чат для записи;
- роль в канале для отправки: подписчик писать не может;
- тариф и владельца для экспорта;
- не изменились ли права с прошлого запуска.

При провале задача **не сохраняется**, инструмент возвращает точную причину.
Для чтения обычно достаточно `chats:read`, `messages:read`, `users:read`.
Для отправки — `messages:create` и роль owner/admin/editor в канале.

Если `PACHCA_TOKEN` нет и плагин не может сам вызвать `/oauth/token/info`,
передайте `capabilities` из MCP: `scopes` из `pachca_get_token_info`,
`role` и `accountId` из `pachca_get_my_card`, `chatRoles` из
`pachca_list_members?role=...`. `plan` и `isOwner` API не отдаёт: их
подтверждает пользователь. Без этих данных задача помечается
`unverified` и не сохраняется.

Запуск:

```text
pachca.tasks { "action": "check" }
pachca.tasks { "action": "run", "id": "T-20261102-a1b2c" }
```

- `activity` и `monitor` плагин выполняет детерминированно и пишет результат
  в `.pachca/task-results/`;
- `digest`, `report`, `custom` возвращают контекст и промпт; модель выполняет
  задачу и сохраняет итог через `action: "complete"`;
- `send_message` сам не отправляется: нужно подтверждение пользователя и
  отдельный вызов MCP `pachca_send_message`.

### 9. Обработать outbox-очередь

Кнопки «Отправить» в отчёте ставят черновики в `.pachca/outbox/`
(`pending_confirmation`). Обработка — по `references/outbox.md`:

1. прочитать очередь, показать пользователю канал, текст и источник каждого
   сообщения;
2. получить отдельное явное подтверждение по каждому сообщению;
3. preflight: `messages:create`, роль в чате owner/admin/editor, чат не
   архивный; при провале — `rejected` с причиной, не отправлять;
4. отправить через MCP `pachca_send_message`;
5. перенести файл в `outbox/sent/` (или `status: sent` + `messageId`).

Без подтверждения пользователя не отправлять ничего. При read-only токене
кнопки в отчёте неактивны, очередь пуста — это ожидаемое состояние.

## Границы и честность

- API не отдаёт роль участника в чате в общем списке. Для записи плагин
  делает отдельные запросы по `role=owner|admin|editor|member`; если роль не
  подтверждена, задача блокируется.
- API не отличает Владельца пространства от Администратора. Экспорт
  блокируется, пока пользователь явно не подтвердит `isOwner: true`.
- Тариф пространства не приходит в `/oauth/token/info`; для экспорта его нужно
  подтвердить в `capabilities.plan`.
- Сообщение в закрытом чате не читается, если токен не участник. Отчёт
  показывает coverage и ошибки, а не делает вид, что данные полные.
- Смысловой анализ — суждение модели. Оно проверяемо только по цитатам.
  Черновики сообщений — тоже суждение: они редактируются и отправляются
  только с подтверждением пользователя.
- Запись outbox из браузера требует File System Access API (Chromium);
  при недоступности отчёт скачивает JSON с инструкцией положить его в
  `.pachca/outbox/`. Это ограничение показывается в отчёте, а не скрывается.
- Активность в чате коррелирует с работой, но не измеряет продуктивность
  человека. См. `references/report-schema.md`.

## Типовые ошибки

| Симптом | Причина | Что делать |
|---|---|---|
| `PACHCA_TOKEN не задан` | нет env | экспортировать токен (или алиас `PACHKA_TOKEN`) или собирать через MCP |
| `401 invalid_token` | токен отозван/просрочен | новый токен или OAuth |
| `403 insufficient_scope` | нет скоупа | добавить скоуп в токен |
| `403 role_forbidden` | роль не позволяет | сменить токен/роль, не обходить |
| `snapshot_missing` | не было сбора | `pachca.collect` |
| `chat_role_unverified` | роль в чате не подтверждена | дать плагину токен или `capabilities.chatRoles` |
| `channel_role_forbidden` | подписчик канала | не сохранять задачу на отправку |
| `plan_unverified` | тариф не подтверждён | подтвердить «Корпорация» |
| пустой отчёт | окно без сообщений | увеличить `days`, проверить `lastCollectedAt` |
| все проекты `unknown` | нет analysis | заполнить `analysis.json` |
| кнопка «Отправить» неактивна | нет `messages:create` | расширить скоуп токена; это ожидаемо для read-only |
| браузер не пишет в outbox | нет File System Access API / отказ | скачать JSON и положить в `.pachca/outbox/` вручную |
| сообщение `rejected` в очереди | роль/скоуп/архив не прошли preflight | исправить права или канал, не обходить |
| черновики без канала | analysis без `chatId`/draft | заполнить `blockers[].draft` и `chatId` |

## QA-чек-лист

- [ ] `pachca.status deep` показывает живой токен или подключённый OAuth.
- [ ] `pachca.collect` вернул `chatsFailed: 0` или список ошибок.
- [ ] В `analysis.json` у каждого проекта есть evidence ID.
- [ ] У проектов без блокеров в HTML стоит «—».
- [ ] В диаграмме нет исключённых, в панели исключений они есть.
- [ ] Молчащие > 2 дней подсвечены, порог совпадает с запросом.
- [ ] В HTML нет внешних `script`, `link`, `@import`, `fetch`.
- [ ] Текст сообщений экранирован, `javascript:` ссылок нет.
- [ ] Задача без прав не сохранилась и объяснила причину.
- [ ] `tasks check` перед запуском проходит.
- [ ] Форма v2: сводка структурирована (сроки → риски → главное → зависимости), личные сообщения — первая секция после сводки.
- [ ] У каждого черновика указан канал; кнопки неактивны без `messages:create` и активны с ним.
- [ ] Outbox-файлы имеют `pending_confirmation`, без секретов; ничего не отправлено без подтверждения.
- [ ] `python scripts/check_report.py` и `validate_analysis.py` зелёные.

## Проверка примера

```bash
cd opencode-plugins/pachca
node test/run-tests.mjs
node test/api.test.mjs
node --experimental-loader ./test/loader.mjs test/plugin.test.mjs
node test/build-example.mjs

cd ../../integrations/pachca-report
python scripts/check_report.py examples/example-report.html
python scripts/validate_analysis.py examples/example-snapshot.json examples/example-analysis.json
```

## Файлы

| Файл | Содержание |
|---|---|
| `references/pachca-api.md` | методы, скоупы, роли, лимиты, MCP-инструменты |
| `references/report-schema.md` | snapshot/analysis/actions, формулы, качество, HTML-контракт v2 |
| `references/outbox.md` | очередь черновиков, схема файла, запись из браузера, обработка и preflight |
| `references/tasks.md` | действия, preflight, запуск, ограничения |
| `references/security.md` | токены, OAuth, prompt injection, XSS |
| `scripts/check_report.py` | проверка автономности HTML |
| `scripts/validate_analysis.py` | проверка evidence ID |
| `templates/exclusions.md` | форма исключений |
| `templates/projects.md` | форма сопоставления |
| `templates/tasks.md` | форма задач |
| `examples/example-report.html` | эталонный отчёт |
| `examples/example-snapshot.json` | эталонный snapshot |
| `examples/example-analysis.json` | эталонный analysis |

## Ссылки

- Pachca MCP: <https://dev.pachca.com/guides/mcp/overview>
- Pachca API: <https://dev.pachca.com/api/authorization>
- Права и роли: <https://dev.pachca.com/guides/permissions>
- File System API (MDN): <https://developer.mozilla.org/en-US/docs/Web/API/File_System_API>
- File System Access (WICG): <https://wicg.github.io/file-system-access/>
- OpenCode plugins: <https://opencode.ai/v2/docs/build/plugins>
- OpenCode MCP: <https://opencode.ai/v2/docs/mcp-servers>
- MCP authorization: <https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization>