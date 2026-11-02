/**
 * Preflight for saved channel tasks.
 *
 * Pachca combines scopes, space role, chat role, plan and membership. A task
 * is saved only when every required check can be proven from the current
 * token/snapshot. If the API cannot expose a fact (for example, Owner vs
 * Admin on the export endpoint), the task is blocked instead of being saved
 * with a hopeful assumption.
 */

import { asArray, asString } from "./util.js";

export const ACTION_SPECS = {
  read_messages: {
    label: "Читать сообщения",
    scopes: ["chats:read", "messages:read"],
    kind: "read",
  },
  read_members: {
    label: "Читать участников",
    scopes: ["chat_members:read"],
    kind: "read",
  },
  search_messages: {
    label: "Искать сообщения",
    scopes: ["search:messages"],
    kind: "read",
    chatOptional: true,
  },
  send_message: {
    label: "Отправлять сообщения",
    scopes: ["messages:create"],
    kind: "write",
    write: true,
  },
  react: {
    label: "Ставить реакции",
    scopes: ["reactions:write"],
    kind: "write",
    write: true,
  },
  manage_members: {
    label: "Управлять участниками",
    scopes: ["chat_members:write"],
    kind: "write",
    write: true,
    chatRole: ["owner", "admin"],
  },
  export_messages: {
    label: "Экспортировать сообщения",
    scopes: ["chat_exports:write", "chat_exports:read"],
    kind: "write",
    write: true,
    plan: "corporation",
    ownerOnly: true,
  },
};

const ALIASES = {
  read: "read_messages",
  messages: "read_messages",
  "messages:read": "read_messages",
  summary: "read_messages",
  summarize: "read_messages",
  digest: "read_messages",
  report: "read_messages",
  monitor: "read_messages",
  members: "read_members",
  activity: "read_members",
  search: "search_messages",
  "search:messages": "search_messages",
  send: "send_message",
  post: "send_message",
  "messages:create": "send_message",
  reaction: "react",
  "reactions:write": "react",
  manage: "manage_members",
  export: "export_messages",
};

export function inferActions(text, kind = "custom") {
  const source = asString(text).toLowerCase();
  const actions = new Set(normalizeActions([], kind));
  if (/(отправ|напиш|send|post|опублик)/i.test(source)) actions.add("send_message");
  if (/(экспорт|export|выгруз)/i.test(source)) actions.add("export_messages");
  if (/(участник|members|состав)/i.test(source)) actions.add("read_members");
  if (/(реакц|react)/i.test(source)) actions.add("react");
  return [...actions];
}

export function normalizeActions(actions, kind = "custom") {
  const source = asArray(actions).length
    ? asArray(actions)
    : kind === "activity"
      ? ["read_messages", "read_members"]
      : kind === "monitor"
        ? ["read_messages"]
        : ["read_messages"];
  const output = [];
  for (const item of source) {
    const key = ALIASES[String(item).toLowerCase()] || String(item).toLowerCase();
    if (ACTION_SPECS[key] && !output.includes(key)) output.push(key);
  }
  return output.length ? output : ["read_messages"];
}

export function findChannel(snapshot, { channelId, channel } = {}) {
  const chats = asArray(snapshot?.chats);
  if (channelId) {
    const byId = chats.find((chat) => String(chat.id) === String(channelId));
    return byId ? { ok: true, chat: byId } : { ok: false, code: "chat_not_found", message: `Чат ${channelId} не найден среди доступных` };
  }
  const needle = asString(channel).trim().toLowerCase();
  if (!needle) return { ok: false, code: "channel_required", message: "Укажите канал или channel_id" };
  const exact = chats.filter((chat) => String(chat.name).trim().toLowerCase() === needle);
  if (exact.length === 1) return { ok: true, chat: exact[0] };
  if (exact.length > 1) {
    return {
      ok: false,
      code: "channel_ambiguous",
      message: `Несколько чатов с названием «${channel}»: ${exact.map((chat) => chat.id).join(", ")}`,
      candidates: exact.map((chat) => ({ id: chat.id, name: chat.name })),
    };
  }
  const partial = chats.filter((chat) => String(chat.name).toLowerCase().includes(needle));
  if (partial.length === 1) return { ok: true, chat: partial[0] };
  if (partial.length > 1) {
    return {
      ok: false,
      code: "channel_ambiguous",
      message: `Название «${channel}» совпало с несколькими чатами`,
      candidates: partial.map((chat) => ({ id: chat.id, name: chat.name })),
    };
  }
  return { ok: false, code: "chat_not_found", message: `Канал «${channel}» не найден` };
}

function hasScope(scopes, scope) {
  return scopes.includes(scope);
}

