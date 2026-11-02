# Pachca tasks

Задачи по каналам. Плагин сохраняет задачу только после preflight
прав. Перед запуском проверка повторяется. Редактируйте текст после
`prompt: |` с сохранением отступа в четыре пробела.

## T-20261102-a1b2c · Мониторинг блокеров в Мобильном
- channel_id: 2
- channel: Мобильное приложение
- kind: monitor
- actions: read_messages
- status: active
- created: 2026-11-02
- last_check: 2026-11-02T12:00:00.000Z
- last_run: 
- check: ok
- check_reason: Права подтверждены
- keywords: блокер, ключ, staging
- permission_source: rest:token-info

## T-20261102-d3e4f · Экспорт истории релизов
- channel_id: 5
- channel: Архив запуска
- kind: custom
- actions: export_messages
- status: disabled
- created: 2026-11-02
- last_check: 2026-11-02T12:00:00.000Z
- last_run: 
- check: blocked
- check_reason: Нужен тариф «Корпорация» и роль Владельца; API не подтверждает владельца
- keywords: 
- permission_source: snapshot:token-info
- prompt: Собрать все решения по запуску и сохранить в архив.
