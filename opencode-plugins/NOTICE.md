# Установка и воспроизведение сессий

Пошаговая инструкция для другой машины с OpenCode Desktop. В результате
будут доступны:

- панель **Markdown**;
- панель **WGSL Viz** и инструменты `wgslviz.push` / `wgslviz.status`;
- viz-сервер на `127.0.0.1:8787`;
- команда `/visualize` и навык `visualize`;
- индикатор квоты и `quota_status` (сторонний плагин);
- опционально MCP Ferrum для медицинских объёмов.

## 1. Требования

| Компонент | Версия / условие |
|---|---|
| OpenCode Desktop | 2.x с Plugin API `@opencode/plugin` 2.2.x |
| Node.js | 20.19+ или 22+ |
| Bun | 1.2+ (для `md-viewer`; можно заменить на npm + `npx vite build`) |
| Python | 3.10+ (viz-сервер, только stdlib) |
| Браузер | WebGPU: современный Edge/Chrome или панель Desktop |
| Ferrum | опционально; нужен для DICOM/NIfTI и stream-режима |

Модель должна поддерживать tool calling: плагины добавляют инструменты
`wgslviz.push`, `wgslviz.status`, `quota_status` и RPC Markdown-панели.

## 2. Клонирование

```bash
git clone https://github.com/Kauter1989/opencode-skills.git
cd opencode-skills/skills/opencode-plugins
```

Дальше команды даны от каталога `opencode-plugins`, если не указано иное.

## 3. Сборка плагинов

### Markdown-панель

```bash
cd md-viewer
bun install
bun run build
```

Если Bun нет:

```bash
npm install
npx vite build
```

### WGSL-панель

```bash
cd ../wgsl-viz/plugin
npm ci
npm run build
```

`package-lock.json` закрепляет `@opencode/plugin` 2.2.0. Если ваша версия
Desktop требует другую версию API, обновите зависимость и пересоберите
`dist/gui-experimental.cjs`.

## 4. Установка в глобальный каталог

### Windows PowerShell

```powershell
$oc = "$env:USERPROFILE\.config\opencode"
New-Item -ItemType Directory -Force "$oc\plugins","$oc\skills","$oc\commands" | Out-Null

Copy-Item -Recurse .\md-viewer "$oc\plugins\opencode-md-panel"
Copy-Item -Recurse .\wgsl-viz\plugin "$oc\plugins\opencode-wgsl-viz"
Copy-Item -Recurse .\skills\visualize "$oc\skills\visualize"
Copy-Item .\commands\visualize.md "$oc\commands\visualize.md"
```

### macOS / Linux

```bash
oc="$HOME/.config/opencode"
mkdir -p "$oc/plugins" "$oc/skills" "$oc/commands"
cp -r md-viewer "$oc/plugins/opencode-md-panel"
cp -r wgsl-viz/plugin "$oc/plugins/opencode-wgsl-viz"
cp -r skills/visualize "$oc/skills/visualize"
cp commands/visualize.md "$oc/commands/visualize.md"
```

Можно не копировать плагины, а указать в конфигурации абсолютные пути к
каталогам в репозитории. Тогда после `git pull` не нужно копировать заново.

## 5. Конфигурация OpenCode

Откройте или создайте `~/.config/opencode/opencode.json`. Возьмите
[`config/opencode.example.json`](config/opencode.example.json) и замените
пути.

Минимальный вариант:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": [
    "C:/Users/<user>/.config/opencode/plugins/opencode-md-panel",
    "@slkiser/opencode-quota",
    "C:/Users/<user>/.config/opencode/plugins/opencode-wgsl-viz"
  ],
  "skills": [
    "C:/Users/<user>/.config/opencode/skills"
  ]
}
```

Если Ferrum не нужен, блок `mcp` можно не добавлять.

### Секреты

В исходном профиле рядом с `opencode.json` был `service.json` с паролем.
Он **намеренно не скопирован**. Если ваш локальный сервис его требует,
создайте файл вручную на новой машине и не коммитьте.

Ключи провайдеров добавьте через:

```bash
opencode auth login
```

или через настройки провайдеров в Desktop. Не храните ключи в
`opencode.json` и в этом репозитории.

## 6. Ferrum (опционально)

Нужен для медицинских объёмов, MPR и stream-режима.

1. Установите или соберите `ferrum-cli` версии 0.3.0+.
2. Пропишите MCP-сервер в `opencode.json`:

   ```jsonc
   {
     "mcp": {
       "servers": {
         "ferrum": {
           "type": "local",
           "command": ["C:/path/to/ferrum-cli.exe", "mcp"],
           "timeout": { "startup": 20000 }
         }
       }
     }
   }
   ```

3. Для stream-режима запустите frame-server:

   ```bash
   ferrum-cli serve -w <workspace> --port 8788 --size 640
   ```

4. Навык `ferrum` положите в каталог `skills`, который указан в
   `opencode.json`.

Без Ferrum работают формулы, heightfield, сферы, кубы, custom-меши и
Markdown-панель. Медицинские объёмы и ferrum-stream требуют бинарник.

## 7. Запуск

```bash
python wgsl-viz/server/server.py
```

Проверка:

```bash
curl -s http://127.0.0.1:8787/api/state?meta=1
```

Ожидается JSON с `version`, `focusToken`, `geometryToken`, `title`.

Затем перезапустите OpenCode или откройте
**Settings → Extensions → Plugins → Reload**.

## 8. Проверка сессии

1. **Markdown:** палитра команд → **Open Markdown panel**; в боковой панели
   появится список `.md` файлов.
2. **3D:** команда `/visualize сфера с fresnel-rim` или запрос
   «покажи сферу в 3D». Должна открыться панель **WGSL Viz**.
3. **Инструменты:** `wgslviz.status` возвращает версию сцены.
4. **Квота:** индикатор в интерфейсе или `quota_status`.
5. **Fallback:** если панель Desktop не открылась, откройте
   `http://127.0.0.1:8787/index.html`.

