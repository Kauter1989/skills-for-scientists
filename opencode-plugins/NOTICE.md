# Источники и лицензии

Папка `opencode-plugins` содержит локальные плагины и инструкции для внешних
плагинов и MCP-интеграций. Ниже — происхождение и статус лицензий.

| Компонент | Источник | Лицензия | Примечание |
|---|---|---|---|
| `md-viewer/` | локальный проект `opencode-md-plugin` | не заявлена | в исходном каталоге не было `LICENSE` |
| `pachca/` | оригинальный код для этой библиотеки; контракты — официальная документация Pachca и OpenCode | Apache 2.0 (репозиторий) | код не вендорит `pachca/openapi`; используются только публичные контракты и идеи |
| `supermemory/` | `supermemoryai/opencode-supermemory` | MIT по README | отдельного `LICENSE` в корне нет; исходники не вендорятся |
| `freecad-mcp/` | `neka-nat/freecad-mcp` | MIT | внешняя MCP-интеграция; исходники не вендорятся |
| `cae-mesh-mcp/` | `tangency-labs/fieldcraft` | Apache-2.0 | временный upstream; исходники не вендорятся |
| `ferrum/` | `Kauter1989/ferrum` | MIT OR Apache-2.0 | MCP + навык; исходники не вендорятся |
| `@opencode/plugin` | npm-зависимость плагина | проверяется в пакете | версия `2.2.1` закреплена в `package.json` и `bun.lock` |
| `solid-js`, `vite`, `vite-plugin-solid`, `typescript` | npm dev-зависимости | у каждого пакета своя | в репозиторий не вендорятся |

## Что это значит

Компонент без заявленной лицензии нельзя публично распространять без
разрешения автора. Если репозиторий публичный, перед релизом:

1. добавьте `LICENSE` в `md-viewer` или в корень с совместимой лицензией;
2. получите разрешение автора, если код не ваш;
3. сохраните ссылки на источники и дату снимка.

Зависимости из npm распространяются по своим лицензиям; они не входят в
репозиторий и устанавливаются из registry.

## Снимок

- дата: `2026-11-03`;
- версия `@opencode/plugin` в `md-viewer` и `pachca`: `2.2.1`;
- Pachca MCP: `https://mcp.pachca.com/mcp`, документация `https://dev.pachca.com`;
- supermemory: `https://github.com/supermemoryai/opencode-supermemory`;
- freecad-mcp: `https://github.com/neka-nat/freecad-mcp`;
- cae-mesh-mcp: `https://github.com/tangency-labs/fieldcraft` (temporary);
- ferrum: `https://github.com/Kauter1989/ferrum`.

## Секреты

В папке нет `service.json`, `auth.json`, токенов и ключей. Если вы добавляете
локальный конфиг с секретами, держите его вне репозитория.