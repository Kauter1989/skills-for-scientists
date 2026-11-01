import { onCleanup, onMount } from "solid-js"
import { Command, MenuItem, Panel, Plugin, type PanelTab } from "@opencode/plugin/gui"

/**
 * GUI part (experimental) of the WGSL Viz plugin.
 * Adds a native side panel to OpenCode Desktop that renders whatever WGSL
 * scene the viz-server (../server.py) currently holds (shader + geometry).
 * The panel opens itself when an agent pushes a scene with focus=true,
 * so no human action is required to "switch to 3D".
 */

const VIZ_URL = "http://127.0.0.1:8787"

// Interactive camera shared by the mesh and stream modes.
const vizCam = { yaw: 0, pitch: 0, dist: 6 }
let vizStream: { orbit(dx: number, dy: number): void; zoom(dy: number): void } | null = null

// ---------- column-major mat4 helpers (same convention as WGSL) ----------
const m4 = () => new Float32Array(16)
function m4mul(a: Float32Array, b: Float32Array, out = m4()) {
  for (let c = 0; c < 4; c++)
    for (let r = 0; r < 4; r++) {
      let s = 0
      for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k]
      out[c * 4 + r] = s
    }
  return out
}
function m4persp(fovy: number, aspect: number, near: number, far: number, out = m4()) {
  const f = 1 / Math.tan(fovy / 2)
  out.fill(0)
  out[0] = f / aspect
  out[5] = f
  out[10] = far / (near - far)
  out[11] = -1
  out[14] = (near * far) / (near - far)
  return out
}
function m4look(eye: number[], target: number[], up: number[], out = m4()) {
  let zx = eye[0] - target[0], zy = eye[1] - target[1], zz = eye[2] - target[2]
  let l = Math.hypot(zx, zy, zz)
  zx /= l; zy /= l; zz /= l
  let xx = up[1] * zz - up[2] * zy, xy = up[2] * zx - up[0] * zz, xz = up[0] * zy - up[1] * zx
  l = Math.hypot(xx, xy, xz)
  xx /= l; xy /= l; xz /= l
  const yx = zy * xz - zz * xy, yy = zz * xx - zx * xz, yz = zx * xy - zy * xx
  out.set([
    xx, yx, zx, 0, xy, yy, zy, 0, xz, yz, zz, 0,
    -(xx * eye[0] + xy * eye[1] + xz * eye[2]),
    -(yx * eye[0] + yy * eye[1] + yz * eye[2]),
    -(zx * eye[0] + zy * eye[1] + zz * eye[2]), 1,
  ])
  return out
}
function m4rotX(a: number, out = m4()) { const c = Math.cos(a), s = Math.sin(a); out.set([1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0, 0, 0, 0, 1]); return out }
function m4rotY(a: number, out = m4()) { const c = Math.cos(a), s = Math.sin(a); out.set([c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1]); return out }

// ---------- geometry: cube | sphere | grid | custom ----------
function ramp(t: number) {
  t = Math.min(1, Math.max(0, t))
  return [0.25 + 0.7 * t, 0.45 + 0.25 * Math.sin(t * Math.PI), 0.85 - 0.55 * t]
}

function buildCube() {
  const faces = [
    { n: [0, 0, 1], c: [0.96, 0.45, 0.35], v: [[-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]] },
    { n: [0, 0, -1], c: [0.30, 0.62, 0.92], v: [[1, -1, -1], [-1, -1, -1], [-1, 1, -1], [1, 1, -1]] },
    { n: [1, 0, 0], c: [0.96, 0.76, 0.30], v: [[1, -1, 1], [1, -1, -1], [1, 1, -1], [1, 1, 1]] },
    { n: [-1, 0, 0], c: [0.55, 0.80, 0.45], v: [[-1, -1, -1], [-1, -1, 1], [-1, 1, 1], [-1, 1, -1]] },
    { n: [0, 1, 0], c: [0.72, 0.55, 0.92], v: [[-1, 1, 1], [1, 1, 1], [1, 1, -1], [-1, 1, -1]] },
    { n: [0, -1, 0], c: [0.38, 0.82, 0.76], v: [[-1, -1, -1], [1, -1, -1], [1, -1, 1], [-1, -1, 1]] },
  ]
  const verts = new Float32Array(24 * 9)
  const idx: number[] = []
  let vi = 0
  for (const f of faces) {
    const base = vi / 9
    for (const p of f.v) {
      verts[vi++] = p[0]; verts[vi++] = p[1]; verts[vi++] = p[2]
      verts[vi++] = f.n[0]; verts[vi++] = f.n[1]; verts[vi++] = f.n[2]
      verts[vi++] = f.c[0]; verts[vi++] = f.c[1]; verts[vi++] = f.c[2]
    }
    idx.push(base, base + 1, base + 2, base, base + 2, base + 3)
  }
  return { vertices: verts, indices: idx }
}

