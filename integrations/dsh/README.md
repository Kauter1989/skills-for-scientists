# dsh — перенос настройки dsh на Qwen Cloud

Образец конфигурации DeepSeek Harness (dsh) с провайдером **Qwen Cloud
(Alibaba Token Plan)** через OpenAI-compatible эндпоинт и моделью по умолчанию
на этой ветке. Каталог нужен, чтобы на другом ПК за пять шагов повторить
рабочую настройку без секретов в репозитории.

Это **не** навык: `SKILL.md` здесь нет намеренно, потому что процедура — одна
настройка, а не повторяемая задача для агента, и каталог не должен появляться в
каталоге навыков как `integrations-dsh`.

## Что лежит

```
integrations/dsh/
├── README.md                          эта инструкция
├── examples/
│   ├── cordis.patch.qwen.yml          личный слой патча профиля: провайдер + модель по умолчанию
│   ├── package.json                   манифест профиля: какие bundle-слои собираются
│   └── .credentials.yaml.example      шаблон managed-хранилища секретов (без значений)
└── scripts/
    └── check_example.py               проверка примера перед переносом
```

## Как устроен конфиг dsh

| Файл | Роль |
|---|---|
| `$DSH_HOME/profiles/<profile>/package.json` | профиль и упорядоченный список `dsh.profile.bundles` |
| `$DSH_HOME/profiles/<profile>/cordis.yml` | корень загрузчика Cordis; не править |
| `$DSH_HOME/profiles/<profile>/cordis.patch.yml` | **личный слой патча**; применяется после всех bundle-слоёв |
| `$DSH_HOME/profiles/<profile>/pnpm-workspace.yaml` | настройки pnpm для внешних плагинов профиля |
| `$DSH_HOME/.credentials.yaml` | managed-хранилище секретов; создаётся самим dsh |

- `$DSH_HOME` по умолчанию — `%USERPROFILE%\.dsh` на Windows и `~/.dsh` на
  Linux/macOS. Имя профиля задаёт переменная `DSH_PROFILE`; у приложения это
  `desktop`.
- В `cordis.patch.yml` запись `config` **заменяется целиком, а не сливается**,
  поэтому при переопределении строки (например, `llm-pi-ai`) перечисляйте все
  поля, которые строка должна иметь.
- Ключ в `cordis.patch.yml` не кладётся никогда: там только имя
  credential-ссылки (`apiKeyEnv`). Значение берётся из окружения или из
  `$DSH_HOME/.credentials.yaml`. Порядок источников: managed
  `.credentials.yaml` → наследуемое окружение → `.env` проекта → `.env`
  пользователя.

## Перенос на другой ПК

### 1. Установить dsh и один раз запустить

Запуск нужен, чтобы dsh создал `$DSH_HOME`, профиль и `pnpm-workspace.yaml`.
Имя профиля проверяется так:

```powershell
"$env:DSH_PROFILE"; "$env:DSH_PROFILE_DIR"
```

Если переменная пуста, профиль называется `desktop` (приложение) или
запускается через `dsh --profile <name>`.

### 2. Задать ключ Qwen Cloud

Ключ выдаётся в консоли Qwen Cloud (Token Plan). В конфиг и в git он не
попадает.

```powershell
# Windows: переменная пользователя, действует после новой сессии
[Environment]::SetEnvironmentVariable('QWEN_TOKEN_PLAN_API_KEY','<ключ>','User')
```

```bash
# Linux/macOS
echo 'export QWEN_TOKEN_PLAN_API_KEY=<ключ>' >> ~/.bashrc
```

Или вариант Б: ключ в managed-хранилище через интерфейс — **Settings →
Models**, карточка провайдера, поле ключа. Интерфейс пишет значение в
`$DSH_HOME/.credentials.yaml` под ссылку из `apiKeyEnv`.

### 3. Скопировать файлы профиля

```powershell
$src = 'C:\path\to\skills-for-scientists\integrations\dsh\examples'
$dst = Join-Path $env:USERPROFILE ".dsh\profiles\$env:DSH_PROFILE"
# если DSH_PROFILE пуст: $dst = Join-Path $env:USERPROFILE '.dsh\profiles\desktop'

# файлы профиля
Copy-Item "$src\cordis.patch.qwen.yml" "$dst\cordis.patch.yml"
Copy-Item "$src\package.json"          "$dst\package.json"

# pnpm-workspace.yaml: только если файла нет (dsh создаёт его сам)
if (-not (Test-Path "$dst\pnpm-workspace.yaml")) {
  Copy-Item "$src\pnpm-workspace.yaml" "$dst\pnpm-workspace.yaml"
}
```

Строки, которых нет в образце, при этом теряются. Если на целевом ПК уже
есть свой patch-слой, **переносите только нужные записи**, а не файл целиком:
`cordis.patch.yml` — один YAML-массив, и две записи с одним `id` конфликтуют.

### 4. Перезапустить dsh и проверить модель

