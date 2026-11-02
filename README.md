# opencode-skills

A personal skill library for OpenCode: software development, research and
reporting. Each skill is a separate directory with `SKILL.md` and, when
needed, references, scripts and templates. A skill produces a verifiable
artifact, not just text in a chat.

Library map by process block: [`docs/skills-map.html`](docs/skills-map.html).
Development plan and queue: [`docs/skills-development-plan.html`](docs/skills-development-plan.html).
Mandatory rules for agents: [`AGENTS.md`](AGENTS.md).

No new skill is written without research into analogs and scientific sources.
Priority order: **harness → dev → science → integrations → reports**.

## What is inside

| Skill | Folder | Purpose | Artifact |
|---|---|---|---|
| [`harness-skill-template`](harness/harness-skill-template/SKILL.md) | `harness/` | Skill contract and scaffold: frontmatter, required sections, template, generator and validator | `SKILL.md`, validator report |
| [`harness-rule-to-mechanism`](harness/harness-rule-to-mechanism/SKILL.md) | `harness/` | Turns a rule into an executable check: hook, lint, test, policy or CI, with a registry and test evidence | check, `docs/rules/registry.yml` |
| [`harness-skill-audit`](harness/harness-skill-audit/SKILL.md) | `harness/` | Library audit: structure, duplicate triggers, artifacts, links and domain coverage | `docs/audits/<date>.html` and `.json` |
| [`harness-init`](harness/harness-init/SKILL.md) | `harness/` | Meta-skill bootstrap: survey, starter skills, profile, AGENTS.md, hooks, CI and HTML workflow approval | `bootstrap-plan.html`, `profile.yml` |
| [`dev-feature-start`](dev/dev-feature-start/SKILL.md) | `dev/` | Feature start: branch, brief with user stories, behavioral, functional and unit tests when coverage rules apply, red/green gates | `overview.md`, branch |
| [`dev-spec-chain`](dev/dev-spec-chain/SKILL.md) | `dev/` | Meta-skill: survey, choose spec-kit/OpenSpec/BMAD/lightweight and generate a repository-specific stage-skill chain | `.opencode/spec-chain.yml`, stage skills |
| [`dev-bug-processing`](dev/dev-bug-processing/SKILL.md) | `dev/` | Meta-skill: survey, choose a debugging approach and generate `dev-bug-process` with reproducibility invariants | `.opencode/bug-processing.yml`, `dev-bug-process` |
| [`dev-pr-report-html`](dev/dev-pr-report-html/SKILL.md) | `dev/` | HTML report for feature or milestone changes: six agent-development metrics, evidence and decisions | standalone `report.html` |
| [`pptx-report`](reports/pptx-report/SKILL.md) | `reports/` | Rigorous PPTX presentations and analytical reports: research talks, project reports and management analytics | `deck.pptx`, PNG previews |
| [`pachca-report`](integrations/pachca-report/SKILL.md) | `integrations/` | Pachca chats to an interactive HTML report: project progress and blockers, participant activity with >2-day silence, MD exclusions, and permission-checked channel tasks | standalone `report.html`, `.pachca/*.md` |

### Meta-skills

A meta-skill does not hard-code a process. It surveys the context, selects an
approach and generates artifacts for a specific repository or field.

| Skill | What it surveys | What it generates |
|---|---|---|
| `harness-init` | repository, stack, team | scaffold, AGENTS.md, hooks, CI, workflow |
| `dev-spec-chain` | greenfield/brownfield, roles, stack | stage-skill chain and manifest |
| `dev-bug-processing` | stack, tests, tracker, environment | `dev-bug-process` and manifest |

