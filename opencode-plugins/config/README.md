# Конфигурация OpenCode

`opencode.example.json` — минимальный пример глобального
`~/.config/opencode/opencode.json` с Markdown-панелью.
`opencode.pachca.example.json` — пример с плагином Pachca и MCP-сервером
(вход через OAuth).

## Что входит

- `plugins`: путь к `opencode-md-panel` или `pachca`;
- `mcp.servers.pachca`: адрес MCP; плагин добавляет его сам, если сервера нет.

Для токена не добавляйте его в JSON. Задайте `PACHCA_TOKEN` в окружении:
плагин подставит `Bearer {env:PACHCA_TOKEN}` в заголовок MCP.

## Что не входит

- `service.json` и любые пароли/токены;
- `auth.json` и ключи провайдеров;
- `node_modules` и кэши;
- персональные абсолютные пути.

Секреты создаются на новой машине заново:

```bash
opencode auth login
```

Если вашей интеграции нужен локальный `service.json`, создайте его вручную
рядом с `opencode.json` и не коммитьте.

## Пути

В JSON используйте прямые слэши: `C:/Users/...` или `~/...`. Обратные слэши
нужно экранировать, поэтому они не рекомендуются.

Если плагин остаётся в репозитории:

```text
<repo>/skills/opencode-plugins/md-viewer
```

Если он скопирован в глобальный каталог:

```text
~/.config/opencode/plugins/opencode-md-panel
```