function buildSphere(radius = 1, segments = 48, rings = 32) {
  const verts: number[] = [], idx: number[] = []
  for (let y = 0; y <= rings; y++) {
    const phi = (y / rings) * Math.PI
    for (let x = 0; x <= segments; x++) {
      const theta = (x / segments) * Math.PI * 2
      const nx = Math.sin(phi) * Math.cos(theta), ny = Math.cos(phi), nz = Math.sin(phi) * Math.sin(theta)
      const c = ramp((ny + 1) / 2)
      verts.push(nx * radius, ny * radius, nz * radius, nx, ny, nz, c[0], c[1], c[2])
    }
  }
  for (let y = 0; y < rings; y++)
    for (let x = 0; x < segments; x++) {
      const a = y * (segments + 1) + x, b = a + segments + 1
      idx.push(a, b, a + 1, a + 1, b, b + 1)
    }
  return { vertices: new Float32Array(verts), indices: idx }
}

function buildGrid(nx = 96, ny = 96, size = 4) {
  const verts: number[] = [], idx: number[] = [], half = size / 2
  for (let y = 0; y <= ny; y++)
    for (let x = 0; x <= nx; x++) {
      const px = (x / nx) * size - half, pz = (y / ny) * size - half
      const c = ramp(1 - Math.hypot(px, pz) / half)
      verts.push(px, 0, pz, 0, 1, 0, c[0], c[1], c[2])
    }
  for (let y = 0; y < ny; y++)
    for (let x = 0; x < nx; x++) {
      const a = y * (nx + 1) + x, b = a + nx + 1
      idx.push(a, b, a + 1, a + 1, b, b + 1)
    }
  return { vertices: new Float32Array(verts), indices: idx }
}

function buildCustom(g: any) {
  const p = g.positions, n = g.normals, c = g.colors, idx = g.indices
  if (!Array.isArray(p) || !Array.isArray(n) || !Array.isArray(c) || !Array.isArray(idx))
    throw new Error("custom geometry: positions/normals/colors/indices required")
  if (p.length % 3 || p.length !== n.length || p.length !== c.length)
    throw new Error("custom geometry: array sizes inconsistent")
  const verts = new Float32Array(p.length * 3)
  for (let i = 0, k = 0; i < p.length; i += 3) {
    verts[k++] = p[i]; verts[k++] = p[i + 1]; verts[k++] = p[i + 2]
    verts[k++] = n[i]; verts[k++] = n[i + 1]; verts[k++] = n[i + 2]
    verts[k++] = c[i]; verts[k++] = c[i + 1]; verts[k++] = c[i + 2]
  }
  return { vertices: verts, indices: idx as number[] }
}

function buildGeometry(g: any) {
  const kind = (g && g.kind) || "cube"
  if (kind === "sphere") return buildSphere(g.radius ?? 1, g.segments ?? 48, g.rings ?? 32)
  if (kind === "grid") return buildGrid(g.nx ?? 96, g.ny ?? 96, g.size ?? 4)
  if (kind === "custom") return buildCustom(g)
  return buildCube()
}

