# opencode-plugins

Плагины OpenCode, вынесенные из локального профиля, и инструкции по их
установке на другой машине. Сейчас здесь два плагина: Markdown-панель и
Pachca.

## Состав

| Путь | Компонент | Назначение |
|---|---|---|
| `md-viewer/` | `opencode-md-panel` | панель Markdown: список `.md` файлов сессии, просмотр, редактирование, сохранение |
| `pachca/` | `opencode-pachca` | MCP-подключение Пачки, сбор чатов, интерактивный HTML-отчёт, MD-исключения и задачи с preflight прав |
| `config/` | пример конфигурации | `opencode.json` без секретов |
| `INSTALL.md` | инструкция | сборка, установка, проверка, troubleshooting |
| `NOTICE.md` | происхождение | источники и статус лицензий |

## Быстрый старт

```bash
git clone https://github.com/Kauter1989/opencode-skills.git
cd opencode-skills/skills/opencode-plugins/md-viewer

bun install
bun run build
```

Затем добавьте плагин в `~/.config/opencode/opencode.json`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": [
    "C:/Users/<user>/.config/opencode/plugins/opencode-md-panel"
  ]
}
```

Полная последовательность с копированием и проверкой —
[`INSTALL.md`](INSTALL.md).

### Pachca

```bash
cd pachca
node test/run-tests.mjs
node test/api.test.mjs
node --experimental-loader ./test/loader.mjs test/plugin.test.mjs
node test/build-example.mjs
```

Подключение — путь к каталогу `pachca/` в `plugins` и либо `PACHCA_TOKEN`,
либо OAuth через `/mcps`. Инструкция: [`pachca/INSTALL.md`](pachca/INSTALL.md).
Навык интеграции: [`../integrations/pachca-report/SKILL.md`](../integrations/pachca-report/SKILL.md).

## Что делает Pachca

- регистрирует официальный MCP-сервер `https://mcp.pachca.com/mcp`;
- собирает все чаты пользователя, сообщения, треды и участников;
- пишет интерактивный автономный HTML-отчёт: прогресс/блокеры проектов,
  активность, молчащие > 2 дней, исключения;
- хранит `.pachca/exclusions.md`, `.pachca/projects.md`, `.pachca/tasks.md`;
- проверяет скоупы, роль, тариф и доступ к каналу до сохранения задачи;
- не хранит токен и не делает внешних запросов из HTML.

## Что делает Markdown-панель

- показывает все Markdown-файлы текущей папки сессии;
- ищет по имени файла;
- рендерит Markdown так же, как лента сообщений OpenCode;
- позволяет редактировать и сохранять файл;
- поддерживает `Preview`, `Revert`, `Reload`;
- читает и пишет только `.md`, `.markdown`, `.mdx`, `.mdown`, `.mkd` внутри
  каталога сессии; лимит — 4 МБ на файл.

## Проверка

1. Перезапустите OpenCode или откройте
   **Settings → Extensions → Plugins → Reload**.
2. Палитра команд → **Open Markdown panel**.
3. В боковой панели появится список `.md` файлов текущей сессии.
4. Откройте файл, нажмите **Edit**, измените текст и **Save**.

## Безопасность

- `service.json`, `auth.json`, токены и ключи не входят в папку.
- Плагин ограничен каталогом сессии и расширениями Markdown.
- Плагин выполняет локальный код; устанавливайте только проверенные версии.
- Перед публичным распространением проверьте лицензию:
  [`NOTICE.md`](NOTICE.md).

## Лицензии

Исходники `md-viewer` перенесены из локального проекта, в котором не было
файла лицензии. Перед публичным распространением добавьте лицензию или
получите разрешение автора. Подробности — в [`NOTICE.md`](NOTICE.md).