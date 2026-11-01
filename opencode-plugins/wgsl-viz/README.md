# wgsl-viz — 3D/WebGPU панель OpenCode

Плагин для OpenCode Desktop: агент отправляет WGSL-сцену, панель «WGSL Viz»
открывается сама и рендерит её через WebGPU. Сервер хранит текущую сцену и
раздаёт статическую страницу для встроенного браузера.

## Состав

| Путь | Что это |
|---|---|
| `plugin/` | исходники плагина `opencode-wgsl-viz` |
| `plugin/src/index.ts` | инструменты `wgslviz.push` и `wgslviz.status` |
| `plugin/src/gui.tsx` | нативная панель Desktop |
| `plugin/dist/gui-experimental.cjs` | собранный GUI-бандл |
| `server/server.py` | viz-сервер на `127.0.0.1:8787`, только stdlib |
| `server/index.html` | браузерный раннер и редактор WGSL |
| `server/phong.wgsl` | стартовая сцена, если нет `current.json` |

## Сборка

```bash
cd plugin
npm ci
npm run build
```

Или без npm-скрипта:

```bash
npx vite build
```

GUI-часть собирается в `dist/gui-experimental.cjs`. Серверная часть
загружается напрямую из `src/index.ts`.

## Запуск сервера

```bash
python server/server.py
curl -s http://127.0.0.1:8787/api/state?meta=1
```

Сервер слушает только `127.0.0.1:8787`. Текущая сцена сохраняется в
`server/current.json`; этот файл не коммитится.

## Подключение

```jsonc
{
  "plugins": ["<путь-к-репозиторию>/skills/opencode-plugins/wgsl-viz/plugin"]
}
```

После изменения `dist/` перезагрузите плагины в
**Settings → Extensions → Plugins → Reload** или перезапустите OpenCode.

## Проверка

1. Открыть панель: палитра команд → **Open WGSL Viz**.
2. Отправить сцену:

   ```json
   {"code": "<WGSL>", "title": "demo", "geometry": {"kind": "sphere"}, "focus": true}
   ```

   Через инструмент `wgslviz.push` или `POST /api/scene`.
3. `wgslviz.status` должен показать версию и заголовок.
4. Если панель Desktop недоступна, открыть
   `http://127.0.0.1:8787/index.html`.

## Ограничения

- Нужен WebGPU: современный Chromium/Edge или OpenCode Desktop с WebGPU.
- Порт 8787 занят другим процессом → освободить порт.
- GUI experimental может не совпасть с версией Desktop; тогда работает
  браузерная вкладка.
- Плагин не запускает сервер сам; сервер поднимает агент или пользователь.