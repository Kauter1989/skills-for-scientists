/**
 * Minimal Pachca REST client used by the local report tools.
 *
 * The MCP server remains the primary integration for the agent. This client
 * exists so a user who exports PACHCA_TOKEN can collect and render a report
 * deterministically, without asking the model to copy every message.
 */

import { asArray, asNumber, asString, iso, mapLimit, parseDate, sleep, uniqueBy } from "./util.js";

export const DEFAULT_BASE_URL = "https://api.pachca.com/api/shared/v1";
export const DEFAULT_MCP_URL = "https://mcp.pachca.com/mcp";

export class PachcaError extends Error {
  constructor(message, { status = 0, code = "api_error", scopes = [], retryAfter = null, body = null } = {}) {
    super(message);
    this.name = "PachcaError";
    this.status = status;
    this.code = code;
    this.scopes = scopes;
    this.retryAfter = retryAfter;
    this.body = body;
  }
}

function scopeFromChallenge(header) {
  if (!header) return [];
  const match = /scope="([^"]+)"/i.exec(header);
  return match ? match[1].split(/\s+/).filter(Boolean) : [];
}

function errorMessage(body, status) {
  if (body && typeof body === "object") {
    if (typeof body.error_description === "string") return body.error_description;
    if (typeof body.error === "string") return body.error;
    if (Array.isArray(body.errors) && body.errors.length) {
      return body.errors.map((item) => item?.message || item?.code).filter(Boolean).join("; ");
    }
  }
  return `Pachca API returned HTTP ${status}`;
}

