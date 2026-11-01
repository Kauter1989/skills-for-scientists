#!/usr/bin/env python3
"""Генератор мешей для скилла visualize: печатает объект geometry
(kind=custom) для scene-API viz-сервера (POST /api/scene).

Примеры:
  python gen_geometry.py --surface "0.4*sin(1.5*x)*cos(1.5*z) + 0.1*sin(4*x+3*z)" \
         --nx 128 --ny 128 --size 6 --out geom.json
  python gen_geometry.py --sphere 1.2 --segments 64 --rings 48
  python gen_geometry.py --grid 96 96 4

В формуле --surface доступны: x, z, pi, e, sin cos tan exp sqrt log log2 log10
abs hypot atan2 pow. Нормали считаются конечными разностями, цвет — градиентом
по высоте (или --color r,g,b).
"""
import argparse
import json
import math

SAFE = {n: getattr(math, n) for n in (
    "sin", "cos", "tan", "exp", "sqrt", "log", "log2", "log10",
    "fabs", "hypot", "atan2", "pow", "pi", "e",
)}
SAFE["abs"] = abs


def ramp(t):
    t = min(1.0, max(0.0, t))
    return [round(0.25 + 0.7 * t, 4),
            round(0.45 + 0.25 * math.sin(t * math.pi), 4),
            round(0.85 - 0.55 * t, 4)]


def sphere(radius, segments, rings):
    P, N, C, idx = [], [], [], []
    for y in range(rings + 1):
        phi = y / rings * math.pi
        for x in range(segments + 1):
            theta = x / segments * 2 * math.pi
            nx = math.sin(phi) * math.cos(theta)
            ny = math.cos(phi)
            nz = math.sin(phi) * math.sin(theta)
            P += [round(nx * radius, 4), round(ny * radius, 4), round(nz * radius, 4)]
            N += [round(nx, 4), round(ny, 4), round(nz, 4)]
            C += ramp((ny + 1) / 2)
    for y in range(rings):
        for x in range(segments):
            a = y * (segments + 1) + x
            b = a + segments + 1
            idx += [a, b, a + 1, a + 1, b, b + 1]
    return {"kind": "custom", "positions": P, "normals": N, "colors": C, "indices": idx}


def grid(nx, ny, size):
    P, N, C, idx = [], [], [], []
    half = size / 2
    for y in range(ny + 1):
        for x in range(nx + 1):
            px = x / nx * size - half
            pz = y / ny * size - half
            P += [round(px, 4), 0.0, round(pz, 4)]
            N += [0.0, 1.0, 0.0]
            C += ramp(1 - math.hypot(px, pz) / half)
    for y in range(ny):
        for x in range(nx):
            a = y * (nx + 1) + x
            b = a + nx + 1
            idx += [a, b, a + 1, a + 1, b, b + 1]
    return {"kind": "custom", "positions": P, "normals": N, "colors": C, "indices": idx}


def surface(expr, nx, ny, size, color=None):
    hf = eval("lambda x, z: " + expr, {"__builtins__": {}, **SAFE})
    half = size / 2
    e = size / (min(nx, ny) * 2)
    hs = [[hf(x / nx * size - half, y / ny * size - half) for x in range(nx + 1)]
          for y in range(ny + 1)]
    hmin = min(min(r) for r in hs)
    hmax = max(max(r) for r in hs)
    span = (hmax - hmin) or 1.0
    P, N, C, idx = [], [], [], []
    for y in range(ny + 1):
        for x in range(nx + 1):
            px = x / nx * size - half
            pz = y / ny * size - half
            h = hs[y][x]
            hx = (hf(px + e, pz) - hf(px - e, pz)) / (2 * e)
            hz = (hf(px, pz + e) - hf(px, pz - e)) / (2 * e)
            lx, ly, lz = -hx, 1.0, -hz
            ln = math.sqrt(lx * lx + ly * ly + lz * lz)
            P += [round(px, 4), round(h, 4), round(pz, 4)]
            N += [round(lx / ln, 4), round(ly / ln, 4), round(lz / ln, 4)]
            C += color if color else ramp((h - hmin) / span)
    for y in range(ny):
        for x in range(nx):
            a = y * (nx + 1) + x
            b = a + nx + 1
            idx += [a, b, a + 1, a + 1, b, b + 1]
    return {"kind": "custom", "positions": P, "normals": N, "colors": C, "indices": idx}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--surface", help="формула высоты h(x, z)")
    ap.add_argument("--sphere", type=float, help="радиус сферы")
    ap.add_argument("--grid", nargs=3, type=float, metavar=("NX", "NY", "SIZE"))
    ap.add_argument("--nx", type=int, default=128)
    ap.add_argument("--ny", type=int, default=128)
    ap.add_argument("--size", type=float, default=6.0)
    ap.add_argument("--segments", type=int, default=64)
    ap.add_argument("--rings", type=int, default=48)
    ap.add_argument("--color", help="фиксированный цвет r,g,b (0..1)")
    ap.add_argument("--out", help="файл для JSON (по умолчанию stdout)")
    a = ap.parse_args()

    color = None
    if a.color:
        color = [round(float(v), 4) for v in a.color.split(",")]

    if a.surface:
        geom = surface(a.surface, a.nx, a.ny, a.size, color)
    elif a.sphere:
        geom = sphere(a.sphere, a.segments, a.rings)
    elif a.grid:
        geom = grid(int(a.grid[0]), int(a.grid[1]), a.grid[2])
    else:
        ap.error("нужен один из --surface / --sphere / --grid")
        return

    text = json.dumps(geom, separators=(",", ":"))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"geometry written: {a.out} ({len(geom['positions']) // 3} verts, "
              f"{len(geom['indices']) // 3} tris)")
    else:
        print(text)


if __name__ == "__main__":
    main()
