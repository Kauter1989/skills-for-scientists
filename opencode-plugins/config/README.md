# Конфигурация OpenCode

`opencode.example.json` — рабочий скелет глобального
`~/.config/opencode/opencode.json`. Замените пути и команду Ferrum.

## Что входит

- `plugins`: Markdown-панель, WGSL-визуализация, квота;
- `skills`: каталог установленных навыков (включая `visualize` и Ferrum);
- `mcp.servers.ferrum`: локальный MCP-сервер Ferrum.

## Что не входит

- `service.json` и любые пароли/токены;
- `auth.json` и ключи провайдеров;
- `node_modules`, кэши и `current.json` viz-сервера;
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

Если плагины остаются в репозитории, путь выглядит так:

```text
<repo>/skills/opencode-plugins/md-viewer
<repo>/skills/opencode-plugins/wgsl-viz/plugin
```

Если они скопированы в глобальный каталог:

```text
~/.config/opencode/plugins/opencode-md-panel
~/.config/opencode/plugins/opencode-wgsl-viz
```