export function createClient({ token, baseUrl = DEFAULT_BASE_URL } = {}) {
  if (!token) throw new PachcaError("PACHCA_TOKEN is not set", { code: "missing_token" });
  const root = baseUrl.replace(/\/+$/, "");

  async function request(path, { query, signal, method = "GET", body } = {}) {
    const url = new URL(`${root}${path}`);
    for (const [key, value] of Object.entries(query || {})) {
      if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
    }
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const response = await fetch(url, {
        method,
        signal,
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
          ...(body ? { "Content-Type": "application/json" } : {}),
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      const text = await response.text();
      let parsed = null;
      try {
        parsed = text ? JSON.parse(text) : null;
      } catch {
        parsed = { raw: text };
      }
      if (response.ok) return parsed;
      if (response.status === 429 && attempt < 2) {
        const retryAfter = Number(response.headers.get("retry-after") || 1);
        await sleep(Math.min(Math.max(retryAfter, 1), 10) * 1000, signal);
        continue;
      }
      if (response.status >= 500 && attempt < 2) {
        await sleep(500 * (attempt + 1), signal);
        continue;
      }
      const code =
        parsed?.error ||
        parsed?.errors?.[0]?.code ||
        (response.status === 402 ? "payment_required" : "api_error");
      throw new PachcaError(errorMessage(parsed, response.status), {
        status: response.status,
        code,
        scopes: scopeFromChallenge(response.headers.get("www-authenticate")),
        retryAfter: response.headers.get("retry-after"),
        body: parsed,
      });
    }
    throw new PachcaError("Pachca API retry limit reached", { code: "retry_limit" });
  }

  async function paginate(path, query = {}, { signal, maxPages = 100 } = {}) {
    const output = [];
    let cursor;
    for (let page = 0; page < maxPages; page += 1) {
      const response = await request(path, {
        query: { ...query, ...(cursor ? { cursor } : {}) },
        signal,
      });
      output.push(...asArray(response?.data));
      const paginateInfo = response?.meta?.paginate;
      if (!paginateInfo?.has_next || !paginateInfo.next_page) break;
      cursor = paginateInfo.next_page;
    }
    return output;
  }

  return {
    tokenInfo: () => request("/oauth/token/info"),
    profile: () => request("/profile"),
    users: ({ signal } = {}) => paginate("/users", { limit: 50 }, { signal }),
    chats: ({ signal, includeArchived = true } = {}) =>
      paginate(
        "/chats",
        {
          availability: "is_member",
          archived: includeArchived ? "true" : "false",
          sort: "last_message_at",
          order: "desc",
          limit: 50,
        },
        { signal },
      ),
    chat: (chatId, { signal } = {}) => request(`/chats/${encodeURIComponent(chatId)}`, { signal }),
    members: (chatId, { signal, role = "all" } = {}) =>
      paginate(`/chats/${encodeURIComponent(chatId)}/members`, { role, limit: 50 }, { signal }),
    messages: (chatId, { signal, limit = 50 } = {}) =>
      paginate(
        "/messages",
        {
          chat_id: chatId,
          sort: "id",
          order: "desc",
          limit,
        },
        { signal },
      ),
    messagesPage: (chatId, { signal, cursor, limit = 50 } = {}) =>
      request("/messages", {
        query: {
          chat_id: chatId,
          sort: "id",
          order: "desc",
          limit,
          ...(cursor ? { cursor } : {}),
        },
        signal,
      }),
  };
}

export function displayName(user) {
  if (!user) return "Неизвестный участник";
  const name = [user.first_name, user.last_name].filter(Boolean).join(" ").trim();
  return name || user.nickname || String(user.id ?? "—");
}

function normalizeUser(user) {
  return {
    id: String(user.id),
    name: displayName(user),
    firstName: user.first_name || "",
    lastName: user.last_name || "",
    nickname: user.nickname || "",
    role: user.role || "user",
    bot: Boolean(user.bot),
    suspended: Boolean(user.suspended),
    lastActivityAt: user.last_activity_at || null,
    timeZone: user.time_zone || null,
  };
}

function normalizeChat(chat) {
  return {
    id: String(chat.id),
    name: chat.name || `Чат ${chat.id}`,
    channel: Boolean(chat.channel),
    personal: Boolean(chat.personal),
    public: Boolean(chat.public),
    archived: Boolean(chat.archived),
    ownerId: chat.owner_id == null ? null : String(chat.owner_id),
    memberIds: asArray(chat.member_ids).map(String),
    groupTagIds: asArray(chat.group_tag_ids).map(String),
    createdAt: chat.created_at || null,
    lastMessageAt: chat.last_message_at || null,
    messages: [],
    coverage: {
      fetched: 0,
      threadsFetched: 0,
      truncated: false,
      skipped: false,
      ok: true,
      errors: [],
    },
  };
}

function normalizeMessage(message, { chatId, thread = false } = {}) {
  return {
    id: String(message.id),
    chatId: String(chatId ?? message.chat_id ?? ""),
    rootChatId: message.root_chat_id == null ? String(chatId ?? "") : String(message.root_chat_id),
    entityType: message.entity_type || (thread ? "thread" : "discussion"),
    userId: message.user_id == null ? "" : String(message.user_id),
    content: asString(message.content),
    createdAt: message.created_at || null,
    url: message.url || "",
    isThread: Boolean(thread || message.entity_type === "thread"),
    threadChatId: message.thread?.chat_id == null ? null : String(message.thread.chat_id),
    parentMessageId: message.parent_message_id == null ? null : String(message.parent_message_id),
    files: asArray(message.files).map((file) => ({
      name: file.name || "",
      type: file.file_type || "file",
      url: file.url || "",
    })),
    important: Boolean(message.important),
  };
}

function mergeUsers(users, extra) {
  return uniqueBy([...users, ...extra].filter(Boolean), (user) => user.id);
}

/**
 * Collect all chats where the token owner is a member and every message since
 * `since`. Threads attached to collected messages are included once, keyed by
 * message id.
 */
export async function collectSnapshot({
  token,
  baseUrl = DEFAULT_BASE_URL,
  since,
  until = new Date(),
  includeArchived = true,
  includeThreads = true,
  maxMessagesPerChat = 500,
  maxThreads = 50,
  chatIds = null,
  knownMessageIds = [],
  signal,
  onProgress = null,
} = {}) {
  const client = createClient({ token, baseUrl });
  const asOf = parseDate(until) || new Date();
  const from = parseDate(since) || new Date(asOf.getTime() - 14 * 86_400_000);

  const tokenInfo = (await client.tokenInfo()).data || {};
  const profile = await client.profile().then(
    (response) => response.data,
    (error) => {
      if (error?.status === 403) return null;
      throw error;
    },
  );
  const users = (await client.users({ signal }).catch(() => [])).map(normalizeUser);
  const self = profile ? normalizeUser(profile) : users.find((user) => user.id === String(tokenInfo.user_id));
  if (self && !users.some((user) => user.id === self.id)) users.push(self);

  const allChats = (await client.chats({ signal, includeArchived })).map(normalizeChat);
  const wanted = chatIds && chatIds.length ? new Set(chatIds.map(String)) : null;
  const chats = allChats.filter((chat) => !wanted || wanted.has(chat.id));

  const threadIds = new Set();
  const seenMessages = new Set(asArray(knownMessageIds).map(String));
  let totalMessages = 0;
  let truncatedChats = 0;
  let failedChats = 0;

  const collectChat = async (chat) => {
    if (chat.lastMessageAt && parseDate(chat.lastMessageAt) < from) {
      chat.coverage.skipped = true;
      return;
    }
    try {
      let count = 0;
      let cursor;
      let stopped = false;
      for (let page = 0; page < 20 && !stopped; page += 1) {
        const response = await client.messagesPage(chat.id, { signal, cursor, limit: 50 });
        const raw = asArray(response?.data);
        for (const item of raw) {
          const created = parseDate(item.created_at);
          if (created && created < from) {
            stopped = true;
            break;
          }
          if (created && created > asOf) continue;
          if (seenMessages.has(String(item.id))) continue;
          seenMessages.add(String(item.id));
          chat.messages.push(normalizeMessage(item, { chatId: chat.id }));
          count += 1;
          totalMessages += 1;
          if (item.thread?.chat_id != null) threadIds.add(String(item.thread.chat_id));
          if (count >= maxMessagesPerChat) {
            chat.coverage.truncated = true;
            truncatedChats += 1;
            stopped = true;
            break;
          }
        }
        const next = response?.meta?.paginate;
        if (!next?.has_next || !next.next_page) break;
        cursor = next.next_page;
      }
      chat.coverage.fetched = count;
    } catch (error) {
      failedChats += 1;
      chat.coverage.ok = false;
      chat.coverage.errors.push({
        stage: "messages",
        status: error?.status || 0,
        code: error?.code || "error",
        message: error?.message || String(error),
      });
    }
    onProgress?.({ chat: chat.name, id: chat.id, fetched: chat.coverage.fetched });
  };

  await mapLimit(chats, 4, collectChat, signal);

  if (includeThreads && threadIds.size) {
    const selected = [...threadIds].slice(0, maxThreads);
    await mapLimit(
      selected,
      4,
      async (threadId) => {
        const parent = chats.find((chat) => chat.messages.some((message) => message.threadChatId === threadId));
        if (!parent) return;
        try {
          let count = 0;
          let cursor;
          let stopped = false;
          for (let page = 0; page < 20 && !stopped; page += 1) {
            const response = await client.messagesPage(threadId, { signal, cursor, limit: 50 });
            const raw = asArray(response?.data);
            for (const item of raw) {
              const created = parseDate(item.created_at);
              if (created && created < from) {
                stopped = true;
                break;
              }
              if (created && created > asOf) continue;
              if (seenMessages.has(String(item.id))) continue;
              seenMessages.add(String(item.id));
              parent.messages.push(normalizeMessage(item, { chatId: parent.id, thread: true }));
              count += 1;
              totalMessages += 1;
              if (count >= maxMessagesPerChat) {
                parent.coverage.truncated = true;
                truncatedChats += 1;
                stopped = true;
                break;
              }
            }
            const next = response?.meta?.paginate;
            if (!next?.has_next || !next.next_page) break;
            cursor = next.next_page;
          }
          parent.coverage.threadsFetched += 1;
        } catch (error) {
          parent.coverage.errors.push({
            stage: "thread",
            threadId,
            status: error?.status || 0,
            code: error?.code || "error",
            message: error?.message || String(error),
          });
        }
      },
      signal,
    );
  }

  for (const chat of chats) {
    chat.messages.sort((a, b) => String(a.createdAt).localeCompare(String(b.createdAt)));
    chat.coverage.fetched = chat.messages.length;
  }

  const authorIds = new Set(chats.flatMap((chat) => chat.messages.map((message) => message.userId)));
  const authors = [...authorIds]
    .filter((id) => id && !users.some((user) => user.id === id))
    .map((id) => ({ id, name: `Сотрудник ${id}` }));
  const allUsers = mergeUsers(users, authors);

  return {
    schemaVersion: 1,
    source: "rest",
    collectedAt: iso(asOf),
    window: { from: iso(from), to: iso(asOf) },
    account: {
      id: self?.id || String(tokenInfo.user_id || ""),
      name: self?.name || "Пользователь",
      nickname: self?.nickname || "",
      role: self?.role || "user",
      bot: Boolean(self?.bot || profile?.bot),
      tokenType: profile?.bot ? "bot" : "personal",
      tokenName: tokenInfo.name || "",
      scopes: asArray(tokenInfo.scopes),
      plan: "unknown",
    },
    users: allUsers,
    chats,
    stats: {
      chatsAvailable: allChats.length,
      chatsSelected: chats.length,
      chatsRead: chats.filter((chat) => chat.coverage.ok).length,
      chatsFailed: chats.filter((chat) => !chat.coverage.ok).length || failedChats,
      chatsTruncated: truncatedChats,
      messages: totalMessages,
      threads: threadIds.size,
    },
  };
}

export function summarizeSnapshot(snapshot) {
  return {
    source: snapshot?.source || "unknown",
    collectedAt: snapshot?.collectedAt || null,
    window: snapshot?.window || null,
    account: snapshot?.account
      ? {
          id: snapshot.account.id,
          name: snapshot.account.name,
          role: snapshot.account.role,
          tokenType: snapshot.account.tokenType,
          scopes: snapshot.account.scopes,
        }
      : null,
    stats: snapshot?.stats || null,
    chats:
      snapshot?.chats?.map((chat) => ({
        id: chat.id,
        name: chat.name,
        messages: chat.messages?.length || 0,
        errors: chat.coverage?.errors?.length || 0,
        truncated: Boolean(chat.coverage?.truncated),
      })) || [],
  };
}

export function tokenScopesFromSnapshot(snapshot) {
  return asArray(snapshot?.account?.scopes).map(String);
}

export function userById(snapshot, id) {
  return asArray(snapshot?.users).find((user) => String(user.id) === String(id)) || null;
}

export function chatById(snapshot, id) {
  return asArray(snapshot?.chats).find((chat) => String(chat.id) === String(id)) || null;
}

export function messageById(snapshot, chatId, id) {
  const chat = chatById(snapshot, chatId);
  return asArray(chat?.messages).find((message) => String(message.id) === String(id)) || null;
}

export { normalizeChat, normalizeMessage, normalizeUser, asNumber };