// ---------- panel renderer ----------
async function startViz(canvas: HTMLCanvasElement, setStatus: (s: string) => void): Promise<() => void> {
  const nav = navigator as unknown as { gpu?: any }
  if (!nav.gpu) { setStatus("WebGPU is not available in this window"); return () => {} }
  const adapter = await nav.gpu.requestAdapter()
  if (!adapter) { setStatus("No GPU adapter"); return () => {} }
  const device = await adapter.requestDevice()
  const context = canvas.getContext("webgpu") as any
  const format = nav.gpu.getPreferredCanvasFormat()
  context.configure({ device, format, alphaMode: "opaque" })

  const uniforms = new Float32Array(44)
  const ubuf = device.createBuffer({ size: uniforms.byteLength, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST })
  const bgl = device.createBindGroupLayout({
    entries: [{ binding: 0, visibility: GPUShaderStage.VERTEX | GPUShaderStage.FRAGMENT, buffer: { type: "uniform" } }],
  })
  const bindGroup = device.createBindGroup({ layout: bgl, entries: [{ binding: 0, resource: { buffer: ubuf } }] })

  let vbuf: any = null, ibuf: any = null, depthTex: any = null
  let pipeline: any = null
  let indexFormat: "uint16" | "uint32" = "uint16"
  let indexCount = 0
  let version = -1, geomVersion = -1
  let time = 0, last = 0

  // ---------- image mode: готовые рендеры (FERRUM и др.) ----------
  const IMG_WGSL = `
struct U {
  mvp : mat4x4<f32>, model : mat4x4<f32>, lightPos : vec4<f32>,
  cameraPos : vec4<f32>, params : vec4<f32>,
};
@group(0) @binding(0) var<uniform> u : U;
@group(0) @binding(1) var tex : texture_2d<f32>;
@group(0) @binding(2) var smp : sampler;
struct VOut {
  @builtin(position) pos : vec4<f32>,
  @location(0) uv : vec2<f32>,
};
@vertex
fn vs_img(@builtin(vertex_index) vi : u32) -> VOut {
  var p = array<vec2<f32>, 6>(
    vec2<f32>(-1.0, -1.0), vec2<f32>(1.0, -1.0), vec2<f32>(1.0, 1.0),
    vec2<f32>(-1.0, -1.0), vec2<f32>(1.0, 1.0), vec2<f32>(-1.0, 1.0));
  var out : VOut;
  out.pos = vec4<f32>(p[vi], 0.0, 1.0);
  out.uv = vec2<f32>((p[vi].x + 1.0) * 0.5, (p[vi].y + 1.0) * 0.5);
  return out;
}
@fragment
fn fs_img(in : VOut) -> @location(0) vec4<f32> {
  let aI = u.params.w;
  let aS = u.cameraPos.w;
  let fw = min(1.0, aI / aS);
  let fh = min(1.0, aS / aI);
  let t = (in.uv - 0.5) / vec2<f32>(fw, fh) + 0.5;
  if (t.x < 0.0 || t.x > 1.0 || t.y < 0.0 || t.y > 1.0) {
    return vec4<f32>(0.043, 0.055, 0.082, 1.0);
  }
  let c = textureSampleLevel(tex, smp, t, 0.0);
  return vec4<f32>(c.rgb, 1.0);
}
`;
  let imageMode = false, imageReady = false, imagePipeline: any = null
  let imageBind: any = null, imageTex: any = null, imageSampler: any = null, imageBgl: any = null
  let imageAspect = 1

  function ensureImagePipeline() {
    if (imagePipeline) return
    const module = device.createShaderModule({ code: IMG_WGSL })
    imageBgl = device.createBindGroupLayout({ entries: [
      { binding: 0, visibility: GPUShaderStage.VERTEX | GPUShaderStage.FRAGMENT, buffer: { type: "uniform" } },
      { binding: 1, visibility: GPUShaderStage.FRAGMENT, texture: { sampleType: "float" } },
      { binding: 2, visibility: GPUShaderStage.FRAGMENT, sampler: {} },
    ]})
    imagePipeline = device.createRenderPipeline({
      layout: device.createPipelineLayout({ bindGroupLayouts: [imageBgl] }),
      vertex: { module, entryPoint: "vs_img" },
      fragment: { module, entryPoint: "fs_img", targets: [{ format }] },
      primitive: { topology: "triangle-list" },
    })
    imageSampler = device.createSampler({ magFilter: "linear", minFilter: "linear" })
  }

  async function setImageBlob(blob: Blob) {
    ensureImagePipeline()
    const bmp = await createImageBitmap(blob)
    if (imageTex) imageTex.destroy()
    imageTex = device.createTexture({
      size: [bmp.width, bmp.height, 1], format: "rgba8unorm",
      usage: GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST | GPUTextureUsage.RENDER_ATTACHMENT,
    })
    device.queue.copyExternalImageToTexture(
      { source: bmp, flipY: true }, { texture: imageTex }, [bmp.width, bmp.height, 1])
    imageAspect = bmp.width / bmp.height
    imageBind = device.createBindGroup({ layout: imageBgl, entries: [
      { binding: 0, resource: { buffer: ubuf } },
      { binding: 1, resource: imageTex.createView() },
      { binding: 2, resource: imageSampler },
    ]})
    imageReady = true
    if (bmp.close) bmp.close()
  }

  async function setImageSource(url: string) {
    ensureImagePipeline()
    const r = await fetch(url, { cache: "no-store" })
    if (!r.ok) throw new Error("image fetch " + r.status)
    await setImageBlob(await r.blob())
  }

  // ---- stream mode: ferrum frame server renders, the panel displays ----
  let streamMode = false, streamBusy = false, streamPending = false, streamPendingSize = 0
  let streamUrl = "", streamPreset = "lung_vessels", streamClip = ""
  let streamIdle = 640, streamDrag = 320, streamThreshold = -400, streamTimer: any = 0

  async function streamRequest(size: number) {
    if (!streamUrl) return
    if (streamBusy) { streamPending = true; streamPendingSize = size; return }
    streamBusy = true
    try {
      const body = {
        yaw: vizCam.yaw, pitch: vizCam.pitch, dist: 1.35 * (vizCam.dist / 6),
        mode: "transfer_function", preset: streamPreset,
        threshold: streamThreshold, clip: streamClip, size,
      }
      const r = await fetch(streamUrl, {
        method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
        signal: AbortSignal.timeout(8000),
      })
      if (!r.ok) throw new Error("HTTP " + r.status)
      await setImageBlob(await r.blob())
      setStatus("ferrum " + streamPreset + (streamClip ? ", clip " + streamClip : "") + " — " + size + "px")
    } catch (e: any) {
      setStatus("stream: " + e.message)
    }
    streamBusy = false
    if (streamPending) { streamPending = false; streamRequest(streamPendingSize || size) }
  }

  function scheduleStream(drag: boolean) {
    if (!streamMode) return
    clearTimeout(streamTimer)
    if (drag) streamRequest(streamDrag)
    else streamTimer = setTimeout(() => streamRequest(streamIdle), 350)
  }

  // ---------- volume mode: interactive raycasting (CT/MRI) ----------
  const VOL_WGSL = `
struct VolU {
  eye    : vec4<f32>,
  right  : vec4<f32>,
  up     : vec4<f32>,
  fwd    : vec4<f32>,
  params : vec4<f32>,
  info   : vec4<f32>,
  range  : vec4<f32>,
  clip   : vec4<f32>,
};
@group(0) @binding(0) var<uniform> u : VolU;
@group(0) @binding(1) var vol : texture_3d<f32>;
@group(0) @binding(2) var smp : sampler;
struct VOut {
  @builtin(position) pos : vec4<f32>,
  @location(0) uv : vec2<f32>,
};
@vertex
fn vs_vol(@builtin(vertex_index) vi : u32) -> VOut {
  var p = array<vec2<f32>, 6>(
    vec2<f32>(-1.0, -1.0), vec2<f32>(1.0, -1.0), vec2<f32>(1.0, 1.0),
    vec2<f32>(-1.0, -1.0), vec2<f32>(1.0, 1.0), vec2<f32>(-1.0, 1.0));
  var out : VOut;
  out.pos = vec4<f32>(p[vi], 0.0, 1.0);
  out.uv = vec2<f32>((p[vi].x + 1.0) * 0.5, (p[vi].y + 1.0) * 0.5);
  return out;
}
fn sampleV(pmm : vec3<f32>) -> f32 {
  let t = pmm / (2.0 * u.info.xyz) + 0.5;
  if (any(t < vec3<f32>(0.0)) || any(t > vec3<f32>(1.0))) { return 0.0; }
  return textureSampleLevel(vol, smp, t, 0.0).r;
}
fn grad(pmm : vec3<f32>) -> vec3<f32> {
  let e = 1.0;
  return vec3<f32>(
    sampleV(pmm + vec3<f32>(e, 0.0, 0.0)) - sampleV(pmm - vec3<f32>(e, 0.0, 0.0)),
    sampleV(pmm + vec3<f32>(0.0, e, 0.0)) - sampleV(pmm - vec3<f32>(0.0, e, 0.0)),
    sampleV(pmm + vec3<f32>(0.0, 0.0, e)) - sampleV(pmm - vec3<f32>(0.0, 0.0, e)));
}
@fragment
fn fs_vol(in : VOut) -> @location(0) vec4<f32> {
  let aspect = u.range.z;
  let ndc = (in.uv - 0.5) * 2.0;
  let dirW = normalize(u.fwd.xyz + u.right.xyz * (ndc.x * aspect * 0.5) + u.up.xyz * (ndc.y * 0.5));
  let eye = u.eye.xyz;
  let b = u.info.xyz;
  let inv = 1.0 / dirW;
  let t0v = (-b - eye) * inv;
  let t1v = (b - eye) * inv;
  let tmin = max(max(min(t0v.x, t1v.x), min(t0v.y, t1v.y)), min(t0v.z, t1v.z));
  let tmax = min(min(max(t0v.x, t1v.x), max(t0v.y, t1v.y)), max(t0v.z, t1v.z));
  let bg = vec3<f32>(0.043, 0.055, 0.082);
  if (tmax <= max(tmin, 0.0)) { return vec4<f32>(bg, 1.0); }
  var tStart = tmin;
  var tEnd = tmax;
  let c = u.clip.xyz;
  if (c.x > 0.0 && c.y > 0.0 && c.z > 0.0) {
    let i2 = 1.0 / dirW;
    let c0 = (-c - eye) * i2;
    let c1 = ( c - eye) * i2;
    let cmin = max(max(min(c0.x, c1.x), min(c0.y, c1.y)), min(c0.z, c1.z));
    let cmax = min(min(max(c0.x, c1.x), max(c0.y, c1.y)), max(c0.z, c1.z));
    tStart = max(tmin, cmin);
    tEnd = min(tmax, cmax);
  }
  if (tEnd <= max(tStart, 0.0)) { return vec4<f32>(bg, 1.0); }
  var t = max(tStart, 0.0);
  let step = u.params.z;
  let mode = u.params.x;
  let thrN = clamp((u.params.y - u.range.x) / max(1.0, u.range.y - u.range.x), 0.0, 1.0);
  let band = max(0.01, u.range.w);
  var acc = vec3<f32>(0.0);
  var alpha = 0.0;
  var mipV = 0.0;
  for (var i = 0; i < 220; i = i + 1) {
    let p = eye + dirW * t;
    let v = sampleV(p);
    if (mode < 0.5) {
      if (v >= thrN) {
        let g = grad(p);
        let n = normalize(-g + vec3<f32>(0.00001));
        let L = normalize(vec3<f32>(0.6, 0.8, 0.5));
        let Vv = -dirW;
        let dif = max(dot(n, L), 0.0);
        let spec = pow(max(dot(reflect(-L, n), Vv), 0.0), 24.0);
        let base = vec3<f32>(0.88, 0.62, 0.55);
        acc = base * (0.22 + 0.78 * dif) + vec3<f32>(spec * 0.45);
        alpha = 1.0;
        break;
      }
    } else if (mode < 1.5) {
      mipV = max(mipV, v);
    } else {
      let d = abs(v - thrN);
      let a = clamp(1.0 - d / band, 0.0, 1.0) * 0.16;
      if (a > 0.0) {
        let c = mix(vec3<f32>(0.35, 0.55, 0.95), vec3<f32>(0.95, 0.60, 0.45), clamp(v * 1.2, 0.0, 1.0));
        acc = acc + c * a * (1.0 - alpha);
        alpha = alpha + a * (1.0 - alpha);
        if (alpha > 0.95) { break; }
      }
    }
    t = t + step;
    if (t > tEnd) { break; }
  }
  if (mode >= 0.5 && mode < 1.5) { acc = vec3<f32>(mipV); alpha = 1.0; }
  let col = mix(bg, acc, clamp(alpha, 0.0, 1.0));
  return vec4<f32>(col, 1.0);
}
`;
  let volumeMode = false, volumeReady = false, volPipe: any = null, volBind: any = null
  let volTex: any = null, volBgl: any = null, volSampler: any = null, volUbuf: any = null
  let volMeta: any = null, volMode = 0, volThr = -400
  const volU = new Float32Array(32)

  function ensureVolPipeline() {
    if (volPipe) return
    const module = device.createShaderModule({ code: VOL_WGSL })
    volBgl = device.createBindGroupLayout({ entries: [
      { binding: 0, visibility: GPUShaderStage.VERTEX | GPUShaderStage.FRAGMENT, buffer: { type: "uniform" } },
      { binding: 1, visibility: GPUShaderStage.FRAGMENT, texture: { sampleType: "float", viewDimension: "3d" } },
      { binding: 2, visibility: GPUShaderStage.FRAGMENT, sampler: {} },
    ]})
    volPipe = device.createRenderPipeline({
      layout: device.createPipelineLayout({ bindGroupLayouts: [volBgl] }),
      vertex: { module, entryPoint: "vs_vol" },
      fragment: { module, entryPoint: "fs_vol", targets: [{ format }] },
      primitive: { topology: "triangle-list" },
    })
    volSampler = device.createSampler({ magFilter: "linear", minFilter: "linear", mipmapFilter: "linear" })
    volUbuf = device.createBuffer({ size: volU.byteLength, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST })
  }

  async function setVolume(g: any) {
    ensureVolPipeline()
    const r = await fetch(g.url, { cache: "no-store" })
    if (!r.ok) throw new Error("volume fetch " + r.status)
    const buf = new Uint8Array(await r.arrayBuffer())
    const [dx, dy, dz] = g.dims
    if (buf.length !== dx * dy * dz) throw new Error("volume size mismatch")
    if (volTex) volTex.destroy()
    volTex = device.createTexture({
      size: [dx, dy, dz], format: "r8unorm", dimension: "3d",
      usage: GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST,
    })
    const bpr = Math.ceil(dx / 256) * 256
    let data: Uint8Array = buf
    if (bpr !== dx) {
      data = new Uint8Array(bpr * dy * dz)
      for (let z = 0; z < dz; z++)
        for (let y = 0; y < dy; y++)
          data.set(buf.subarray((z * dy + y) * dx, (z * dy + y) * dx + dx), (z * dy + y) * bpr)
    }
    device.queue.writeTexture({ texture: volTex }, data,
      { bytesPerRow: bpr, rowsPerImage: dy }, [dx, dy, dz])
    volMeta = { dims: g.dims, spacing: g.spacing || [1, 1, 1], min: g.min ?? 0, max: g.max ?? 1,
      band: g.band ?? 400, clip: g.clip || [0, 0, 0] }
    if (g.mode !== undefined) volMode = g.mode
    if (g.threshold !== undefined) volThr = g.threshold
    volBind = device.createBindGroup({ layout: volBgl, entries: [
      { binding: 0, resource: { buffer: volUbuf } },
      { binding: 1, resource: volTex.createView() },
      { binding: 2, resource: volSampler },
    ]})
    volumeReady = true
  }

  function applyGeometry(g: any) {
    if (g && g.kind === "stream") {
      volumeMode = false
      imageMode = true
      imageReady = false
      streamMode = true
      streamUrl = /^https?:/.test(g.url || "") ? g.url : VIZ_URL + (g.url || "")
      streamPreset = g.preset || "lung_vessels"
      streamClip = g.clip || g.clipStr || ""
      streamIdle = g.size || 640
      streamDrag = g.dragSize || 320
      streamThreshold = g.threshold ?? -400
      streamRequest(streamDrag)
      scheduleStream(false)
      return
    }
    streamMode = false
    if (g && g.kind === "volume") {
      imageMode = false
      volumeMode = true
      volumeReady = false
      const url = /^https?:/.test(g.url || "") ? g.url : VIZ_URL + (g.url || "")
      setVolume(Object.assign({}, g, { url })).catch((e: any) => setStatus("volume: " + e.message))
      return
    }
    volumeMode = false
    if (g && g.kind === "image") {
      imageMode = true
      imageReady = false
      const url = /^https?:/.test(g.url || "") ? g.url : VIZ_URL + (g.url || "")
      setImageSource(url).catch((e: any) => setStatus("image: " + e.message))
      return
    }
    imageMode = false
    const { vertices, indices } = buildGeometry(g)
    const maxIdx = indices.reduce((m, v) => (v > m ? v : m), 0)
    indexFormat = maxIdx > 65535 ? "uint32" : "uint16"
    indexCount = indices.length
    const idxArr = indexFormat === "uint32" ? new Uint32Array(indices) : new Uint16Array(indices)
    if (vbuf) vbuf.destroy()
    if (ibuf) ibuf.destroy()
    vbuf = device.createBuffer({ size: vertices.byteLength, usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST })
    device.queue.writeBuffer(vbuf, 0, vertices)
    ibuf = device.createBuffer({ size: idxArr.byteLength, usage: GPUBufferUsage.INDEX | GPUBufferUsage.COPY_DST })
    device.queue.writeBuffer(ibuf, 0, idxArr)
  }

  const desc = (module: any) => ({
    layout: device.createPipelineLayout({ bindGroupLayouts: [bgl] }),
    vertex: {
      module, entryPoint: "vs_main",
      buffers: [{
        arrayStride: 36,
        attributes: [
          { shaderLocation: 0, offset: 0, format: "float32x3" },
          { shaderLocation: 1, offset: 12, format: "float32x3" },
          { shaderLocation: 2, offset: 24, format: "float32x3" },
        ],
      }],
    },
    fragment: { module, entryPoint: "fs_main", targets: [{ format }] },
    primitive: { topology: "triangle-list", cullMode: "none" },
    depthStencil: { format: "depth24plus", depthWriteEnabled: true, depthCompare: "less" },
  })

  async function applyScene(s: any) {
    if (s.geometryToken !== geomVersion) {
      geomVersion = s.geometryToken
      try { applyGeometry(s.geometry) } catch (e: any) { setStatus("geometry: " + e.message); return }
    }
    if (s.version === version) return
    version = s.version
    if (imageMode) { setStatus("v" + s.version + (s.title ? " — " + s.title : "") + " (image)"); return }
    const module = device.createShaderModule({ code: s.code })
    const info = await module.getCompilationInfo()
    if (info.messages.some((m: any) => m.type === "error")) {
      setStatus("v" + s.version + ": WGSL compile error")
      return
    }
    device.pushErrorScope("validation")
    const p = device.createRenderPipeline(desc(module))
    const err = await device.popErrorScope()
    if (err) { setStatus("v" + s.version + ": pipeline error"); return }
    pipeline = p
    setStatus("v" + s.version + (s.title ? " — " + s.title : ""))
  }

  async function pull() {
    try {
      const r = await fetch(VIZ_URL + "/api/state?meta=1", { cache: "no-store" })
      if (!r.ok) return
      const m = await r.json()
      if (m.version === version && m.geometryToken === geomVersion) return
      const full = await fetch(VIZ_URL + "/api/state", { cache: "no-store" })
      if (full.ok) await applyScene(await full.json())
    } catch {
      setStatus("viz-server unreachable: " + VIZ_URL)
    }
  }

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const w = Math.max(1, Math.round(canvas.clientWidth * dpr))
    const h = Math.max(1, Math.round(canvas.clientHeight * dpr))
    if (w < 2 || h < 2) return
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w
      canvas.height = h
      if (depthTex) depthTex.destroy()
      depthTex = device.createTexture({ size: [w, h, 1], format: "depth24plus", usage: GPUTextureUsage.RENDER_ATTACHMENT })
    }
  }

  let raf = 0
  function frame(nowMs: number) {
    raf = requestAnimationFrame(frame)
    const now = nowMs * 0.001
    const dt = Math.min(last ? now - last : 0, 0.1)
    last = now
    time += dt
    resize()
    if (!depthTex) return
    if (imageMode) { if (!imageReady || !imageBind) return }
    else if (volumeMode) { if (!volumeReady || !volBind) return }
    else if (!pipeline || !vbuf || !ibuf) return
    const model = m4mul(m4rotY(time * 0.55 + vizCam.yaw), m4rotX(time * 0.33 + vizCam.pitch))
    const eye = [Math.sin(time * 0.21) * 1.1, 0.85 + Math.sin(time * 0.17) * 0.35, 6]
    const view = m4look(eye, [0, 0, 0], [0, 1, 0])
    const proj = m4persp((45 * Math.PI) / 180, canvas.width / canvas.height, 0.1, 100)
    const mvp = m4mul(proj, m4mul(view, model))
    uniforms.set(mvp, 0)
    uniforms.set(model, 16)
    uniforms.set([Math.sin(time * 0.9) * 4.6, 2.3 + Math.sin(time * 1.31) * 1.4, Math.cos(time * 0.9) * 4.6, 1], 32)
    uniforms.set([eye[0], eye[1], eye[2], imageMode ? canvas.width / canvas.height : 1], 36)
    uniforms.set([34, 0.55, time, imageMode ? imageAspect : 0], 40)
    device.queue.writeBuffer(ubuf, 0, uniforms)
    if (volumeMode && volMeta) {
      const hx = volMeta.dims[0] * volMeta.spacing[0] / 2
      const hy = volMeta.dims[1] * volMeta.spacing[1] / 2
      const hz = volMeta.dims[2] * volMeta.spacing[2] / 2
      const diag = Math.hypot(hx, hy, hz)
      const aspect = Math.max(0.35, canvas.width / Math.max(1, canvas.height))
      const fit = Math.max(hz, hx / aspect, hy)
      const rad = (fit / 0.5) * 1.25 * (6 / 6)
      const yaw = time * 0.12, pitch = 0.25
      const cp = Math.cos(pitch)
      const ex = Math.sin(yaw) * cp * rad, ey = Math.sin(pitch) * rad, ez = Math.cos(yaw) * cp * rad
      let fx = -ex, fy = -ey, fz = -ez
      const fl = Math.hypot(fx, fy, fz) || 1; fx /= fl; fy /= fl; fz /= fl
      let rx = -fz, ry = 0, rz = fx
      const rl = Math.hypot(rx, ry, rz) || 1; rx /= rl; ry /= rl; rz /= rl
      const ux = ry * fz - rz * fy, uy = rz * fx - rx * fz, uz = rx * fy - ry * fx
      const step = (volMeta.spacing[0] + volMeta.spacing[1] + volMeta.spacing[2]) / 3 * 1.4
      volU.set([ex, ey, ez, rad], 0)
      volU.set([rx, ry, rz, 0], 4)
      volU.set([ux, uy, uz, 0], 8)
      volU.set([fx, fy, fz, 0], 12)
      volU.set([volMode, volThr, step, time], 16)
      volU.set([hx, hy, hz, 0], 20)
      volU.set([volMeta.min, volMeta.max, canvas.width / canvas.height,
        (volMeta.band / 2) / Math.max(1, volMeta.max - volMeta.min)], 24)
      volU.set([volMeta.clip[0], volMeta.clip[1], volMeta.clip[2], 0], 28)
      device.queue.writeBuffer(volUbuf, 0, volU)
    }
    const enc = device.createCommandEncoder()
    const passDesc: any = {
      colorAttachments: [{
        view: context.getCurrentTexture().createView(),
        clearValue: { r: 0.043, g: 0.055, b: 0.082, a: 1 },
        loadOp: "clear", storeOp: "store",
      }],
    }
    if (!imageMode && !volumeMode) passDesc.depthStencilAttachment = { view: depthTex.createView(), depthClearValue: 1, depthLoadOp: "clear", depthStoreOp: "store" }
    const pass = enc.beginRenderPass(passDesc)
    if (imageMode && imageReady && imageBind) {
      pass.setPipeline(imagePipeline)
      pass.setBindGroup(0, imageBind)
      pass.draw(6)
    } else if (volumeMode && volumeReady && volBind) {
      pass.setPipeline(volPipe)
      pass.setBindGroup(0, volBind)
      pass.draw(6)
    } else {
      pass.setPipeline(pipeline)
      pass.setBindGroup(0, bindGroup)
      pass.setVertexBuffer(0, vbuf)
      pass.setIndexBuffer(ibuf, indexFormat)
      pass.drawIndexed(indexCount)
    }
    pass.end()
    device.queue.submit([enc.finish()])
  }

  applyGeometry(null)
  vizStream = {
    orbit(dx, dy) { vizCam.yaw += dx; vizCam.pitch += dy; scheduleStream(true) },
    zoom(dy) {
      vizCam.dist = Math.min(20, Math.max(2.8, vizCam.dist * (1 + Math.sign(dy) * 0.08)))
      scheduleStream(false)
    },
  }
  const iv = setInterval(pull, 800)
  await pull()
  raf = requestAnimationFrame(frame)
  return () => { cancelAnimationFrame(raf); clearInterval(iv); vizStream = null }
}

