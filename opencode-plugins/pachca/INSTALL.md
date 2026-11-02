# Установка opencode-pachca

Плагин проверен на OpenCode V2 (Plugin API `@opencode/plugin` 2.2.x). Нужен
OpenCode Desktop или сервер с поддержкой плагинов; Node.js на машине
пользователя не обязателен, но нужен для запуска тестов из репозитория.

## 1. Требования

| Компонент | Условие |
|---|---|
| OpenCode | V2, плагины включены |
| Pachca | пространство, доступ к API и MCP |
| `PACHCA_TOKEN` | для REST-сбора; можно не задавать при OAuth |
| Node.js 20+ | только для тестов и генерации примера |

## 2. Клонировать репозиторий

```bash
git clone https://github.com/Kauter1989/opencode-skills.git
cd opencode-skills/skills/opencode-plugins/pachca
```

## 3. Установить зависимость

Если OpenCode не подхватывает `@opencode/plugin` из своего окружения:

```bash
cd opencode-plugins/pachca
npm install
# или
bun install
```

`node_modules` не коммитится. При обновлении плагина повторите установку,
если менялась версия зависимости.

## 4. Подключить плагин

Откройте `~/.config/opencode/opencode.json` (или проектный
`opencode.json`) и добавьте путь к каталогу плагина:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": [
    "C:/Users/<user>/opencode-skills/skills/opencode-plugins/pachca"
  ]
}
```

Правила:

- путь указывает на каталог, где лежит `package.json`;
- используйте прямые слэши; обратные нужно экранировать;
- не указывайте `src/index.js`;
- не копируйте `node_modules` и не храните токен в конфиге.

Если плагин скопирован в глобальную папку:

```powershell
$oc = "$env:USERPROFILE\.config\opencode"
New-Item -ItemType Directory -Force "$oc\plugins" | Out-Null
Copy-Item -Recurse . "$oc\plugins\pachca"
```

Тогда в конфиге:

```jsonc
"plugins": ["C:/Users/<user>/.config/opencode/plugins/pachca"]
```

## 5. Токен или OAuth

### Вариант A: токен

Создайте токен в Пачке: **Интеграции → API → Создать токен**. Для отчёта
достаточно чтения:

```
profile:read
chats:read
chat_members:read
messages:read
threads:read
users:read
search:chats
search:messages
search:users
```

Задайте переменную в окружении, из которого запускается OpenCode:

```powershell
[Environment]::SetEnvironmentVariable("PACHCA_TOKEN", "<TOKEN>", "User")
```

Перезапустите OpenCode. Не пишите токен в `opencode.json` и не коммитьте.

### Вариант B: OAuth через MCP

Не задавайте `PACHCA_TOKEN`. Плагин добавит сервер с OAuth. Откройте
`/mcps`, выберите `pachca`, войдите в Пачку и разрешите доступ.

Если сервер уже добавлен вручную, плагин его не перезаписывает.

## 6. Навык

Скопируйте навык:

```powershell
Copy-Item -Recurse ..\..\reports\pachca-report "$env:USERPROFILE\.config\opencode\skill\pachca-report"
```

или в проект:

```powershell
New-Item -ItemType Directory -Force .opencode\skill | Out-Null
Copy-Item -Recurse ..\..\reports\pachca-report .opencode\skill\pachca-report
```

OpenCode перечитывает конфигурацию и навыки без перезапуска; принудительно —
`/reload`.

## 7. Проверка

1. В новой сессии вызовите:

```text
pachca.status { "deep": true }
```

2. Ожидаемо:
   - `mcp.configured: true`;
   - `tokenConfigured: true` или подключённый OAuth;
   - `token.scopes` содержит `chats:read` и `messages:read`;
   - `stateDir` указывает на `.pachca`.

3. Соберите тестовый слой:

```text
pachca.collect { "days": 7 }
```

4. Соберите отчёт без анализа:

```text
pachca.report { "title": "Проверка Pachca" }
```

5. Откройте `.pachca/reports/pachca-report-YYYY-MM-DD.html`.

## 8. Проверка без Пачки

```bash
node test/run-tests.mjs
node test/api.test.mjs
node --experimental-loader ./test/loader.mjs test/plugin.test.mjs
node test/build-example.mjs
cd ../../reports/pachca-report
python scripts/check_report.py examples/example-report.html
python scripts/validate_analysis.py examples/example-snapshot.json examples/example-analysis.json
```

Тесты используют локальный mock-сервер и не обращаются к Пачке.

## 9. Troubleshooting

| Симптом | Причина | Решение |
|---|---|---|
| `pachca` нет в списке MCP | путь к плагину неверный | указать каталог с `package.json`, перезагрузить |
| `needs authentication` | OAuth не завершён | `/mcps` → `pachca` → вход |
| `PACHCA_TOKEN не задан` | переменная не видна процессу | задать в окружении и перезапустить |
| `401` | токен отозван | новый токен |
| `403 insufficient_scope` | нет скоупа | добавить право в токен |
| Пустой отчёт | нет новых сообщений | увеличить `days`, проверить `lastCollectedAt` |
| `snapshot_missing` | не было `collect` | `pachca.collect` |
| `chat_role_unverified` | роль в чате не подтверждена | дать токен или `capabilities.chatRoles` |
| HTML не открывается | файл не создан | проверить `output`, права на `.pachca` |

## 10. Обновление

```bash
git pull
```

Если плагин подключён путём к репозиторию, перезапуск не нужен: `/reload`.
Если скопирован в `~/.config/opencode/plugins`, повторите копирование.

## 11. Что не переносится

- `PACHCA_TOKEN` и OAuth-хранилище;
- `.pachca/` с рабочими данными;
- `node_modules`;
- абсолютные пути другой машины.