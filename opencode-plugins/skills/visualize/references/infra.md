# Инфраструктура визуализации

## Компоненты

| Компонент | Где | Зачем |
| --- | --- | --- |
| viz-сервер | `opencode-plugins/wgsl-viz/server/server.py`, порт 8787 (bind 127.0.0.1) | хранит сцену, раздаёт статику и API |
| Раннер-страница | `http://localhost:8787/index.html` | редактор WGSL + рендер (встроенный браузер / внешнее окно) |
| Плагин `wgslviz` | `opencode-plugins/wgsl-viz/plugin` | инструменты `push`/`status` + нативная панель Desktop |
| GUI-бандл панели | `opencode-plugins/wgsl-viz/plugin/dist/gui-experimental.cjs` | пересборка: `npm run build` или `npx vite build` (Node 20.19+) |
| Подключён | глобальный `~/.config/opencode/opencode.json` → `plugins` | GUI доступен во всех окнах Desktop |
| FERRUM (мед. объёмы) | MCP `ferrum` = `ferrum-cli mcp` (команда в `opencode.json`, версия 0.3.0+); skill `ferrum` из каталога `skills` релиза Ferrum | DICOM/NIfTI: срезы, MPR, 3D DVR, измерения, сегментация |
| FERRUM frame-server | `ferrum-cli serve -w <ws> --port 8788 --size 640` — HTTP `POST /frame {yaw,pitch,dist,mode,preset,clip,size}` → PNG | интерактивный 3D в панели рендерером ferrum (CPU raycaster) |

## Запуск сервера

```sh
python opencode-plugins/wgsl-viz/server/server.py        # фон сессии
curl -s http://127.0.0.1:8787/api/state?meta=1       # проверка
```

Текущая сцена переживает рестарт сервера (`current.json` рядом с server.py).

## Где человек видит сцену

1. Нативная панель **«WGSL Viz»**: боковая область сессии Desktop
   (пункт «+» → WGSL Viz, или палитра команд → «Open WGSL Viz»).
   Открывается сама при push с `focus:true`.
2. Вкладка встроенного браузера `http://localhost:8787/index.html` (Review pane).
3. Внешнее окно: `msedge --app="http://localhost:8787/index.html"` или двойной клик
   по `index.html` (file:// тоже работает, но без push-API).

## Troubleshooting

- `viz server unreachable` в панели/странице → сервер не запущен: поднять (см. выше).
- Панель не появляется в Desktop → Settings > Extensions > Plugins: статус
  `opencode-wgsl-viz`; GUI experimental и мог не совпасть с версией приложения →
  пересобрать бандл или пользоваться вкладкой браузера (сцена та же).
- Ошибки WGSL → страница/панель показывают сообщение компилятора; `status` не меняется.
- Порт 8787 занят → найти и остановить: `Get-NetTCPConnection -LocalPort 8787`.
- WebGPU отсутствует (старый браузер) → страница покажет fatal-оверлей с инструкцией.
