# Установка Markdown-панели

Инструкция для другой машины с OpenCode Desktop. В результате появится
панель **Markdown** для файлов текущей сессии.

## 1. Требования

| Компонент | Версия / условие |
|---|---|
| OpenCode Desktop | 2.x с Plugin API `@opencode/plugin` 2.2.x |
| Node.js | 20.19+ или 22+ |
| Bun | 1.2+; можно заменить на npm + `npx vite build` |

Модель должна поддерживать tool calling: плагин добавляет RPC Markdown-панели.

## 2. Клонирование

```bash
git clone https://github.com/Kauter1989/skills-for-scientists.git
cd skills-for-scientists/opencode-plugins/md-viewer
```

Дальше команды даны от каталога `md-viewer`.

## 3. Сборка

```bash
bun install
bun run build
```

Если Bun нет:

```bash
npm install
npx vite build
```

GUI-часть собирается в `dist/gui-experimental.cjs`. Серверная часть
загружается напрямую из `src/index.ts`.

## 4. Установка

### Windows PowerShell

```powershell
$oc = "$env:USERPROFILE\.config\opencode"
New-Item -ItemType Directory -Force "$oc\plugins" | Out-Null
Copy-Item -Recurse . "$oc\plugins\opencode-md-panel"
```

### macOS / Linux

```bash
oc="$HOME/.config/opencode"
mkdir -p "$oc/plugins"
cp -r . "$oc/plugins/opencode-md-panel"
```

Можно не копировать плагин, а указать в конфигурации абсолютный путь к
`opencode-plugins/md-viewer`. Тогда после `git pull` не нужно копировать
заново.

## 5. Конфигурация

Откройте или создайте `~/.config/opencode/opencode.json`. Возьмите
[`../config/opencode.example.json`](../config/opencode.example.json) и
замените путь.

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": [
    "C:/Users/<user>/.config/opencode/plugins/opencode-md-panel"
  ]
}
```

Если плагин остаётся в репозитории:

```jsonc
{
  "plugins": [
    "C:/Users/<user>/skills-for-scientists/opencode-plugins/md-viewer"
  ]
}
```

Используйте прямые слэши. Обратные слэши в JSON нужно экранировать.

## 6. Секреты

`service.json`, `auth.json`, токены и ключи провайдеров не входят в этот
плагин. Если локальный сервис требует `service.json`, создайте его вручную
и не коммитьте.

Ключи провайдеров добавьте через:

```bash
opencode auth login
```

или через настройки провайдеров в Desktop.

## 7. Перезапуск

Перезапустите OpenCode или откройте
**Settings → Extensions → Plugins → Reload**.

## 8. Проверка

1. Палитра команд → **Open Markdown panel**.
2. В боковой панели появится список `.md` файлов текущей сессии.
3. Откройте файл, нажмите **Edit**, измените текст и **Save**.
4. **Preview** возвращает просмотр, **Revert** отменяет несохранённые
   правки, **Reload** перечитывает файл с диска.

Проверка ограничений:

- файл вне каталога сессии должен быть отклонён;
- файл не-Markdown должен быть отклонён;
- файл больше 4 МБ должен быть отклонён.

## 9. Troubleshooting

| Симптом | Что проверить |
|---|---|
| Панели нет в меню | плагин добавлен в `plugins`; путь указывает на каталог с `package.json` |
| Панель пустая | сессия открыта в каталоге с `.md`; плагин загружен |
| Ошибка загрузки плагина | пересобран ли `dist/gui-experimental.cjs`; версия OpenCode |
| Изменения не сохраняются | файл существует; расширение Markdown; размер меньше 4 МБ |
| После `git pull` старая версия | пересобрать `dist` и перезагрузить плагины |

## 10. Обновление

```bash
git pull
cd md-viewer
bun install
bun run build
```

Если плагин скопирован в `~/.config/opencode/plugins`, повторите
копирование и перезагрузите плагины.

## 11. Что не переносится

- `service.json` и пароли;
- `auth.json`, ключи провайдеров, кэш моделей;
- `node_modules`;
- персональные абсолютные пути.