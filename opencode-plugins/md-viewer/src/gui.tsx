import { createEffect, createMemo, createSignal, For, Show, type JSX } from "solid-js"
import { Command, MenuItem, Panel, Plugin, type PanelTab } from "@opencode/plugin/gui"
import { Md } from "./rpc"

/**
 * Desktop GUI part: a side panel that lists the Markdown files of the current
 * session directory, renders them and lets the user edit and save them in place.
 */

const mono = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

function MarkdownPanel(props: { ctx: any; session: { directory: string } }) {
  const ui = props.ctx.ui
  const [files, setFiles] = createSignal<string[]>([])
  const [query, setQuery] = createSignal("")
  const [current, setCurrent] = createSignal<string | null>(null)
  const [content, setContent] = createSignal("")
  const [draft, setDraft] = createSignal("")
  const [editing, setEditing] = createSignal(false)
  const [loading, setLoading] = createSignal(false)
  const [saving, setSaving] = createSignal(false)
  const [error, setError] = createSignal<string | null>(null)

  const dirty = createMemo(() => editing() && draft() !== content())

  const shown = createMemo(() => {
    const q = query().trim().toLowerCase()
    const list = files()
    return q ? list.filter((file) => file.toLowerCase().includes(q)) : list
  })

  let lastDirectory = ""

  const rpc = () => props.ctx.client.rpc(Md)

  async function refresh(directory: string) {
    lastDirectory = directory
    setLoading(true)
    setError(null)
    try {
      const result = (await rpc().list({ directory })) as { files: string[]; error?: string }
      setFiles(result.files ?? [])
      if (result.error) setError(result.error)
      if (current() && !(result.files ?? []).includes(current()!)) {
        setCurrent(null)
        setContent("")
        setDraft("")
        setEditing(false)
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setLoading(false)
    }
  }

  async function open(file: string) {
    if (dirty() && current() !== file) {
      const ok = await props.ctx.dialogs.confirm({
        title: "Discard changes?",
        description: `${current()} has unsaved changes.`,
        confirm: "Discard",
        danger: true,
      })
      if (!ok) return
    }
    setLoading(true)
    setError(null)
    try {
      const result = (await rpc().read({ directory: props.session.directory, path: file })) as {
        ok: boolean
        content: string
        error?: string
      }
      if (!result.ok) {
        setError(result.error ?? "could not read the file")
        return
      }
      setCurrent(file)
      setContent(result.content)
      setDraft(result.content)
      setEditing(false)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setLoading(false)
    }
  }

  async function save() {
    const file = current()
    if (!file) return
    setSaving(true)
    setError(null)
    try {
      const result = (await rpc().write({
        directory: props.session.directory,
        path: file,
        content: draft(),
      })) as { ok: boolean; error?: string }
      if (!result.ok) {
        setError(result.error ?? "could not save the file")
        props.ctx.toast.show({ variant: "error", title: "Save failed", description: result.error })
        return
      }
      setContent(draft())
      setEditing(false)
      props.ctx.toast.show({ variant: "success", title: "Saved", description: file })
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause)
      setError(message)
      props.ctx.toast.show({ variant: "error", title: "Save failed", description: message })
    } finally {
      setSaving(false)
    }
  }

  function discard() {
    setDraft(content())
    setEditing(false)
  }

  createEffect(() => {
    const directory = props.session.directory
    if (!directory || directory === lastDirectory) return
    setCurrent(null)
    setContent("")
    setDraft("")
    setEditing(false)
    void refresh(directory)
  })

  const row = (active: boolean): JSX.CSSProperties => ({
    display: "block",
    width: "100%",
    "text-align": "left",
    padding: "5px 10px",
    border: "none",
    "border-radius": "6px",
    background: active ? "var(--color-surface-raised, rgba(127,127,127,.18))" : "transparent",
    color: "inherit",
    cursor: "pointer",
    font: "12px " + mono,
    "white-space": "nowrap",
    overflow: "hidden",
    "text-overflow": "ellipsis",
  })

  return (
    <div style={{ display: "flex", width: "100%", height: "100%", "min-height": "0", overflow: "hidden" }}>
      <div
        style={{
          width: "232px",
          "min-width": "160px",
          display: "flex",
          "flex-direction": "column",
          "border-right": "1px solid var(--color-border, rgba(127,127,127,.25))",
          "min-height": "0",
        }}
      >
        <div style={{ padding: "8px", display: "flex", "flex-direction": "column", gap: "6px" }}>
          <div style={{ display: "flex", gap: "4px", "align-items": "center" }}>
            <input
              value={query()}
              placeholder="Filter files"
              onInput={(event) => setQuery(event.currentTarget.value)}
              style={{
                flex: "1",
                "min-width": "0",
                background: "transparent",
                color: "inherit",
                border: "1px solid var(--color-border, rgba(127,127,127,.3))",
                "border-radius": "6px",
                padding: "4px 7px",
                font: "12px " + mono,
              }}
            />
            <button
              title="Refresh"
              onClick={() => void refresh(props.session.directory)}
              style={{
                border: "none",
                background: "transparent",
                color: "inherit",
                cursor: "pointer",
                "font-size": "14px",
                padding: "2px 5px",
                opacity: "0.75",
              }}
            >
              R
            </button>
          </div>
          <div style={{ font: "11px " + mono, opacity: "0.55", overflow: "hidden", "text-overflow": "ellipsis" }}>
            {files().length} file{files().length === 1 ? "" : "s"}
          </div>
        </div>
        <div style={{ flex: "1", "overflow-y": "auto", padding: "0 5px 8px" }}>
          <For each={shown()}>
            {(file) => (
              <button title={file} style={row(current() === file)} onClick={() => void open(file)}>
                {file}
              </button>
            )}
          </For>
          <Show when={!loading() && shown().length === 0}>
            <div style={{ padding: "8px", font: "12px " + mono, opacity: "0.6" }}>
              {files().length === 0 ? "No Markdown files here" : "Nothing matches"}
            </div>
          </Show>
        </div>
      </div>

      <div style={{ flex: "1", display: "flex", "flex-direction": "column", "min-width": "0", "min-height": "0" }}>
        <div
          style={{
            display: "flex",
            "align-items": "center",
            gap: "6px",
            padding: "7px 10px",
            "border-bottom": "1px solid var(--color-border, rgba(127,127,127,.25))",
            "min-height": "38px",
          }}
        >
          <div
            title={current() ?? ""}
            style={{
              flex: "1",
              "min-width": "0",
              overflow: "hidden",
              "text-overflow": "ellipsis",
              "white-space": "nowrap",
              font: "12px " + mono,
            }}
          >
            {current() ?? "Select a Markdown file"}
            <Show when={dirty()}>
              <span style={{ color: "var(--color-warning, #d9a441)" }}> *</span>
            </Show>
          </div>
          <Show when={current()}>
            <button style={button()} onClick={() => setEditing((value) => !value)}>
              {editing() ? "Preview" : "Edit"}
            </button>
            <Show when={editing()}>
              <button style={button()} onClick={discard}>
                Revert
              </button>
              <button style={button(true)} disabled={saving() || !dirty()} onClick={() => void save()}>
                {saving() ? "Saving..." : "Save"}
              </button>
            </Show>
            <Show when={!editing()}>
              <button style={button()} title="Reload from disk" onClick={() => current() && void open(current()!)}>
                Reload
              </button>
            </Show>
          </Show>
        </div>

        <Show when={error()}>
          <div
            style={{
              margin: "8px 10px 0",
              padding: "6px 8px",
              "border-radius": "6px",
              background: "var(--color-danger-muted, rgba(200,60,60,.12))",
              color: "var(--color-danger, #d56)",
              font: "12px " + mono,
            }}
          >
            {error()}
          </div>
        </Show>

        <div
          style={{
            flex: "1",
            "min-height": "0",
            overflow: editing() ? "hidden" : "auto",
            padding: editing() ? "0" : "12px 16px",
          }}
        >
          <Show
            when={current()}
            fallback={<div style={{ opacity: "0.6", font: "13px " + mono }}>Pick a file on the left.</div>}
          >
            <Show
              when={editing()}
              fallback={
                <div>
                  <ui.Markdown text={content()} />
                </div>
              }
            >
              <textarea
                value={draft()}
                spellcheck={false}
                onInput={(event) => setDraft(event.currentTarget.value)}
                onKeyDown={(event) => {
                  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
                    event.preventDefault()
                    if (dirty()) void save()
                  }
                  event.stopPropagation()
                }}
                style={{
                  width: "100%",
                  height: "100%",
                  resize: "none",
                  border: "none",
                  outline: "none",
                  padding: "12px 16px",
                  background: "transparent",
                  color: "inherit",
                  font: "13px/1.55 " + mono,
                  "tab-size": "2",
                }}
              />
            </Show>
          </Show>
        </div>
      </div>
    </div>
  )
}

