/**
 * Small, dependency-free helpers shared by the Pachca plugin server and tests.
 * Nothing in this module talks to the network or to the OpenCode API.
 */

export const DAY_MS = 86_400_000;

export function iso(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) throw new Error(`Invalid date: ${String(value)}`);
  return date.toISOString();
}

export function parseDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function daysBetween(from, to) {
  const a = parseDate(from);
  const b = parseDate(to);
  if (!a || !b) return null;
  return Math.round(((b.getTime() - a.getTime()) / DAY_MS) * 10) / 10;
}

export function* chunks(items, size) {
  for (let index = 0; index < items.length; index += size) {
    yield items.slice(index, index + size);
  }
}

export async function mapLimit(items, limit, mapper, signal) {
  const results = new Array(items.length);
  let cursor = 0;
  const worker = async () => {
    for (;;) {
      const index = cursor++;
      if (index >= items.length) return;
      if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
      results[index] = await mapper(items[index], index);
    }
  };
  const workers = Array.from({ length: Math.max(1, Math.min(limit, items.length)) }, worker);
  await Promise.all(workers);
  return results;
}

export function sleep(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(new DOMException("Aborted", "AbortError"));
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

export function asArray(value) {
  return Array.isArray(value) ? value : [];
}

export function asString(value, fallback = "") {
  return typeof value === "string" ? value : value == null ? fallback : String(value);
}

export function asNumber(value, fallback = 0) {
  const number = typeof value === "number" ? value : Number(value);
  return Number.isFinite(number) ? number : fallback;
}

export function escapeHtml(value) {
  return asString(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function escapeJson(value) {
  return JSON.stringify(value)
    .replaceAll("<", "\\u003c")
    .replaceAll(">", "\\u003e")
    .replaceAll("&", "\\u0026")
    .replaceAll("\u2028", "\\u2028")
    .replaceAll("\u2029", "\\u2029");
}

export function truncate(value, max = 240) {
  const text = asString(value).replace(/\s+/g, " ").trim();
  return text.length <= max ? text : `${text.slice(0, max - 1)}…`;
}

export function uniqueBy(items, key) {
  const seen = new Set();
  const output = [];
  for (const item of items) {
    const value = typeof key === "function" ? key(item) : item[key];
    if (seen.has(value)) continue;
    seen.add(value);
    output.push(item);
  }
  return output;
}

export function slug(value) {
  return asString(value)
    .toLowerCase()
    .replace(/[^a-z0-9а-яё]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64) || "report";
}

export function jsonResult(value) {
  return { content: JSON.stringify(value, null, 2) };
}

export function errorResult(error, extra = {}) {
  const message = error instanceof Error ? error.message : String(error);
  return {
    content: JSON.stringify(
      {
        ok: false,
        error: message,
        ...extra,
      },
      null,
      2,
    ),
    isError: true,
  };
}

export function daysWord(value) {
  const number = Math.abs(Number(value));
  const mod10 = number % 10;
  const mod100 = number % 100;
  if (mod10 === 1 && mod100 !== 11) return "день";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "дня";
  return "дней";
}

export function formatDate(value, locale = "ru-RU") {
  const date = parseDate(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(date);
}

export function formatDay(value, locale = "ru-RU") {
  const date = parseDate(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}