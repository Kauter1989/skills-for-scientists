# Установка freecad-mcp

MCP-интеграция FreeCAD: агент создаёт и редактирует модели, выполняет Python
в контексте FreeCAD, читает документы и запускает FEM-анализ.

Upstream: <https://github.com/neka-nat/freecad-mcp> (MIT, 3.1k★).

## 1. Требования

| Компонент | Условие |
|---|---|
| FreeCAD | 0.21+ или 1.0+ |
| Python / uv | `uv` или `uvx` в PATH |
| OpenCode | MCP-серверы в `opencode.json` |
| GPU/desktop | для GUI-режима FreeCAD; headless зависит от сборки |

## 2. Установка FreeCAD addon

```bash
git clone https://github.com/neka-nat/freecad-mcp.git
cd freecad-mcp
```

Скопируйте `addon/FreeCADMCP` в каталог addon'ов FreeCAD:

| ОС | Каталог |
|---|---|
| Windows | `%APPDATA%\FreeCAD\Mod\FreeCADMCP` |
| Linux | `~/.local/share/FreeCAD/Mod/FreeCADMCP` |
| macOS | `~/Library/Application Support/FreeCAD/Mod/FreeCADMCP` |

Перезапустите FreeCAD, выберите workbench **MCP Addon** и нажмите
**Start RPC Server** на панели **FreeCAD MCP**.

Подробная установка с скриншотами:
<https://github.com/neka-nat/freecad-mcp/blob/main/docs/installation.md>.

## 3. Подключение MCP в OpenCode

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "freecad": {
        "type": "local",
        "command": ["uvx", "freecad-mcp"]
      }
    }
  }
}
```

`uvx` запускает MCP-сервер, который соединяется с addon'ом внутри FreeCAD.
FreeCAD должен быть открыт, RPC-сервер — запущен.

## 4. Проверка

1. Перезапустите OpenCode.
2. В новой сессии вызовите инструмент создания документа.
3. Создайте простой объект, например куб.
4. Запросите список объектов и скриншот вида.
5. Убедитесь, что изменения видны в открытом FreeCAD.

## 5. Безопасность

- MCP-сервер исполняет Python внутри FreeCAD; считайте это полным доступом
  к модели и окружению FreeCAD.
- Не подключайте недоверенные addon'ы и не запускайте чужие скрипты.
- Ограничьте рабочий каталог и не давайте агенту доступ к лишним файлам.
- Сохраняйте модели в Git только после проверки.

## 6. Ограничения

- Нужен запущенный FreeCAD с RPC-сервером; без него инструменты не работают.
- FEM-анализ зависит от установленных solver'ов FreeCAD.
- Это MCP-интеграция, а не OpenCode-плагин: она добавляется в секцию `mcp`,
  а не в `plugins`.

## 7. Лицензия

MIT. См. upstream `LICENSE`.