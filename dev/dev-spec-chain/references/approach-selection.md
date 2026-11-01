# Выбор подхода

Нормативный документ `dev-spec-chain`. Определяет, какой подход положить в
основу сгенерированной цепочки.

## 1. Профиль репозитория

| Вопрос | Варианты | Зачем |
|---|---|---|
| Какой репозиторий? | greenfield / brownfield | greenfield требует полной спецификации, brownfield — изменений |
| Размер изменений | small / medium / large | глубина церемонии |
| Роли | small / enterprise | нужны ли story-файлы и роли |
| Compliance | none / audit | нужны ли строгие гейты и evidence |
| Стек | python / js / другой | шаблоны команд и тестов |
| Approval | user / autonomous | кто утверждает стадии |
| Строгость | light / standard / strict | набор стадий и гейтов |

## 2. Матрица

| Профиль | Подход | Стадии |
|---|---|---|
| Greenfield, стабильные требования | `spec-kit` | specify, clarify, plan, tasks, analyze, implement |
| Brownfield, изменения в коде | `openspec` | specify, clarify, plan, tasks, analyze |
| Много ролей, enterprise, audit | `bmad` | specify, clarify, plan, tasks, analyze, implement |
| Малая команда, малый change size | `lightweight` | specify, plan, tasks, analyze |

Правила:

- **Greenfield** — сначала полная спецификация, потом план и задачи.
- **Brownfield** — spec deltas: что меняется, что остаётся, какие
  инварианты; не переписывать всю систему.
- **Enterprise/audit** — роли, story-файлы, evidence для каждого гейта.
- **Lightweight** — минимум стадий, но traceability и тесты до кода
  сохраняются.

## 3. Что берём из аналогов

| Источник | Что берём | Что не берём |
|---|---|---|
| spec-kit | полную цепочку и конституцию | жёсткую привязку к шаблонам |
| OpenSpec | spec deltas и изменения | лишнюю церемонию |
| BMAD | story-файлы и роли | тяжёлую ролевую модель |
| superpowers | дизайн до кода | процесс целиком |

## 4. Гейты

- `light`: specify approved, plan approved, tasks traceable.
- `standard`: плюс clarify закрыт и analyze пройден.
- `strict`: плюс implement только после analyze, полный green прогон и
  evidence для каждого гейта.

## 5. Ошибки выбора

- brownfield через полный spec-kit «с нуля»;
- greenfield через одни spec deltas;
- enterprise без ролей и evidence;
- lightweight без traceability;
- выбор подхода без вопросов пользователю;
- генерация implement там, где команда ещё не готова к TDD.