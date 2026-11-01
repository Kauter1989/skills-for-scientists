import { mkdir, readdir, readFile, stat, writeFile } from "node:fs/promises"
import { dirname, extname, join, relative, resolve, sep } from "node:path"
import { Plugin } from "@opencode/plugin"
import { Md } from "./rpc"

/**
 * Server part of the Markdown panel plugin.
 * Reads and writes Markdown files inside the current session directory for
 * the desktop GUI part (./gui-experimental).
 */

const MARKDOWN = new Set([".md", ".markdown", ".mdx", ".mdown", ".mkd"])
const SKIP_DIRS = new Set([
  "node_modules",
  ".git",
  ".hg",
  ".svn",
  "dist",
  "build",
  "out",
  "coverage",
  ".next",
  ".nuxt",
  ".cache",
  ".turbo",
  ".venv",
  "venv",
  "__pycache__",
  "target",
  "vendor",
])
const MAX_FILE = 4 * 1024 * 1024
const MAX_FILES = 4000
const MAX_DEPTH = 16

function inside(root: string, path: string) {
  const rel = relative(root, path)
  return rel === "" || (!rel.startsWith("..") && !rel.includes(`..${sep}`) && !rel.startsWith(sep))
}

function candidate(directory: string, path: string) {
  const root = resolve(directory)
  const target = resolve(root, path)
  if (!inside(root, target)) throw new Error("path escapes the workspace")
  if (!MARKDOWN.has(extname(target).toLowerCase())) throw new Error("not a Markdown file")
  return { root, target }
}

async function scan(root: string) {
  const files: string[] = []

  async function walk(dir: string, depth: number) {
    if (depth > MAX_DEPTH || files.length >= MAX_FILES) return
    let entries
    try {
      entries = await readdir(dir, { withFileTypes: true })
    } catch {
      return
    }
    for (const entry of entries) {
      if (files.length >= MAX_FILES) return
      if (entry.isDirectory()) {
        if (SKIP_DIRS.has(entry.name)) continue
        await walk(join(dir, entry.name), depth + 1)
      } else if (entry.isFile() && MARKDOWN.has(extname(entry.name).toLowerCase())) {
        files.push(relative(root, join(dir, entry.name)).split(sep).join("/"))
      }
    }
  }

  await walk(root, 0)
  return files.sort((a, b) => a.localeCompare(b))
}

export default Plugin.define({
  id: "md-panel",
  async setup(ctx) {
    await ctx.rpc.register(Md, {
      list: async (input) => {
        const { directory } = input as { directory: string }
        try {
          const root = resolve(directory)
          const info = await stat(root)
          if (!info.isDirectory()) return { files: [], error: "not a directory" }
          return { files: await scan(root) }
        } catch (error) {
          return { files: [], error: error instanceof Error ? error.message : String(error) }
        }
      },
      read: async (input) => {
        const { directory, path } = input as { directory: string; path: string }
        try {
          const { target } = candidate(directory, path)
          const info = await stat(target)
          if (!info.isFile()) return { ok: false, content: "", error: "not a file" }
          if (info.size > MAX_FILE) return { ok: false, content: "", error: "file is larger than 4 MB" }
          return { ok: true, content: await readFile(target, "utf8") }
        } catch (error) {
          return { ok: false, content: "", error: error instanceof Error ? error.message : String(error) }
        }
      },
      write: async (input) => {
        const { directory, path, content } = input as {
          directory: string
          path: string
          content: string
        }
        try {
          const { target } = candidate(directory, path)
          const info = await stat(target).catch(() => undefined)
          if (!info?.isFile()) return { ok: false, error: "file does not exist" }
          if (Buffer.byteLength(content, "utf8") > MAX_FILE) {
            return { ok: false, error: "file would be larger than 4 MB" }
          }
          await mkdir(dirname(target), { recursive: true })
          await writeFile(target, content, "utf8")
          return { ok: true }
        } catch (error) {
          return { ok: false, error: error instanceof Error ? error.message : String(error) }
        }
      },
    })
  },
})