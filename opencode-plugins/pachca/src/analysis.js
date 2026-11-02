/**
 * Deterministic normalization, activity accounting and analysis validation.
 * The model supplies project semantics; this module enforces evidence and
 * computes every number that appears in the report.
 */

import {
  asArray,
  asNumber,
  asString,
  daysBetween,
  daysWord,
  parseDate,
  truncate,
  uniqueBy,
} from "./util.js";

export const PROJECT_STATUSES = ["on_track", "at_risk", "blocked", "unknown"];
export const CONFIDENCE_LEVELS = ["high", "medium", "low"];
export const SEVERITIES = ["low", "medium", "high"];

export function normalizeSnapshot(input) {
  if (!input || typeof input !== "object") throw new Error("Snapshot must be an object");
  if (!Array.isArray(input.chats)) throw new Error("Snapshot.chats must be an array");
  const collectedAt = input.collectedAt || new Date().toISOString();
  const window = {
    from: input.window?.from || null,
    to: input.window?.to || collectedAt,
  };
  const users = asArray(input.users).map((user) => ({
    id: String(user.id ?? ""),
    name: user.name || [user.firstName, user.lastName].filter(Boolean).join(" ") || user.nickname || `Сотрудник ${user.id}`,
    nickname: user.nickname || "",
    role: user.role || "user",
    bot: Boolean(user.bot),
    suspended: Boolean(user.suspended),
    lastActivityAt: user.lastActivityAt || null,
    timeZone: user.timeZone || null,
  }));
  const chats = input.chats.map((chat) => ({
    id: String(chat.id ?? ""),
    name: chat.name || `Чат ${chat.id}`,
    channel: Boolean(chat.channel),
    personal: Boolean(chat.personal),
    public: Boolean(chat.public),
    archived: Boolean(chat.archived),
    ownerId: chat.ownerId == null ? null : String(chat.ownerId),
    memberIds: asArray(chat.memberIds).map(String),
    lastMessageAt: chat.lastMessageAt || null,
    coverage: {
      fetched: asNumber(chat.coverage?.fetched, 0),
      threadsFetched: asNumber(chat.coverage?.threadsFetched, 0),
      truncated: Boolean(chat.coverage?.truncated),
      skipped: Boolean(chat.coverage?.skipped),
      ok: chat.coverage?.ok !== false,
      errors: asArray(chat.coverage?.errors),
    },
    messages: asArray(chat.messages).map((message) => ({
      id: String(message.id ?? ""),
      chatId: String(message.chatId ?? chat.id),
      rootChatId: String(message.rootChatId ?? chat.id),
      userId: String(message.userId ?? ""),
      userName: message.userName || "",
      content: asString(message.content),
      createdAt: message.createdAt || null,
      url: message.url || "",
      isThread: Boolean(message.isThread),
      threadChatId: message.threadChatId ? String(message.threadChatId) : null,
      parentMessageId: message.parentMessageId ? String(message.parentMessageId) : null,
      files: asArray(message.files),
      important: Boolean(message.important),
    })),
  }));
  return {
    schemaVersion: 1,
    source: input.source || "unknown",
    collectedAt,
    window,
    account: input.account
      ? {
          id: String(input.account.id ?? ""),
          name: input.account.name || "Пользователь",
          nickname: input.account.nickname || "",
          role: input.account.role || "user",
          bot: Boolean(input.account.bot),
          tokenType: input.account.tokenType || "personal",
          tokenName: input.account.tokenName || "",
          scopes: asArray(input.account.scopes).map(String),
          plan: input.account.plan || "unknown",
        }
      : null,
    users: uniqueBy(users, (user) => user.id),
    chats,
    stats: input.stats || {},
  };
}

export function userName(snapshot, id) {
  const user = snapshot.users.find((item) => item.id === String(id));
  return user?.name || `Сотрудник ${id}`;
}

export function isBot(snapshot, id) {
  const user = snapshot.users.find((item) => item.id === String(id));
  return Boolean(user?.bot);
}