function VizView() {
  let canvas: HTMLCanvasElement | undefined
  let status: HTMLDivElement | undefined
  let dragging = false, lx = 0, ly = 0
  const down = (e: PointerEvent) => {
    dragging = true; lx = e.clientX; ly = e.clientY
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  }
  const move = (e: PointerEvent) => {
    if (!dragging) return
    vizStream?.orbit((e.clientX - lx) * 0.008, (e.clientY - ly) * 0.008)
    lx = e.clientX; ly = e.clientY
  }
  const up = () => { dragging = false }
  onMount(() => {
    let stop = () => {}
    void startViz(canvas!, (t) => { if (status) status.textContent = t }).then((fn) => { stop = fn })
    onCleanup(() => stop())
  })
  return (
    <div style={{ position: "relative", width: "100%", height: "100%", background: "#0d1017" }}>
      <canvas
        ref={canvas}
        style={{ width: "100%", height: "100%", display: "block", "touch-action": "none" }}
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={up}
        onWheel={(e) => { e.preventDefault(); vizStream?.zoom(e.deltaY) }}
      />
      <div
        ref={status}
        style={{ position: "absolute", left: "8px", bottom: "6px", color: "#8fa3c8", font: "11px monospace", opacity: "0.8" }}
      >
        connecting…
      </div>
    </div>
  )
}

