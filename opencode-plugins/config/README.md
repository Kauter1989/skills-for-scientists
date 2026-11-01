# Конфигурация OpenCode

`opencode.example.json` — минимальный пример глобального
`~/.config/opencode/opencode.json` с Markdown-панелью.

## Что входит

- `plugins`: путь к `opencode-md-panel`.

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