import { Rpc } from "@opencode/plugin/rpc"

/**
 * RPC contract shared by the server part and the desktop GUI part.
 * All paths are relative to the session directory and restricted to Markdown.
 */
export const Md = Rpc.define({
  id: "md-panel",
  methods: {
    list: {
      input: {
        type: "object",
        properties: {
          directory: { type: "string" },
        },
        required: ["directory"],
        additionalProperties: false,
      },
      output: {
        type: "object",
        properties: {
          files: { type: "array", items: { type: "string" } },
          error: { type: "string" },
        },
        required: ["files"],
        additionalProperties: false,
      },
    },
    read: {
      input: {
        type: "object",
        properties: {
          directory: { type: "string" },
          path: { type: "string" },
        },
        required: ["directory", "path"],
        additionalProperties: false,
      },
      output: {
        type: "object",
        properties: {
          ok: { type: "boolean" },
          content: { type: "string" },
          error: { type: "string" },
        },
        required: ["ok", "content"],
        additionalProperties: false,
      },
    },
    write: {
      input: {
        type: "object",
        properties: {
          directory: { type: "string" },
          path: { type: "string" },
          content: { type: "string" },
        },
        required: ["directory", "path", "content"],
        additionalProperties: false,
      },
      output: {
        type: "object",
        properties: {
          ok: { type: "boolean" },
          error: { type: "string" },
        },
        required: ["ok"],
        additionalProperties: false,
      },
    },
  },
  events: {},
})