export default Plugin.define({
  i18n: {
    en: { title: "WGSL Viz", "command.open": "Open WGSL Viz", "menu.open": "WGSL Viz" },
  },
  setup(ctx) {
    const tab: PanelTab = {
      id: "main",
      get title() { return ctx.t("title") },
      closable: "compact",
      fallback: true,
    }

    ctx.add(Panel, {
      id: "main",
      region: "side",
      list: (input) => (input.open.includes("main") ? [tab] : []),
      render: () => <VizView />,
    })

    ctx.add(Command, () => ({
      id: "open",
      title: ctx.t("command.open"),
      run: () => {
        const s = ctx.sessions.current()
        if (s) ctx.layout.open(`${ctx.id}:main`, s)
      },
    }))

    ctx.add(MenuItem, (): MenuItem => {
      const s = ctx.sessions.current()
      return {
        menu: "session.panel",
        id: "open",
        title: ctx.t("menu.open"),
        icon: "globe",
        opened: !!s && ctx.layout.state(`${ctx.id}:main`, s) !== "closed",
        run: () => { if (s) ctx.layout.open(`${ctx.id}:main`, s) },
      }
    })

    // Auto-open: an agent push with focus=true bumps focusToken on the
    // viz-server; the window notices and opens the panel by itself.
    let lastFocus = -1
    const iv = setInterval(() => {
      void (async () => {
        try {
          const r = await fetch(VIZ_URL + "/api/state?meta=1", { cache: "no-store" })
          if (!r.ok) return
          const m = (await r.json()) as { focusToken: number }
          if (lastFocus === -1) { lastFocus = m.focusToken; return }
          if (m.focusToken !== lastFocus) {
            lastFocus = m.focusToken
            const s = ctx.sessions.current()
            if (s && ctx.layout.state(`${ctx.id}:main`, s) === "closed") ctx.layout.open(`${ctx.id}:main`, s)
          }
        } catch { /* viz-server down: nothing to focus */ }
      })()
    }, 1500)
    return () => clearInterval(iv)
  },
})
