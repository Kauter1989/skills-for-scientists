/**
 * Durable Markdown/JSON state for the Pachca report plugin.
 *
 * The Markdown files are deliberately human-editable: users may remove
 * participants from the chart or correct a task without opening JSON.
 */

import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { asArray, asString, iso, parseDate, slug } from "./util.js";

export const DEFAULT_STATE_DIR = ".pachca";

export function statePaths(directory, stateDir = DEFAULT_STATE_DIR) {
  const root = resolve(directory, stateDir);
  return {
    root,
    state: join(root, "state.json"),
    exclusions: join(root, "exclusions.md"),
    projects: join(root, "projects.md"),
    tasks: join(root, "tasks.md"),
    snapshots: join(root, "snapshots"),
    analyses: join(root, "analyses"),
    reports: join(root, "reports"),
    results: join(root, "task-results"),
  };
}

export async function ensureState(paths) {
  await Promise.all(
    [paths.root, paths.snapshots, paths.analyses, paths.reports, paths.results].map((dir) =>
      mkdir(dir, { recursive: true }),
    ),
  );
}

async function readText(path, fallback = "") {
  try {
    return await readFile(path, "utf8");
  } catch (error) {
    if (error && error.code === "ENOENT") return fallback;
    throw error;
  }
}

async function writeTextAtomic(path, text) {
  await mkdir(dirname(path), { recursive: true });
  const temporary = `${path}.${process.pid}.${Date.now()}.tmp`;
  await writeFile(temporary, text, "utf8");
  await rename(temporary, path);
}

export async function readJson(path, fallback = null) {
  const text = await readText(path);
  if (!text.trim()) return fallback;
  return JSON.parse(text);
}

export async function writeJson(path, value) {
  await writeTextAtomic(path, `${JSON.stringify(value, null, 2)}\n`);
}

export async function loadState(paths) {
  const state = await readJson(paths.state, {});
  return {
    schemaVersion: 1,
    lastCollectedAt: null,
    lastReportAt: null,
    seenMessageIds: [],
    failedChatIds: [],
    ...state,
  };
}

export async function saveState(paths, state) {
  await ensureState(paths);
  await writeJson(paths.state, state);
}

export async function saveSnapshot(paths, snapshot) {
  await ensureState(paths);
  const stamp = iso(snapshot.collectedAt || new Date()).replaceAll(":", "-").replace(/\.\d+Z$/, "Z");
  const path = join(paths.snapshots, `snapshot-${stamp}.json`);
  await writeJson(path, snapshot);
  return path;
}

export async function saveAnalysis(paths, analysis) {
  await ensureState(paths);
  const stamp = iso(analysis.generatedAt || new Date()).replaceAll(":", "-").replace(/\.\d+Z$/, "Z");
  const path = join(paths.analyses, `analysis-${stamp}.json`);
  await writeJson(path, analysis);
  return path;
}

export async function latestFile(paths, kind) {
  const directory = kind === "analysis" ? paths.analyses : paths.snapshots;
  const { readdir } = await import("node:fs/promises");
  const entries = await readdir(directory).catch(() => []);
  const prefix = kind === "analysis" ? "analysis-" : "snapshot-";
  const files = entries.filter((name) => name.startsWith(prefix) && name.endsWith(".json")).sort();
  return files.length ? join(directory, files.at(-1)) : null;
}

/* ------------------------------------------------------------------ */
/* Markdown tables                                                     */
/* ------------------------------------------------------------------ */

function splitRow(line) {
  const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  const cells = [];
  let current = "";
  let escaped = false;
  for (const character of trimmed) {
    if (escaped) {
      current += character;
      escaped = false;
      continue;
    }
    if (character === "\\") {
      escaped = true;
      continue;
    }
    if (character === "|") {
      cells.push(current.trim());
      current = "";
      continue;
    }
    current += character;
  }
  cells.push(current.trim());
  return cells;
}

function cleanCell(value) {
  return asString(value)
    .replace(/^`|`$/g, "")
    .replaceAll("\\|", "|")
    .trim();
}

function parseTable(text, header) {
  const lines = text.split(/\r?\n/);
  const start = lines.findIndex((line) => line.trim().replace(/\s+/g, " ").toLowerCase() === header.toLowerCase());
  if (start < 0) return [];
  const rows = [];
  for (let index = start + 1; index < lines.length; index += 1) {
    const line = lines[index];
    if (!line.trim()) continue;
    if (!line.trim().startsWith("|")) break;
    if (/^\|?\s*:?-{2,}/.test(line.trim())) continue;
    rows.push(splitRow(line).map(cleanCell));
  }
  return rows;
}

