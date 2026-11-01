// =====================================================================
//  Phong — универсальный шаблон освещения (cube / sphere / custom)
//  Контракт: vs_main / fs_main, uniform group 0 binding 0
//  (mvp, model, lightPos, cameraPos, params = (shininess, spec, time, 0))
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

@vertex
fn vs_main(
  @location(0) position : vec3<f32>,
  @location(1) normal   : vec3<f32>,
  @location(2) color    : vec3<f32>,
) -> VsOut {
  var out : VsOut;
  let world    = u.model * vec4<f32>(position, 1.0);
  out.worldPos = world.xyz;
  out.normal   = normalize((u.model * vec4<f32>(normal, 0.0)).xyz);
  out.color    = color;
  out.clipPos  = u.mvp * vec4<f32>(position, 1.0);
  return out;
}

@fragment
fn fs_main(f : VsOut) -> @location(0) vec4<f32> {
  let N = normalize(f.normal);
  let L = normalize(u.lightPos.xyz - f.worldPos);
  let V = normalize(u.cameraPos.xyz - f.worldPos);
  let R = reflect(-L, N);

  let ambient  = 0.16 * f.color;
  let diffuse  = max(dot(N, L), 0.0) * f.color;
  let specular = pow(max(dot(R, V), 0.0), u.params.x) * u.params.y * vec3<f32>(1.0);

  let lit = ambient + (diffuse + specular) * vec3<f32>(1.0, 0.96, 0.90);
  return vec4<f32>(lit, 1.0);
}