Meta-skill candidates: `dev-regression-guard`, `dev-verification-live`,
`dev-milestone-audit`, `dev-ship`, `sci-experiment-plan`, `sci-stats-plan`,
`sci-stats-report`, `sci-literature-review`, `sci-repro-run`,
`dev-postmortem`, `harness-analyze-codebase`. Full breakdown and filters are
in [`docs/skills-map.html`](docs/skills-map.html#meta).

Deferred skills not implemented in this cycle:

- `harness-skill-eval` — `deferred`: evaluating a skill on real tasks.
  Research and review are kept in `docs/research/` and `docs/reviews/`.

`dev-pr-report-html` calculates Feature Token Budget, Architecture Drift
Score, Cognitive Load Index, Agent Iteration Rate, Hallucination Risk and
Context Window Utilization. The page needs no network and opens from disk.
Example: [`dev/dev-pr-report-html/examples/example-report.html`](dev/dev-pr-report-html/examples/example-report.html).

`pachca-report` connects to Pachca through the official MCP server or REST,
collects all chats where the user is a member, and writes an interactive
standalone HTML report. Project progress and blockers must cite message IDs;
participants silent for more than two days are highlighted; exclusions and
saved channel tasks live in human-editable Markdown. Saved tasks are refused
until scopes, role, plan and chat access pass a preflight.
Example: [`integrations/pachca-report/examples/example-report.html`](integrations/pachca-report/examples/example-report.html).

## Domains and prefixes

A skill name starts with its domain prefix; the folder defines the area:

| Folder | Name prefix | Domain |
|---|---|---|
| `dev/` | `dev-` | development: features, defects, checks, audit, release |
| `sci/` | `sci-` | research: hypotheses, experiments, statistics, data |
| `harness/` | `harness-` | harness-wide: initialization, rules, the skills themselves |
| `reports/` | no prefix | reporting and presentations: `pptx-report` |
| `integrations/` | `integrations-` for new skills; `pachca-report` keeps its name | external environments and APIs: Pachca, messengers, service connectors |

The prefix makes the domain visible after installation into a flat skill
directory (`~/.config/opencode/skill/`). New integration skills use
`integrations-`; `pachca-report` keeps its historical name. The domain folder is only repository
organization; installation copies the specific skill, and its directory name
must match the skill name.

## Installation

OpenCode discovers skills in two locations:

- personal: `~/.config/opencode/skill/<name>/SKILL.md`;
- project: `<repo>/.opencode/skill/<name>/SKILL.md`.

Copy the whole skill directory — `SKILL.md`, `references/`, `scripts/`,
`templates/`, `examples/`:

```powershell
# Windows: harness skill
Copy-Item -Recurse .\harness\harness-skill-template "$env:USERPROFILE\.config\opencode\skill\harness-skill-template"

# Windows: development skill
Copy-Item -Recurse .\dev\dev-pr-report-html "$env:USERPROFILE\.config\opencode\skill\dev-pr-report-html"

# Windows: reporting skill
Copy-Item -Recurse .\reports\pptx-report "$env:USERPROFILE\.config\opencode\skill\pptx-report"

# Windows: Pachca integration skill
Copy-Item -Recurse .\integrations\pachca-report "$env:USERPROFILE\.config\opencode\skill\pachca-report"
```

```bash
# Linux/macOS
cp -r harness/harness-skill-template ~/.config/opencode/skill/
cp -r dev/dev-pr-report-html ~/.config/opencode/skill/
cp -r reports/pptx-report ~/.config/opencode/skill/
cp -r integrations/pachca-report ~/.config/opencode/skill/
```

After installation, verify that the `skill` tool finds the skill. Before
installation, `SKILL.md` and `references/` can be read directly from this
repository.

## OpenCode plugins

`opencode-plugins/` contains the source of the OpenCode Markdown panel and the
Pachca plugin, plus installation instructions for another machine.

- overview: [`opencode-plugins/README.md`](opencode-plugins/README.md);
- installation: [`opencode-plugins/INSTALL.md`](opencode-plugins/INSTALL.md);
- Pachca plugin: [`opencode-plugins/pachca/README.md`](opencode-plugins/pachca/README.md),
  [`opencode-plugins/pachca/INSTALL.md`](opencode-plugins/pachca/INSTALL.md);
- configuration without secrets: [`opencode-plugins/config/`](opencode-plugins/config/);
- licenses and provenance: [`opencode-plugins/NOTICE.md`](opencode-plugins/NOTICE.md).

Secrets, `auth.json` and a local `service.json` are not part of the repository.

## Structure

```
skills/
├── AGENTS.md                  mandatory development rules
├── docs/
│   ├── skills-map.html        skill and process-block map
│   ├── skills-development-plan.html  plan and queue
│   ├── research/              research ledgers by skill
│   ├── reviews/               HTML reviews by skill
│   ├── audits/                HTML/JSON audit reports
│   ├── rules/                 registry.yml — rule registry
│   └── templates/
│       ├── skill-research.md  research ledger
│       └── skill-review.html  skill HTML review
├── dev/                       development, prefix dev-
│   ├── dev-feature-start/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   ├── scripts/
│   │   ├── templates/
│   │   └── examples/
│   ├── dev-spec-chain/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   ├── scripts/
│   │   ├── templates/
│   │   └── examples/
│   ├── dev-bug-processing/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   ├── scripts/
│   │   ├── templates/
│   │   └── examples/
│   └── dev-pr-report-html/
│       ├── SKILL.md
│       ├── references/
│       ├── scripts/
│       ├── templates/
│       └── examples/
├── sci/                       research, prefix sci- (currently empty)
├── harness/                   harness, prefix harness-
│   ├── harness-skill-template/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   ├── scripts/
│   │   ├── templates/
│   │   └── examples/
│   ├── harness-rule-to-mechanism/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   ├── scripts/
│   │   ├── templates/
│   │   └── examples/
│   ├── harness-skill-audit/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   ├── scripts/
│   │   ├── templates/
│   │   └── examples/
│   └── harness-init/
│       ├── SKILL.md
│       ├── references/
│       ├── scripts/
│       ├── templates/
│       └── examples/
├── opencode-plugins/          OpenCode plugins and instructions
│   ├── README.md
│   ├── INSTALL.md
│   ├── NOTICE.md
│   ├── md-viewer/
│   ├── pachca/
│   │   ├── src/               plugin: MCP, API, analysis, HTML, tasks
│   │   ├── test/              unit + mock HTTP tests
│   │   ├── examples/
│   │   ├── README.md
│   │   └── INSTALL.md
│   └── config/
├── integrations/              external environments and APIs
│   └── pachca-report/
│       ├── SKILL.md
│       ├── examples/
│       ├── references/
│       ├── scripts/
│       └── templates/
├── reports/                   reporting, no prefix
│   └── pptx-report/
│       ├── SKILL.md
│       ├── examples/
│       ├── references/
│       ├── scripts/
│       └── templates/
└── LICENSE
```

## How a skill is developed

Every skill goes through five gates defined in `AGENTS.md`:

```
Research → Review → Implementation → Verification → PR
```

1. **Research.** At least three GitHub analogs and two scientific or official
   sources. Output: `docs/research/<skill>.md`.
2. **Review.** A standalone HTML plan based on
   `docs/templates/skill-review.html`. No code is written without `approved`
   status.
3. **Implementation.** `SKILL.md`, `references/`, `scripts/`,
   `templates/`, `examples/`.
4. **Verification.** The example reproduces, scripts run, HTML opens without
   network access, the map and README are updated.
5. **PR.** The branch is pushed, the PR is open, and the description links the
   research ledger, review HTML and validator output. Merging without a PR is
   forbidden.

Library rules:

1. The domain is defined by the folder and name prefix: `dev/` + `dev-`,
   `sci/` + `sci-`, `harness/` + `harness-`. Reporting skills live in
   `reports/`.
2. Skill directories are flat inside a domain: one directory, one skill.
3. The frontmatter `description` contains Russian and English triggers: a
   skill must be found by a task description, not by its file name.
4. If a skill promises a number, that number has a formula, a source and a
   data-quality level.
5. If a skill changes a repository, it has a check and a cleanup path.
6. A new skill does not duplicate an existing one: first check the map and
   neighboring triggers.

## Verification

```bash
# build the demo HTML report
cd dev/dev-pr-report-html
python scripts/build_report.py --example -o examples/example-report.html --strict

# collect metrics from Git
python scripts/collect_metrics.py --repo . --from HEAD~1 --to HEAD --out metrics.json

# Pachca plugin and example
cd opencode-plugins/pachca
node test/run-tests.mjs
node test/api.test.mjs
node --experimental-loader ./test/loader.mjs test/plugin.test.mjs
node test/build-example.mjs
cd ../../integrations/pachca-report
python scripts/check_report.py examples/example-report.html
python scripts/validate_analysis.py examples/example-snapshot.json examples/example-analysis.json
```

Scripts use only the Python 3.9+ standard library. The Pachca plugin tests use
Node 20+ and a local mock HTTP server.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).