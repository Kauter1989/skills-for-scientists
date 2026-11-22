#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверить analysis.json против snapshot.json.

Использование:
    python scripts/validate_analysis.py snapshot.json analysis.json
    python scripts/validate_analysis.py snapshot.json analysis.json --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

STATUSES = {"on_track", "at_risk", "blocked", "unknown"}
CONFIDENCE = {"high", "medium", "low"}
SEVERITIES = {"low", "medium", "high"}


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"error: файл не найден: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: некорректный JSON в {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"error: корень {path} должен быть объектом")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверить evidence ID в analysis.json.")
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("analysis", type=Path)
    parser.add_argument("--strict", action="store_true", help="считать отсутствие цитат ошибкой")
    args = parser.parse_args(argv)

    snapshot = load(args.snapshot)
    analysis = load(args.analysis)
    chats = {str(chat.get("id")): chat for chat in snapshot.get("chats", [])}
    ids_by_chat = {
        chat_id: {str(message.get("id")) for message in chat.get("messages", [])}
        for chat_id, chat in chats.items()
    }
    errors: list[str] = []
    warnings: list[str] = []

    projects = analysis.get("projects")
    if not isinstance(projects, list) or not projects:
        errors.append("analysis.projects должен быть непустым массивом")
        projects = []

    seen: set[str] = set()
    verified = 0
    for index, project in enumerate(projects, start=1):
        label = f"projects[{index}]"
        if not isinstance(project, dict):
            errors.append(f"{label}: должен быть объектом")
            continue
        chat_id = str(project.get("chatId") or "")
        if not chat_id:
            errors.append(f"{label}: нет chatId")
            continue
        label = f"{label} ({chat_id})"
        if chat_id not in chats:
            errors.append(f"{label}: чата нет в snapshot")
            continue
        if chat_id in seen:
            errors.append(f"{label}: chatId повторяется")
            continue
        seen.add(chat_id)

        status = project.get("status")
        if status not in STATUSES:
            errors.append(f"{label}: status={status!r}, допустимо {sorted(STATUSES)}")
        confidence = project.get("confidence", "low")
        if confidence not in CONFIDENCE:
            errors.append(f"{label}: confidence={confidence!r}, допустимо {sorted(CONFIDENCE)}")
        progress = project.get("progress") or project.get("summary")
        if not isinstance(progress, str) or not progress.strip():
            errors.append(f"{label}: progress пуст")

        blockers = project.get("blockers", [])
        if not isinstance(blockers, list):
            errors.append(f"{label}: blockers должен быть массивом")
            blockers = []
        for blocker_index, blocker in enumerate(blockers, start=1):
            blocker_label = f"{label}.blockers[{blocker_index}]"
            if not isinstance(blocker, dict):
                errors.append(f"{blocker_label}: должен быть объектом")
                continue
            if not str(blocker.get("text") or "").strip():
                errors.append(f"{blocker_label}: text пуст")
            severity = blocker.get("severity", "medium")
            if severity not in SEVERITIES:
                errors.append(f"{blocker_label}: severity={severity!r}")
            if "draft" in blocker and not isinstance(blocker["draft"], str):
                errors.append(f"{blocker_label}: draft должен быть строкой")
            evidence = blocker.get("evidenceMessageIds", [])
            if not isinstance(evidence, list) or not evidence:
                message = f"{blocker_label}: нет evidenceMessageIds"
                (errors if args.strict else warnings).append(message)
                continue
            for message_id in evidence:
                if str(message_id) not in ids_by_chat[chat_id]:
                    errors.append(f"{blocker_label}: сообщение {message_id} не найдено в чате {chat_id}")

        points = project.get("progressPoints")
        if points is not None:
            if not isinstance(points, list) or any(not isinstance(t, str) or not t.strip() for t in points):
                errors.append(f"{label}: progressPoints должен быть массивом непустых строк")

        evidence = project.get("evidenceMessageIds", [])
        if not isinstance(evidence, list) or not evidence:
            message = f"{label}: нет evidenceMessageIds"
            (errors if args.strict else warnings).append(message)
            continue
        found_all = True
        for message_id in evidence:
            if str(message_id) not in ids_by_chat[chat_id]:
                found_all = False
                errors.append(f"{label}: сообщение {message_id} не найдено в чате {chat_id}")
        if found_all:
            verified += 1

    cross = analysis.get("crossProject")
    if cross is not None:
        if not isinstance(cross, dict):
            errors.append("crossProject должен быть объектом")
        else:
            if "summary" in cross and not isinstance(cross["summary"], str):
                errors.append("crossProject.summary должен быть строкой")
            for key in ("highlights", "external"):
                items = cross.get(key)
                if items is None:
                    continue
                if not isinstance(items, list):
                    errors.append(f"crossProject.{key} должен быть массивом")
                    continue
                for i, item in enumerate(items, start=1):
                    if not isinstance(item, dict) or not str(item.get("text") or "").strip():
                        errors.append(f"crossProject.{key}[{i}]: нужен объект с непустым text")
            risks = cross.get("risks")
            if risks is not None:
                if not isinstance(risks, list):
                    errors.append("crossProject.risks должен быть массивом")
                else:
                    for i, item in enumerate(risks, start=1):
                        if not isinstance(item, dict) or not str(item.get("text") or "").strip():
                            errors.append(f"crossProject.risks[{i}]: нужен объект с непустым text")
                        elif item.get("severity", "medium") not in SEVERITIES:
                            errors.append(f"crossProject.risks[{i}]: severity={item.get('severity')!r}")
            deadlines = cross.get("deadlines")
            if deadlines is not None:
                if not isinstance(deadlines, list):
                    errors.append("crossProject.deadlines должен быть массивом")
                else:
                    for i, item in enumerate(deadlines, start=1):
                        if not isinstance(item, dict) or not str(item.get("what") or "").strip():
                            errors.append(f"crossProject.deadlines[{i}]: нужен объект с непустым what")
                            continue
                        date = str(item.get("date") or "")
                        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                            errors.append(f"crossProject.deadlines[{i}]: date должен быть YYYY-MM-DD")

    missing = set(chats) - seen
    if missing:
        warnings.append(
            "чаты без анализа: " + ", ".join(f"{chat_id} ({chats[chat_id].get('name')})" for chat_id in sorted(missing))
        )

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(f"ok: {len(projects)} проектов, {verified} с подтверждёнными цитатами")
    if warnings:
        print(f"warnings: {len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())