function button(primary = false): JSX.CSSProperties {
  return {
    border: primary ? "none" : "1px solid var(--color-border, rgba(127,127,127,.3))",
    background: primary ? "var(--color-accent, #4f7cff)" : "transparent",
    color: primary ? "#fff" : "inherit",
    "border-radius": "6px",
    padding: "3px 9px",
    cursor: "pointer",
    font: "12px " + mono,
    opacity: "1",
  }
}

export default Plugin.define({
  i18n: {
    en: { title: "Markdown", "command.open": "Open Markdown panel", "menu.open": "Markdown" },
    ru: { title: "Markdown", "command.open": "Открыть панель Markdown", "menu.open": "Markdown" },
  },
  setup(ctx) {
    const tab: PanelTab = {
      id: "main",
      get title() {
        return ctx.t("title")
      },
      closable: "compact",
      fallback: true,
    }

    ctx.add(Panel, {
      id: "main",
      region: "side",
      list: (input) => (input.open.includes("main") ? [tab] : []),
      render: (props) => (
        <MarkdownPanel ctx={ctx as any} session={props.session as unknown as { directory: string }} />
      ),
    })

    ctx.add(Command, () => ({
      id: "open",
      title: ctx.t("command.open"),
      run: () => {
        const session = ctx.sessions.current()
        if (session) ctx.layout.open(`${ctx.id}:main`, session)
      },
    }))

    ctx.add(MenuItem, (): MenuItem => {
      const session = ctx.sessions.current()
      return {
        menu: "session.panel",
        id: "open",
        title: ctx.t("menu.open"),
        icon: "folder",
        opened: !!session && ctx.layout.state(`${ctx.id}:main`, session) !== "closed",
        run: () => {
          if (session) ctx.layout.open(`${ctx.id}:main`, session)
        },
      }
    })
  },
})