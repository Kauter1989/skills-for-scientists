# Схема snapshot, analysis и HTML-контракт

## 1. Snapshot

Плагин пишет snapshot в `.pachca/snapshots/snapshot-*.json`. Минимальная
схема:

```json
{
  "schemaVersion": 1,
  "source": "rest",
  "collectedAt": "2026-11-02T12:00:00.000Z",
  "window": { "from": "2026-10-19T12:00:00.000Z", "to": "2026-11-02T12:00:00.000Z" },
  "account": {
    "id": "101",
    "name": "Анна Петрова",
    "role": "admin",
    "tokenType": "personal",
    "scopes": ["chats:read", "messages:read"],
    "plan": "unknown"
  },
  "users": [
    { "id": "101", "name": "Анна Петрова", "bot": false, "role": "admin" }
  ],
  "chats": [
    {
      "id": "1",
      "name": "Платформа",
      "channel": false,
      "personal": false,
      "public": false,
      "archived": false,
      "memberIds": ["101"],
      "messages": [
        {
          "id": "m1",
          "chatId": "1",
          "userId": "101",
          "content": "API v2 готов на 80%",
          "createdAt": "2026-11-02T09:00:00.000Z",
          "url": "https://app.pachca.com/chats/1?message=m1",
          "isThread": false
        }
      ],
      "coverage": { "fetched": 1, "ok": true, "truncated": false, "errors": [] }
    }
  ],
  "stats": {
    "chatsAvailable": 1,
    "chatsSelected": 1,
    "chatsRead": 1,
    "chatsFailed": 0,
    "messages": 1,
    "threads": 0
  }
}
```

Требования:

- `id` — строки, даже если API отдаёт числа;
- `createdAt` — ISO-8601 UTC;
- `account.scopes` — массив скоупов токена, иначе preflight задач не сможет
  подтвердить права;
- `coverage.ok: false` — чат не прочитан, его ошибки попадут в отчёт;
- `messages` уникальны по `id`, треды помечены `isThread`;
- `source` — `rest` или `mcp`.

## 2. Analysis

Модель заполняет `.pachca/analyses/analysis-*.json`:

```json
{
  "schemaVersion": 1,
  "generatedAt": "2026-11-02T12:10:00.000Z",
  "projects": [
    {
      "chatId": "1",
      "project": "Платформа",
      "status": "on_track",
      "progress": "API v2 готов на 80%; осталась интеграция с биллингом.",
      "blockers": [],
      "nextSteps": ["Закрыть интеграцию с биллингом"],
      "confidence": "high",
      "evidenceMessageIds": ["m1"]
    }
  ],
  "crossProject": { "summary": "Один проект заблокирован доступом к staging." },
  "notes": "Личные чаты не анализировались."
}
```

Поля:

| Поле | Допустимо | Смысл |
|---|---|---|
| `status` | `on_track`, `at_risk`, `blocked`, `unknown` | состояние проекта |
| `progress` | строка | что изменилось, с опорой на сообщения |
| `blockers` | массив | `{ text, severity, evidenceMessageIds }` |
| `blockers[].severity` | `low`, `medium`, `high` | серьёзность |
| `nextSteps` | массив строк | следующий шаг |
| `confidence` | `high`, `medium`, `low` | уверенность вывода |
| `evidenceMessageIds` | массив ID | цитаты прогресса |
| `crossProject.summary` | строка | сводка по всем проектам |

Правила:

1. `blockers: []` — блокеров не найдено. В HTML печатается «—».
2. Каждый блокер должен иметь хотя бы один ID из своего чата.
3. Если ID не найден, проект помечается неподтверждённым; блокер получает
   «без подтверждённой цитаты».
4. Если анализ не передан, все проекты получают `status: unknown`, а отчёт
   предупреждает об этом.
5. Нельзя придумывать проект, которого нет в snapshot: такой элемент
   пропускается с предупреждением.
6. Личные чаты по умолчанию не считаются проектами.
7. Прогресс — не пересказ всей переписки. Одно-два предложения: изменение,
   решение, риск.

## 3. Активность

Для каждого участника (не бота):

```
messages(u) = |{ m : m.userId = u, m.createdAt >= window.from, m.createdAt <= window.to }|
last(u) = max(m.createdAt) по всем выбранным чатам
daysSilent(u) = (snapshot.collectedAt - last(u)) / 86 400 000
inactive(u) = last(u) = null OR daysSilent(u) > inactivityDays
```

- `inactivityDays` по умолчанию 2, настраивается.
- Дни календарные, не рабочие; это продуктовое решение, а не научный закон.
- Если сообщений в окне нет, `daysSilent` не вычисляется и в отчёте стоит
  «нет сообщений в окне».
- Боты не попадают в диаграмму. Их сообщения остаются в общем счётчике.
- Участник, который не состоит в чате, но писал в открытом канале, попадает
  в активность этого чата.
- Исключение убирает участника из диаграммы, но не из данных проекта.

Фильтр по чату пересчитывает счётчик и молчание по этому чату.

## 4. Уровни качества

| Уровень | Что означает | Пример |
|---|---|---|
| `measured` | прямой счёт из API | число сообщений, число участников |
| `derived` | вычислено из измеренного | дни молчания |
| `estimated` | оценка по явной формуле | — |
| `expert` | суждение по цитатам | прогресс, блокер |
| `missing` | данных нет | нет analysis, нет цитаты |

В HTML прогресс и блокеры — `expert`; без цитаты — `missing`. Отчёт не
выдаёт суждение за измерение.

## 5. HTML-контракт

Обязательные элементы:

- `id="projects"` — карточки проектов;
- `id="activity"` — диаграмма и фильтры;
- `id="tasks"` — сохранённые задачи;
- `id="method"` — методика и ограничения;
- `id="report-data"` — JSON сводки;
- `data-by-chat` у строки участника — счётчики по чатам для фильтра;
- `.inactive` и `.long-silence` — визуальное выделение;
- панель «Исключены из диаграммы».

Запрещено:

- `<script src=...>`, `<link rel="stylesheet">`, `@import`, CDN;
- `fetch(`, `XMLHttpRequest`, WebSocket;
- внешние шрифты и картинки;
- неэкранированный пользовательский текст;
- `href="javascript:..."`.

Данные вставляются в атрибуты и JSON с экранированием `<`, `>`, `&`,
кавычек и `</script>`. Ссылки на сообщения разрешены только на
`https://app.pachca.com/...`.

## 6. Ограничения отчёта

- сообщения — прокси активности, не productivity score;
- число сообщений коррелирует с работой команды, но не доказывает причинность;
- высокий объём может означать и прогресс, и борьбу с проблемой;
- смысловой анализ зависит от модели и проверяется только цитатами;
- закрытые чаты вне членства не читаются;
- API не отдаёт тариф и различие Владелец/Администратор;
- отчёт не заменяет экспорт, аудит и штатную аналитику Пачки.

## 7. Источники

- Wang et al. (2022), DOI `10.1145/3512941`.
- Kuutila et al. (2020), DOI `10.1145/3387940.3392224`.
- “Just slack it” (2020), DOI `10.1177/1461444820975723`.
- “Archetypes of delay” (2020), DOI `10.1016/j.infsof.2020.106435`.
- Dashboard Design Patterns (2022), DOI `10.1109/TVCG.2022.3209448`.
- MCP Authorization 2025-11-25.