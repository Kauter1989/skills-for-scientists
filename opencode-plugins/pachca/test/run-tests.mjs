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
const actions = JSON.parse(await readFile(new URL("./fixtures/actions.json", import.meta.url), "utf8"));

function reportData(html) {
  const match = html.match(/<script id="report-data" type="application\/json">([\s\S]*?)<\/script>/);
  assert.ok(match, "report-data script present");
  return JSON.parse(match[1]);
}

function sendButtonTags(html) {
  return html.match(/<button[^>]*class="send-btn"[^>]*data-chat[^>]*>/g) || [];
}

function readOnlyFixture() {
  return normalizeSnapshot({
    ...fixture,
    account: {
      ...fixture.account,
      scopes: fixture.account.scopes.filter((scope) => scope !== "messages:create"),
    },
  });
}

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
  assert.match(html, /id="summary"/);
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
  assert.doesNotMatch(html, /WebSocket/);
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

// ---- form v2.2 -----------------------------------------------------------

test("validateAnalysis passes progressPoints and blocker drafts, keeps backward compatibility", () => {
  const snapshot = normalizeSnapshot(fixture);
  const validated = validateAnalysis(analysis, snapshot);
  const platform = validated.projects.find((project) => project.chatId === "1");
  const mobile = validated.projects.find((project) => project.chatId === "2");
  assert.deepEqual(platform.progressPoints, [
    "API v2 готов примерно на 80%.",
    "Staging проверен: все проверки зелёные, релиз можно планировать.",
    "Осталась интеграция с биллингом.",
  ]);
  assert.ok(mobile.blockers[0].draft.includes("ключа от staging"));
  const legacy = validateAnalysis(
    {
      projects: [
        {
          chatId: "1",
          status: "on_track",
          progress: "Старый формат без новых полей",
          blockers: [{ text: "Блокер", evidenceMessageIds: ["m1"] }],
          evidenceMessageIds: ["m1"],
        },
      ],
    },
    snapshot,
  );
  const legacyProject = legacy.projects.find((project) => project.chatId === "1");
  assert.deepEqual(legacyProject.progressPoints, []);
  assert.equal(legacyProject.blockers[0].draft, "");
  const trimmed = validateAnalysis(
    {
      projects: [
        { chatId: "1", progress: "x", progressPoints: ["  пункт  ", "", "   "], evidenceMessageIds: ["m1"] },
      ],
    },
    snapshot,
  );
  assert.deepEqual(trimmed.projects.find((project) => project.chatId === "1").progressPoints, ["пункт"]);
});

test("buildReportModel normalizes the actions panel: evidence filtering, sorting, sendEnabled", () => {
  const snapshot = normalizeSnapshot(fixture);
  const model = buildReportModel({ snapshot, analysis, actions });
  assert.deepEqual(model.actions.items.map((item) => item.id), ["A-1", "A-2", "A-3"]);
  assert.deepEqual(model.actions.items.find((item) => item.id === "A-2").ev, ["m10"]);
  assert.deepEqual(model.actions.items.find((item) => item.id === "A-1").ev, ["m7", "m6"]);
  assert.deepEqual(model.actions.owner.aliases, ["Аня", "@Анна Петрова"]);
  assert.equal(model.sendEnabled, true);

  const shuffled = buildReportModel({
    snapshot,
    analysis,
    actions: {
      owner: { id: "101", name: "Анна Петрова" },
      basis: "test",
      addressedToYou: 1,
      yourOpenAsks: 0,
      items: [
        { id: "B-1", kind: "decision", priority: "P1", chatId: "2", evidence: "m7", draft: "d1" },
        { id: "B-2", kind: "reply", priority: "P0", chatId: "2", evidence: "m1,m10,missing", draft: "d2" },
        { id: "B-3", kind: "process", priority: "P0", chatId: "1", evidence: "", draft: "" },
      ],
    },
  });
  assert.deepEqual(shuffled.actions.items.map((item) => item.id), ["B-2", "B-3", "B-1"]);
  assert.deepEqual(shuffled.actions.items[0].ev, ["m1", "m10"]);

  const none = buildReportModel({ snapshot, analysis });
  assert.equal(none.actions, null);
  const readOnly = buildReportModel({ snapshot: readOnlyFixture(), analysis });
  assert.equal(readOnly.sendEnabled, false);
});