export function computeActivity(
  snapshot,
  { asOf = snapshot.collectedAt, inactivityDays = 2, includeBots = false, exclusions = [] } = {},
) {
  const threshold = Math.max(0, asNumber(inactivityDays, 2));
  const asOfDate = parseDate(asOf) || new Date();
  const excludedIds = new Set(asArray(exclusions).map((item) => String(item.userId)));
  const excludedNames = new Set(asArray(exclusions).map((item) => String(item.name).toLowerCase()));
  const memberIds = new Set();
  for (const chat of snapshot.chats) {
    for (const id of chat.memberIds) memberIds.add(String(id));
  }
  const users = new Map();
  for (const user of snapshot.users) users.set(String(user.id), { ...user });
  for (const chat of snapshot.chats) {
    for (const message of chat.messages) {
      if (!users.has(message.userId)) {
        users.set(message.userId, {
          id: message.userId,
          name: message.userName || `Сотрудник ${message.userId}`,
          nickname: "",
          role: "user",
          bot: false,
          suspended: false,
          lastActivityAt: null,
          timeZone: null,
        });
      }
      memberIds.add(String(message.userId));
    }
  }

  const participants = [];
  for (const id of memberIds) {
    const user = users.get(id) || { id, name: `Сотрудник ${id}`, bot: false };
    if (user.bot && !includeBots) continue;
    const byChat = {};
    let total = 0;
    let last = null;
    for (const chat of snapshot.chats) {
      const messages = chat.messages.filter((message) => message.userId === id);
      if (!chat.memberIds.includes(id) && messages.length === 0) {
        continue;
      }
      const chatLast = messages.reduce(
        (latest, message) => (!latest || String(message.createdAt) > latest ? message.createdAt : latest),
        null,
      );
      const days = chatLast ? daysBetween(chatLast, asOfDate) : null;
      byChat[chat.id] = {
        count: messages.length,
        lastMessageAt: chatLast,
        daysSilent: days,
        inactive: chatLast ? days > threshold : true,
      };
      total += messages.length;
      if (chatLast && (!last || chatLast > last)) last = chatLast;
    }
    const days = last ? daysBetween(last, asOfDate) : null;
    const excluded =
      excludedIds.has(id) || excludedNames.has(String(user.name || "").toLowerCase());
    const inactive = last ? days > threshold : true;
    const silentLabel = last
      ? days > threshold
        ? `${String(days).replace(".", ",")} ${daysWord(days)}`
        : "активен"
      : "нет сообщений в окне";
    participants.push({
      id,
      name: user.name || `Сотрудник ${id}`,
      nickname: user.nickname || "",
      bot: Boolean(user.bot),
      role: user.role || "user",
      count: total,
      lastMessageAt: last,
      daysSilent: days,
      inactive,
      silentLabel,
      excluded,
      exclusionReason: excluded
        ? asArray(exclusions).find(
            (item) =>
              String(item.userId) === id ||
              String(item.name).toLowerCase() === String(user.name).toLowerCase(),
          )?.reason || ""
        : "",
      byChat,
    });
  }

  participants.sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, "ru"));
  const visible = participants.filter((item) => !item.excluded);
  const excluded = participants.filter((item) => item.excluded);
  return {
    asOf: asOfDate.toISOString(),
    inactivityDays: threshold,
    participants,
    visible,
    excluded,
    stats: {
      total: participants.length,
      visible: visible.length,
      inactive: visible.filter((item) => item.inactive).length,
      active: visible.filter((item) => !item.inactive).length,
      excluded: excluded.length,
      messages: snapshot.chats.reduce((sum, chat) => sum + chat.messages.length, 0),
    },
  };
}

export function validateAnalysis(analysis, snapshot, projectsMapping = []) {
  const mapping = new Map(asArray(projectsMapping).map((item) => [String(item.chatId), item]));
  const warnings = [];
  if (!analysis || typeof analysis !== "object") {
    return {
      projects: snapshot.chats.map((chat) => unknownProject(chat, mapping)),
      warnings: ["analysis.json не передан: прогресс и блокеры помечены как unknown"],
      quality: "missing",
      crossProject: null,
    };
  }
  if (analysis.schemaVersion != null && analysis.schemaVersion !== 1) {
    warnings.push(`Неизвестная версия analysis: ${analysis.schemaVersion}`);
  }
  const seen = new Set();
  const projects = [];
  for (const raw of asArray(analysis.projects)) {
    const chatId = String(raw.chatId ?? raw.chat_id ?? "");
    const chat = snapshot.chats.find((item) => item.id === chatId);
    if (!chat) {
      warnings.push(`analysis: чат ${chatId || "(пусто)"} отсутствует в snapshot; проект пропущен`);
      continue;
    }
    if (seen.has(chatId)) warnings.push(`analysis: проект для чата ${chatId} повторяется; взят первый`);
    if (seen.has(chatId)) continue;
    seen.add(chatId);
    const status = PROJECT_STATUSES.includes(raw.status) ? raw.status : "unknown";
    if (raw.status && !PROJECT_STATUSES.includes(raw.status)) {
      warnings.push(`${chat.name}: статус «${raw.status}» неизвестен, заменён на unknown`);
    }
    const confidence = CONFIDENCE_LEVELS.includes(raw.confidence) ? raw.confidence : "low";
    const messageIds = new Set(chat.messages.map((message) => message.id));
    const evidenceIds = asArray(raw.evidenceMessageIds).map(String);
    const missingEvidence = evidenceIds.filter((id) => !messageIds.has(id));
    if (missingEvidence.length) {
      warnings.push(`${chat.name}: evidence ID не найдены — ${missingEvidence.join(", ")}`);
    }
    const blockers = asArray(raw.blockers).map((blocker) => {
      const ids = asArray(blocker.evidenceMessageIds).map(String);
      const missing = ids.filter((id) => !messageIds.has(id));
      if (missing.length) {
        warnings.push(`${chat.name}: блокер без найденных цитат (${missing.join(", ")})`);
      }
      return {
        text: asString(blocker.text || blocker.description || "").trim(),
        severity: SEVERITIES.includes(blocker.severity) ? blocker.severity : "medium",
        evidenceMessageIds: ids,
        verified: ids.length > 0 && missing.length === 0,
      };
    });
    const unverifiedBlockers = blockers.filter((item) => item.text && !item.verified).length;
    const hasEvidence = evidenceIds.length > 0 && missingEvidence.length === 0;
    const progress = asString(raw.progress || raw.summary || "").trim();
    const project = {
      chatId,
      chatName: chat.name,
      project:
        asString(raw.project || "").trim() ||
        mapping.get(chatId)?.project ||
        chat.name,
      status,
      progress: progress || "Нет данных о прогрессе",
      blockers,
      nextSteps: asArray(raw.nextSteps).map((item) => asString(item).trim()).filter(Boolean),
      evidenceMessageIds: evidenceIds,
      confidence: hasEvidence ? confidence : confidence === "high" ? "medium" : confidence,
      evidenceQuality: hasEvidence ? "expert" : "missing",
      verified: hasEvidence && (blockers.length === 0 || unverifiedBlockers === 0),
      warnings: [],
      messages: chat.messages,
      chat,
    };
    if (!progress) project.warnings.push("Прогресс не заполнен");
    if (!hasEvidence) project.warnings.push("Нет подтверждённых цитат");
    if (unverifiedBlockers) project.warnings.push(`${unverifiedBlockers} блокер(ов) без цитат`);
    projects.push(project);
  }
  for (const chat of snapshot.chats) {
    if (!seen.has(chat.id)) projects.push(unknownProject(chat, mapping));
  }
  const verified = projects.filter((item) => item.verified).length;
  const quality =
    projects.length === 0
      ? "missing"
      : verified === projects.length
        ? "high"
        : verified > 0
          ? "medium"
          : "low";
  return {
    projects,
    warnings,
    quality,
    crossProject: analysis.crossProject || null,
    generatedAt: analysis.generatedAt || null,
    notes: analysis.notes || "",
  };
}

