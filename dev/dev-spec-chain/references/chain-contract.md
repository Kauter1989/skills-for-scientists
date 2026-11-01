# Контракт сгенерированной цепочки

Нормативный документ `dev-spec-chain`. Определяет, что создаётся в целевом
репозитории и как это проверяется.

## 1. Расположение

```
<repo>/
├── .opencode/
│   ├── spec-chain.yml
│   └── skill/
│       ├── dev-specify/SKILL.md
│       ├── dev-clarify/SKILL.md
│       ├── dev-plan/SKILL.md
│       ├── dev-tasks/SKILL.md
│       ├── dev-analyze/SKILL.md
│       └── dev-implement/SKILL.md
├── docs/features/<slug>/
│   ├── overview.md
│   ├── spec.md
│   ├── plan.md
│   └── tasks.md
└── spec-chain-report.md
```

`<slug>` — конкретная фича. Сгенерированные навыки не хранятся в этой
библиотеке.

## 2. Манифест

```yaml
version: 1
repo: example-service
profile:
  mode: brownfield
  change_size: medium
  roles: small
  compliance: none
  stack: python
  approval: user
approach: openspec
gates:
  strict: standard
  tests_first: true
stages:
  - id: specify
    title: Specify
    skill: dev-specify
    input: docs/features/<slug>/overview.md
    output: docs/features/<slug>/spec.md
    gate: spec approved
```

Поля:

- `version` — 1;
- `approach` — `spec-kit`, `openspec`, `bmad`, `lightweight`;
- `stages` — непустой список с уникальными `id`;
- `gates.tests_first` — всегда `true`;
- у каждой стадии есть `skill`, `input`, `output`, `gate`.

## 3. Сгенерированный навык

Каждый stage-навык содержит:

- frontmatter `name`, совпадающий с каталогом;
- `description` с триггерами;
- разделы «Когда применять», «Когда не применять», «Вход», «Процедура»,
  «Выход», «Доказательства», «Границы», «Типовые ошибки», «QA»;
- `examples/README.md` с примером входа и выхода стадии.

## 4. Порядок стадий

- `specify` раньше `clarify`;
- `clarify` раньше `plan`;
- `plan` раньше `tasks`;
- `tasks` раньше `analyze`;
- `analyze` раньше `implement`, если implement включён;
- `implement` не запускается, пока не пройден analyze.

## 5. Проверка

```bash
python check_spec_chain.py --root /path/to/repo
python check_spec_chain.py --root /path/to/repo --json
```

Проверяется:

- манифест и его поля;
- наличие каждого stage-навыка;
- совпадение `name` и каталога;
- обязательные разделы;
- `examples/`;
- порядок стадий;
- `tests_first: true`.

Смысл стадий и качество артефактов проверяются на ревью, а не скриптом.

## 6. Обновление

- изменение профиля → новый `spec-chain-plan.html` и `approved`;
- изменение подхода → перегенерация chain;
- ручные правки сгенерированных навыков фиксируются в manifest или
  теряются при следующей генерации;
- `--force` перезаписывает существующие файлы, поэтому применяется только
  после решения пользователя.