test("report-data carries form v2.2 fields and keeps existing ones", () => {
  const snapshot = normalizeSnapshot(fixture);
  const withActions = reportData(renderReport(buildReportModel({ snapshot, analysis, actions })));
  assert.equal(withActions.formVersion, 2);
  assert.equal(withActions.sendMechanism, "outbox");
  assert.equal(withActions.sendEnabled, true);
  assert.equal(withActions.actionsPresent, true);
  assert.equal(withActions.schemaVersion, 1);
  assert.ok(withActions.window);
  assert.ok(withActions.stats);
  assert.equal(withActions.analysisQuality, "medium");
  const without = reportData(renderReport(buildReportModel({ snapshot, analysis })));
  assert.equal(without.actionsPresent, false);
  const readOnly = reportData(renderReport(buildReportModel({ snapshot: readOnlyFixture(), analysis })));
  assert.equal(readOnly.sendEnabled, false);
});

test("summary renders structured blocks; today/tomorrow relative to collectedAt; thesis on its own line", () => {
  const snapshot = normalizeSnapshot(fixture);
  const html = renderReport(buildReportModel({ snapshot, analysis, actions }));
  assert.match(html, /id="summary"/);
  assert.match(html, /Ближайшие сроки/);
  assert.match(html, /Блокеры и риски/);
  assert.match(html, /Главное за окно/);
  assert.match(html, /Внешние зависимости/);
  // collectedAt = 2026-11-02 UTC: deadline 02.11 → today, 03.11 → tomorrow, 06.11 → plain
  assert.match(html, /<li class="today"><span class="due">02\.11 · сегодня<\/span>/);
  assert.match(html, /<li class="tomorrow"><span class="due">03\.11 · завтра<\/span>/);
  assert.match(html, /<li class=""><span class="due">06\.11 · пятница<\/span>/);
  assert.match(html, /<details class="sum-text"><summary>Текстовая версия сводки<\/summary>/);
  const riskBlock = html.slice(html.indexOf("Блокеры и риски"), html.indexOf("Главное за окно"));
  const sevOrder = [...riskBlock.matchAll(/class="severity (high|medium|low)"/g)].map((match) => match[1]);
  assert.deepEqual(sevOrder, ["high", "medium", "low"]);
  // highlights/external: project tag on its own line above the thesis text (block div)
  const hlBlock = html.slice(html.indexOf("Главное за окно"), html.indexOf("Внешние зависимости"));
  assert.match(hlBlock, /<span class="proj-tag">Платформа<\/span><div>API v2 готов на 80%/);
  assert.match(hlBlock, /<span class="proj-tag">Дизайн-система<\/span><div>Компоненты кнопок готовы\.<\/div>/);
  const extStart = html.indexOf("Внешние зависимости");
  const extBlock = html.slice(extStart, html.indexOf("</section>", extStart));
  assert.match(extBlock, /<span class="proj-tag">Мобильное приложение<\/span><div>Ключ от инфраструктуры/);
  // no thesis text inline right after a proj-tag without a block separator
  assert.doesNotMatch(html, /<span class="proj-tag">[^<]*<\/span>[^<\s]/);
  assert.match(html, /\.hl li>div\{margin-top:3px\}/);
});

test("summary falls back to the callout when crossProject has only text", () => {
  const snapshot = normalizeSnapshot(fixture);
  const fallback = { ...analysis, crossProject: { summary: "Только текстовая сводка." } };
  const html = renderReport(buildReportModel({ snapshot, analysis: fallback }));
  assert.match(html, /<div class="callout"><b>Сводка по всем проектам<\/b><p>Только текстовая сводка\.<\/p><\/div>/);
  assert.doesNotMatch(html, /<div class="sum-grid">/);
});

