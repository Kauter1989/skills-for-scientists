// =====================================================================
//  Phong Cube — WGSL / WebGPU
//  Контракт среды (точки входа обязаны называться vs_main и fs_main):
//    vertex:   @location(0) position vec3, @location(1) normal vec3,
//              @location(2) color vec3   (stride 36 байт)
//    fragment: fs_main(...) -> @location(0) vec4<f32>
//  Uniform (group 0, binding 0):
//    mvp, model : mat4x4<f32>
//    lightPos, cameraPos : vec4<f32>  (xyz используется)
//    params = (shininess, specStrength, time, 0)
//  Геометрия: 24 вершины, 36 индексов, triangle-list, cull off.
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
  let N = normalize(f.normal);                      // нормаль поверхности
  let L = normalize(u.lightPos.xyz - f.worldPos);   // направление на источник
  let V = normalize(u.cameraPos.xyz - f.worldPos);  // направление на наблюдателя
  let R = reflect(-L, N);                           // отражённый луч

  let shininess    = u.params.x;
  let specStrength = u.params.y;
  let lightColor   = vec3<f32>(1.0, 0.96, 0.90);    // тёплый источник

  // Модель Фонга: ambient + diffuse + specular
  let ambient  = 0.16 * f.color;
  let diffuse  = max(dot(N, L), 0.0) * f.color;
  let specular = pow(max(dot(R, V), 0.0), shininess) * specStrength * vec3<f32>(1.0);

  let lit = ambient + (diffuse + specular) * lightColor;
  return vec4<f32>(lit, 1.0);
}
