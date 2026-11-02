import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
  buildReportModel,
  computeActivity,
  normalizeSnapshot,
  validateAnalysis,
} from "../src/analysis.js";
import { inferActions, preflightTask } from "../src/permissions.js";
import { renderReport } from "../src/report.js";
import {
  loadExclusions,
  loadProjects,
  loadTasks,
  renderExclusions,
  renderProjects,
  renderTasks,
  saveExclusions,
  saveProjects,
  saveTasks,
  statePaths,
} from "../src/state.js";

const fixture = JSON.parse(await readFile(new URL("./fixtures/snapshot.json", import.meta.url), "utf8"));
const analysis = JSON.parse(await readFile(new URL("./fixtures/analysis.json", import.meta.url), "utf8"));

test("snapshot normalizes ids and keeps coverage", () => {
  const snapshot = normalizeSnapshot(fixture);
  assert.equal(snapshot.chats.length, 5);
  assert.equal(snapshot.chats[0].id, "1");
  assert.equal(snapshot.chats[0].messages.length, 6);
  assert.equal(snapshot.chats[0].coverage.ok, true);
  assert.equal(snapshot.account.scopes.includes("messages:read"), true);
});

test("activity counts messages, excludes bots and excluded users", () => {
  const snapshot = normalizeSnapshot(fixture);
  const activity = computeActivity(snapshot, {
    inactivityDays: 2,
    exclusions: [{ userId: "104", name: "Глеб Орлов", reason: "отпуск" }],
  });
  const byName = Object.fromEntries(activity.participants.map((person) => [person.name, person]));
  assert.equal(byName["Анна Петрова"].count, 4);
  assert.equal(byName["Борис Смирнов"].count, 4);
  assert.equal(byName["Вера Ким"].count, 2);
  assert.equal(byName["Дарья Волкова"].count, 0);
  assert.equal(byName["Глеб Орлов"].excluded, true);
  assert.equal(byName["Глеб Орлов"].inactive, true);
  assert.equal(byName["Вера Ким"].inactive, true);
  assert.equal(byName["Анна Петрова"].inactive, false);
  assert.equal(activity.stats.excluded, 1);
  assert.equal(activity.visible.some((person) => person.name === "Релиз-бот"), false);
  assert.equal(activity.visible.some((person) => person.name === "Глеб Орлов"), false);
  assert.equal(activity.stats.visible, 4);
});

test("analysis validation keeps evidence and marks missing projects unknown", () => {
  const snapshot = normalizeSnapshot(fixture);
  const validated = validateAnalysis(analysis, snapshot, [
    { chatId: "1", project: "Платформа" },
    { chatId: "2", project: "Мобильное приложение" },
  ]);
  assert.equal(validated.projects.length, 5);
  const platform = validated.projects.find((project) => project.chatId === "1");
  const mobile = validated.projects.find((project) => project.chatId === "2");
  const personal = validated.projects.find((project) => project.chatId === "4");
  assert.equal(platform.status, "on_track");
  assert.equal(platform.blockers.length, 0);
  assert.equal(platform.verified, true);
  assert.equal(mobile.status, "blocked");
  assert.equal(mobile.blockers[0].verified, true);
  assert.equal(personal.status, "unknown");
  assert.equal(personal.verified, false);
  assert.equal(validated.quality, "medium");
});

test("analysis rejects invented evidence ids", () => {
  const snapshot = normalizeSnapshot(fixture);
  const broken = {
    ...analysis,
    projects: [
      {
        chatId: "1",
        status: "on_track",
        progress: "Всё хорошо",
        blockers: [{ text: "Нет", evidenceMessageIds: ["does-not-exist"] }],
        evidenceMessageIds: ["nope"],
        confidence: "high",
      },
    ],
  };
  const validated = validateAnalysis(broken, snapshot);
  const project = validated.projects.find((item) => item.chatId === "1");
  assert.equal(project.verified, false);
  assert.ok(validated.warnings.some((warning) => warning.includes("не найдены")));
});

test("inferred task actions include write operations from the description", () => {
  assert.deepEqual(
    inferActions("Найди блокеры и отправь дайджест в канал", "digest").sort(),
    ["read_messages", "send_message"].sort(),
  );
  assert.deepEqual(inferActions("Покажи активность участников", "activity").sort(), [
    "read_members",
    "read_messages",
  ]);
});

