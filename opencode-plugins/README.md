# opencode-plugins

Вендорная папка плагинов и навыков, которые нужны для воспроизведения
сессий OpenCode Desktop с 3D-визуализацией, Markdown-панелью и квотой.

Здесь лежат **исходники и собранные артефакты**, а не глобальная
конфигурация. Секреты, токены и `auth.json` в репозиторий не входят.

## Состав

| Путь | Компонент | Назначение |
|---|---|---|
| `md-viewer/` | `opencode-md-panel` | панель Markdown: список файлов, просмотр, редактирование, сохранение |
| `wgsl-viz/plugin/` | `opencode-wgsl-viz` | инструменты `wgslviz.push` / `wgslviz.status` и нативная 3D-панель |
| `wgsl-viz/server/` | viz-server | хранит сцену, отдаёт `/api/scene`, `/api/state` и `index.html` |
| `quota/` | `@slkiser/opencode-quota` | сторонний плагин квот; инструкция по установке |
| `skills/visualize/` | навык `visualize` | workflow «запрос → WGSL + геометрия → push в панель» |
| `commands/visualize.md` | команда OpenCode | `/visualize <запрос>` |
| `config/` | пример конфигурации | `opencode.json` без секретов |

## Быстрый старт

```bash
git clone https://github.com/Kauter1989/opencode-skills.git
cd opencode-skills/skills/opencode-plugins

# 1. Собрать Markdown-панель
cd md-viewer
bun install
bun run build

# 2. Собрать WGSL-панель
cd ../wgsl-viz/plugin
npm ci
npm run build

# 3. Установить навык и команду (пример для Windows PowerShell)
cd ../../..
Copy-Item -Recurse .\opencode-plugins\skills\visualize "$env:USERPROFILE\.config\opencode\skills\visualize"
Copy-Item .\opencode-plugins\commands\visualize.md "$env:USERPROFILE\.config\opencode\commands\visualize.md"
```

Полная последовательность с конфигурацией и проверкой —
[`INSTALL.md`](INSTALL.md).

## Как это работает

```text
запрос пользователя
    → навык visualize выбирает WGSL и геометрию
    → инструмент wgslviz.push
    → POST http://127.0.0.1:8787/api/scene
    → панель «WGSL Viz» или index.html рендерит сцену
```

Markdown-панель работает независимо: она читает и пишет `.md` только внутри
каталога текущей сессии.

## Проверка

```bash
# сервер
python wgsl-viz/server/server.py
curl -s http://127.0.0.1:8787/api/state?meta=1

# плагины
# OpenCode → Settings → Extensions → Plugins → Reload
```

В сессии должны быть доступны:

- `wgslviz.push` и `wgslviz.status`;
- панель **Markdown**;
- индикатор квоты и `quota_status`;
- команда `/visualize`.

## Безопасность

- Не коммитить `service.json`, `auth.json`, токены и ключи.
- Markdown-панель ограничена расширениями `.md`, `.markdown`, `.mdx`,
  `.mdown`, `.mkd` и каталогом сессии; лимит 4 МБ.
- Viz-сервер слушает только `127.0.0.1`.
- Плагины выполняют локальный код; ставьте только те, которые понимаете.
- Перед публикацией репозитория проверьте лицензии компонентов:
  [`NOTICE.md`](NOTICE.md).

## Лицензии

`quota/` — сторонний пакет MIT. Исходники `md-viewer`, `wgsl-viz` и
`skills/visualize` перенесены из личных проектов; в них не было файла
лицензии. Перед публичным распространением добавьте лицензию или получите
разрешение автора. Подробности — в [`NOTICE.md`](NOTICE.md).