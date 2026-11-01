import { Plugin } from "@opencode/plugin"

/**
 * Server part of the WGSL Viz plugin.
 * Adds agent tools that push WGSL scenes (shader + geometry) to the viz-server
 * (see ../server.py). The GUI part (./gui-experimental) renders them in a
 * native OpenCode Desktop side panel and opens itself on focus pushes,
 * so neither a human nor a manual UI action is required.
 */

const DEFAULT_URL = "http://127.0.0.1:8787"

/** Stream scenes take ferrum's clip box as text; fold `clipStr` into `clip`. */
function normalizeGeometry(g: Record<string, unknown> | undefined, clipStr?: string) {
  if (!g) return null
  const geom: Record<string, unknown> = { ...g }
  if (geom.kind === "stream" && clipStr) geom.clip = clipStr
  return geom
}

const GEOMETRY_SCHEMA = {
  type: "object",
  description:
    "Optional geometry for the scene. kind=cube|sphere|grid|custom. " +
    "sphere: radius, segments, rings. grid: nx, ny, size (flat XZ plane for heightfield shaders). " +
    "custom: flat arrays positions/normals/colors (3 floats per vertex) and indices.",
  properties: {
    kind: { type: "string", enum: ["cube", "sphere", "grid", "custom", "image", "volume", "stream"] },
    radius: { type: "number" },
    segments: { type: "integer" },
    rings: { type: "integer" },
    nx: { type: "integer" },
    ny: { type: "integer" },
    size: { type: "number" },
    positions: { type: "array", items: { type: "number" } },
    normals: { type: "array", items: { type: "number" } },
    colors: { type: "array", items: { type: "number" } },
    indices: { type: "array", items: { type: "number" } },
    data: { type: "string", description: "kind=image: base64 PNG to display in the panel" },
    url: { type: "string", description: "kind=image: URL of the image; kind=volume: URL of raw u8 volume" },
    dims: { type: "array", items: { type: "integer" }, description: "kind=volume: [x,y,z] voxel counts" },
    spacing: { type: "array", items: { type: "number" }, description: "kind=volume: voxel spacing in mm" },
    min: { type: "number", description: "kind=volume: HU minimum of the normalized u8 range" },
    max: { type: "number", description: "kind=volume: HU maximum of the normalized u8 range" },
    mode: { type: "integer", description: "kind=volume: 0 isosurface, 1 MIP, 2 transfer-function band" },
    threshold: { type: "number", description: "kind=volume: isosurface/band threshold in HU" },
    band: { type: "number", description: "kind=volume: TF band width in HU (default 400)" },
    clip: { type: "array", items: { type: "number" }, description: "kind=volume: clip-box half extents in mm [x,y,z] (default no clip)" },
    preset: { type: "string", description: "kind=stream: ferrum CT preset (lung_vessels, soft_tissue_bone, bone)" },
    clipStr: { type: "string", description: "kind=stream: ferrum clip box min_x,min_y,min_z:max_x,max_y,max_z" },
    dragSize: { type: "integer", description: "kind=stream: frame size while dragging (default 320)" },
  },
  required: ["kind"],
  additionalProperties: false,
} as const

export default Plugin.define({
  id: "wgslviz",
  async setup(ctx) {
    const vizUrl = String(ctx.options.url ?? DEFAULT_URL).replace(/\/$/, "")

    await ctx.tool.transform((editor) => {
      editor.namespace({
        name: "wgslviz",
        description: "3D visualization panel: send WGSL scenes to be rendered live in OpenCode",
      })

      editor.add({
        name: "push",
        description:
          "Send a WGSL scene to the OpenCode 3D visualization panel (opens the panel automatically). " +
          "Contract: vertex entry vs_main with @location(0) position vec3, @location(1) normal vec3, " +
          "@location(2) color vec3 (stride 36 bytes); fragment entry fs_main returning @location(0) vec4<f32>; " +
          "uniform @group(0) @binding(0) struct { mvp, model: mat4x4<f32>; lightPos, cameraPos, params: vec4<f32> } " +
          "with params = (shininess, specStrength, time, 0). Geometry kinds: cube, sphere, grid, custom.",
        input: {
          type: "object",
          properties: {
            code: { type: "string", description: "Complete WGSL source" },
            title: { type: "string", description: "Short scene title shown in the panel" },
            geometry: GEOMETRY_SCHEMA,
            focus: {
              type: "boolean",
              description: "Open/focus the visualization panel automatically (default true)",
            },
          },
          required: ["code"],
          additionalProperties: false,
        },
        execute: async (input: {
          code: string
          title?: string
          geometry?: Record<string, unknown>
          focus?: boolean
        }) => {
          try {
            const res = await fetch(vizUrl + "/api/scene", {
              method: "POST",
              headers: { "content-type": "application/json" },
              body: JSON.stringify({
                code: input.code,
                title: input.title ?? "",
                geometry: normalizeGeometry(input.geometry, input.clipStr),
                focus: input.focus !== false,
              }),
            })
            if (!res.ok) return { content: `WGSL viz server replied HTTP ${res.status}` }
            const j = (await res.json()) as { version: number; geometryToken: number }
            return {
              content:
                `Scene delivered to the WGSL visualization panel (v${j.version}, geometry g${j.geometryToken}). ` +
                `The panel opens itself when focus is on.`,
            }
          } catch {
            return {
              content:
                `WGSL viz server is not reachable at ${vizUrl}. ` +
                `Start it with: python opencode-plugins/wgsl-viz/server/server.py`,
            }
          }
        },
      })

      editor.add({
        name: "status",
        description: "Show which scene version/title is currently rendered in the WGSL visualization panel.",
        input: { type: "object", properties: {}, additionalProperties: false },
        execute: async () => {
          try {
            const res = await fetch(vizUrl + "/api/state?meta=1")
            if (!res.ok) return { content: `viz server replied HTTP ${res.status}` }
            const j = (await res.json()) as { version: number; title: string; geometryToken: number }
            return {
              content: `WGSL viz panel shows v${j.version} (geometry g${j.geometryToken})${j.title ? " — " + j.title : ""}`,
            }
          } catch {
            return { content: `WGSL viz server is not reachable at ${vizUrl}` }
          }
        },
      })
    })
  },
})
