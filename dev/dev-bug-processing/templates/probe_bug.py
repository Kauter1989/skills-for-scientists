#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Измерить детерминированность воспроизведения дефекта.

Запускает команду N раз и классифицирует результат:
    deterministic-fail, nondeterministic-fail, deterministic-pass, flaky, error

Использование:
    python probe_bug.py --runs 3 --out probe.json -- python -m pytest tests/test_bug.py
    python probe_bug.py --runs 5 --require deterministic-fail -- <команда>

Только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def normalize(text: str, cwd: Path | None = None) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if cwd is not None:
        text = text.replace(str(cwd), ".")
        text = text.replace(str(cwd).replace("\\", "/"), ".")
    text = re.sub(r"\bRan (\d+) tests? in [0-9.]+s", r"Ran \1 tests in <time>s", text)
    text = re.sub(
        r"\b[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9:.]+(?:Z|[+-][0-9:]+)?",
        "<timestamp>",
        text,
    )
    text = re.sub(r"\b[0-9]+(?:\.[0-9]+)?s\b", "<duration>", text)
    return text


def tail(text: str, cwd: Path | None = None, limit: int = 4000) -> str:
    text = normalize(text, cwd)
    return text[-limit:]


def digest(returncode: int, stdout: str, stderr: str, cwd: Path) -> str:
    payload = f"{returncode}\n{normalize(stdout, cwd)}\n{normalize(stderr, cwd)}".encode(
        "utf-8", "replace"
    )
    return hashlib.sha256(payload).hexdigest()


def run_once(command: list[str], cwd: Path, timeout: float) -> dict:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "returncode": completed.returncode,
            "timed_out": False,
            "duration_ms": duration_ms,
            "stdout_tail": tail(completed.stdout, cwd),
            "stderr_tail": tail(completed.stderr, cwd),
            "output_sha256": digest(completed.returncode, completed.stdout, completed.stderr, cwd),
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        return {
            "returncode": 124,
            "timed_out": True,
            "duration_ms": duration_ms,
            "stdout_tail": tail(stdout, cwd),
            "stderr_tail": tail(stderr, cwd),
            "output_sha256": digest(124, stdout, stderr, cwd),
        }
    except FileNotFoundError as exc:
        return {
            "returncode": 127,
            "timed_out": False,
            "duration_ms": 0,
            "stdout_tail": "",
            "stderr_tail": f"command not found: {exc}",
            "output_sha256": "",
            "error": "command-not-found",
        }


def classify(results: list[dict]) -> tuple[str, int, int, bool]:
    failed = sum(1 for item in results if item.get("returncode", 0) != 0)
    passed = len(results) - failed
    if any(item.get("error") == "command-not-found" for item in results):
        return "error", failed, passed, False
    hashes = {item.get("output_sha256", "") for item in results}
    identical = len(hashes) == 1
    if failed == 0:
        return "deterministic-pass", failed, passed, identical
    if passed == 0:
        if identical:
            return "deterministic-fail", failed, passed, True
        return "nondeterministic-fail", failed, passed, False
    return "flaky", failed, passed, identical


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Прогоны команды и классификация воспроизведения")
    parser.add_argument("--runs", type=int, default=3, help="число прогонов, по умолчанию 3")
    parser.add_argument("--retries", type=int, default=0, help="дополнительные прогоны при ошибке")
    parser.add_argument("--timeout", type=float, default=300.0, help="таймаут одного прогона, секунды")
    parser.add_argument("--cwd", type=Path, default=Path("."), help="рабочий каталог")
    parser.add_argument("--out", type=Path, default=None, help="куда записать JSON")
    parser.add_argument(
        "--require",
        choices=["deterministic-fail", "deterministic-pass", "flaky"],
        default=None,
        help="ожидаемая классификация; иначе exit 1",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="команда после --")
    args = parser.parse_args(argv)

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("нужна команда после --")
    if args.runs < 1:
        parser.error("--runs должен быть >= 1")

    cwd_display = str(args.cwd)
    cwd = args.cwd.resolve()
    total = args.runs + max(0, args.retries)
    results = [run_once(command, cwd, args.timeout) for _ in range(total)]
    classification, failed, passed, identical = classify(results)

    data = {
        "version": 1,
        "created": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "command": command,
        "cwd": cwd_display,
        "runs": total,
        "timeout_seconds": args.timeout,
        "classification": classification,
        "failed": failed,
        "passed": passed,
        "identical_output": identical,
        "results": results,
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{classification}: {failed} failed / {passed} passed / {total} runs")
        print(f"ok: {args.out}")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))

    if args.require and classification != args.require:
        print(
            f"error: ожидалось {args.require}, получено {classification}",
            file=sys.stderr,
        )
        return 1
    return 0 if classification != "error" else 2


if __name__ == "__main__":
    raise SystemExit(main())