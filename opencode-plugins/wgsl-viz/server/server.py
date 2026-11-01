#!/usr/bin/env python3
"""WGSL Playground viz-server v2: статика + scene-API для агентов и людей.

Эндпоинты:
    POST /api/scene   (алиас /api/shader)
        body: raw WGSL  или  JSON {"code", "title", "focus", "geometry"}
        geometry: null | {"kind": "cube"|"sphere"|"grid"|"custom", ...}
          sphere: radius, segments, rings
          grid:   nx, ny, size
          custom: positions[], normals[], colors[], indices[]  (flat f32/u32)
        focus: true (default) — инкрементирует focusToken: GUI-панель плагина
               сама открывает вкладку, человеку вмешиваться не нужно.
    GET  /api/state          -> полное состояние {version, focusToken,
                                geometryToken, title, code, geometry}
    GET  /api/state?meta=1   -> только {version, focusToken, geometryToken, title}

Страница index.html и GUI-панель плагина поллят meta и тянут полное состояние
только при изменении version/geometryToken. Текущая сцена дублируется
в current.json (переживает рестарт сервера).
"""
import base64
import json
import os
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(ROOT, "phong.wgsl")
CURRENT = os.path.join(ROOT, "current.json")
LOCK = threading.Lock()
STATE = {
    "version": 0,
    "focusToken": 0,
    "geometryToken": 0,
    "title": "",
    "code": "",
    "geometry": None,
}


def load_initial():
    if os.path.exists(CURRENT):
        try:
            with open(CURRENT, "r", encoding="utf-8") as f:
                saved = json.load(f)
            STATE["code"] = saved.get("code", "") or ""
            STATE["title"] = saved.get("title", "") or ""
            STATE["geometry"] = saved.get("geometry")
            return
        except (OSError, ValueError):
            pass
    if os.path.exists(SEED):
        with open(SEED, "r", encoding="utf-8") as f:
            STATE["code"] = f.read()


def persist():
    try:
        with open(CURRENT, "w", encoding="utf-8") as f:
            json.dump(
                {"code": STATE["code"], "title": STATE["title"], "geometry": STATE["geometry"]},
                f,
                ensure_ascii=False,
            )
    except OSError:
        pass


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def _json(self, obj, code=200):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/state":
            with LOCK:
                if "meta=1" in self.path:
                    self._json({
                        "version": STATE["version"],
                        "focusToken": STATE["focusToken"],
                        "geometryToken": STATE["geometryToken"],
                        "title": STATE["title"],
                    })
                else:
                    self._json(dict(STATE))
            return
        super().do_GET()

    def do_POST(self):
        path = self.path.split("?")[0]
        if path in ("/api/scene", "/api/shader"):
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n)
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()
            title, geometry, focus = "", None, True
            if ctype == "application/json":
                try:
                    obj = json.loads(raw.decode("utf-8"))
                except Exception:
                    self._json({"error": "bad json"}, 400)
                    return
                code = obj.get("code", "")
                title = obj.get("title", "") or ""
                focus = bool(obj.get("focus", True))
                geometry = obj.get("geometry") or None
            else:
                code = raw.decode("utf-8", "replace")
            if not isinstance(code, str) or not code.strip():
                self._json({"error": "empty code"}, 400)
                return
            if geometry is not None and not isinstance(geometry, dict):
                self._json({"error": "geometry must be an object"}, 400)
                return
            if isinstance(geometry, dict) and geometry.get("kind") == "image" and geometry.get("data"):
                try:
                    rawimg = base64.b64decode(geometry["data"])
                except Exception:
                    self._json({"error": "bad base64 image"}, 400)
                    return
                files_dir = os.path.join(ROOT, "files")
                os.makedirs(files_dir, exist_ok=True)
                fname = "scene_%d.png" % (STATE["geometryToken"] + 1)
                with open(os.path.join(files_dir, fname), "wb") as f:
                    f.write(rawimg)
                geometry = {"kind": "image", "url": "/files/" + fname}
            with LOCK:
                STATE["version"] += 1
                STATE["code"] = code
                STATE["title"] = title
                if geometry is not None:
                    STATE["geometry"] = geometry
                    STATE["geometryToken"] += 1
                if focus:
                    STATE["focusToken"] += 1
                persist()
                self._json({
                    "ok": True,
                    "version": STATE["version"],
                    "focusToken": STATE["focusToken"],
                    "geometryToken": STATE["geometryToken"],
                })
            return
        self._json({"error": "not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    load_initial()
    srv = ThreadingHTTPServer(("127.0.0.1", 8787), Handler)
    print("wgsl-viz server v2 on http://127.0.0.1:8787", flush=True)
    srv.serve_forever()
