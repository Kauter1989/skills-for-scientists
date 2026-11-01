#!/usr/bin/env python3
"""Подготовка объёма для интерактивного volume-рендера в панели wgslviz.

Читает DICOM-папку (или NIfTI через ferrum-export, если он есть), приводит к
HU, даунсемплит до --max-dim и пишет:
  <out>.u8.raw  — нормализованный объём uint8 (x внутри строки, y строки, z срезы)
  <out>.meta.json — {"dims":[x,y,z],"spacing":[sx,sy,sz],"min":HU,"max":HU}

Пример:
  python vol_prep.py --dicom <dicom-dir> --max-dim 256 \
         --out opencode-plugins/wgsl-viz/volumes/lungs
"""
import argparse
import glob
import json
import os

import numpy as np
import pydicom


def read_dicom_volume(path):
    files = glob.glob(os.path.join(path, "*.dcm")) + glob.glob(os.path.join(path, "*.DCM"))
    if not files:
        raise SystemExit("no .dcm files in " + path)
    metas = []
    for f in files:
        ds = pydicom.dcmread(f, stop_before_pixels=True)
        z = float(getattr(ds, "SliceLocation", 0.0) or 0.0)
        idx = int(getattr(ds, "InstanceNumber", 0) or 0)
        metas.append((f, z, idx))
    metas.sort(key=lambda m: (m[1], m[2]))
    slices = []
    spacing = None
    hu_min, hu_max = 0.0, 1.0
    for f, _z, _i in metas:
        ds = pydicom.dcmread(f)
        arr = ds.pixel_array.astype(np.float32)
        slope = float(getattr(ds, "RescaleSlope", 1.0) or 1.0)
        inter = float(getattr(ds, "RescaleIntercept", 0.0) or 0.0)
        arr = arr * slope + inter
        slices.append(arr)
        if spacing is None:
            dy, dx = (float(v) for v in ds.PixelSpacing)
            dz = float(getattr(ds, "SpacingBetweenSlices", getattr(ds, "SliceThickness", 1.0)) or 1.0)
            spacing = (dx, dy, dz)
    vol = np.stack(slices, axis=0)          # (z, y, x)
    if len(metas) > 1:
        zs = np.array([m[1] for m in metas], dtype=np.float32)
        dzs = np.diff(zs)
        if len(dzs) and np.all(dzs > 0):
            spacing = (spacing[0], spacing[1], float(np.median(dzs)))
    return vol, spacing


def downsample(vol, max_dim):
    z, y, x = vol.shape
    f = 1
    while max(z, y, x) // f > max_dim:
        f += 1
    if f == 1:
        return vol
    zt, yt, xt = z // f, y // f, x // f
    cut = vol[: zt * f, : yt * f, : xt * f]
    return cut.reshape(zt, f, yt, f, xt, f).mean(axis=(1, 3, 5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dicom", required=True)
    ap.add_argument("--max-dim", type=int, default=256)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    vol, spacing = read_dicom_volume(a.dicom)
    vol = downsample(vol, a.max_dim)
    z, y, x = vol.shape
    vmin, vmax = float(vol.min()), float(vol.max())
    u8 = np.clip((vol - vmin) / max(1e-6, (vmax - vmin)) * 255.0, 0, 255).astype(np.uint8)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    raw_path = a.out + ".u8.raw"
    meta_path = a.out + ".meta.json"
    with open(raw_path, "wb") as fh:
        fh.write(u8.tobytes(order="C"))
    meta = {
        "dims": [int(x), int(y), int(z)],
        "spacing": [round(float(s), 4) for s in spacing],
        "min": round(vmin, 2),
        "max": round(vmax, 2),
    }
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
    print(f"volume: {x}x{y}x{z}, spacing {spacing}, HU [{vmin:.0f}, {vmax:.0f}]")
    print(f"raw: {raw_path} ({os.path.getsize(raw_path)} bytes)")
    print(f"meta: {meta_path}")


if __name__ == "__main__":
    main()
