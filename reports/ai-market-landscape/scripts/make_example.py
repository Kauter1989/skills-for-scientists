"""Собрать полный снимок примера: курируемый реестр + OpenRouter + Хабр.

Запуск из каталога навыка:
    python scripts/make_example.py
Создаёт examples/example-companies.json, examples/example-profile.md,
examples/example-analysis.json и examples/example-report.html.
Требует сети (OpenRouter и RSS Хабра). Только стандартная библиотека.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXAMPLES = ROOT / "examples"
TMP = EXAMPLES / ".tmp"
SNAPSHOT = "2026-11-06"


def run(args: list[str]) -> None:
    print("$", " ".join(args))
    result = subprocess.run([sys.executable, *args], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    TMP.mkdir(parents=True, exist_ok=True)
    run(["scripts/profile.py", "--file", str(EXAMPLES / "example-profile.md"), "init",
         "--name", "ИИ-рынок РФ и мир", "--force"])
    run(["scripts/profile.py", "--file", str(EXAMPLES / "example-profile.md"), "confirm"])

    run(["scripts/collect.py", "--source", "openrouter", "--as-of", SNAPSHOT,
         "--out", str(TMP / "openrouter.json")])
    run(["scripts/collect.py", "--source", "habr",
         "--query", "GigaChat Сбер", "--query", "YandexGPT", "--query", "Cotype МТС",
         "--query", "Тинькофф ИИ", "--as-of", SNAPSHOT, "--out", str(TMP / "habr.json")])

    base = json.loads((TMP / "openrouter.json").read_text(encoding="utf-8"))
    curated = json.loads((EXAMPLES / "example-companies.json").read_text(encoding="utf-8"))
    habr = json.loads((TMP / "habr.json").read_text(encoding="utf-8"))
    # Слияние идемпотентно: повторный запуск не дублирует записи, а
    # переиспользует курируемые строки из предыдущего примера.
    curated_rows = {c["id"]: c for c in curated["companies"] if not c.get("source", "").startswith("collect.py")}
    habr_rows = {c["id"]: c for c in habr["companies"]}
    merged = dict(curated_rows)
    for company in base["companies"]:
        merged[company["id"]] = company
    for company in habr["companies"]:
        merged.setdefault(company["id"], company)
    base["companies"] = list(merged.values())
    base["sources"] = curated.get("sources", []) + base.get("sources", []) + habr.get("sources", [])
    base["warnings"] = (["снимок собран из двух источников: OpenRouter (мир) и RSS Хабра (сигналы РФ)",
                         "курируемые записи РФ и мира добавлены из ручного реестра примера"]
                        + base.get("warnings", []) + habr.get("warnings", []))
    (EXAMPLES / "example-companies.json").write_text(
        json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ok: {EXAMPLES / 'example-companies.json'} — {len(base['companies'])} записей")

    run(["scripts/collect.py", "--in", str(EXAMPLES / "example-companies.json"),
         "--check-sites", "--as-of", SNAPSHOT, "--out", str(EXAMPLES / "example-companies.json")])
    run(["scripts/analyze.py", str(EXAMPLES / "example-companies.json"),
         "--profile", str(EXAMPLES / "example-profile.md"),
         "-o", str(EXAMPLES / "example-analysis.json"), "--strict"])
    run(["scripts/build_report.py", "--analysis", str(EXAMPLES / "example-analysis.json"),
         "--companies", str(EXAMPLES / "example-companies.json"),
         "-o", str(EXAMPLES / "example-report.html"), "--strict"])
    run(["scripts/check_report.py", str(EXAMPLES / "example-report.html")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())