# opencode-pachca

OpenCode V2 plugin for [Pachca](https://pachca.com): connects the official MCP
server and adds deterministic local tools for the `pachca-report` skill.

## What it does

1. Registers the Pachca MCP server `https://mcp.pachca.com/mcp` when it is not
   configured yet.
   - If `PACHCA_TOKEN` is set, uses a Bearer header and disables OAuth for that
     server.
   - Otherwise leaves OAuth enabled: open `/mcps` and sign in.
2. Adds local tools in the `pachca` namespace:
   - `pachca.status` — MCP state, token presence, scopes, state counts;
   - `pachca.collect` — reads all user chats, messages, threads and members
     through REST when `PACHCA_TOKEN` is available;
   - `pachca.report` — validates evidence and writes the standalone HTML;
   - `pachca.exclusions` — manages `.pachca/exclusions.md`;
   - `pachca.projects` — manages `.pachca/projects.md`;
   - `pachca.tasks` — saves and checks channel tasks, runs deterministic
     monitor/activity tasks or prepares LLM context.

The plugin never stores the token and never makes the HTML depend on network
resources.

## Install

See [`INSTALL.md`](INSTALL.md). Short version for a local checkout:

```bash
cd opencode-plugins/pachca
npm install   # or: bun install
```

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": [
    "C:/Users/<user>/opencode-skills/skills/opencode-plugins/pachca"
  ]
}
```

Use forward slashes. The path must point to the plugin directory, not to
`src/index.js`. Reload plugins or run `/reload`.

## Environment

| Variable | Required | Meaning |
|---|---|---|
| `PACHCA_TOKEN` | for REST tools | personal or bot token; never commit it |
| `PACHCA_MCP_URL` | no | override MCP URL (plugin option `mcpUrl`) |

Plugin options (object form):

```jsonc
{
  "plugins": [
    {
      "package": "C:/path/to/pachca",
      "options": {
        "mcpName": "pachca",
        "mcpUrl": "https://mcp.pachca.com/mcp",
        "tokenEnv": "PACHCA_TOKEN",
        "registerMcp": true,
        "stateDir": ".pachca"
      }
    }
  ]
}
```

## State

The plugin creates `.pachca/` in the session directory:

```
.pachca/
├── state.json
├── exclusions.md     # people removed from the activity chart
├── projects.md       # chat_id -> project mapping
├── tasks.md          # permission-checked saved tasks
├── snapshots/
├── analyses/
├── reports/
└── task-results/
```

Add `.pachca/` to `.gitignore` if the repository is public. Reports contain
message excerpts and names.

## Permission preflight

`pachca.tasks add` refuses to write `tasks.md` unless it can prove:

- the chat exists and is visible to the token;
- required scopes are present (`chats:read`, `messages:read`, ...);
- the chat is not archived for write actions;
- for a channel post, the user's chat role is owner/admin/editor, not a
  subscriber;
- for export, `plan: corporation` and `isOwner: true` are explicitly
  confirmed;
- the role in the chat is known; otherwise the task is blocked with
  `chat_role_unverified`.

The API does not expose the space plan or the Owner/Admin distinction. Those
must be supplied in `capabilities`; the plugin does not guess.

## Tools

```text
pachca.status { "deep": true }
pachca.collect { "days": 14 }
pachca.report { "analysisPath": ".pachca/analyses/analysis-....json" }
pachca.exclusions { "action": "add", "name": "Имя", "reason": "отпуск" }
pachca.projects { "action": "set", "chatId": "1", "project": "Платформа" }
pachca.tasks { "action": "add", "channel": "Канал", "kind": "monitor", "actions": ["read_messages"], "keywords": ["блокер"] }
pachca.tasks { "action": "check" }
pachca.tasks { "action": "run", "id": "T-..." }
```

In Code Mode the tools are under `tools.pachca.*`; direct MCP tools are under
the `pachca` server namespace.

## Verification

```bash
node test/run-tests.mjs
node test/api.test.mjs
node --experimental-loader ./test/loader.mjs test/plugin.test.mjs
node test/build-example.mjs
```

The tests use Node 20+ built-ins, a local mock HTTP server and a stub for
`@opencode/plugin`; they do not call Pachca. The example report is written to `examples/example-report.html` and
`reports/pachca-report/examples/example-report.html`.

## Boundaries

- Does not bypass scopes, roles or closed chats.
- Does not send or delete messages on its own.
- Does not evaluate people; activity is a signal, not a productivity score.
- Does not read plan or Owner status from an API that does not expose them.
- Does not render raw message HTML; all content is escaped.
- Does not use CDN, external fonts, images or network requests in the report.

## License

Apache License 2.0, same as the repository. See `../../LICENSE`.