function unknownProject(chat, mapping) {
  return {
    chatId: chat.id,
    chatName: chat.name,
    project: mapping.get(chat.id)?.project || chat.name,
    status: "unknown",
    progress: "Нет анализа новых сообщений",
    blockers: [],
    nextSteps: [],
    evidenceMessageIds: [],
    confidence: "low",
    evidenceQuality: "missing",
    verified: false,
    warnings: ["Нет анализа"],
    messages: chat.messages,
    chat,
  };
}

export function evidenceForProject(project, limit = 8) {
  const ids = new Set([
    ...asArray(project.evidenceMessageIds),
    ...asArray(project.blockers).flatMap((blocker) => asArray(blocker.evidenceMessageIds)),
  ]);
  const messages = asArray(project.messages).filter((message) => ids.has(message.id));
  return messages.slice(-limit).map((message) => ({
    ...message,
    excerpt: truncate(message.content, 260),
  }));
}

export function buildReportModel({
  snapshot: rawSnapshot,
  analysis,
  exclusions = [],
  tasks = [],
  projectsMapping = [],
  inactivityDays = 2,
  includeBots = false,
  title = "Pachca · отчёт по рабочим чатам",
  generatedAt = new Date().toISOString(),
}) {
  const snapshot = normalizeSnapshot(rawSnapshot);
  const activity = computeActivity(snapshot, {
    asOf: snapshot.collectedAt,
    inactivityDays,
    includeBots,
    exclusions,
  });
  const validated = validateAnalysis(analysis, snapshot, projectsMapping);
  const projects = validated.projects.map((project) => ({
    ...project,
    evidence: evidenceForProject(project),
  }));
  const projectStats = {
    total: projects.length,
    blocked: projects.filter((item) => item.status === "blocked").length,
    atRisk: projects.filter((item) => item.status === "at_risk").length,
    onTrack: projects.filter((item) => item.status === "on_track").length,
    unknown: projects.filter((item) => item.status === "unknown").length,
    withBlockers: projects.filter((item) => item.blockers.length > 0).length,
    verified: projects.filter((item) => item.verified).length,
  };
  const failedChats = snapshot.chats
    .filter((chat) => chat.coverage.ok === false)
    .map((chat) => ({
      id: chat.id,
      name: chat.name,
      errors: chat.coverage.errors,
    }));
  return {
    schemaVersion: 1,
    generatedAt,
    title,
    snapshot,
    activity,
    projects,
    projectStats,
    analysis: {
      quality: validated.quality,
      warnings: validated.warnings,
      crossProject: validated.crossProject,
      notes: validated.notes,
      generatedAt: validated.generatedAt,
    },
    tasks: asArray(tasks),
    exclusions: asArray(exclusions),
    failedChats,
    coverage: {
      chatsAvailable: asNumber(snapshot.stats.chatsAvailable, snapshot.chats.length),
      chatsSelected: asNumber(snapshot.stats.chatsSelected, snapshot.chats.length),
      chatsRead: asNumber(snapshot.stats.chatsRead, snapshot.chats.length - failedChats.length),
      chatsFailed: failedChats.length,
      messages: activity.stats.messages,
      threads: asNumber(snapshot.stats.threads, 0),
      truncated: snapshot.chats.filter((chat) => chat.coverage.truncated).length,
      window: snapshot.window,
      source: snapshot.source,
    },
  };
}