function tableCell(value) {
  return asString(value).replaceAll("|", "\\|").replace(/\r?\n/g, " ");
}

/* ------------------------------------------------------------------ */
/* Exclusions                                                          */
/* ------------------------------------------------------------------ */

const EXCLUSIONS_HEADER = "| user_id | Имя | Причина | Добавлено |";
const EXCLUSIONS_RULE = "|---|---|---|---|";

export async function loadExclusions(paths) {
  const text = await readText(paths.exclusions);
  const rows = parseTable(text, EXCLUSIONS_HEADER);
  return rows
    .filter((row) => row[0])
    .map((row) => ({
      userId: row[0],
      name: row[1] || row[0],
      reason: row[2] || "",
      addedAt: row[3] || "",
    }));
}

export function renderExclusions(exclusions) {
  const lines = [
    "# Исключения из диаграммы активности",
    "",
    "Участники из этой таблицы не показываются в диаграмме, но остаются",
    "в данных проекта и в панели исключений отчёта. Удалите строку или",
    "выполните `pachca.exclusions` с действием `remove`, чтобы вернуть",
    "участника.",
    "",
    EXCLUSIONS_HEADER,
    EXCLUSIONS_RULE,
    ...exclusions.map(
      (item) =>
        `| ${tableCell(item.userId)} | ${tableCell(item.name)} | ${tableCell(item.reason)} | ${tableCell(item.addedAt)} |`,
    ),
    "",
  ];
  return lines.join("\n");
}

export async function saveExclusions(paths, exclusions) {
  await writeTextAtomic(paths.exclusions, renderExclusions(exclusions));
}

/* ------------------------------------------------------------------ */
/* Project mapping                                                     */
/* ------------------------------------------------------------------ */

const PROJECTS_HEADER = "| chat_id | Проект | Алиасы | Обновлено |";
const PROJECTS_RULE = "|---|---|---|---|";

export async function loadProjects(paths) {
  const text = await readText(paths.projects);
  const rows = parseTable(text, PROJECTS_HEADER);
  return rows
    .filter((row) => row[0])
    .map((row) => ({
      chatId: row[0],
      project: row[1] || row[0],
      aliases: (row[2] || "").split(",").map((item) => item.trim()).filter(Boolean),
      updatedAt: row[3] || "",
    }));
}

export function renderProjects(projects) {
  return [
    "# Соответствие чатов и проектов",
    "",
    "Одна строка — один чат. Если проект не указан, отчёт использует",
    "название чата и помечает проект как `unknown` до анализа.",
    "",
    PROJECTS_HEADER,
    PROJECTS_RULE,
    ...projects.map(
      (item) =>
        `| ${tableCell(item.chatId)} | ${tableCell(item.project)} | ${tableCell((item.aliases || []).join(", "))} | ${tableCell(item.updatedAt)} |`,
    ),
    "",
  ].join("\n");
}

export async function saveProjects(paths, projects) {
  await writeTextAtomic(paths.projects, renderProjects(projects));
}

/* ------------------------------------------------------------------ */
/* Tasks                                                               */
/* ------------------------------------------------------------------ */

const TASK_KEYS = [
  "channel_id",
  "channel",
  "kind",
  "actions",
  "status",
  "created",
  "last_check",
  "last_run",
  "check",
  "check_reason",
  "keywords",
  "prompt",
  "result",
  "result_path",
  "permission_source",
];

