# Установка ferrum

FERRUM — визуализация и сегментация медицинских объёмов: DICOM/NIfTI, срезы,
MPR, 3D volume rendering, измерения, аннотации и сегменты. Для OpenCode
используется MCP-сервер `ferrum-cli mcp` и навык `skills/ferrum`.

> FERRUM — не медицинское изделие. Результаты и сегменты требуют проверки
> квалифицированным специалистом; навык не ставит диагноз.

Upstream: <https://github.com/Kauter1989/ferrum> (MIT OR Apache-2.0).

## 1. Требования

| Компонент | Условие |
|---|---|
| GPU | Vulkan, Metal, DirectX 12 или OpenGL |
| ОС | Windows x86_64, Linux x86_64, macOS Apple Silicon |
| `ferrum-cli` | из релиза или сборки |
| OpenCode | MCP-серверы и навыки |
| Rust | только для сборки из исходников |

## 2. Установка

Рекомендуется готовый релиз:
<https://github.com/Kauter1989/ferrum/releases/latest>.

В архиве релиза есть `ferrum-cli`, desktop-приложение и `skills/ferrum`.

Сборка из исходников:

```bash
git clone https://github.com/Kauter1989/ferrum.git
cd ferrum
cargo build --release
```

Точную команду сборки CLI сверяйте с README релиза: структура workspace
может меняться.

## 3. Подключение MCP в OpenCode

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "ferrum": {
        "type": "local",
        "command": [
          "C:/path/to/ferrum-cli.exe",
          "mcp",
          "--workspace-root",
          "C:/work/ferrum"
        ],
        "timeout": {
          "startup": 20000
        }
      }
    }
  }
}
```

`--workspace-root` задаёт каталог, где агент создаёт workspace'ы исследований.

## 4. Установка навыка

Скопируйте `skills/ferrum` из релиза или репозитория:

```powershell
Copy-Item -Recurse .\skills\ferrum "$env:USERPROFILE\.config\opencode\skills\ferrum"
```

или в проект:

```powershell
New-Item -ItemType Directory -Force .opencode\skills | Out-Null
Copy-Item -Recurse .\skills\ferrum .opencode\skills\ferrum
```

Навык содержит `SKILL.md`, reference-страницы, JSON-схемы и evals.

## 5. Проверка

1. Перезапустите OpenCode.
2. Убедитесь, что MCP-сервер `ferrum` подключён.
3. Откройте тестовый DICOM/NIfTI:

   ```bash
   ferrum-cli study open --workspace ws/ct1 /data/series
   ```

4. Запросите срез или MPR и проверьте изображение.
5. Числа берите только из `ferrum_probe`, `ferrum_stats` или
   `ferrum_measure_*`, не из пикселей изображения.

## 6. Безопасность и клинические границы

- Не публиковать PHI и идентификаторы пациентов в отчётах и логах.
- Исходные исследования открываются read-only; workspace хранит ссылки и
  хэши.
- Сегменты и аннотации агента имеют статус `proposed` до подтверждения
  человеком.
- Не использовать для диагностики, скрининга или выбора лечения.
- Проверять результаты на фантомах и контрольных данных.

## 7. Ограничения

- Не заменяет PACS, диктологию и клиническую валидацию.
- Для AI-сегментации нужен разрешённый engine по протоколу `ferrum-engine/1`.
- Качество и скорость зависят от GPU.
- Лицензия: MIT OR Apache-2.0.