test("draft boxes under every blocker and action item; channels labeled; progressPoints as bullets", () => {
  const snapshot = normalizeSnapshot(fixture);
  const model = buildReportModel({ snapshot, analysis, actions });
  const html = renderReport(model);
  const blockerCount = model.projects.reduce((sum, project) => sum + project.blockers.length, 0);
  assert.equal(blockerCount, 1);
  const boxes = html.match(/class="draft-box"/g) || [];
  assert.equal(boxes.length, blockerCount + actions.items.length);
  const spoilers = html.match(/<details class="draft-details">/g) || [];
  assert.equal(spoilers.length, blockerCount);
  assert.match(html, /Черновик сообщения → канал: Мобильное приложение/);
  assert.match(html, /Канал: <b>Мобильное приложение<\/b> · #2/);
  assert.match(html, /Канал: <b>Личный чат · Борис Смирнов<\/b> · #4/);
  assert.match(html, /data-ref="blocker:Мобильное приложение:1"/);
  assert.match(html, /data-ref="A-1"/);
  assert.match(html, /https:\/\/app\.pachca\.com\/chats\/2\?message=m7/);
  assert.match(html, /https:\/\/app\.pachca\.com\/chats\/4\?message=m10/);
  assert.match(html, /<ul class="prog"><li>API v2 готов примерно на 80%\.<\/li>/);
  assert.match(html, /ждут вашего ответа/);
  assert.match(html, /ждут решения или аппрува/);
  assert.match(html, /решения по проектам/);
  assert.match(html, /процессные риски/);
  assert.match(html, /Личные сообщения: что ждут от вас — Анна Петрова/);
});

test("send buttons disabled for read-only token, enabled with messages:create", () => {
  const snapshot = normalizeSnapshot(fixture);
  const enabledHtml = renderReport(buildReportModel({ snapshot, analysis, actions }));
  const enabledButtons = sendButtonTags(enabledHtml);
  assert.equal(enabledButtons.length, 4);
  assert.ok(enabledButtons.every((tag) => !tag.includes("disabled")));
  assert.match(enabledHtml, /var SEND_ENABLED=true;/);
  assert.match(enabledHtml, /очередь \.pachca\/outbox\/ → ваше подтверждение → pachca_send_message/);

  const disabledHtml = renderReport(buildReportModel({ snapshot: readOnlyFixture(), analysis, actions }));
  const disabledButtons = sendButtonTags(disabledHtml);
  assert.equal(disabledButtons.length, 4);
  assert.ok(disabledButtons.every((tag) => tag.includes("disabled")));
  assert.ok(
    disabledButtons.every((tag) => tag.includes('title="Токен только на чтение: нет скоупа messages:create"')),
  );
  assert.match(disabledHtml, /var SEND_ENABLED=false;/);
  assert.match(disabledHtml, /недоступно: токен только на чтение \(нет messages:create\)/);
});

test("outbox dialog and queue schema present; no network APIs; dialog precedes the script", () => {
  const snapshot = normalizeSnapshot(fixture);
  const html = renderReport(buildReportModel({ snapshot, analysis, actions }));
  assert.match(html, /<dialog id="send-dialog"/);
  assert.match(html, /id="sd-confirm"/);
  assert.match(html, /id="sd-copy"/);
  assert.match(html, /id="sd-cancel"/);
  assert.match(html, /id="sd-status"/);
  assert.match(html, /kind:'pachca-outbox-message'/);
  assert.match(html, /status:'pending_confirmation'/);
  assert.match(html, /sendPolicy:'confirm_then_send'/);
  assert.match(html, /'pachca-outbox-'\+payload\.chatId\+'-'\+Date\.now\(\)\+'\.json'/);
  assert.match(html, /indexedDB\.open\('pachca-outbox',1\)/);
  assert.match(html, /createObjectStore\('handles'\)/);
  assert.match(html, /\.get\('dir'\)/);
  assert.match(html, /showDirectoryPicker/);
  assert.match(html, /queryPermission/);
  assert.match(html, /requestPermission/);
  assert.match(html, /Ничего не отправляется автоматически/);
  assert.match(html, /Content-Security-Policy/);
  assert.doesNotMatch(html, /fetch\s*\(/);
  assert.doesNotMatch(html, /XMLHttpRequest/);
  assert.doesNotMatch(html, /WebSocket/);
  assert.ok(html.indexOf('<dialog id="send-dialog"') < html.indexOf("var SEND_ENABLED="));
});

test("section order and nav numbering adapt to the actions panel", () => {
  const snapshot = normalizeSnapshot(fixture);
  const withActions = renderReport(buildReportModel({ snapshot, analysis, actions }));
  const order = ["summary", "actions", "projects", "activity", "tasks", "method"].map((id) =>
    withActions.indexOf(`id="${id}"`),
  );
  assert.ok(order.every((index) => index >= 0));
  assert.deepEqual([...order].sort((a, b) => a - b), order);
  assert.match(withActions, /03 · Смысл/);
  assert.match(withActions, /04 · Люди/);
  assert.match(withActions, /<a href="#actions">Личные сообщения<\/a>/);
  const without = renderReport(buildReportModel({ snapshot, analysis }));
  assert.doesNotMatch(without, /id="actions"/);
  assert.doesNotMatch(without, /<a href="#actions">/);
  assert.match(without, /02 · Смысл/);
  assert.match(without, /03 · Люди/);
});