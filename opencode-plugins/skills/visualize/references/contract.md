# Контракт сцены viz-сервера

## WGSL

- Точки входа обязательны: `@vertex vs_main`, `@fragment fs_main -> @location(0) vec4<f32>`.
- Vertex-атрибуты (interleaved, stride 36 байт):
  `@location(0) position vec3`, `@location(1) normal vec3`, `@location(2) color vec3`.
- Uniform `@group(0) @binding(0)`, struct ровно такой (176 байт):

```wgsl
struct Uniforms {
  mvp       : mat4x4<f32>,   // projection * view * model
  model     : mat4x4<f32>,   // только вращение; нормали = mat3(model)
  lightPos  : vec4<f32>,     // xyz — орбитальный источник света
  cameraPos : vec4<f32>,     // xyz — позиция камеры
  params    : vec4<f32>,     // x=shininess, y=specStrength, z=time (сек), w=0
};
```

- Геометрия: triangle-list, cull off, depth24plus, depthCompare less.
- Камера: дистанция ~6, fov 45°, цель — начало координат; меш центрируй в原点
  и масштабируй примерно в [-2, 2], иначе не попадёт в кадр.

## Геометрия (поле `geometry` в POST /api/scene)

| kind     | Параметры                          | Что даёт                                  |
| -------- | ---------------------------------- | ----------------------------------------- |
| `cube`   | —                                  | куб 2×2×2, цветные грани (default)         |
| `sphere` | `radius`, `segments`, `rings`      | UV-сфера, нормали наружу, градиент по Y    |
| `grid`   | `nx`, `ny`, `size`                 | плоскость XZ (нормаль +Y) для heightfield  |
| `custom` | `positions`, `normals`, `colors`, `indices` | произвольный меш (flat f32/u32 массивы) |
| `image`  | `data` (base64 PNG) или `url` | готовый рендер (например, из FERRUM) на текстурном кваде |
| `volume` | `url` (raw u8), `dims`, `spacing`, `min`, `max`, `mode`, `threshold` | интерактивный raycasting объёма: 0 isosurface, 1 MIP, 2 TF-полоса; drag/wheel/1/2/3/-/= |
| `stream` | `url` (frame server), `preset`, `clip`/`clipStr`, `size`, `dragSize`, `threshold` | интерактивные кадры ferrum: drag → dragSize px, отпустил → size px; wheel — зум |

- `custom`: длины `positions == normals == colors`, кратны 3; `indices` — треугольники.
- Индексы > 65535 → раннер сам переключится на uint32.
- Если `geometry` не передано — сохраняется геометрия предыдущей сцены.

## HTTP API

- `POST /api/scene` (алиас `/api/shader`): JSON `{code, title?, geometry?, focus?}`
  или raw WGSL (тогда focus=true, геометрия не меняется).
  `focus:true` (default) инкрементирует `focusToken` → GUI-панель сама открывается.
- `GET /api/state?meta=1` → `{version, focusToken, geometryToken, title}` (дёшево, для поллинга).
- `GET /api/state` → полное состояние incl. `code` и `geometry`.
- Рендереры поллят meta каждые ~0.8 c и тянут полное состояние только при изменении
  `version`/`geometryToken`.

## Инструменты плагина wgslviz

- `push {code, title?, geometry?, focus?}` → POST /api/scene; панель открывается сама.
- `status {}` → текущие version/geometryToken/title.
