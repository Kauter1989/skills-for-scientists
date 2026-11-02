import assert from "node:assert/strict";
import { createServer } from "node:http";
import test from "node:test";

import { collectSnapshot, createClient } from "../src/api.js";

function json(response, status, body) {
  response.writeHead(status, { "Content-Type": "application/json" });
  response.end(JSON.stringify(body));
}

async function withServer(handler, callback) {
  const server = createServer(handler);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const port = server.address().port;
    return await callback(`http://127.0.0.1:${port}/api/shared/v1`);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

test("REST collector paginates, stops at the window, attaches threads and reports failed chats", async () => {
  const seen = [];
  await withServer((request, response) => {
    const url = new URL(request.url, "http://localhost");
    const path = url.pathname.replace("/api/shared/v1", "");
    seen.push(`${path}${url.search}`);
    if (path === "/oauth/token/info") {
      return json(response, 200, {
        data: {
          id: 1,
          token: "masked",
          user_id: 10,
          scopes: ["chats:read", "messages:read", "chat_members:read", "profile:read", "users:read"],
          name: "test",
        },
      });
    }
    if (path === "/profile") {
      return json(response, 200, {
        data: { id: 10, first_name: "Анна", last_name: "Тестова", nickname: "anna", role: "admin", bot: false },
      });
    }
    if (path === "/users") {
      return json(response, 200, {
        data: [
          { id: 10, first_name: "Анна", last_name: "Тестова", nickname: "anna", role: "admin", bot: false },
          { id: 11, first_name: "Борис", last_name: "Тестов", nickname: "boris", role: "user", bot: false },
        ],
        meta: { paginate: { next_page: "", prev_page: "", has_next: false, has_prev: false } },
      });
    }
    if (path === "/chats") {
      return json(response, 200, {
        data: [
          {
            id: 1,
            name: "Проект",
            channel: false,
            personal: false,
            public: false,
            archived: false,
            owner_id: 10,
            member_ids: [10, 11],
            group_tag_ids: [],
            last_message_at: "2026-11-02T09:00:00.000Z",
          },
          {
            id: 2,
            name: "Закрытый",
            channel: false,
            personal: false,
            public: false,
            archived: false,
            owner_id: 11,
            member_ids: [11],
            group_tag_ids: [],
            last_message_at: "2026-11-02T08:00:00.000Z",
          },
        ],
        meta: { paginate: { next_page: "", prev_page: "", has_next: false, has_prev: false } },
      });
    }
    if (path === "/messages" && url.searchParams.get("chat_id") === "2") {
      return json(response, 403, { error: "role_forbidden", error_description: "No access" });
    }
    if (path === "/messages" && url.searchParams.get("chat_id") === "77") {
      return json(response, 200, {
        data: [
          {
            id: 105,
            entity_type: "thread",
            chat_id: 77,
            root_chat_id: 1,
            content: "Ответ в треде",
            user_id: 11,
            created_at: "2026-11-02T09:30:00.000Z",
            url: "https://app.pachca.com/chats/77?message=105",
          },
        ],
        meta: { paginate: { next_page: "", prev_page: "", has_next: false, has_prev: false } },
      });
    }
    if (path === "/messages" && url.searchParams.get("chat_id") === "1") {
      const cursor = url.searchParams.get("cursor");
      if (!cursor) {
        return json(response, 200, {
          data: [
            {
              id: 101,
              entity_type: "discussion",
              chat_id: 1,
              root_chat_id: 1,
              content: "Новое сообщение",
              user_id: 10,
              created_at: "2026-11-02T09:00:00.000Z",
              url: "https://app.pachca.com/chats/1?message=101",
              thread: { id: 55, chat_id: 77 },
            },
            {
              id: 102,
              entity_type: "discussion",
              chat_id: 1,
              root_chat_id: 1,
              content: "Ещё новое",
              user_id: 11,
              created_at: "2026-11-01T09:00:00.000Z",
              url: "https://app.pachca.com/chats/1?message=102",
            },
            {
              id: 103,
              entity_type: "discussion",
              chat_id: 1,
              root_chat_id: 1,
              content: "Старое, за окном",
              user_id: 11,
              created_at: "2026-10-01T09:00:00.000Z",
              url: "https://app.pachca.com/chats/1?message=103",
            },
          ],
          meta: { paginate: { next_page: "next", prev_page: "", has_next: true, has_prev: false } },
        });
      }
      return json(response, 200, {
        data: [
          {
            id: 104,
            entity_type: "discussion",
            chat_id: 1,
            root_chat_id: 1,
            content: "Ещё более старое",
            user_id: 10,
            created_at: "2026-09-01T09:00:00.000Z",
            url: "https://app.pachca.com/chats/1?message=104",
          },
        ],
        meta: { paginate: { next_page: "", prev_page: "", has_next: false, has_prev: false } },
      });
    }
    return json(response, 404, { error: "not_found", error_description: `Unknown ${path}` });
  }, async (baseUrl) => {
    const snapshot = await collectSnapshot({
      token: "secret",
      baseUrl,
      since: "2026-10-20T00:00:00.000Z",
      until: "2026-11-02T12:00:00.000Z",
      includeThreads: true,
      includeArchived: true,
    });
    assert.equal(snapshot.source, "rest");
    assert.equal(snapshot.chats.length, 2);
    const project = snapshot.chats.find((chat) => chat.id === "1");
    assert.equal(project.messages.length, 3); // 101, 102, thread 105; 103 is outside the window
    assert.equal(project.messages.some((message) => message.id === "105"), true);
    assert.equal(project.messages.some((message) => message.id === "103"), false);
    assert.equal(project.coverage.threadsFetched, 1);
    const closed = snapshot.chats.find((chat) => chat.id === "2");
    assert.equal(closed.coverage.ok, false);
    assert.equal(snapshot.stats.chatsFailed, 1);
    assert.equal(snapshot.users.some((user) => user.name === "Анна Тестова"), true);
    assert.equal(snapshot.account.scopes.includes("messages:read"), true);
    assert.ok(seen.some((path) => path.includes("chat_id=77")));
    assert.ok(!JSON.stringify(snapshot).includes("secret"));
  });
});

test("client reports missing token before network", () => {
  assert.throws(() => createClient({}), /PACHCA_TOKEN/);
});