function parseTaskSection(section) {
  const first = section.split(/\r?\n/, 1)[0].trim();
  const match = first.match(/^##\s+(T-[A-Za-z0-9-]+)\s*[·-]\s*(.+)$/);
  if (!match) return null;
  const task = {
    id: match[1],
    title: match[2].trim(),
    channelId: "",
    channel: "",
    kind: "custom",
    actions: [],
    status: "active",
    created: "",
    lastCheck: "",
    lastRun: "",
    check: "unchecked",
    checkReason: "",
    keywords: [],
    prompt: "",
    result: "",
    resultPath: "",
    permissionSource: "",
  };
  const lines = section.split(/\r?\n/).slice(1);
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const entry = line.match(/^-\s+([a-z_]+):\s?(.*)$/i);
    if (!entry) continue;
    const key = entry[1].toLowerCase();
    let value = entry[2];
    if (value === "|") {
      const body = [];
      while (index + 1 < lines.length && /^\s{2,}/.test(lines[index + 1])) {
        index += 1;
        body.push(lines[index].replace(/^\s{2,}/, ""));
      }
      value = body.join("\n");
    }
    const clean = value.trim();
    switch (key) {
      case "channel_id":
        task.channelId = clean;
        break;
      case "channel":
        task.channel = clean;
        break;
      case "kind":
        task.kind = clean || "custom";
        break;
      case "actions":
        task.actions = clean.split(",").map((item) => item.trim()).filter(Boolean);
        break;
      case "status":
        task.status = clean || "active";
        break;
      case "created":
        task.created = clean;
        break;
      case "last_check":
        task.lastCheck = clean;
        break;
      case "last_run":
        task.lastRun = clean;
        break;
      case "check":
        task.check = clean || "unchecked";
        break;
      case "check_reason":
        task.checkReason = clean;
        break;
      case "keywords":
        task.keywords = clean.split(",").map((item) => item.trim()).filter(Boolean);
        break;
      case "prompt":
        task.prompt = clean;
        break;
      case "result":
        task.result = clean;
        break;
      case "result_path":
        task.resultPath = clean;
        break;
      case "permission_source":
        task.permissionSource = clean;
        break;
      default:
        break;
    }
  }
  return task;
}

export async function loadTasks(paths) {
  const text = await readText(paths.tasks);
  const sections = text.split(/^(?=##\s+T-)/m).slice(1);
  return sections.map(parseTaskSection).filter(Boolean);
}

function block(key, value) {
  const text = asString(value);
  if (!text.includes("\n")) return `- ${key}: ${text}`;
  return [`- ${key}: |`, ...text.split(/\r?\n/).map((line) => `    ${line}`)].join("\n");
}

export function renderTasks(tasks) {
  const lines = [
    "# Pachca tasks",
    "",
    "Задачи по каналам. Плагин сохраняет задачу только после preflight",
    "прав. Перед запуском проверка повторяется. Редактируйте текст после",
    "`prompt: |` с сохранением отступа в четыре пробела.",
    "",
  ];
  for (const task of tasks) {
    lines.push(`## ${task.id} · ${task.title}`);
    lines.push(block("channel_id", task.channelId));
    lines.push(block("channel", task.channel));
    lines.push(block("kind", task.kind));
    lines.push(block("actions", (task.actions || []).join(", ")));
    lines.push(block("status", task.status));
    lines.push(block("created", task.created));
    lines.push(block("last_check", task.lastCheck));
    lines.push(block("last_run", task.lastRun));
    lines.push(block("check", task.check));
    lines.push(block("check_reason", task.checkReason));
    lines.push(block("keywords", (task.keywords || []).join(", ")));
    lines.push(block("permission_source", task.permissionSource));
    if (task.prompt) lines.push(block("prompt", task.prompt));
    if (task.result) lines.push(block("result", task.result));
    if (task.resultPath) lines.push(block("result_path", task.resultPath));
    lines.push("");
  }
  return lines.join("\n");
}

export async function saveTasks(paths, tasks) {
  await writeTextAtomic(paths.tasks, renderTasks(tasks));
}

export function newTaskId(now = new Date()) {
  const stamp = iso(now).slice(0, 10).replaceAll("-", "");
  const random = Math.random().toString(36).slice(2, 7);
  return `T-${stamp}-${random}`;
}

export async function saveTaskResult(paths, task, text) {
  await ensureState(paths);
  const stamp = iso(new Date()).slice(0, 10);
  const path = join(paths.results, `${task.id}-${stamp}-${slug(task.title)}.md`);
  await writeTextAtomic(path, text);
  return path;
}

/* ------------------------------------------------------------------ */
/* Snapshot / analysis lookup                                          */
/* ------------------------------------------------------------------ */

export async function resolveSnapshotPath(paths, value) {
  if (value) return resolve(value);
  return latestFile(paths, "snapshot");
}

export async function resolveAnalysisPath(paths, value) {
  if (value) return resolve(value);
  return latestFile(paths, "analysis");
}

export function normalizeIso(value, fallback = null) {
  const date = parseDate(value);
  return date ? date.toISOString() : fallback;
}

export function listCounts(exclusions, tasks) {
  return {
    exclusions: asArray(exclusions).length,
    tasks: asArray(tasks).length,
    activeTasks: asArray(tasks).filter((task) => task.status === "active").length,
  };
}