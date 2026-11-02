# Установка opencode-supermemory

Плагин постоянной памяти для OpenCode: профиль пользователя, знания проекта,
поиск по памяти, автосохранение и индексация кодовой базы.

## 1. Требования

| Компонент | Условие |
|---|---|
| OpenCode | 2.x с поддержкой `plugins` |
| Bun | для `bunx` |
| Аккаунт Supermemory | OAuth или `SUPERMEMORY_API_KEY` |
| Сеть | API `api.supermemory.ai` или свой `baseUrl` |

## 2. Установка

```bash
bunx opencode-supermemory@latest install --no-tui
bunx opencode-supermemory@latest login
bunx opencode-supermemory@latest status
```

Для headless-среды вместо `login`:

```bash
export SUPERMEMORY_API_KEY="sm_..."
```

или создайте `~/.config/opencode/supermemory.jsonc`:

```jsonc
{
  "apiKey": "sm_..."
}
```

## 3. Конфигурация OpenCode

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": ["opencode-supermemory"],
  "permission": {
    "supermemory_recall": "allow"
  }
}
```

Для OpenCode V1 используется ключ `plugin`, для OpenCode 2 — `plugins`.
Установщик добавляет оба варианта.

## 4. Проверка

1. Перезапустите OpenCode.
2. Выполните `bunx opencode-supermemory@latest status`.
3. В сессии проверьте команды `/supermemory-status` и `/supermemory-index`.
4. Убедитесь, что `opencode plugin list` показывает `supermemory`.

## 5. Что получает агент

- контекст профиля и знаний проекта в начале сессии;
- `supermemory` tool: `add`, `search`, `profile`, `list`, `forget`, `help`;
- автоматическое сохранение завершённых turn'ов;
- recall по ключевым словам и смысловому запросу;
- индексацию кодовой базы через `/supermemory-index`.

## 6. Безопасность

- Содержимое в `<private>...</private>` не сохраняется.
- OAuth-credentials лежат в `~/.supermemory-opencode/credentials.json`;
  не коммитьте их.
- API-ключ храните в переменной окружения или локальном конфиге вне Git.
- Память может содержать чувствительные данные проекта: проверяйте scope
  `user` / `project`.

## 7. Ограничения

- Нужен аккаунт Supermemory и сеть; без них recall недоступен.
- Плагин сторонний; поведение и API могут меняться между версиями.
- В README заявлена MIT, но отдельного `LICENSE` в корне репозитория нет.
  Перед публичным распространением проверьте условия у автора.

Источник: <https://github.com/supermemoryai/opencode-supermemory>