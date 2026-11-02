import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import plugin from "../src/index.js";
import { saveSnapshot, statePaths } from "../src/state.js";

const snapshot = JSON.parse(await readFile(new URL("./fixtures/snapshot.json", import.meta.url), "utf8"));
const analysis = JSON.parse(await readFile(new URL("./fixtures/analysis.json", import.meta.url), "utf8"));

async function harness() {
  const directory = await mkdtemp(join(tmpdir(), "pachca-plugin-"));
  const tools = new Map();
  const ctx = {
    location: { directory },
    options: { registerMcp: false, stateDir: ".pachca" },
    mcp: {
      list: async () => [],
      transform: async (callback) => {
        callback({ get: () => undefined, set: () => {}, update: () => {}, remove: () => {}, list: () => [] });
      },
    },
    tool: {
      transform: async (callback) => {
        const editor = {
          namespace: () => {},
          add: (tool) => tools.set(tool.name, tool),
          get: (name) => tools.get(name),
          list: () => [...tools.values()],
          update: () => {},
          remove: () => {},
        };
        callback(editor);
      },
    },
  };
  await plugin.setup(ctx);
  return {
    directory,
    tools,
    call: (name, input = {}) => {
      const tool = tools.get(name);
      assert.ok(tool, `tool ${name} is registered`);
      return tool.execute(input, { signal: new AbortController().signal, sessionID: "ses_test" });
    },
    async cleanup() {
      await rm(directory, { recursive: true, force: true });
    },
  };
}

test("plugin registers six tools and renders an end-to-end report", async () => {
  const h = await harness();
  try {
    assert.equal(h.tools.size, 6);
    const status = JSON.parse((await h.call("status", {})).content);
    assert.equal(status.ok, true);
    assert.equal(status.mcp.configured, false);

    const paths = statePaths(h.directory, ".pachca");
    await saveSnapshot(paths, snapshot);

    const report = JSON.parse(
      (
        await h.call("report", {
          snapshot,
          analysis,
          output: "report.html",
          inactivityDays: 2,
          title: "Тестовый отчёт",
        })
      ).content,
    );
    assert.equal(report.ok, true);
    assert.equal(report.summary.projects, 5);
    const html = await readFile(join(h.directory, "report.html"), "utf8");
    assert.match(html, /Тестовый отчёт/);
    assert.match(html, /Мобильное приложение/);

    const added = JSON.parse(
      (
        await h.call("exclusions", {
          action: "add",
          userId: "104",
          name: "Глеб Орлов",
          reason: "отпуск",
        })
      ).content,
    );
    assert.equal(added.ok, true);
    const list = JSON.parse((await h.call("exclusions", { action: "list" })).content);
    assert.equal(list.exclusions.length, 1);

    const project = JSON.parse(
      (
        await h.call("projects", {
          action: "set",
          chatId: "1",
          project: "Платформа",
          aliases: ["core"],
        })
      ).content,
    );
    assert.equal(project.ok, true);

    const task = JSON.parse(
      (
        await h.call("tasks", {
          action: "add",
          channel: "Платформа",
          title: "Мониторинг API",
          kind: "monitor",
          actions: ["read_messages"],
          keywords: ["API"],
          capabilities: {
            scopes: ["chats:read", "messages:read", "users:read"],
            role: "user",
            accountId: "101",
            source: "test",
          },
        })
      ).content,
    );
    assert.equal(task.ok, true);
    assert.equal(task.task.check, "ok");

    const run = JSON.parse(
      (await h.call("tasks", { action: "run", id: task.task.id })).content,
    );
    assert.equal(run.ok, true);
    assert.match(run.result, /API/);

    const blocked = JSON.parse(
      (
        await h.call("tasks", {
          action: "add",
          channel: "Платформа",
          title: "Отправка без права",
          kind: "custom",
          actions: ["send_message"],
          capabilities: {
            scopes: ["chats:read", "messages:read"],
            role: "user",
            accountId: "101",
            source: "test",
          },
        })
      ).content,
    );
    assert.equal(blocked.ok, false);
    assert.equal(blocked.code, "preflight_failed");
  } finally {
    await h.cleanup();
  }
});