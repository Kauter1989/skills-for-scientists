// =====================================================================
//  Heightfield — поверхность по формуле (анимированная)
//  Геометрия: {kind:"grid", nx:128, ny:128, size:6} (плоскость XZ)
//  Высота и нормали считаются аналитически в vertex-шейдере;
//  время — u.params.z. Контракт uniform — как в phong.wgsl.
//  Замени тело height() на свою формулу (x, z — мировые координаты).
// =====================================================================

struct Uniforms {
  mvp       : mat4x4<f32>,
  model     : mat4x4<f32>,
  lightPos  : vec4<f32>,
  cameraPos : vec4<f32>,
  params    : vec4<f32>,
};

@group(0) @binding(0) var<uniform> u : Uniforms;

struct VsOut {
  @builtin(position) clipPos : vec4<f32>,
  @location(0) worldPos : vec3<f32>,
  @location(1) normal   : vec3<f32>,
  @location(2) color    : vec3<f32>,
};

fn height(p : vec2<f32>, t : f32) -> f32 {
  return 0.45 * sin(p.x * 1.6 + t) * cos(p.y * 1.6 - t * 0.7)
       + 0.18 * sin(p.x * 4.0 - t * 1.3) * sin(p.y * 3.0 + t * 0.9);
}

fn surfaceNormal(p : vec2<f32>, t : f32) -> vec3<f32> {
  let e = 0.02;
  let hx = height(p + vec2<f32>(e, 0.0), t) - height(p - vec2<f32>(e, 0.0), t);
  let hz = height(p + vec2<f32>(0.0, e), t) - height(p - vec2<f32>(0.0, e), t);
  return normalize(vec3<f32>(-hx / (2.0 * e), 1.0, -hz / (2.0 * e)));
}

fn ramp(h : f32) -> vec3<f32> {          // холодный -> тёплый по высоте
  let t = clamp(h * 1.2 + 0.5, 0.0, 1.0);
  return vec3<f32>(0.20 + 0.75 * t, 0.40 + 0.30 * sin(t * 3.14159), 0.85 - 0.60 * t);
}

@vertex
fn vs_main(
  @location(0) position : vec3<f32>,
  @location(1) normal   : vec3<f32>,
  @location(2) color    : vec3<f32>,
) -> VsOut {
  var out : VsOut;
  let t   = u.params.z;
  let h   = height(position.xz, t);
  let pos = vec3<f32>(position.x, h, position.z);
  let world    = u.model * vec4<f32>(pos, 1.0);
  out.worldPos = world.xyz;
  out.normal   = normalize((u.model * vec4<f32>(surfaceNormal(position.xz, t), 0.0)).xyz);
  out.color    = ramp(h);
  out.clipPos  = u.mvp * vec4<f32>(pos, 1.0);
  return out;
}

@fragment
fn fs_main(f : VsOut) -> @location(0) vec4<f32> {
  let N = normalize(f.normal);
  let L = normalize(u.lightPos.xyz - f.worldPos);
  let V = normalize(u.cameraPos.xyz - f.worldPos);
  let R = reflect(-L, N);

  let ambient  = 0.18 * f.color;
  let diffuse  = max(dot(N, L), 0.0) * f.color;
  let specular = pow(max(dot(R, V), 0.0), u.params.x) * u.params.y * vec3<f32>(1.0);

  let lit = ambient + (diffuse + specular) * vec3<f32>(1.0, 0.96, 0.90);
  return vec4<f32>(lit, 1.0);
}
