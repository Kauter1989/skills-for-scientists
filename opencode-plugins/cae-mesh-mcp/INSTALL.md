# Установка cae-mesh-mcp (временный вариант)

> **Статус: temporary.** Отдельного публичного MCP-сервера именно для CAE-мешей
> не найдено. Временно используется FieldCraft: он умеет hex/tet-мешинг,
> FEA/CFD и отдаёт те же команды через MCP. Заменить, когда появится
> специализированный CAE-mesh MCP.

Upstream: <https://github.com/tangency-labs/fieldcraft> (Apache-2.0, 282★).

## 1. Что даёт

- открытие параметрической детали;
- тетраэдральный и гексаэдральный мешинг;
- материалы, нагрузки, закрепления;
- FEA/CFD-расчёт и проверка сеточной сходимости;
- MCP-сервер `fieldcraft-cli mcp` для агента.

## 2. Требования

| Компонент | Условие |
|---|---|
| FieldCraft | релиз для Windows/macOS/Linux или сборка из Rust |
| `fieldcraft-cli` | в PATH или абсолютный путь |
| OpenCode | MCP-серверы в `opencode.json` |
| GPU | рекомендуется для интерактивного режима; headless работает без окна |

## 3. Установка

Скачайте релиз: <https://github.com/tangency-labs/fieldcraft/releases/latest>.

Или соберите из исходников:

```bash
git clone https://github.com/tangency-labs/fieldcraft.git
cd fieldcraft
cargo build --release -p fieldcraft-cli
```

Бинарник: `target/release/fieldcraft-cli` (`fieldcraft-cli.exe` на Windows).

## 4. Подключение MCP в OpenCode

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "fieldcraft": {
        "type": "local",
        "command": [
          "C:/path/to/fieldcraft-cli.exe",
          "mcp",
          "--automation-read-root",
          "C:/work/models",
          "--automation-write-root",
          "C:/work/models/out"
        ]
      }
    }
  }
}
```

`--automation-read-root` и `--automation-write-root` ограничивают файловый
доступ агента. Без них ограничения нет. Для просмотра работы агента в
открытом приложении используйте `--connect 127.0.0.1:7070`.

## 5. Проверка

1. Запустите `fieldcraft-cli mcp` вручную — сервер должен отвечать по stdio.
2. Перезапустите OpenCode.
3. Откройте простую деталь, постройте mesh, задайте материал и нагрузку.
4. Запустите расчёт и проверьте, что результат и сетка доступны агенту.

Документация MCP: <https://github.com/tangency-labs/fieldcraft/blob/main/docs/mcp.md>.

## 6. Безопасность

- FieldCraft выполняет инженерные расчёты и файловые операции; задавайте
  read/write roots.
- Не давайте агенту доступ к чужим каталогам и-production-данным.
- Результаты расчёта проверяйте сеточной сходимостью и аналитикой; не
  считайте один запуск доказательством.

## 7. Ограничения

- Это временный upstream: полноценное CAE-приложение, а не узкий mesh-MCP.
- Ранняя стадия проекта; API и возможности могут меняться.
- Лицензия Apache-2.0.

## 8. Критерий замены

Заменить на специализированный CAE-mesh MCP, если он даёт:

- больше форматов сеток;
- меньше зависимостей;
- стабильный API и лицензию;
- отдельные инструменты только для mesh generation/quality.