test("preflight blocks missing scopes, channel role and unverified owner", () => {
  const snapshot = normalizeSnapshot(fixture);
  const read = preflightTask({
    snapshot,
    channelId: "1",
    actions: ["read_messages"],
    capabilities: { scopes: ["chats:read", "messages:read"], role: "user", accountId: "101" },
  });
  assert.equal(read.ok, true);

  const sendWithoutScope = preflightTask({
    snapshot,
    channelId: "1",
    actions: ["send_message"],
    capabilities: { scopes: ["chats:read", "messages:read"], role: "user", accountId: "101" },
  });
  assert.equal(sendWithoutScope.ok, false);
  assert.ok(sendWithoutScope.missingScopes.includes("messages:create"));

  const subscriber = preflightTask({
    snapshot,
    channelId: "2",
    actions: ["send_message"],
    capabilities: {
      scopes: ["chats:read", "messages:read", "messages:create"],
      role: "user",
      accountId: "101",
      chatRoles: { "2": "member" },
    },
  });
  assert.equal(subscriber.ok, false);
  assert.ok(subscriber.checks.some((check) => check.code === "channel_role_forbidden"));

  const editor = preflightTask({
    snapshot,
    channelId: "2",
    actions: ["send_message"],
    capabilities: {
      scopes: ["chats:read", "messages:read", "messages:create"],
      role: "user",
      accountId: "101",
      chatRoles: { "2": "editor" },
    },
  });
  assert.equal(editor.ok, true);

  const exportUnknownPlan = preflightTask({
    snapshot,
    channelId: "2",
    actions: ["export_messages"],
    capabilities: {
      scopes: ["chat_exports:read", "chat_exports:write"],
      role: "admin",
      accountId: "101",
      plan: "unknown",
      isOwner: true,
    },
  });
  assert.equal(exportUnknownPlan.ok, false);
  assert.ok(exportUnknownPlan.checks.some((check) => check.code === "plan_unverified"));
});

test("state MD files round-trip", async () => {
  const root = await mkdtemp(join(tmpdir(), "pachca-state-"));
  try {
    const paths = statePaths(root, ".pachca");
    const exclusions = [
      { userId: "104", name: "Глеб Орлов", reason: "отпуск", addedAt: "2026-11-02" },
    ];
    const projects = [{ chatId: "1", project: "Платформа", aliases: ["core"], updatedAt: "2026-11-02" }];
    const tasks = [
      {
        id: "T-20261102-abcde",
        title: "Мониторинг блокеров",
        channelId: "1",
        channel: "Платформа",
        kind: "monitor",
        actions: ["read_messages"],
        status: "active",
        created: "2026-11-02",
        lastCheck: "2026-11-02T12:00:00.000Z",
        lastRun: "",
        check: "ok",
        checkReason: "Права подтверждены",
        keywords: ["блокер", "/срыв/i"],
        prompt: "Строка 1\nСтрока 2",
        result: "",
        resultPath: "",
        permissionSource: "snapshot:token-info",
      },
    ];
    assert.ok(renderExclusions(exclusions).includes("| 104 |"));
    assert.ok(renderProjects(projects).includes("| 1 | Платформа |"));
    assert.ok(renderTasks(tasks).includes("- prompt: |"));
    await saveExclusions(paths, exclusions);
    await saveProjects(paths, projects);
    await saveTasks(paths, tasks);
    assert.deepEqual(await loadExclusions(paths), exclusions);
    assert.deepEqual(await loadProjects(paths), projects);
    const loaded = await loadTasks(paths);
    assert.equal(loaded.length, 1);
    assert.equal(loaded[0].prompt, "Строка 1\nСтрока 2");
    assert.deepEqual(loaded[0].keywords, ["блокер", "/срыв/i"]);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("report is standalone and contains required sections", () => {
  const snapshot = normalizeSnapshot(fixture);
  const model = buildReportModel({
    snapshot,
    analysis,
    exclusions: [{ userId: "104", name: "Глеб Орлов", reason: "отпуск", addedAt: "2026-11-02" }],
    tasks: [
      {
        id: "T-1",
        title: "Мониторинг",
        channel: "Платформа",
        channelId: "1",
        kind: "monitor",
        actions: ["read_messages"],
        status: "active",
        check: "ok",
        checkReason: "Права подтверждены",
        lastRun: "",
      },
    ],
    projectsMapping: [{ chatId: "1", project: "Платформа" }],
    inactivityDays: 2,
  });
  const html = renderReport(model);
  assert.match(html, /id="projects"/);
  assert.match(html, /id="activity"/);
  assert.match(html, /id="tasks"/);
  assert.match(html, /id="report-data"/);
  assert.match(html, /Глеб Орлов/);
  assert.match(html, /Исключены из диаграммы/);
  assert.match(html, /<p class="empty">—<\/p>/);
  assert.match(html, /data-by-chat=/);
  assert.doesNotMatch(html, /<script[^>]+src=/i);
  assert.doesNotMatch(html, /<link[^>]+rel=["']stylesheet/i);
  assert.doesNotMatch(html, /@import/i);
  assert.doesNotMatch(html, /fetch\s*\(/);
  assert.doesNotMatch(html, /XMLHttpRequest/);
  assert.doesNotMatch(html, /<img[^>]+src=["']https?:/i);
});

test("report escapes message text and task text", () => {
  const snapshot = normalizeSnapshot(fixture);
  snapshot.chats[0].messages[0].content = `<script>alert(1)</script> & "quotes"`;
  const model = buildReportModel({
    snapshot,
    analysis: {
      projects: [
        {
          chatId: "1",
          status: "on_track",
          progress: `<img src=x onerror=alert(1)>`,
          blockers: [],
          evidenceMessageIds: ["m1"],
          confidence: "high",
        },
      ],
    },
  });
  const html = renderReport(model);
  assert.doesNotMatch(html, /<script>alert\(1\)<\/script>/);
  assert.doesNotMatch(html, /<img src=x/);
  assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
});