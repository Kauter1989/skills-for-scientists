"use strict";Object.defineProperties(exports,{__esModule:{value:!0},[Symbol.toStringTag]:{value:"Module"}});const N=require("solid-js/web"),$e=require("solid-js"),H=require("@opencode/plugin/gui");var nt=N.template('<div style=position:relative;width:100%;height:100%;background:#0d1017><canvas style=width:100%;height:100%;display:block;touch-action:none></canvas><div style="position:absolute;left:8px;bottom:6px;color:#8fa3c8;font:11px monospace;opacity:0.8">connecting…');const E="http://127.0.0.1:8787",S={yaw:0,pitch:0,dist:6};let J=null;const $=()=>new Float32Array(16);function ye(e,i,s=$()){for(let o=0;o<4;o++)for(let t=0;t<4;t++){let a=0;for(let n=0;n<4;n++)a+=e[n*4+t]*i[o*4+n];s[o*4+t]=a}return s}function at(e,i,s,o,t=$()){const a=1/Math.tan(e/2);return t.fill(0),t[0]=a/i,t[5]=a,t[10]=o/(s-o),t[11]=-1,t[14]=s*o/(s-o),t}function ot(e,i,s,o=$()){let t=e[0]-i[0],a=e[1]-i[1],n=e[2]-i[2],l=Math.hypot(t,a,n);t/=l,a/=l,n/=l;let c=s[1]*n-s[2]*a,f=s[2]*t-s[0]*n,p=s[0]*a-s[1]*t;l=Math.hypot(c,f,p),c/=l,f/=l,p/=l;const g=a*p-n*f,y=n*c-t*p,P=t*f-a*c;return o.set([c,g,t,0,f,y,a,0,p,P,n,0,-(c*e[0]+f*e[1]+p*e[2]),-(g*e[0]+y*e[1]+P*e[2]),-(t*e[0]+a*e[1]+n*e[2]),1]),o}function st(e,i=$()){const s=Math.cos(e),o=Math.sin(e);return i.set([1,0,0,0,0,s,o,0,0,-o,s,0,0,0,0,1]),i}function lt(e,i=$()){const s=Math.cos(e),o=Math.sin(e);return i.set([s,0,-o,0,0,1,0,0,o,0,s,0,0,0,0,1]),i}function qe(e){return e=Math.min(1,Math.max(0,e)),[.25+.7*e,.45+.25*Math.sin(e*Math.PI),.85-.55*e]}function ct(){const e=[{n:[0,0,1],c:[.96,.45,.35],v:[[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]]},{n:[0,0,-1],c:[.3,.62,.92],v:[[1,-1,-1],[-1,-1,-1],[-1,1,-1],[1,1,-1]]},{n:[1,0,0],c:[.96,.76,.3],v:[[1,-1,1],[1,-1,-1],[1,1,-1],[1,1,1]]},{n:[-1,0,0],c:[.55,.8,.45],v:[[-1,-1,-1],[-1,-1,1],[-1,1,1],[-1,1,-1]]},{n:[0,1,0],c:[.72,.55,.92],v:[[-1,1,1],[1,1,1],[1,1,-1],[-1,1,-1]]},{n:[0,-1,0],c:[.38,.82,.76],v:[[-1,-1,-1],[1,-1,-1],[1,-1,1],[-1,-1,1]]}],i=new Float32Array(216),s=[];let o=0;for(const t of e){const a=o/9;for(const n of t.v)i[o++]=n[0],i[o++]=n[1],i[o++]=n[2],i[o++]=t.n[0],i[o++]=t.n[1],i[o++]=t.n[2],i[o++]=t.c[0],i[o++]=t.c[1],i[o++]=t.c[2];s.push(a,a+1,a+2,a,a+2,a+3)}return{vertices:i,indices:s}}function ut(e=1,i=48,s=32){const o=[],t=[];for(let a=0;a<=s;a++){const n=a/s*Math.PI;for(let l=0;l<=i;l++){const c=l/i*Math.PI*2,f=Math.sin(n)*Math.cos(c),p=Math.cos(n),g=Math.sin(n)*Math.sin(c),y=qe((p+1)/2);o.push(f*e,p*e,g*e,f,p,g,y[0],y[1],y[2])}}for(let a=0;a<s;a++)for(let n=0;n<i;n++){const l=a*(i+1)+n,c=l+i+1;t.push(l,c,l+1,l+1,c,c+1)}return{vertices:new Float32Array(o),indices:t}}function ft(e=96,i=96,s=4){const o=[],t=[],a=s/2;for(let n=0;n<=i;n++)for(let l=0;l<=e;l++){const c=l/e*s-a,f=n/i*s-a,p=qe(1-Math.hypot(c,f)/a);o.push(c,0,f,0,1,0,p[0],p[1],p[2])}for(let n=0;n<i;n++)for(let l=0;l<e;l++){const c=n*(e+1)+l,f=c+e+1;t.push(c,f,c+1,c+1,f,f+1)}return{vertices:new Float32Array(o),indices:t}}function mt(e){const i=e.positions,s=e.normals,o=e.colors,t=e.indices;if(!Array.isArray(i)||!Array.isArray(s)||!Array.isArray(o)||!Array.isArray(t))throw new Error("custom geometry: positions/normals/colors/indices required");if(i.length%3||i.length!==s.length||i.length!==o.length)throw new Error("custom geometry: array sizes inconsistent");const a=new Float32Array(i.length*3);for(let n=0,l=0;n<i.length;n+=3)a[l++]=i[n],a[l++]=i[n+1],a[l++]=i[n+2],a[l++]=s[n],a[l++]=s[n+1],a[l++]=s[n+2],a[l++]=o[n],a[l++]=o[n+1],a[l++]=o[n+2];return{vertices:a,indices:t}}function pt(e){const i=e&&e.kind||"cube";return i==="sphere"?ut(e.radius??1,e.segments??48,e.rings??32):i==="grid"?ft(e.nx??96,e.ny??96,e.size??4):i==="custom"?mt(e):ct()}async function dt(e,i){const s=navigator;if(!s.gpu)return i("WebGPU is not available in this window"),()=>{};const o=await s.gpu.requestAdapter();if(!o)return i("No GPU adapter"),()=>{};const t=await o.requestDevice(),a=e.getContext("webgpu"),n=s.gpu.getPreferredCanvasFormat();a.configure({device:t,format:n,alphaMode:"opaque"});const l=new Float32Array(44),c=t.createBuffer({size:l.byteLength,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST}),f=t.createBindGroupLayout({entries:[{binding:0,visibility:GPUShaderStage.VERTEX|GPUShaderStage.FRAGMENT,buffer:{type:"uniform"}}]}),p=t.createBindGroup({layout:f,entries:[{binding:0,resource:{buffer:c}}]});let g=null,y=null,P=null,Z=null,K="uint16",ge=0,Q=-1,ee=-1,M=0,te=0;const De=`
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
`;let T=!1,B=!1,re=null,q=null,I=null,xe=null,ie=null,be=1;function we(){if(re)return;const r=t.createShaderModule({code:De});ie=t.createBindGroupLayout({entries:[{binding:0,visibility:GPUShaderStage.VERTEX|GPUShaderStage.FRAGMENT,buffer:{type:"uniform"}},{binding:1,visibility:GPUShaderStage.FRAGMENT,texture:{sampleType:"float"}},{binding:2,visibility:GPUShaderStage.FRAGMENT,sampler:{}}]}),re=t.createRenderPipeline({layout:t.createPipelineLayout({bindGroupLayouts:[ie]}),vertex:{module:r,entryPoint:"vs_img"},fragment:{module:r,entryPoint:"fs_img",targets:[{format:n}]},primitive:{topology:"triangle-list"}}),xe=t.createSampler({magFilter:"linear",minFilter:"linear"})}async function Pe(r){we();const u=await createImageBitmap(r);I&&I.destroy(),I=t.createTexture({size:[u.width,u.height,1],format:"rgba8unorm",usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST|GPUTextureUsage.RENDER_ATTACHMENT}),t.queue.copyExternalImageToTexture({source:u,flipY:!0},{texture:I},[u.width,u.height,1]),be=u.width/u.height,q=t.createBindGroup({layout:ie,entries:[{binding:0,resource:{buffer:c}},{binding:1,resource:I.createView()},{binding:2,resource:xe}]}),B=!0,u.close&&u.close()}async function We(r){we();const u=await fetch(r,{cache:"no-store"});if(!u.ok)throw new Error("image fetch "+u.status);await Pe(await u.blob())}let ne=!1,ae=!1,oe=!1,Me=0,se="",le="lung_vessels",D="",Te=640,ce=320,Ge=-400,Se=0;async function W(r){if(se){if(ae){oe=!0,Me=r;return}ae=!0;try{const u={yaw:S.yaw,pitch:S.pitch,dist:1.35*(S.dist/6),mode:"transfer_function",preset:le,threshold:Ge,clip:D,size:r},m=await fetch(se,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(u),signal:AbortSignal.timeout(8e3)});if(!m.ok)throw new Error("HTTP "+m.status);await Pe(await m.blob()),i("ferrum "+le+(D?", clip "+D:"")+" — "+r+"px")}catch(u){i("stream: "+u.message)}ae=!1,oe&&(oe=!1,W(Me||r))}}function ue(r){ne&&(clearTimeout(Se),r?W(ce):Se=setTimeout(()=>W(Te),350))}const Ye=`
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
`;let V=!1,Y=!1,fe=null,X=null,L=null,me=null,Ue=null,pe=null,d=null,ze=0,Ve=-400;const G=new Float32Array(32);function Xe(){if(fe)return;const r=t.createShaderModule({code:Ye});me=t.createBindGroupLayout({entries:[{binding:0,visibility:GPUShaderStage.VERTEX|GPUShaderStage.FRAGMENT,buffer:{type:"uniform"}},{binding:1,visibility:GPUShaderStage.FRAGMENT,texture:{sampleType:"float",viewDimension:"3d"}},{binding:2,visibility:GPUShaderStage.FRAGMENT,sampler:{}}]}),fe=t.createRenderPipeline({layout:t.createPipelineLayout({bindGroupLayouts:[me]}),vertex:{module:r,entryPoint:"vs_vol"},fragment:{module:r,entryPoint:"fs_vol",targets:[{format:n}]},primitive:{topology:"triangle-list"}}),Ue=t.createSampler({magFilter:"linear",minFilter:"linear",mipmapFilter:"linear"}),pe=t.createBuffer({size:G.byteLength,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST})}async function je(r){Xe();const u=await fetch(r.url,{cache:"no-store"});if(!u.ok)throw new Error("volume fetch "+u.status);const m=new Uint8Array(await u.arrayBuffer()),[x,v,h]=r.dims;if(m.length!==x*v*h)throw new Error("volume size mismatch");L&&L.destroy(),L=t.createTexture({size:[x,v,h],format:"r8unorm",dimension:"3d",usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});const b=Math.ceil(x/256)*256;let R=m;if(b!==x){R=new Uint8Array(b*v*h);for(let U=0;U<h;U++)for(let z=0;z<v;z++)R.set(m.subarray((U*v+z)*x,(U*v+z)*x+x),(U*v+z)*b)}t.queue.writeTexture({texture:L},R,{bytesPerRow:b,rowsPerImage:v},[x,v,h]),d={dims:r.dims,spacing:r.spacing||[1,1,1],min:r.min??0,max:r.max??1,band:r.band??400,clip:r.clip||[0,0,0]},r.mode!==void 0&&(ze=r.mode),r.threshold!==void 0&&(Ve=r.threshold),X=t.createBindGroup({layout:me,entries:[{binding:0,resource:{buffer:pe}},{binding:1,resource:L.createView()},{binding:2,resource:Ue}]}),Y=!0}function Ee(r){if(r&&r.kind==="stream"){V=!1,T=!0,B=!1,ne=!0,se=/^https?:/.test(r.url||"")?r.url:E+(r.url||""),le=r.preset||"lung_vessels",D=r.clip||r.clipStr||"",Te=r.size||640,ce=r.dragSize||320,Ge=r.threshold??-400,W(ce),ue(!1);return}if(ne=!1,r&&r.kind==="volume"){T=!1,V=!0,Y=!1;const h=/^https?:/.test(r.url||"")?r.url:E+(r.url||"");je(Object.assign({},r,{url:h})).catch(b=>i("volume: "+b.message));return}if(V=!1,r&&r.kind==="image"){T=!0,B=!1;const h=/^https?:/.test(r.url||"")?r.url:E+(r.url||"");We(h).catch(b=>i("image: "+b.message));return}T=!1;const{vertices:u,indices:m}=pt(r);K=m.reduce((h,b)=>b>h?b:h,0)>65535?"uint32":"uint16",ge=m.length;const v=K==="uint32"?new Uint32Array(m):new Uint16Array(m);g&&g.destroy(),y&&y.destroy(),g=t.createBuffer({size:u.byteLength,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST}),t.queue.writeBuffer(g,0,u),y=t.createBuffer({size:v.byteLength,usage:GPUBufferUsage.INDEX|GPUBufferUsage.COPY_DST}),t.queue.writeBuffer(y,0,v)}const He=r=>({layout:t.createPipelineLayout({bindGroupLayouts:[f]}),vertex:{module:r,entryPoint:"vs_main",buffers:[{arrayStride:36,attributes:[{shaderLocation:0,offset:0,format:"float32x3"},{shaderLocation:1,offset:12,format:"float32x3"},{shaderLocation:2,offset:24,format:"float32x3"}]}]},fragment:{module:r,entryPoint:"fs_main",targets:[{format:n}]},primitive:{topology:"triangle-list",cullMode:"none"},depthStencil:{format:"depth24plus",depthWriteEnabled:!0,depthCompare:"less"}});async function Je(r){if(r.geometryToken!==ee){ee=r.geometryToken;try{Ee(r.geometry)}catch(h){i("geometry: "+h.message);return}}if(r.version===Q)return;if(Q=r.version,T){i("v"+r.version+(r.title?" — "+r.title:"")+" (image)");return}const u=t.createShaderModule({code:r.code});if((await u.getCompilationInfo()).messages.some(h=>h.type==="error")){i("v"+r.version+": WGSL compile error");return}t.pushErrorScope("validation");const x=t.createRenderPipeline(He(u));if(await t.popErrorScope()){i("v"+r.version+": pipeline error");return}Z=x,i("v"+r.version+(r.title?" — "+r.title:""))}async function Ae(){try{const r=await fetch(E+"/api/state?meta=1",{cache:"no-store"});if(!r.ok)return;const u=await r.json();if(u.version===Q&&u.geometryToken===ee)return;const m=await fetch(E+"/api/state",{cache:"no-store"});m.ok&&await Je(await m.json())}catch{i("viz-server unreachable: "+E)}}function Ze(){const r=Math.min(window.devicePixelRatio||1,2),u=Math.max(1,Math.round(e.clientWidth*r)),m=Math.max(1,Math.round(e.clientHeight*r));u<2||m<2||(e.width!==u||e.height!==m)&&(e.width=u,e.height=m,P&&P.destroy(),P=t.createTexture({size:[u,m,1],format:"depth24plus",usage:GPUTextureUsage.RENDER_ATTACHMENT}))}let de=0;function _e(r){de=requestAnimationFrame(_e);const u=r*.001,m=Math.min(te?u-te:0,.1);if(te=u,M+=m,Ze(),!P)return;if(T){if(!B||!q)return}else if(V){if(!Y||!X)return}else if(!Z||!g||!y)return;const x=ye(lt(M*.55+S.yaw),st(M*.33+S.pitch)),v=[Math.sin(M*.21)*1.1,.85+Math.sin(M*.17)*.35,6],h=ot(v,[0,0,0],[0,1,0]),b=at(45*Math.PI/180,e.width/e.height,.1,100),R=ye(b,ye(h,x));if(l.set(R,0),l.set(x,16),l.set([Math.sin(M*.9)*4.6,2.3+Math.sin(M*1.31)*1.4,Math.cos(M*.9)*4.6,1],32),l.set([v[0],v[1],v[2],T?e.width/e.height:1],36),l.set([34,.55,M,T?be:0],40),t.queue.writeBuffer(c,0,l),V&&d){const Be=d.dims[0]*d.spacing[0]/2,Ie=d.dims[1]*d.spacing[1]/2,Le=d.dims[2]*d.spacing[2]/2,Qe=Math.max(.35,e.width/Math.max(1,e.height)),j=Math.max(Le,Be/Qe,Ie)/.5*1.25*(6/6),Re=M*.12,Fe=.25,ke=Math.cos(Fe),Ce=Math.sin(Re)*ke*j,Oe=Math.sin(Fe)*j,Ne=Math.cos(Re)*ke*j;let A=-Ce,F=-Oe,_=-Ne;const ve=Math.hypot(A,F,_)||1;A/=ve,F/=ve,_/=ve;let k=-_,C=0,O=A;const he=Math.hypot(k,C,O)||1;k/=he,C/=he,O/=he;const et=C*_-O*F,tt=O*A-k*_,rt=k*F-C*A,it=(d.spacing[0]+d.spacing[1]+d.spacing[2])/3*1.4;G.set([Ce,Oe,Ne,j],0),G.set([k,C,O,0],4),G.set([et,tt,rt,0],8),G.set([A,F,_,0],12),G.set([ze,Ve,it,M],16),G.set([Be,Ie,Le,0],20),G.set([d.min,d.max,e.width/e.height,d.band/2/Math.max(1,d.max-d.min)],24),G.set([d.clip[0],d.clip[1],d.clip[2],0],28),t.queue.writeBuffer(pe,0,G)}const U=t.createCommandEncoder(),z={colorAttachments:[{view:a.getCurrentTexture().createView(),clearValue:{r:.043,g:.055,b:.082,a:1},loadOp:"clear",storeOp:"store"}]};!T&&!V&&(z.depthStencilAttachment={view:P.createView(),depthClearValue:1,depthLoadOp:"clear",depthStoreOp:"store"});const w=U.beginRenderPass(z);T&&B&&q?(w.setPipeline(re),w.setBindGroup(0,q),w.draw(6)):V&&Y&&X?(w.setPipeline(fe),w.setBindGroup(0,X),w.draw(6)):(w.setPipeline(Z),w.setBindGroup(0,p),w.setVertexBuffer(0,g),w.setIndexBuffer(y,K),w.drawIndexed(ge)),w.end(),t.queue.submit([U.finish()])}Ee(null),J={orbit(r,u){S.yaw+=r,S.pitch+=u,ue(!0)},zoom(r){S.dist=Math.min(20,Math.max(2.8,S.dist*(1+Math.sign(r)*.08))),ue(!1)}};const Ke=setInterval(Ae,800);return await Ae(),de=requestAnimationFrame(_e),()=>{cancelAnimationFrame(de),clearInterval(Ke),J=null}}function vt(){let e,i,s=!1,o=0,t=0;const a=c=>{s=!0,o=c.clientX,t=c.clientY,c.currentTarget.setPointerCapture(c.pointerId)},n=c=>{s&&(J?.orbit((c.clientX-o)*.008,(c.clientY-t)*.008),o=c.clientX,t=c.clientY)},l=()=>{s=!1};return $e.onMount(()=>{let c=()=>{};dt(e,f=>{i&&(i.textContent=f)}).then(f=>{c=f}),$e.onCleanup(()=>c())}),(()=>{var c=nt(),f=c.firstChild,p=f.nextSibling;f.addEventListener("wheel",P=>{P.preventDefault(),J?.zoom(P.deltaY)}),f.$$pointerup=l,f.$$pointermove=n,f.$$pointerdown=a;var g=e;typeof g=="function"?N.use(g,f):e=f;var y=i;return typeof y=="function"?N.use(y,p):i=p,c})()}const ht=H.Plugin.define({i18n:{en:{title:"WGSL Viz","command.open":"Open WGSL Viz","menu.open":"WGSL Viz"}},setup(e){const i={id:"main",get title(){return e.t("title")},closable:"compact",fallback:!0};e.add(H.Panel,{id:"main",region:"side",list:t=>t.open.includes("main")?[i]:[],render:()=>N.createComponent(vt,{})}),e.add(H.Command,()=>({id:"open",title:e.t("command.open"),run:()=>{const t=e.sessions.current();t&&e.layout.open(`${e.id}:main`,t)}})),e.add(H.MenuItem,()=>{const t=e.sessions.current();return{menu:"session.panel",id:"open",title:e.t("menu.open"),icon:"globe",opened:!!t&&e.layout.state(`${e.id}:main`,t)!=="closed",run:()=>{t&&e.layout.open(`${e.id}:main`,t)}}});let s=-1;const o=setInterval(()=>{(async()=>{try{const t=await fetch(E+"/api/state?meta=1",{cache:"no-store"});if(!t.ok)return;const a=await t.json();if(s===-1){s=a.focusToken;return}if(a.focusToken!==s){s=a.focusToken;const n=e.sessions.current();n&&e.layout.state(`${e.id}:main`,n)==="closed"&&e.layout.open(`${e.id}:main`,n)}}catch{}})()},1500);return()=>clearInterval(o)}});N.delegateEvents(["pointerdown","pointermove","pointerup"]);exports.default=ht;
