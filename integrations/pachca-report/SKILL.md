---
name: pachca-report
description: >-
  Собирает статистику всех чатов Пачки (Pachca) через MCP или REST в один
  интерактивный автономный HTML-отчёт: прогресс и блокеры по проектам,
  активность участников с выделением молчащих более двух дней, исключения
  участников в отдельном Markdown и сохранённые задачи по каналам с проверкой
  прав API до сохранения. Use when asked for a Pachca chat digest, project
  progress and blockers from Pachca messages, participant activity report,
  removal of people from the activity chart, or a saved channel-specific task
  in Pachca. Триггеры: отчёт по Пачке, Pachca report, статистика чатов Пачки,
  прогресс по проектам, блокеры из чатов, активность участников, кто не пишет,
  исключить участника из диаграммы, задача по каналу Пачки, Pachca MCP.
---

# pachca-report — статистика чатов Пачки в HTML

Домен — интеграции с внешними средами и API: навык лежит в `integrations/` и
имя каталога `pachca-report` сохраняется как историческое.

Навык превращает новый слой сообщений из всех чатов Пачки, где состоит
пользователь, в один файл `report.html`. Файл открывается с диска, не делает
внешних запросов, печатается в A4 и прикладывается к ревью, ретро или отчёту.

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
   по сети. Текст сообщений экранируется.
8. **Секреты не попадают в артефакты.** Токен живёт в `PACHCA_TOKEN` или в
   OAuth-хранилище OpenCode. В HTML, Markdown и snapshot его нет.

## Входы

| Вход | Обязательность | Значение |
|---|---|---|
| `PACHCA_TOKEN` | для REST-сбора | персональный токен или токен бота; не коммитится |
| MCP-подключение `pachca` | альтернатива токену | OAuth через `/mcps` |
| окно | нет | по умолчанию 14 дней от последнего сбора |
| `analysis.json` | для прогресса | проекты, статусы, блокеры, evidence ID |
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
├── reports/pachca-report-YYYY-MM-DD.html
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
OpenCode; токен не пишется в конфиг.

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

Прочитайте новые сообщения по каждому проекту и запишите `analysis.json`:

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
      "blockers": [],
      "nextSteps": ["Закрыть интеграцию с биллингом"],
      "confidence": "high",
      "evidenceMessageIds": ["m1", "m2"]
    }
  ],
  "crossProject": { "summary": "Один проект заблокирован доступом к staging." }
}
```

Правила:

- `status`: `on_track`, `at_risk`, `blocked`, `unknown`;
- `blockers: []` — новый блокер не найден, в HTML будет «—»;
- каждый блокер и прогресс подкрепляйте `evidenceMessageIds`;
- если цитат нет, ставьте `confidence: low` и не выдавайте вывод за факт;
- не анализируйте личные чаты как проекты;
- не пересказывайте всю переписку: только изменения, решения, риски, следующий шаг.

### 6. Собрать HTML

```text
pachca.report {
  "analysisPath": ".pachca/analyses/analysis-2026-11-02.json",
  "inactivityDays": 2,
  "title": "Pachca · рабочие чаты, 2 недели"
}
```

Инструмент проверит, что каждый evidence ID существует в snapshot, посчитает
активность и запишет `.pachca/reports/pachca-report-YYYY-MM-DD.html`.

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
- Активность в чате коррелирует с работой, но не измеряет продуктивность
  человека. См. `references/report-schema.md`.

## Типовые ошибки

| Симптом | Причина | Что делать |
|---|---|---|
| `PACHCA_TOKEN не задан` | нет env | экспортировать токен или собирать через MCP |
| `401 invalid_token` | токен отозван/просрочен | новый токен или OAuth |
| `403 insufficient_scope` | нет скоупа | добавить скоуп в токен |
| `403 role_forbidden` | роль не позволяет | сменить токен/роль, не обходить |
| `snapshot_missing` | не было сбора | `pachca.collect` |
| `chat_role_unverified` | роль в чате не подтверждена | дать плагину токен или `capabilities.chatRoles` |
| `channel_role_forbidden` | подписчик канала | не сохранять задачу на отправку |
| `plan_unverified` | тариф не подтверждён | подтвердить «Корпорация» |
| пустой отчёт | окно без сообщений | увеличить `days`, проверить `lastCollectedAt` |
| все проекты `unknown` | нет analysis | заполнить `analysis.json` |

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
| `references/report-schema.md` | snapshot/analysis, формулы, качество, HTML-контракт |
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
- OpenCode plugins: <https://opencode.ai/v2/docs/build/plugins>
- OpenCode MCP: <https://opencode.ai/v2/docs/mcp-servers>
- MCP authorization: <https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization>