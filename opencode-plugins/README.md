# opencode-plugins

Плагины и MCP-интеграции OpenCode, вынесенные из локального профиля, и
инструкции по установке на другой машине.

## Состав

| Категория | Компонент | Назначение |
|---|---|---|
| Memory & context | `supermemory/` | постоянная память: профиль, знания проекта, recall, автосохранение, индексация кода |
| Documents & preview | `md-viewer/` | панель Markdown: список `.md` файлов сессии, просмотр, редактирование, сохранение |
| Collaboration & reporting | `pachca/` | MCP Пачки, сбор чатов, интерактивный HTML-отчёт, исключения и задачи |
| Engineering & simulation | `freecad-mcp/` | FreeCAD через MCP: модели, Python, документы, FEM |
| Engineering & simulation | `cae-mesh-mcp/` | **temporary:** FieldCraft — hex/tet-мешинг, FEA/CFD, MCP |
| Medical imaging | `ferrum/` | DICOM/NIfTI: срезы, MPR, 3D, измерения и сегментация; MCP + навык |
| — | `config/` | примеры конфигурации без секретов |
| — | `INSTALL.md` | каталог плагинов по категориям |
| — | `NOTICE.md` | источники и статус лицензий |

Внешние плагины и MCP-интеграции не вендорятся: в папках лежат проверенные
инструкции установки и ссылки на upstream.

## Быстрый старт: Markdown-панель

```bash
git clone https://github.com/Kauter1989/skills-for-scientists.git
cd skills-for-scientists/opencode-plugins/md-viewer

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

Полная последовательность — [`md-viewer/INSTALL.md`](md-viewer/INSTALL.md).

## Memory & context

### supermemory

Постоянная память между сессиями и проектами: профиль пользователя, знания
проекта, semantic recall, автосохранение turn'ов, индексация кодовой базы.

```bash
bunx opencode-supermemory@latest install --no-tui
bunx opencode-supermemory@latest login
bunx opencode-supermemory@latest status
```

Инструкция: [`supermemory/INSTALL.md`](supermemory/INSTALL.md).

## Collaboration & reporting

### pachca

MCP-подключение Пачки: собирает чаты, сообщения, треды и участников, пишет
автономный HTML-отчёт, хранит `.pachca/*.md` и проверяет права до задач.

```bash
cd pachca
node test/run-tests.mjs
node test/api.test.mjs
node --experimental-loader ./test/loader.mjs test/plugin.test.mjs
```

Инструкция: [`pachca/INSTALL.md`](pachca/INSTALL.md).

## Engineering & simulation

### freecad-mcp

FreeCAD addon + MCP-сервер: создание и редактирование моделей, Python,
инспекция документов и FEM.

Инструкция: [`freecad-mcp/INSTALL.md`](freecad-mcp/INSTALL.md).

### cae-mesh-mcp — temporary

Временный upstream FieldCraft: hex/tet-мешинг, FEA/CFD и MCP. Заменить, когда
появится специализированный CAE-mesh MCP.

Инструкция: [`cae-mesh-mcp/INSTALL.md`](cae-mesh-mcp/INSTALL.md).

## Medical imaging

### ferrum

FERRUM — визуализация и сегментация медицинских объёмов: DICOM/NIfTI, срезы,
MPR, 3D, измерения, аннотации и сегменты. Для OpenCode: `ferrum-cli mcp` +
навык `skills/ferrum`.

Инструкция: [`ferrum/INSTALL.md`](ferrum/INSTALL.md).

> FERRUM — не медицинское изделие. Результаты требуют проверки специалистом;
> навык не ставит диагноз.

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
2. Для плагинов проверьте `opencode plugin list`.
3. Для MCP-интеграций проверьте подключение в `/mcps`.
4. Для каждого компонента выполните проверку из его `INSTALL.md`.

## Безопасность

- `service.json`, `auth.json`, токены и ключи не входят в папку.
- MCP-интеграции исполняют локальный код и требуют доверия к upstream.
- Ограничивайте файловые корни для FreeCAD/FieldCraft/Ferrum.
- Медицинские данные не публикуйте; PHI не должны попадать в логи.
- Перед публичным распространением проверьте лицензии:
  [`NOTICE.md`](NOTICE.md).

## Лицензии

- `md-viewer` — лицензия не заявлена в исходном проекте;
- `pachca` — Apache-2.0;
- `supermemory` — MIT по README, отдельного LICENSE нет;
- `freecad-mcp` — MIT;
- `cae-mesh-mcp` (FieldCraft) — Apache-2.0;
- `ferrum` — MIT OR Apache-2.0.

Подробности — в [`NOTICE.md`](NOTICE.md).