export function preflightTask({
  snapshot,
  channelId,
  channel,
  actions,
  kind = "custom",
  capabilities = {},
} = {}) {
  const checks = [];
  const warnings = [];
  const requiredActions = normalizeActions(actions, kind);
  const scopes = asArray(capabilities.scopes?.length ? capabilities.scopes : snapshot?.account?.scopes).map(String);
  const role = capabilities.role || snapshot?.account?.role || "user";
  const plan = capabilities.plan || snapshot?.account?.plan || "unknown";
  const accountId = String(capabilities.accountId || snapshot?.account?.id || "");
  const chatRoles = capabilities.chatRoles || {};
  const isOwner = capabilities.isOwner === true;

  const resolved = findChannel(snapshot, { channelId, channel });
  const chat = resolved.ok ? resolved.chat : null;
  if (!resolved.ok) {
    checks.push({ ok: false, code: resolved.code, message: resolved.message });
  } else {
    checks.push({ ok: true, code: "chat_found", message: `Канал «${chat.name}» (${chat.id})` });
  }

  if (!scopes.length) {
    checks.push({
      ok: false,
      code: "scopes_unavailable",
      message: "Скоупы токена неизвестны: передайте capabilities.scopes из pachca_get_token_info или PACHCA_TOKEN",
    });
  }

  if (chat) {
    const isMember = chat.memberIds.includes(accountId);
    const canRead = isMember || chat.public || role === "admin";
    for (const action of requiredActions) {
      const spec = ACTION_SPECS[action];
      if (!spec) {
        checks.push({ ok: false, code: "unknown_action", message: `Неизвестное действие: ${action}` });
        continue;
      }
      const missing = spec.scopes.filter((scope) => !hasScope(scopes, scope));
      checks.push({
        ok: missing.length === 0,
        code: missing.length ? "missing_scope" : "scope_ok",
        action,
        message: missing.length
          ? `Для «${spec.label}» нужны права: ${missing.join(", ")}`
          : `Права для «${spec.label}» есть`,
        missing,
      });
      if (spec.write && chat.archived) {
        checks.push({
          ok: false,
          code: "chat_archived",
          action,
          message: `Чат «${chat.name}» в архиве: отправка и управление недоступны`,
        });
      }
      if (!canRead) {
        checks.push({
          ok: false,
          code: "chat_forbidden",
          action,
          message: `Нет доступа к чату «${chat.name}»: пользователь не участник закрытого чата`,
        });
      }
      if (spec.kind === "write" && spec.chatRole) {
        const chatRole = chatRoles[chat.id] || capabilities.chatRole;
        if (!chatRole) {
          checks.push({
            ok: false,
            code: "chat_role_unverified",
            action,
            message: `Роль в чате «${chat.name}» не подтверждена: API не отдаёт её в списке участников без фильтра role`,
          });
        } else if (!spec.chatRole.includes(chatRole)) {
          checks.push({
            ok: false,
            code: "chat_role_forbidden",
            action,
            message: `Роль «${chatRole}» в чате «${chat.name}» не позволяет действие`,
          });
        }
      }
      if (action === "send_message" && chat.channel) {
        const chatRole = chatRoles[chat.id] || capabilities.chatRole;
        if (!chatRole) {
          checks.push({
            ok: false,
            code: "channel_role_unverified",
            action,
            message: `Канал «${chat.name}»: роль подписчика/редактора не подтверждена; отправка может быть запрещена`,
          });
        } else if (!["owner", "admin", "editor"].includes(chatRole)) {
          checks.push({
            ok: false,
            code: "channel_role_forbidden",
            action,
            message: `В канале «${chat.name}» роль «${chatRole}» не даёт права писать`,
          });
        }
      }
      if (spec.plan && plan !== spec.plan) {
        checks.push({
          ok: false,
          code: "plan_unverified",
          action,
          message: `Для «${spec.label}» нужен тариф «Корпорация»; текущий тариф: ${plan}`,
        });
      }
      if (spec.ownerOnly && !isOwner) {
        checks.push({
          ok: false,
          code: "owner_unverified",
          action,
          message: `Для «${spec.label}» нужен Владелец пространства; API не отличает Владельца от Администратора`,
        });
      }
    }
  }

  const failed = checks.filter((check) => !check.ok);
  const status = failed.some((check) => check.code === "scopes_unavailable") ? "unverified" : failed.length ? "blocked" : "ok";
  if (!scopes.length) warnings.push("Скоупы не переданы: проверка не может подтвердить права.");
  if (plan === "unknown") warnings.push("Тариф пространства неизвестен; для чтения это не блокирует задачу.");
  return {
    ok: status === "ok",
    status,
    checks,
    warnings,
    requiredActions,
    channel: chat ? { id: chat.id, name: chat.name, channel: chat.channel, archived: chat.archived } : null,
    evidenceSource: capabilities.source || (scopes.length ? "snapshot:token-info" : "missing"),
    checkedAt: new Date().toISOString(),
    missingScopes: [...new Set(failed.flatMap((check) => check.missing || []))],
  };
}

export function describePreflight(result) {
  if (!result) return "Проверка не выполнялась";
  if (result.ok) return "Права подтверждены";
  const parts = result.checks.filter((check) => !check.ok).map((check) => check.message);
  return parts.length ? parts.join("; ") : "Права не подтверждены";
}

export function taskActionScopes(actions) {
  return [...new Set(normalizeActions(actions).flatMap((action) => ACTION_SPECS[action]?.scopes || []))];
}