- В интерфейсе: селектор модели показывает `Alibaba Token Plan` и модели
  `qwen3.8-max`, `deepseek-v4.1-flash-1017`, `glm-5.2`, `glm-5.3`.
- CLI (если `dsh` в PATH): `dsh --profile "$env:DSH_PROFILE" --dump-config`
  печатает собранный профиль; в нём должны быть строки `llm-pi-ai` и
  `agent-default-model`.

### 5. Убедиться, что ключ виден процессу

Переменная, заданная в шаге 2, видна только процессам, запущенным после
изменения: перезапустите приложение. Если модель отвечает ошибкой
`MISSING_CREDENTIAL`, ключ не найден — проверьте имя переменной: оно должно
совпадать с `apiKeyEnv` буквально (`QWEN_TOKEN_PLAN_API_KEY`).

## Проверка примера

```powershell
cd skills/integrations/dsh
python scripts/check_example.py
```

Ожидаемо:

```
модель по умолчанию: qwen-token-plan/deepseek-v4.1-flash-1017
провайдер qwen-token-plan: QWEN_TOKEN_PLAN_API_KEY -> 4 моделей
  qwen3.8-max, deepseek-v4.1-flash-1017, glm-5.2, glm-5.3
OK
```

Скрипт проверяет: YAML разбирается и у строк есть id без дублей; `baseURL`
начинается с `https://`; у провайдера есть `apiKeyEnv`; модель по умолчанию
существует в списке своего провайдера; ссылка из `apiKeyEnv` есть в шаблоне
credentials; `package.json` — валидный JSON с непустым списком bundle; в
файлах нет значений, похожих на ключ. Зависимость — PyYAML (есть в
dsh-runtime); сеть не нужна.

## Границы и честность

- **Числа моделей — не гарантия провайдера.** `contextWindow` и `maxTokens`
  взяты из рабочего профиля и не сверены с каталогом Qwen Cloud: каталог
  требует ключа. Перед переносом сравните с `GET
  /compatible-mode/v1/models` под своим ключом.
- **Проверен только эндпоинт.** `https://token-plan.maas.qwencloudapi.com/compatible-mode/v1/models`
  на момент создания образца отвечает `401 InvalidApiKey` на запрос без ключа,
  то есть хост живой и маршрут OpenAI-compatible существует. Для моделей из
  списка ping не выполнялся.
- **`reasoningEfforts` — объявление уровней, а не факт.** Набор уровней задан
  вручную; если провайдер отвергает значение, модель вернёт ошибку, а не
  молча понизит уровень.
- **`thinkingFormat: qwen` и блок `compat`** описывают формат рассуждений
  выбранного маршрута. Их меняют только если провайдер начнёт отвечать иначе.
- **Скрипт не проверяет живой профиль**, только пример в этом каталоге. Он не
  ходит в `$DSH_HOME` и ничего не пишет.
- **`integrations/dsh` — не навык**: у него нет `SKILL.md` и frontmatter,
  установка в `~/.config/opencode/skill/` для него не применяется.

## Через интерфейс вместо файла

То же самое собирается в **Settings → Models** без правки YAML: карточка
создания провайдера пишет `providers.<route>` в настройки `llm-pi-ai` и
кладет ключ в managed-хранилище. Минус — список моделей вводится вручную, а
страница не даёт поставить `compat`; значение настроек хранится вне git и на
другой ПК не переносится. Файл удобнее, когда настройку надо повторить.

## Типовые ошибки

| Симптом | Причина | Что делать |
|---|---|---|
| `MISSING_CREDENTIAL` | нет env-переменной или ссылки в `.credentials.yaml` | задать ключ под именем из `apiKeyEnv` и перезапустить |
| Модели нет в селекторе | `agent-default-model` ссылается на чужой `provider`/`model` | сверить с ключом в `providers` и `id` модели |
| В селекторе лишние `wan*`, `qwen-audio-*` | модель не в явном списке не бывает; список пуст | заполнить `models` явно |
| Строка `llm-pi-ai` не применилась | `config` заменяется целиком или не совпал `id` | перенести запись целиком, проверить `id` |
| Path вроде `E:\...\plugin\lib\index.js` не грузится | абсолютный путь от другой машины | убрать такую запись, если плагин не нужен |
| `protocol is not configurable` | в `config` осталось лишнее поле | удалить поле, оставить `baseURL`, `apiKeyEnv`, `models` |

## Источники

- Платформа Qwen Cloud: <https://www.qwencloud.com/> — консоль и выдача ключа.
- Эндпоинт Token Plan: `https://token-plan.maas.qwencloudapi.com/compatible-mode/v1` — проверен запросом 2026-11-11 (ответ `401 InvalidApiKey` без ключа).
- Локальная установка dsh 0.2.2-rc.1: `$DSH_HOME/profiles/desktop/` и документация пакетов `dsh-app-boot` (`Profiles`, `PROFILE_TEMPLATES`, `initProfile`) и `dsh-llm-pi-ai` (`Configure provider routes`) в составе установки — прочитано 2026-11-11.