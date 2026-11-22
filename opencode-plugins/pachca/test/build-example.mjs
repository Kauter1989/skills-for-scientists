import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { buildReportModel, normalizeSnapshot } from "../src/analysis.js";
import { renderReport } from "../src/report.js";
import { renderExclusions, renderProjects, renderTasks } from "../src/state.js";

const here = dirname(fileURLToPath(import.meta.url));
const pluginRoot = join(here, "..");
const repoRoot = join(pluginRoot, "..", "..");
const skillRoot = join(repoRoot, "integrations", "pachca-report");

const snapshot = JSON.parse(await readFile(join(here, "fixtures", "snapshot.json"), "utf8"));
const analysis = JSON.parse(await readFile(join(here, "fixtures", "analysis.json"), "utf8"));
const actions = JSON.parse(await readFile(join(here, "fixtures", "actions.json"), "utf8"));
const exclusions = [
  {
    userId: "104",
    name: "Глеб Орлов",
    reason: "отпуск до 10 ноября — по запросу пользователя",
    addedAt: "2026-11-02",
  },
];
const projectsMapping = [
  { chatId: "1", project: "Платформа", aliases: ["core", "api"], updatedAt: "2026-11-02" },
  { chatId: "2", project: "Мобильное приложение", aliases: ["mobile"], updatedAt: "2026-11-02" },
  { chatId: "3", project: "Дизайн-система", aliases: ["design-system"], updatedAt: "2026-11-02" },
  { chatId: "4", project: "Личное", aliases: [], updatedAt: "2026-11-02" },
  { chatId: "5", project: "Архив запуска", aliases: [], updatedAt: "2026-11-02" },
];
const tasks = [
  {
    id: "T-20261102-a1b2c",
    title: "Мониторинг блокеров в Мобильном",
    channelId: "2",
    channel: "Мобильное приложение",
    kind: "monitor",
    actions: ["read_messages"],
    status: "active",
    created: "2026-11-02",
    lastCheck: "2026-11-02T12:00:00.000Z",
    lastRun: "",
    check: "ok",
    checkReason: "Права подтверждены",
    keywords: ["блокер", "ключ", "staging"],
    prompt: "",
    result: "",
    resultPath: "",
    permissionSource: "rest:token-info",
  },
  {
    id: "T-20261102-d3e4f",
    title: "Экспорт истории релизов",
    channelId: "5",
    channel: "Архив запуска",
    kind: "custom",
    actions: ["export_messages"],
    status: "disabled",
    created: "2026-11-02",
    lastCheck: "2026-11-02T12:00:00.000Z",
    lastRun: "",
    check: "blocked",
    checkReason: "Нужен тариф «Корпорация» и роль Владельца; API не подтверждает владельца",
    keywords: [],
    prompt: "Собрать все решения по запуску и сохранить в архив.",
    result: "",
    resultPath: "",
    permissionSource: "snapshot:token-info",
  },
];

const model = buildReportModel({
  snapshot,
  analysis,
  actions,
  exclusions,
  tasks,
  projectsMapping,
  inactivityDays: 2,
  title: "Pachca · рабочие чаты, 2 недели",
});
const html = renderReport(model);

const writes = [
  [join(pluginRoot, "examples", "example-report.html"), html],
  [join(pluginRoot, "examples", "example-snapshot.json"), `${JSON.stringify(snapshot, null, 2)}\n`],
  [join(pluginRoot, "examples", "example-analysis.json"), `${JSON.stringify(analysis, null, 2)}\n`],
  [join(pluginRoot, "examples", "example-actions.json"), `${JSON.stringify(actions, null, 2)}\n`],
  [join(pluginRoot, "examples", "example-exclusions.md"), renderExclusions(exclusions)],
  [join(pluginRoot, "examples", "example-projects.md"), renderProjects(projectsMapping)],
  [join(pluginRoot, "examples", "example-tasks.md"), renderTasks(tasks)],
  [join(skillRoot, "examples", "example-report.html"), html],
  [join(skillRoot, "examples", "example-snapshot.json"), `${JSON.stringify(snapshot, null, 2)}\n`],
  [join(skillRoot, "examples", "example-analysis.json"), `${JSON.stringify(analysis, null, 2)}\n`],
  [join(skillRoot, "examples", "example-actions.json"), `${JSON.stringify(actions, null, 2)}\n`],
  [join(skillRoot, "examples", "example-exclusions.md"), renderExclusions(exclusions)],
  [join(skillRoot, "examples", "example-projects.md"), renderProjects(projectsMapping)],
  [join(skillRoot, "examples", "example-tasks.md"), renderTasks(tasks)],
  [join(skillRoot, "templates", "exclusions.md"), renderExclusions([])],
  [join(skillRoot, "templates", "projects.md"), renderProjects([])],
  [join(skillRoot, "templates", "tasks.md"), renderTasks([])],
];

for (const [path, content] of writes) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, content, "utf8");
}

// Keep the normalized snapshot in the example bundle so consumers see the
// exact shape the renderer expects.
const normalized = normalizeSnapshot(snapshot);
await writeFile(
  join(pluginRoot, "examples", "example-snapshot.normalized.json"),
  `${JSON.stringify(normalized, null, 2)}\n`,
  "utf8",
);

console.log(`example report: ${join(skillRoot, "examples", "example-report.html")}`);
console.log(`bytes: ${Buffer.byteLength(html, "utf8")}`);
console.log(
  `stats: ${model.projects.length} projects, ${model.activity.stats.visible} participants, ${model.activity.stats.inactive} inactive`,
);
console.log(
  `form v2.2: sendEnabled=${model.sendEnabled}, actions=${model.actions ? model.actions.items.length : 0} items`,
);