Ручная проверка сцены:

```bash
curl -s -X POST http://127.0.0.1:8787/api/scene \
  -H "Content-Type: application/json" \
  -d '{"code":"<WGSL>","title":"demo","geometry":{"kind":"sphere"},"focus":true}'
```

## 9. Troubleshooting

| Симптом | Что проверить |
|---|---|
| `viz server unreachable` | запущен ли `server.py`; порт 8787 |
| Панель WGSL не открылась | `Settings → Extensions → Plugins`; пересобрать `dist`; перезапустить Desktop |
| `WebGPU is not available` | открыть в Edge/Chrome или включить WebGPU |
| Markdown-панель пустая | сессия открыта в каталоге с `.md`; плагин загружен |
| `quota_status` недоступен | пакет `@slkiser/opencode-quota` не установлен |
| Ferrum MCP не стартует | путь к `ferrum-cli`, версия 0.3.0+, `timeout.startup` |
| Сцена не меняется | `wgslviz.status`; проверить `focusToken` и `version` |

## 10. Обновление

```bash
git pull
cd md-viewer && bun install && bun run build
cd ../wgsl-viz/plugin && npm ci && npm run build
```

Если плагины скопированы в `~/.config/opencode/plugins`, повторите
копирование и перезагрузите плагины.

## 11. Что не переносится

- `service.json` и пароли;
- `auth.json`, ключи провайдеров, кэш моделей;
- `node_modules` и `current.json` viz-сервера;
- персональные абсолютные пути вида `E:\projects\...`.

Пути в навыке `visualize` даны относительно корня репозитория
`opencode-skills/skills`. Если вы запускаете OpenCode из другого каталога,
замените `opencode-plugins/wgsl-viz` на абсолютный путь.<｜end▁of▁thinking｜>Создам остальные файлы: `INSTALL.md` уже записан. Теперь `NOTICE.md`, `.gitignore`, обновление корневых README/AGENTS/карты, затем проверка и коммит/PR.

Сначала проверю, что скопированные файлы не содержат секретов и больших артефактов. `service.json` не копировали. В md/wgsl исходниках секретов нет. `bun.lock`/`package-lock` могут содержать URL, но не секреты.

Создам `NOTICE.md` с provenance.

<｜DSML｜ calls>
<｜DSML｜ invoke name="write">
<｜DSML｜ parameter name="content" string="true"># Источники и лицензии

Папка `opencode-plugins` собирает компоненты, которые использовались в
локальном профиле OpenCode. Ниже — происхождение и статус лицензий.

| Компонент | Источник | Лицензия | Примечание |
|---|---|---|---|
| `md-viewer/` | локальный проект `opencode-md-plugin` | не заявлена | в исходном каталоге не было `LICENSE` |
| `wgsl-viz/plugin/` | локальный проект `wgsl-playground/opencode-plugin` | не заявлена | в исходном каталоге не было `LICENSE` |
| `wgsl-viz/server/` | локальный проект `wgsl-playground` | не заявлена | `server.py`, `index.html`, `phong.wgsl` |
| `skills/visualize/` | локальный профиль `~/.config/opencode/skills/visualize` | не заявлена | навык и его references/scripts/templates |
| `commands/visualize.md` | локальный профиль `~/.config/opencode/commands` | не заявлена | команда `/visualize` |
| `quota/` | npm `@slkiser/opencode-quota` 6.0.0 | MIT | исходники не вендорятся, только инструкция |
| `@opencode/plugin` | npm-зависимость плагинов | проверяется в пакете | версии закреплены в lock-файлах |

## Что это значит

Компоненты без заявленной лицензии нельзя публично распространять без
разрешения автора. Если репозиторий публичный, перед релизом:

1. добавьте `LICENSE` в каждый компонент или в корень с совместимой
   лицензией;
2. получите разрешение автора, если код не ваш;
3. сохраните ссылки на источники и дату снимка.

`@slkiser/opencode-quota` распространяется по MIT; его условия действуют на
этот пакет, а не на остальные компоненты.

## Снимок

- дата: `2026-11-01`;
- версия `@slkiser/opencode-quota`: `6.0.0`;
- версия `@opencode/plugin` в `md-viewer`: `2.2.1`;
- версия `@opencode/plugin` в `wgsl-viz`: `2.2.0`.

## Секреты

В папке нет `service.json`, `auth.json`, токенов и ключей. Если вы добавляете
локальный конфиг с секретами, держите его вне репозитория.